from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SMOKE_QUERIES: dict[str, tuple[str, tuple[str, ...]]] = {
    "как найти клиентов": ("search/", ("найти", "клиент")),
    "как найти ЛПР": ("search/", ("лпр",)),
    "свой список компаний": ("search/company-list/", ("спис", "компан")),
    "по ИНН": ("search/company-list/", ("инн",)),
    "обогащение": ("search/company-list/", ("обогащ",)),
    "крупный бизнес": ("search/large-business/", ("крупн", "бизнес")),
    "убрать нерелевантные компании": ("search/refine/", ("нерелевант", "компан")),
    "почему 0 контактов": ("contacts/", ("0", "контакт")),
    "нет прямого контакта": ("contacts/", ("нет", "прям", "контакт")),
    "почему в файле звёздочки": ("export/", ("файл", "звездоч")),
    "экспорт": ("export/", ("экспорт",)),
    "как отменить подписку": ("billing/", ("отмен", "подпис")),
    "как вернуть деньги": ("billing/", ("вернут", "деньг")),
    "не пришёл чек": ("billing/", ("чек",)),
    "где взять акт": ("billing/", ("акт",)),
    "закрывающие документы": ("billing/", ("закрывающ", "документ")),
    "кто такой Инвойсбокс": ("billing/", ("инвойсбокс",)),
    "кто такой Noisebox": ("billing/", ("noisebox",)),
    "насколько актуальны данные": ("data-quality/", ("актуальн", "данн")),
}

REQUIRED_DEEP_LINKS: dict[str, tuple[str, ...]] = {
    "export/index.html": ("all-or-selected", "stars", "empty-fields", "over-10000"),
    "billing/index.html": ("invoicebox", "documents", "refund", "cancellation"),
    "search/company-list/index.html": ("enrichment",),
    "data-quality/index.html": ("sources",),
}


def normalize(value: str) -> str:
    value = value.lower().replace("ё", "е")
    return re.sub(r"\s+", " ", value)


def contains_token(text: str, token: str) -> bool:
    if len(token) <= 3 or token.isdigit():
        return re.search(rf"(?<!\w){re.escape(token)}(?!\w)", text) is not None
    return token in text


def load_documents(index_path: Path) -> list[dict[str, str]]:
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    documents = payload.get("docs")
    if not isinstance(documents, list) or not documents:
        raise ValueError("поисковый индекс не содержит документов")
    return documents


def run_smoke(index_path: Path) -> None:
    documents = load_documents(index_path)
    searchable = [
        (
            str(document.get("location", "")),
            normalize(f"{document.get('title', '')} {document.get('text', '')}"),
        )
        for document in documents
    ]

    missing: list[str] = []
    for query, (expected_location, tokens) in SMOKE_QUERIES.items():
        normalized_tokens = tuple(normalize(token) for token in tokens)
        if not any(
            (location == expected_location or location.startswith(f"{expected_location}#"))
            and all(contains_token(text, token) for token in normalized_tokens)
            for location, text in searchable
        ):
            missing.append(query)

    if missing:
        raise ValueError(f"поиск не находит контрольные запросы: {', '.join(missing)}")


def check_deep_links(site_dir: Path) -> None:
    missing: list[str] = []
    for relative_path, anchors in REQUIRED_DEEP_LINKS.items():
        html_path = site_dir / relative_path
        html = html_path.read_text(encoding="utf-8")
        for anchor in anchors:
            if f'id="{anchor}"' not in html:
                missing.append(f"/{relative_path.removesuffix('index.html')}#{anchor}")

    if missing:
        raise ValueError(f"собранный сайт не содержит обязательные deep links: {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверить собранный поисковый индекс MkDocs")
    parser.add_argument("index", type=Path, nargs="?", default=Path("site/search/search_index.json"))
    args = parser.parse_args()

    try:
        run_smoke(args.index)
        check_deep_links(args.index.parents[1])
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Search smoke failed: {error}", file=sys.stderr)
        return 1

    deep_link_count = sum(len(anchors) for anchors in REQUIRED_DEEP_LINKS.values())
    print(f"Search smoke passed: {len(SMOKE_QUERIES)} queries, {deep_link_count} deep links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
