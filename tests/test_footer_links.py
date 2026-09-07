from __future__ import annotations

import copy
import importlib.metadata
import json
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

import yaml
from mkdocs.commands.build import build
from mkdocs.config import load_config

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from footer_links import load_client_base_links  # noqa: E402


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href", "").startswith("https://dealrocket.ru/baza_"):
            self.links.append((attributes["href"], attributes))


class FooterLinksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_client_base_links(ROOT / "data" / "client-base-links.yml")
        cls.urls = [link["url"] for group in cls.data["groups"] for link in group["links"]]

    def test_material_version_matches_footer_override(self) -> None:
        self.assertEqual(importlib.metadata.version("mkdocs-material"), "9.7.7")
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("mkdocs-material==9.7.7", requirements)

    def test_captured_inventory_is_complete_and_unique(self) -> None:
        self.assertEqual(self.data["source_url"], "https://dealrocket.ru/")
        self.assertEqual(self.data["captured_at"], "2026-09-07")
        self.assertEqual(len(self.urls), self.data["expected_unique_links"])
        self.assertEqual(len(self.urls), len(set(self.urls)))

    def test_invalid_inventory_is_rejected(self) -> None:
        cases: dict[str, dict] = {}

        wrong_groups = copy.deepcopy(self.data)
        wrong_groups["groups"][0]["id"] = "wrong"
        cases["wrong groups"] = wrong_groups

        malformed_group = copy.deepcopy(self.data)
        malformed_group["groups"][0] = "wrong"
        cases["malformed group"] = malformed_group

        malformed_link = copy.deepcopy(self.data)
        malformed_link["groups"][0]["links"][0] = "wrong"
        cases["malformed link"] = malformed_link

        wrong_host = copy.deepcopy(self.data)
        wrong_host["groups"][0]["links"][0]["url"] = "https://example.com/baza_test/"
        cases["wrong host"] = wrong_host

        invalid_path = copy.deepcopy(self.data)
        invalid_path["groups"][0]["links"][0]["url"] = "https://dealrocket.ru/baza_test/extra"
        cases["invalid path"] = invalid_path

        query = copy.deepcopy(self.data)
        query["groups"][0]["links"][0]["url"] += "?source=help"
        cases["query"] = query

        duplicate = copy.deepcopy(self.data)
        duplicate["groups"][0]["links"][1]["url"] = duplicate["groups"][0]["links"][0]["url"]
        cases["duplicate"] = duplicate

        count_mismatch = copy.deepcopy(self.data)
        count_mismatch["expected_unique_links"] += 1
        cases["count mismatch"] = count_mismatch

        for name, data in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary_directory:
                path = Path(temporary_directory) / "links.yml"
                path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_client_base_links(path)

    def test_footer_uses_native_disclosure_and_safe_external_links(self) -> None:
        partial = (ROOT / "overrides" / "partials" / "client-base-links.html").read_text(encoding="utf-8")
        footer = (ROOT / "overrides" / "partials" / "footer.html").read_text(encoding="utf-8")
        self.assertIn('<details class="dr-client-bases__details">', partial)
        self.assertIn('<summary class="dr-client-bases__summary">', partial)
        self.assertIn('target="_blank" rel="noopener"', partial)
        self.assertNotIn("nofollow", partial)
        self.assertLess(footer.index('partials/client-base-links.html'), footer.index('class="md-footer-meta'))

    def test_footer_links_are_not_in_navigation_or_assistant_corpus(self) -> None:
        config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        corpus = (ROOT / "docs" / "assets" / "help-corpus.v1.json").read_text(encoding="utf-8")
        self.assertNotIn("dealrocket.ru/baza_", config)
        self.assertNotIn("dealrocket.ru/baza_", corpus)

    def test_rendered_footer_is_present_on_public_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site_dir = Path(temporary_directory) / "site"
            config = load_config(config_file=str(ROOT / "mkdocs.yml"), site_dir=str(site_dir), strict=True)
            build(config)

            surfaces = (
                site_dir / "index.html",
                site_dir / "start" / "preparation" / "index.html",
                site_dir / "404.html",
            )
            for surface in surfaces:
                with self.subTest(surface=surface):
                    html = surface.read_text(encoding="utf-8")
                    parser = LinkParser()
                    parser.feed(html)
                    self.assertEqual([url for url, _ in parser.links], self.urls)
                    self.assertTrue(all(attrs.get("target") == "_blank" for _, attrs in parser.links))
                    self.assertTrue(all(attrs.get("rel") == "noopener" for _, attrs in parser.links))
                    self.assertIn('<details class="dr-client-bases__details">', html)
                    self.assertNotIn('<details class="dr-client-bases__details" open', html)

            search_index = json.loads((site_dir / "search" / "search_index.json").read_text(encoding="utf-8"))
            serialized_search = json.dumps(search_index, ensure_ascii=False)
            self.assertNotIn("dealrocket.ru/baza_", serialized_search)
            self.assertNotIn(self.data["groups"][0]["links"][0]["title"], serialized_search)
            self.assertNotIn("Готовые подборки компаний и контактов", serialized_search)


if __name__ == "__main__":
    unittest.main()
