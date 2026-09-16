from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_support_widget import main, widget_assets


HTML = '''<title>Помощник DealRocket</title><div id="root"></div>
<script type="module" src="/assistant-assets/assets/production-Ab12.js"></script>
<link rel="stylesheet" href="/assistant-assets/assets/production-Cd34.css">'''
CSP = {"Content-Security-Policy": "frame-ancestors 'self' https://help.dealrocket.ru"}
COOKIE = "dr_support_widget_session=test; Secure; HttpOnly; SameSite=strict; Path=/widget/api"


class SupportPreflightTest(unittest.TestCase):
    def test_reads_hashed_assets_from_current_widget(self) -> None:
        self.assertEqual(widget_assets(HTML.encode()), [
            ("/assistant-assets/assets/production-Ab12.js", "js"),
            ("/assistant-assets/assets/production-Cd34.css", "css"),
        ])
        dotted = HTML.replace("production-Ab12.js", "production.foo-Ab12.js")
        self.assertEqual(widget_assets(dotted.encode())[0][0],
                         "/assistant-assets/assets/production.foo-Ab12.js")

    def test_rejects_missing_application_and_assets(self) -> None:
        for html in (
            HTML.replace("Помощник DealRocket", "Other application"),
            HTML.replace('<div id="root"></div>', ""),
            HTML.replace('type="module"', 'type="text/plain"'),
            HTML.replace('rel="stylesheet"', 'rel="icon"'),
        ):
            with self.subTest(html=html), self.assertRaises(RuntimeError):
                widget_assets(html.encode())

    def test_rejects_external_and_unexpected_asset_paths(self) -> None:
        for path in (
            "https://external.example/app.js", "//external.example/app.js",
            "/assets/widget.js", "/assistant-assets/assets/../app.js",
        ):
            with self.subTest(path=path), self.assertRaises(RuntimeError):
                widget_assets(HTML.replace("/assistant-assets/assets/production-Ab12.js", path).encode())

    def test_rejects_html_fallback_and_empty_assets(self) -> None:
        for body, headers in ((HTML.encode(), {"Content-Type": "text/html"}),
                              (b"", {"Content-Type": "text/javascript"})):
            with self.subTest(headers=headers), patch("check_support_widget.read", side_effect=[
                (HTML.encode(), CSP), (body, headers),
            ]), self.assertRaisesRegex(RuntimeError, "empty or has an unexpected content type"):
                main()

    def run_session_preflight(self, policy=CSP, cookie=COOKIE, created=b'{"created": true}',
                              restored=b'{"messages": []}') -> list[str]:
        response = Mock(status=200, headers={"Set-Cookie": cookie})
        response.read.return_value = created
        opener = Mock()
        opener.open.return_value = response
        with patch("check_support_widget.urllib.request.build_opener", return_value=opener), \
             patch("check_support_widget.read", side_effect=[
                 (HTML.encode(), policy),
                 (b"export {};", {"Content-Type": "text/javascript; charset=utf-8"}),
                 (b"body {}", {"Content-Type": "text/css"}),
                 (restored, {}),
             ]) as read_mock:
            main()
            request = opener.open.call_args.args[0]
            self.assertEqual(request.full_url, "https://support.dealrocket.ru/widget/api/session")
            self.assertEqual(request.method, "POST")
            return [call.args[1] for call in read_mock.call_args_list]

    def test_full_preflight_checks_assets_and_restores_session(self) -> None:
        self.assertEqual(self.run_session_preflight(), [
            "/widget", "/assistant-assets/assets/production-Ab12.js",
            "/assistant-assets/assets/production-Cd34.css", "/widget/api/session",
        ])

    def test_session_and_csp_fail_closed(self) -> None:
        cases = [
            ({"policy": {"Content-Security-Policy": "frame-ancestors *"}}, "Widget CSP"),
            ({"created": b'{"created": false}'}, "session was not created"),
            ({"restored": b'{"messages": ["previous session"]}'}, "session is not empty"),
        ]
        for marker in ("dr_support_widget_session=", "Secure", "HttpOnly", "SameSite=strict", "Path=/widget/api"):
            cases.append(({"cookie": COOKIE.replace(marker, "")}, "cookie is incomplete"))
        for kwargs, message in cases:
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(RuntimeError, message):
                self.run_session_preflight(**kwargs)


if __name__ == "__main__":
    unittest.main()
