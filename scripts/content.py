from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REQUIRED_FIELDS = {
    "id",
    "title",
    "description",
    "area",
    "keywords",
    "status",
    "last_verified",
}
PUBLISHED_STATUS = "published"
FRONT_MATTER = re.compile(r"\A---\s*\n(?P<meta>.*?)\n---\s*\n(?P<body>.*)\Z", re.DOTALL)
EMAIL_ADDRESS = re.compile(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b")
RUSSIAN_PHONE = re.compile(
    r"(?<!\d)(?:\+7|8)[\s().-]*\d{3}[\s().-]*\d{3}[\s.-]*\d{2}[\s.-]*\d{2}(?!\d)"
)
PAYMENT_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){15,18}\d(?!\d)")
TELEGRAM_LINK = re.compile(r"(?i)https?://(?:t\.me|telegram\.me)/([a-z0-9_]+)")
TELEGRAM_HANDLE = re.compile(r"(?<![\w@])@([a-zA-Z0-9_]{5,})")
UNVERIFIED_PERCENT = re.compile(r"(?<!\d)\d+(?:[.,]\d+)?\s*%(?![0-9a-fA-F]{2})")
UNVERIFIED_DATABASE_SIZE = re.compile(
    r"(?i)\b\d+[\s,.]*(?:миллион\w*|млн)\s+(?:компан\w*|сотрудник\w*|контакт\w*)"
)
UNVERIFIED_SUPERLATIVE = re.compile(
    r"(?i)\b(?:лучш\w*|единственн\w*|крупнейш\w*)\s+(?:данн\w*|баз\w*|сервис\w*|источник\w*)"
)
ALLOWED_TELEGRAM_HANDLE = "dealrockets"


@dataclass(frozen=True)
class Article:
    path: Path
    metadata: dict[str, Any]
    markdown: str


def load_article(path: Path) -> Article:
    raw = path.read_text(encoding="utf-8")
    match = FRONT_MATTER.match(raw)
    if not match:
        raise ValueError(f"{path}: отсутствует YAML front matter")

    metadata = yaml.safe_load(match.group("meta"))
    if not isinstance(metadata, dict):
        raise ValueError(f"{path}: front matter должен быть объектом")

    missing = REQUIRED_FIELDS - metadata.keys()
    if missing:
        raise ValueError(f"{path}: отсутствуют поля: {', '.join(sorted(missing))}")

    if not isinstance(metadata["keywords"], list) or not metadata["keywords"]:
        raise ValueError(f"{path}: keywords должен быть непустым списком")
    if metadata["status"] != PUBLISHED_STATUS:
        raise ValueError(f"{path}: в docs разрешён только status: published")

    article_id = metadata["id"]
    if not isinstance(article_id, str) or not re.fullmatch(r"[a-z0-9-]+", article_id):
        raise ValueError(f"{path}: id должен быть стабильным kebab-case идентификатором")

    body = match.group("body").strip() + "\n"
    if not body.startswith("# "):
        raise ValueError(f"{path}: тело статьи должно начинаться с H1")
    return Article(path=path, metadata=metadata, markdown=body)


def collect_articles(docs_dir: Path) -> list[Article]:
    articles = [load_article(path) for path in sorted(docs_dir.rglob("*.md"))]
    ids: dict[str, Path] = {}
    for article in articles:
        article_id = article.metadata["id"]
        if article_id in ids:
            raise ValueError(f"Дублирующийся id {article_id}: {ids[article_id]} и {article.path}")
        ids[article_id] = article.path
    return articles


def validate_content_safety(articles: list[Article]) -> None:
    """Fail the public build when client content contains likely PII or unsafe claims."""

    for article in articles:
        metadata_text = " ".join(
            str(value) if not isinstance(value, list) else " ".join(str(item) for item in value)
            for value in article.metadata.values()
        )
        text = f"{metadata_text}\n{article.markdown}"
        relative_path = article.path.as_posix()

        checks = (
            (EMAIL_ADDRESS, "email-адрес"),
            (RUSSIAN_PHONE, "номер телефона"),
            (PAYMENT_CARD, "возможный номер банковской карты"),
            (UNVERIFIED_PERCENT, "неподтверждённый процент"),
            (UNVERIFIED_DATABASE_SIZE, "неподтверждённый размер базы"),
            (UNVERIFIED_SUPERLATIVE, "неподтверждённое превосходное утверждение"),
        )
        for pattern, label in checks:
            if pattern.search(text):
                raise ValueError(f"{relative_path}: найден {label}")

        for match in TELEGRAM_LINK.finditer(text):
            if match.group(1).lower() != ALLOWED_TELEGRAM_HANDLE:
                raise ValueError(f"{relative_path}: найдена непубличная Telegram-ссылка")

        for match in TELEGRAM_HANDLE.finditer(text):
            if match.group(1).lower() != ALLOWED_TELEGRAM_HANDLE:
                raise ValueError(f"{relative_path}: найден непубличный Telegram-аккаунт")


def article_url(path: Path, docs_dir: Path, site_url: str) -> str:
    relative = path.relative_to(docs_dir)
    if relative.name == "index.md":
        slug = "" if relative.parent == Path(".") else relative.parent.as_posix().strip("/")
    else:
        slug = relative.with_suffix("").as_posix()
    suffix = f"{slug}/" if slug else ""
    return f"{site_url.rstrip('/')}/{suffix}"


def build_corpus(articles: list[Article], docs_dir: Path, site_url: str) -> dict[str, Any]:
    documents = []
    for article in articles:
        metadata = article.metadata
        markdown = article.markdown
        documents.append(
            {
                "id": metadata["id"],
                "title": metadata["title"],
                "description": metadata["description"],
                "area": metadata["area"],
                "keywords": metadata["keywords"],
                "status": metadata["status"],
                "last_verified": str(metadata["last_verified"]),
                "url": article_url(article.path, docs_dir, site_url),
                "markdown": markdown,
                "sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            }
        )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "articles": documents,
    }


def write_corpus(corpus: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(corpus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
