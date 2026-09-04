from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from content import build_corpus, collect_articles, validate_content_safety, write_corpus


class SiteConfigLoader(yaml.SafeLoader):
    pass


SiteConfigLoader.add_multi_constructor(
    "tag:yaml.org,2002:python/name:",
    lambda loader, suffix, node: suffix,
)


def load_config(config_path: Path) -> object:
    return yaml.load(config_path.read_text(encoding="utf-8"), Loader=SiteConfigLoader)


def load_site_url(config_path: Path) -> str:
    config = load_config(config_path)
    site_url = config.get("site_url") if isinstance(config, dict) else None
    if not isinstance(site_url, str) or not site_url.startswith("https://"):
        raise ValueError("mkdocs.yml: site_url должен быть HTTPS-адресом")
    return site_url


def collect_nav_paths(value: object) -> set[str]:
    paths: set[str] = set()
    if isinstance(value, str) and value.endswith(".md"):
        paths.add(value.replace("\\", "/"))
    elif isinstance(value, list):
        for item in value:
            paths.update(collect_nav_paths(item))
    elif isinstance(value, dict):
        for item in value.values():
            paths.update(collect_nav_paths(item))
    return paths


def validate_navigation(config_path: Path, docs_dir: Path, articles: list[object]) -> None:
    config = load_config(config_path)
    if not isinstance(config, dict):
        raise ValueError("mkdocs.yml: конфигурация должна быть объектом")
    nav_paths = collect_nav_paths(config.get("nav"))
    article_paths = {
        article.path.relative_to(docs_dir).as_posix()
        for article in articles
        if article.path.name != "404.md"
    }
    missing = article_paths - nav_paths
    unknown = nav_paths - article_paths
    if missing:
        raise ValueError(f"mkdocs.yml: статьи отсутствуют в nav: {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"mkdocs.yml: nav ссылается на неизвестные статьи: {', '.join(sorted(unknown))}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверить статьи и собрать публичный корпус DealRocket Help")
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"))
    parser.add_argument("--config", type=Path, default=Path("mkdocs.yml"))
    parser.add_argument("--output", type=Path, default=Path("docs/assets/help-corpus.v1.json"))
    args = parser.parse_args()

    try:
        articles = collect_articles(args.docs_dir)
        validate_content_safety(articles)
        validate_navigation(args.config, args.docs_dir, articles)
        corpus = build_corpus(articles, args.docs_dir, load_site_url(args.config))
        write_corpus(corpus, args.output)
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"Content validation failed: {error}", file=sys.stderr)
        return 1

    print(f"Content validation passed: {len(articles)} published articles")
    print(f"Corpus written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
