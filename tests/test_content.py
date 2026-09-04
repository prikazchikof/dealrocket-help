from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from content import Article, build_corpus, collect_articles, validate_content_safety  # noqa: E402
from validate_content import load_site_url  # noqa: E402


EXPECTED_ARTICLES = {
    "index.md": "home",
    "start/index.md": "getting-started",
    "search/index.md": "finding-clients",
    "search/company-list/index.md": "search-company-list",
    "search/large-business/index.md": "search-large-business",
    "search/refine/index.md": "search-refine",
    "contacts/index.md": "contacts-and-lists",
    "export/index.md": "exporting-data",
    "data-quality/index.md": "data-and-freshness",
    "billing/index.md": "plans-and-balance",
    "outreach/index.md": "using-exported-data",
}

REQUIRED_MARKDOWN_ANCHORS = {
    "export/index.md": {"all-or-selected", "stars", "empty-fields", "over-10000"},
    "billing/index.md": {"invoicebox", "documents", "refund", "cancellation"},
    "search/company-list/index.md": {"enrichment"},
}


class ContentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.articles = collect_articles(ROOT / "docs")
        cls.site_url = load_site_url(ROOT / "mkdocs.yml")
        cls.corpus = build_corpus(cls.articles, ROOT / "docs", cls.site_url)

    def test_corpus_has_required_topics(self) -> None:
        haystack = " ".join(
            f"{document['title']} {document['description']} {' '.join(document['keywords'])} {document['markdown']}"
            for document in self.corpus["articles"]
        ).lower()
        for topic in (
            "свой список компаний",
            "крупный бизнес",
            "нерелевантные компании",
            "экспорт",
            "закрывающие документы",
            "инвойсбокс",
            "noisebox",
            "вернуть последний платёж",
        ):
            self.assertIn(topic, haystack)

    def test_urls_and_hashes_are_stable_shape(self) -> None:
        for document in self.corpus["articles"]:
            self.assertTrue(document["url"].startswith(self.site_url))
            self.assertRegex(document["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(document["status"], "published")
        self.assertEqual(self.corpus["schema_version"], 1)

    def test_home_corpus_url_is_the_canonical_root(self) -> None:
        home = next(document for document in self.corpus["articles"] if document["id"] == "home")
        self.assertEqual(home["url"], self.site_url)

    def test_exact_public_article_set(self) -> None:
        actual = {
            article.path.relative_to(ROOT / "docs").as_posix(): article.metadata["id"]
            for article in self.articles
        }
        self.assertEqual(actual, EXPECTED_ARTICLES)

    def test_removed_routes_are_not_sources(self) -> None:
        for removed_path in ("enrichment/index.md", "data/index.md", "help/index.md"):
            self.assertFalse((ROOT / "docs" / removed_path).exists())

    def test_scenario_guides_have_explicit_anchors(self) -> None:
        for article in self.articles:
            path = article.path.relative_to(ROOT / "docs").as_posix()
            if path == "index.md":
                continue
            self.assertRegex(article.markdown, r"\{\s*#[a-z0-9-]+\s*\}")

    def test_frontend_deep_link_contract_is_present(self) -> None:
        articles_by_path = {
            article.path.relative_to(ROOT / "docs").as_posix(): article.markdown
            for article in self.articles
        }
        for path, anchors in REQUIRED_MARKDOWN_ANCHORS.items():
            for anchor in anchors:
                self.assertIn(f"{{ #{anchor} }}", articles_by_path[path], f"{path}#{anchor}")

    def test_guides_use_visible_search_aliases(self) -> None:
        for article in self.articles:
            if article.metadata["id"] == "home":
                continue
            self.assertIn("Также ищут:", article.markdown)

    def test_contextual_faqs_are_kept_with_their_guides(self) -> None:
        faq_ids = {
            "finding-clients",
            "search-company-list",
            "search-large-business",
            "search-refine",
            "contacts-and-lists",
            "exporting-data",
            "data-and-freshness",
            "plans-and-balance",
            "using-exported-data",
        }
        for article in self.articles:
            if article.metadata["id"] in faq_ids:
                self.assertIn("## Частые вопросы", article.markdown)

    def test_scenario_guides_are_long_form(self) -> None:
        for article in self.articles:
            if article.metadata["id"] in {"home", "getting-started"}:
                continue
            words = article.markdown.split()
            self.assertGreaterEqual(len(words), 500, article.metadata["id"])

    def test_images_have_alt_text(self) -> None:
        for article in self.articles:
            for line in article.markdown.splitlines():
                if line.startswith("!["):
                    self.assertNotEqual(line.split("]", 1)[0], "![")

    def test_current_articles_pass_content_safety(self) -> None:
        validate_content_safety(self.articles)

    def test_content_safety_rejects_private_contacts_and_claims(self) -> None:
        unsafe_fragments = (
            "Напишите на private@example.com.",
            "Позвоните по номеру +7 999 123-45-67.",
            "Напишите https://t.me/private_manager.",
            "Напишите @private_manager.",
            "Карта для оплаты: 4111 1111 1111 1111.",
            "Средняя конверсия составляет 15%.",
            "У нас лучшие данные на рынке.",
            "В базе 12 миллионов сотрудников.",
        )
        metadata = {
            "id": "unsafe",
            "title": "Небезопасная статья",
            "description": "Тест",
            "area": "test",
            "keywords": ["тест"],
            "status": "published",
            "last_verified": "2026-09-04",
        }
        for fragment in unsafe_fragments:
            with self.subTest(fragment=fragment):
                article = Article(ROOT / "docs" / "unsafe.md", metadata, f"# Тест\n\n{fragment}\n")
                with self.assertRaises(ValueError):
                    validate_content_safety([article])

    def test_public_support_link_is_allowed(self) -> None:
        metadata = {
            "id": "safe",
            "title": "Безопасная статья",
            "description": "Тест",
            "area": "test",
            "keywords": ["тест"],
            "status": "published",
            "last_verified": "2026-09-04",
        }
        article = Article(
            ROOT / "docs" / "safe.md",
            metadata,
            "# Тест\n\nНапишите [в поддержку](https://t.me/dealrockets).\n",
        )
        validate_content_safety([article])

    def test_site_does_not_expose_repository_actions(self) -> None:
        config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        for setting in ("repo_url:", "repo_name:", "edit_uri:", "content.action.edit"):
            self.assertNotIn(setting, config)


if __name__ == "__main__":
    unittest.main()
