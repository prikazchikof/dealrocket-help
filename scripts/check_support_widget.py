"""Fail closed before publishing Help when the embedded Support surface is unavailable."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from http.cookiejar import CookieJar


ORIGIN = "https://support.dealrocket.ru"
TIMEOUT = 10


def read(opener: urllib.request.OpenerDirector, path: str) -> tuple[bytes, object]:
    response = opener.open(ORIGIN + path, timeout=TIMEOUT)
    if response.status != 200:
        raise RuntimeError(f"{path} returned HTTP {response.status}")
    return response.read(), response.headers


def main() -> None:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    widget, headers = read(opener, "/widget")
    policy = headers.get("Content-Security-Policy", "")
    if "Помощник DealRocket".encode() not in widget or b"/assets/widget.js" not in widget:
        raise RuntimeError("Widget HTML is missing the reviewed assets")
    match = re.search(r"(?:^|;)\s*frame-ancestors\s+([^;]+)", policy, re.IGNORECASE)
    ancestors = set(match.group(1).split()) if match else set()
    if ancestors != {"'self'", "https://help.dealrocket.ru"}:
        raise RuntimeError("Widget CSP does not allow only the Help parent")
    for path in ("/assets/chat-client.js", "/assets/widget.js", "/assets/widget.css"):
        read(opener, path)

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
