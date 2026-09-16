"""Fail closed before publishing Help when the embedded Support surface is unavailable."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from html.parser import HTMLParser


ORIGIN = "https://support.dealrocket.ru"
TIMEOUT = 10


class WidgetAssets(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.has_root = False
        self.scripts: list[str] = []
        self.styles: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "div" and attributes.get("id") == "root":
            self.has_root = True
        if tag == "script" and attributes.get("type") == "module":
            self.scripts.append(attributes.get("src") or "")
        if tag == "link" and "stylesheet" in (attributes.get("rel") or "").split():
            self.styles.append(attributes.get("href") or "")


def widget_assets(widget: bytes) -> list[tuple[str, str]]:
    parser = WidgetAssets()
    parser.feed(widget.decode("utf-8"))
    if "Помощник DealRocket".encode() not in widget or not parser.has_root:
        raise RuntimeError("Widget HTML is missing the Assistant application")
    if not parser.scripts or not parser.styles:
        raise RuntimeError("Widget HTML is missing the Assistant assets")
    assets = [(path, "js") for path in parser.scripts] + [(path, "css") for path in parser.styles]
    for path, extension in assets:
        if not re.fullmatch(r"/assistant-assets/assets/[A-Za-z0-9_.-]+\." + extension, path):
            raise RuntimeError("Widget asset is outside the reviewed Assistant asset path")
    return assets


def read(opener: urllib.request.OpenerDirector, path: str) -> tuple[bytes, object]:
    response = opener.open(ORIGIN + path, timeout=TIMEOUT)
    if response.status != 200:
        raise RuntimeError(f"{path} returned HTTP {response.status}")
    return response.read(), response.headers


def main() -> None:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    widget, headers = read(opener, "/widget")
    policy = headers.get("Content-Security-Policy", "")
    assets = widget_assets(widget)
    match = re.search(r"(?:^|;)\s*frame-ancestors\s+([^;]+)", policy, re.IGNORECASE)
    ancestors = set(match.group(1).split()) if match else set()
    if ancestors != {"'self'", "https://help.dealrocket.ru"}:
        raise RuntimeError("Widget CSP does not allow only the Help parent")
    for path, extension in assets:
        body, asset_headers = read(opener, path)
        content_type = asset_headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        expected_types = {"text/javascript", "application/javascript"} if extension == "js" else {"text/css"}
        if not body.strip() or content_type not in expected_types:
            raise RuntimeError(f"Widget asset {path} is empty or has an unexpected content type")

    request = urllib.request.Request(
        ORIGIN + "/widget/api/session",
        data=b"{}",
        headers={"Content-Type": "application/json", "Origin": ORIGIN},
        method="POST",
    )
    response = opener.open(request, timeout=TIMEOUT)
    payload = json.loads(response.read())
    cookie = response.headers.get("Set-Cookie", "")
    if response.status != 200 or payload.get("created") is not True:
        raise RuntimeError("Widget session was not created")
    for marker in ("dr_support_widget_session=", "Secure", "HttpOnly", "SameSite=strict", "Path=/widget/api"):
        if marker not in cookie:
            raise RuntimeError("Widget session cookie is incomplete")
    restored, _ = read(opener, "/widget/api/session")
    if json.loads(restored).get("messages") != []:
        raise RuntimeError("New widget session is not empty")
    print("Support widget is ready for Help publication")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
        raise SystemExit(f"Support widget preflight failed: {exc}") from exc
