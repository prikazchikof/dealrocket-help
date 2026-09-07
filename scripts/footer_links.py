from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import yaml

EXPECTED_GROUP_IDS = ("industries", "roles", "companies")


def load_client_base_links(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Client base links must be a YAML mapping")

    groups = data.get("groups")
    if not isinstance(groups, list):
        raise ValueError("Client base links must define a groups list")

    if not all(isinstance(group, dict) for group in groups):
        raise ValueError("Every client base link group must be a YAML mapping")

    group_ids = tuple(group.get("id") for group in groups)
    if group_ids != EXPECTED_GROUP_IDS:
        raise ValueError(f"Client base link groups must be {EXPECTED_GROUP_IDS}")

    urls: list[str] = []
    for group in groups:
        if not group.get("title") or not isinstance(group.get("links"), list) or not group["links"]:
            raise ValueError(f"Client base link group is incomplete: {group.get('id')}")
        for index, link in enumerate(group["links"]):
            if not isinstance(link, dict):
                raise ValueError(f"Client base link #{index + 1} in {group.get('id')} must be a YAML mapping")
            title = link.get("title")
            url = link.get("url")
            if not isinstance(title, str) or not title.strip():
                raise ValueError("Every client base link must have a title")
            if not isinstance(url, str):
                raise ValueError(f"Client base link has no URL: {title}")
            parsed = urlparse(url)
            if (
                parsed.scheme != "https"
                or parsed.netloc != "dealrocket.ru"
                or re.fullmatch(r"/baza_[a-z0-9_]+/", parsed.path) is None
            ):
                raise ValueError(f"Unexpected client base URL: {url}")
            if parsed.query or parsed.fragment:
                raise ValueError(f"Client base URL must not have query or fragment: {url}")
            urls.append(url)

    if len(urls) != len(set(urls)):
        raise ValueError("Client base URLs must be unique")
    if len(urls) != data.get("expected_unique_links"):
        raise ValueError("Client base link count differs from the captured inventory")
    return data


def on_config(config):
    config_path = Path(config.config_file_path).resolve()
    data = load_client_base_links(config_path.parent / "data" / "client-base-links.yml")
    config.extra["client_base_link_groups"] = data["groups"]
    config.extra["client_base_link_count"] = data["expected_unique_links"]
    return config
