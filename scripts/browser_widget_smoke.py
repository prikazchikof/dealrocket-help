"""Cross-origin Help → Support widget smoke with a fake local provider."""

from __future__ import annotations

import argparse
import functools
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import uvicorn
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
SUPPORT = WORKSPACE / "dealrocket-support"
sys.path.insert(0, str(SUPPORT))

from support.app import create_app  # noqa: E402
from support.corpus import Corpus  # noqa: E402
from support.provider import ModelAnswer  # noqa: E402


def free_port() -> int:
    with socket.socket() as stream:
        stream.bind(("127.0.0.1", 0))
        return stream.getsockname()[1]


class FakeProvider:
    api_key = "test-only"

    async def answer(self, question, history, chunks, user, page):
        return ModelAnswer(
            answer="Выполните действие по шагам и проверьте результат.",
            source_ids=[chunks[0].id],
            handoff=False,
        )


class AliasApp:
    def __init__(self, app, support_port: int, help_origin: str):
        self.app = app
        self.support_origin = f"http://support.dealrocket.lvh.me:{support_port}"
        self.internal_origin = f"http://127.0.0.1:{support_port}"
        self.help_origin = help_origin

    async def __call__(self, scope, receive, send):
        rewritten = dict(scope)
        headers = []
        for name, value in scope.get("headers", []):
            if name == b"host":
                value = self.internal_origin.removeprefix("http://").encode()
            elif name == b"origin" and value.decode() == self.support_origin:
                value = self.internal_origin.encode()
            headers.append((name, value))
        rewritten["headers"] = headers

        async def rewrite_response(message):
            if message["type"] == "http.response.start":
                response_headers = []
                for name, value in message.get("headers", []):
                    if name == b"content-security-policy":
                        value = value.replace(b"https://help.dealrocket.ru", self.help_origin.encode())
                    response_headers.append((name, value))
                message = {**message, "headers": response_headers}
            await send(message)

        await self.app(rewritten, receive, rewrite_response)


def wait_for_port(port: int) -> None:
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"Port {port} did not open")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chromium", "firefox", "webkit"), default="chromium")
    args = parser.parse_args()
    help_port = free_port()
    support_port = free_port()
    help_origin = f"http://help.dealrocket.lvh.me:{help_port}"
    support_origin = f"http://support.dealrocket.lvh.me:{support_port}"

    with tempfile.TemporaryDirectory() as temporary_directory:
        site = Path(temporary_directory) / "site"
        help_python = ROOT / ".venv" / "Scripts" / "python.exe"
        subprocess.run(
            [str(help_python), "-m", "mkdocs", "build", "--strict", "--site-dir", str(site)],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        marker = f'<html data-support-origin="{support_origin}"'
        for html in site.rglob("*.html"):
            content = html.read_text(encoding="utf-8")
            html.write_text(content.replace("<html", marker, 1), encoding="utf-8")

        handler = functools.partial(SimpleHTTPRequestHandler, directory=str(site))
        help_server = ThreadingHTTPServer(("127.0.0.1", help_port), handler)
        help_thread = threading.Thread(target=help_server.serve_forever, daemon=True)
        help_thread.start()

        corpus = Corpus.read(SUPPORT / ".runtime" / "help-corpus.v1.json")
        app = AliasApp(create_app(corpus, FakeProvider(), port=support_port), support_port, help_origin)
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=support_port, log_level="error"))
        support_thread = threading.Thread(target=server.run, daemon=True)
        support_thread.start()
        wait_for_port(support_port)

        try:
            with sync_playwright() as playwright:
                browser = getattr(playwright, args.browser).launch()
                page = browser.new_page(viewport={"width": 1366, "height": 768})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(help_origin + "/")
                launcher = page.get_by_role("button", name="Открыть чат поддержки")
                expect(launcher).to_be_visible()
                expect(page.locator(".dr-support-widget__frame")).to_have_count(0)
                consent = page.locator(".md-consent__inner")
                if consent.is_visible():
                    launcher_box = launcher.bounding_box()
                    consent_box = consent.bounding_box()
                    assert launcher_box["y"] + launcher_box["height"] <= consent_box["y"] - 10

                launcher.click()
                frame = page.frame_locator(".dr-support-widget__frame")
                expect(frame.get_by_role("heading", name="Помощник DealRocket")).to_be_visible()
                expect(frame.get_by_role("button", name="Начать новый разговор")).to_be_enabled()
                cookies = page.context.cookies()
                assert any(cookie["name"] == "dr_support_widget_session" for cookie in cookies)
                assert not any(cookie["name"] == "dr_support_session" for cookie in cookies)
                frame.get_by_role("button", name="С чего начать работу с базой?").click()
                frame.get_by_role("textbox", name="Ваш вопрос о DealRocket").press("Enter")
                expect(frame.locator(".message.assistant")).to_have_count(1)
                expect(frame.get_by_text("Подробнее в справке:")).to_be_visible()

                page.get_by_role("link", name="Тарификация", exact=True).click()
                page.wait_for_url("**/billing/tarification/")
                expect(page.locator(".dr-support-widget__frame")).to_have_count(1)
                expect(frame.locator(".message.assistant")).to_have_count(1)
                expect(frame.locator(".suggestions button").first).to_have_text("Что считается контактом?")

                page.reload()
                frame = page.frame_locator(".dr-support-widget__frame")
                expect(frame.locator(".message.assistant")).to_have_count(1)
                expect(page.locator(".dr-support-widget__panel")).to_be_visible()
                frame.get_by_role("button", name="Закрыть чат").click()
                expect(page.locator(".dr-support-widget__panel")).to_be_hidden()
                expect(launcher).to_be_focused()

                page.set_viewport_size({"width": 390, "height": 844})
                launcher.click()
                panel_box = page.locator(".dr-support-widget__panel").bounding_box()
                assert abs(panel_box["x"]) < 1 and abs(panel_box["y"]) < 1, panel_box
                assert abs(panel_box["width"] - 390) < 1 and abs(panel_box["height"] - 844) < 1, panel_box
                widget_height = frame.locator("html").evaluate(
                    "el => parseFloat(getComputedStyle(el).getPropertyValue('--widget-height'))"
                )
                assert abs(widget_height - 844) < 1
                frame.get_by_role("heading", name="Помощник DealRocket").press("Escape")
                expect(page.locator(".dr-support-widget__panel")).to_be_hidden()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                assert not errors, errors
                browser.close()
        finally:
            server.should_exit = True
            help_server.shutdown()
            support_thread.join(timeout=10)
            help_thread.join(timeout=10)

    print(f"Help widget browser smoke passed: {args.browser}")


if __name__ == "__main__":
    main()
