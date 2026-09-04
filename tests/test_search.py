from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_search import (  # noqa: E402
    REQUIRED_DEEP_LINKS,
    SMOKE_QUERIES,
    check_deep_links,
    contains_token,
    normalize,
    run_smoke,
)


class SearchSmokeTest(unittest.TestCase):
    def test_normalize_handles_russian_yo_and_spacing(self) -> None:
        self.assertEqual(normalize("  ЗВЁЗДОЧКИ\nВ ФАЙЛЕ "), " звездочки в файле ")

    def test_short_tokens_require_word_boundaries(self) -> None:
        self.assertTrue(contains_token("где взять акт за период", "акт"))
        self.assertFalse(contains_token("повторный контакт", "акт"))
        self.assertTrue(contains_token("почему 0 контактов", "0"))
        self.assertFalse(contains_token("доступно 100 контактов", "0"))

    def test_smoke_uses_rendered_search_documents(self) -> None:
        documents = [
            {"location": location, "title": query, "text": " ".join(tokens)}
            for query, (location, tokens) in SMOKE_QUERIES.items()
        ]
        payload = {"docs": documents}
        with tempfile.TemporaryDirectory() as temporary_directory:
            index_path = Path(temporary_directory) / "search_index.json"
            index_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            run_smoke(index_path)

    def test_smoke_fails_when_a_query_is_absent(self) -> None:
        payload = {
            "docs": [
                {"location": location, "title": query, "text": " ".join(tokens)}
                for query, (location, tokens) in list(SMOKE_QUERIES.items())[1:]
            ]
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            index_path = Path(temporary_directory) / "search_index.json"
            index_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                run_smoke(index_path)

    def test_smoke_rejects_a_match_on_the_wrong_page(self) -> None:
        payload = {
            "docs": [
                {"location": "/", "title": query, "text": " ".join(tokens)}
                for query, (_, tokens) in SMOKE_QUERIES.items()
            ]
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            index_path = Path(temporary_directory) / "search_index.json"
            index_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                run_smoke(index_path)

    def test_deep_link_contract_checks_built_html(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site_dir = Path(temporary_directory)
            for relative_path, anchors in REQUIRED_DEEP_LINKS.items():
                html_path = site_dir / relative_path
                html_path.parent.mkdir(parents=True, exist_ok=True)
                html_path.write_text(
                    "".join(f'<h2 id="{anchor}">{anchor}</h2>' for anchor in anchors),
                    encoding="utf-8",
                )
            check_deep_links(site_dir)


if __name__ == "__main__":
    unittest.main()
