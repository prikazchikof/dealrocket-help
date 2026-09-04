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
    "start/why-dealrocket/index.md": "why-dealrocket",
    "search/index.md": "finding-clients",
    "search/ai-assistant/index.md": "ai-client-search",
    "search/filters/index.md": "search-filters",
    "search/company-list/index.md": "search-company-list",
    "search/large-business/index.md": "search-large-business",
    "search/refine/index.md": "search-refine",
    "contacts/index.md": "contacts-and-lists",
    "lists/index.md": "working-with-lists",
    "export/index.md": "exporting-data",
    "data-quality/index.md": "data-and-freshness",
    "billing/index.md": "plans-and-balance",
    "billing/tarification/index.md": "contact-tarification",
    "outreach/index.md": "using-exported-data",
}

REQUIRED_MARKDOWN_ANCHORS = {
    "export/index.md": {"all-or-selected", "stars", "empty-fields", "over-10000"},
    "billing/index.md": {"invoicebox", "documents", "refund", "cancellation"},
    "search/company-list/index.md": {"enrichment"},
    "search/filters/index.md": {
        "ai-filter",
        "job-titles",
        "location",
        "company",
        "company-description",
        "industries",
        "okved",
        "company-size",
        "source",
        "contacts",
        "opened-contacts",
        "record-count",
    },
}

EXPECTED_FILTER_NAMES = {
    "ИИ-помощник",
    "AI-фильтр списка",
    "«Управленческий уровень»",
    "«Функция или департамент»",
    "«Включить должности»",
    "«Исключить должности»",
    "«Год начала работы»",
    "«Работают сейчас»",
    "«Включать отделы»",
    "«Страна»",
    "«Область»",
    "«Город»",
    "«Найти компании»",
    "«Ключевые слова в названии компании»",
    "«Сайт компании»",
    "«ИННы»",
    "«Телефон компании или человека»",
    "«Есть сайт»",
    "«Содержит любое из слов»",
    "«Содержит каждое из слов»",
    "«Не содержит каждое из слов»",
    "«Категории из карт»",
    "«Подборки по семантике»",
    "«Индустрии из соц. сетей»",
    "«Компания содержит каждый из выбранных типов индустрий»",
    "«Исключить категории, подборки и индустрии»",
    "«Вид деятельности»",
    "«Выручка — за год»",
    "«Количество сотрудников»",
    "«Источник данных»",
    "«Один сотрудник из компании»",
    "«Есть имя сотрудника»",
    "Контакты сотрудника: «есть любой контакт», «есть почта», «есть телефон»",
    "Контакты сотрудника: «есть мобильный телефон»",
    "Контакты компании: «есть любой контакт», «есть почта», «есть телефон»",
    "Контакты сотрудника: «контакты открыты» и «контакты закрыты»",
    "Контакты компании: «контакты открыты» и «контакты закрыты»",
    "«Количество отображаемых записей»",
}

VIDEO_ARTICLES = {
    "start/why-dealrocket/index.md": {"456239039": "Почему вы обязаны использовать DealRocket"},
    "search/index.md": {
        "456239040": "Как правильно искать компании по отраслям",
        "456239041": "Как правильно делать поиск по должностям",
    },
    "search/company-list/index.md": {"456239044": "Как найти контакты по своему списку компаний"},
    "search/large-business/index.md": {"456239042": "Как искать контакты в крупном бизнесе"},
    "contacts/index.md": {"456239048": "Что делать, когда нет контакта сотрудника"},
    "lists/index.md": {"456239047": "Как сохранить найденные результаты в список"},
    "export/index.md": {"456239045": "Как экспортировать контакты в Excel или CRM"},
    "data-quality/index.md": {"456239046": "Насколько качественные и актуальные данные"},
    "outreach/index.md": {"456239049": "Что делать с полученной базой"},
}

VIDEO_FREE_ARTICLES = {
    "start/index.md",
    "search/ai-assistant/index.md",
    "search/refine/index.md",
    "billing/index.md",
    "billing/tarification/index.md",
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
            "договор-оферта",
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

    def test_filter_reference_covers_every_visible_filter(self) -> None:
        article = next(article for article in self.articles if article.metadata["id"] == "search-filters")
        rows = [line for line in article.markdown.splitlines() if line.startswith("| **")]
        names = {line.split("**", 2)[1] for line in rows}
        self.assertEqual(names, EXPECTED_FILTER_NAMES)
        for row in rows:
            self.assertEqual(row.count("|"), 5, row)
        self.assertEqual(
            article.markdown.count(
                "| Фильтр | Как работает | Когда использовать | Когда лучше не использовать |"
            ),
            11,
        )
        self.assertIn(
            "| Инструмент | Как работает | Когда использовать | Когда лучше не использовать |",
            article.markdown,
        )

    def test_course_videos_match_their_articles_and_sections(self) -> None:
        articles_by_path = {
            article.path.relative_to(ROOT / "docs").as_posix(): article.markdown
            for article in self.articles
        }
        for path, expected_videos in VIDEO_ARTICLES.items():
            markdown = articles_by_path[path]
            self.assertEqual(markdown.count('class="help-video-player"'), len(expected_videos), path)
            for video_id, title in expected_videos.items():
                self.assertIn(f"id={video_id}", markdown, path)
                self.assertIn(f'title="{title}"', markdown, path)
            self.assertEqual(markdown.count('loading="lazy"'), len(expected_videos), path)
            self.assertEqual(markdown.count("allowfullscreen"), len(expected_videos), path)

        for path in VIDEO_FREE_ARTICLES:
            self.assertNotIn('class="help-video-player"', articles_by_path[path], path)

        self.assertLess(
            articles_by_path["search/index.md"].index("id=456239041"),
            articles_by_path["search/index.md"].index("### Если нужной функции нет в списке"),
        )
        self.assertLess(
            articles_by_path["contacts/index.md"].index("## Что делать, если нет прямого контакта"),
            articles_by_path["contacts/index.md"].index("id=456239048"),
        )

    def test_contextual_faqs_are_kept_with_their_guides(self) -> None:
        faq_ids = {
            "finding-clients",
            "search-company-list",
            "search-large-business",
            "search-refine",
            "contacts-and-lists",
            "working-with-lists",
            "exporting-data",
            "data-and-freshness",
            "using-exported-data",
        }
        for article in self.articles:
            if article.metadata["id"] in faq_ids:
                self.assertIn("## Частые вопросы", article.markdown)

    def test_scenario_guides_are_long_form(self) -> None:
        for article in self.articles:
            if article.metadata["id"] in {
                "home",
                "getting-started",
                "search-large-business",
                "search-refine",
                "working-with-lists",
                "using-exported-data",
                "plans-and-balance",
                "contact-tarification",
                "ai-client-search",
                "why-dealrocket",
            }:
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
