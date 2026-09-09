from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mkdocs.commands.build import build
from mkdocs.config import load_config


ROOT = Path(__file__).resolve().parents[1]


class SupportWidgetTest(unittest.TestCase):
    def test_launcher_is_lazy_persistent_and_origin_bounded(self) -> None:
        script = (ROOT / "docs/assets/javascripts/site.js").read_text(encoding="utf-8")
        self.assertIn('dataset.supportOrigin || "https://support.dealrocket.ru"', script)
        self.assertIn('candidate.origin === "https://support.dealrocket.ru"', script)
        self.assertIn('candidate.hostname === "support.dealrocket.lvh.me"', script)
        self.assertIn('aria-label="Открыть чат поддержки"', script)
        self.assertIn('var source = SUPPORT_ORIGIN + "/widget?page="', script)
        self.assertIn("iframe.src = source", script)
        self.assertLess(script.index("function createFrame()"), script.index('var source = SUPPORT_ORIGIN + "/widget?page="'))
        self.assertIn("document.body.appendChild(root)", script)
        self.assertIn("sessionStorage.setItem(SUPPORT_STATE_KEY", script)
        self.assertIn("event.origin !== SUPPORT_ORIGIN", script)
        self.assertIn("event.source !== iframe.contentWindow", script)
        self.assertIn('event.data.type === "dr-support-ready"', script)
        self.assertIn('event.data.type === "dr-support-close"', script)
        self.assertIn("document.activeElement === iframe", script)
        self.assertNotIn("message: message", script)
        self.assertNotIn("document.body.innerText", script)

    def test_context_mapping_uses_only_existing_api_categories(self) -> None:
        script = (ROOT / "docs/assets/javascripts/site.js").read_text(encoding="utf-8")
        for path, page in (
            ('pathname.indexOf("/billing/") === 0', 'return "billing"'),
            ('pathname === "/results/lists/"', 'return "lists"'),
            ('pathname === "/results/export/"', 'return "export"'),
            ('pathname === "/results/contacts/"', 'return "contacts"'),
            ('pathname.indexOf("/search/") === 0', 'return "search"'),
        ):
            self.assertIn(path, script)
            self.assertIn(page, script)
        for forbidden in ("location.href", "document.title", "textContent: document"):
            self.assertNotIn(forbidden, script)

    def test_responsive_panel_does_not_enter_page_flow(self) -> None:
        styles = (ROOT / "docs/assets/stylesheets/extra.css").read_text(encoding="utf-8")
        self.assertIn(".dr-support-widget__launcher", styles)
        self.assertIn("position: fixed", styles)
        self.assertIn("width: 48px", styles)
        self.assertIn("border-radius: 10px", styles)
        self.assertIn("width: min(360px", styles)
        self.assertIn("height: min(540px", styles)
        self.assertIn("@media screen and (max-width: 720px)", styles)
        self.assertIn("height: 100dvh", styles)
        self.assertIn("body.dr-support-widget-open", styles)

    def test_build_includes_launcher_assets_on_home_article_and_404(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site_dir = Path(temporary_directory) / "site"
            config = load_config(config_file=str(ROOT / "mkdocs.yml"), site_dir=str(site_dir), strict=True)
            build(config)
            for path in (
                site_dir / "index.html",
                site_dir / "results" / "export" / "index.html",
                site_dir / "404.html",
            ):
                html = path.read_text(encoding="utf-8")
                self.assertIn("assets/javascripts/site", html)
            self.assertTrue((site_dir / "assets" / "javascripts" / "site.js").is_file())

    def test_pages_publish_is_gated_by_support_preflight(self) -> None:
        workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        probe = "python scripts/check_support_widget.py"
        self.assertIn(probe, workflow)
        self.assertLess(workflow.index(probe), workflow.index("actions/upload-pages-artifact"))

        preflight = (ROOT / "scripts/check_support_widget.py").read_text(encoding="utf-8")
        self.assertIn("ancestors != {\"'self'\", \"https://help.dealrocket.ru\"}", preflight)


if __name__ == "__main__":
    unittest.main()
