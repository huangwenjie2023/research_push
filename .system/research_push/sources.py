from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import quote, urlencode
from xml.etree import ElementTree

from .models import Item, Topic
from .net import env_header, fetch_json, fetch_bytes, network_error_message


def collect_all(config: dict, topics: list[Topic]) -> tuple[list[Item], list[str]]:
    items: list[Item] = []
    warnings: list[str] = []
    for source in config.get("sources", []):
        if not source.get("enabled", True):
            continue
        api_key_env = source.get("api_key_env")
        if source.get("type") in {"placeholder"}:
            warnings.append(f"Skip {source['id']}: adapter not implemented yet.")
            continue
        if api_key_env and source.get("require_key") and not os.environ.get(api_key_env):
            warnings.append(f"Skip {source['id']}: missing {api_key_env}.")
            continue
        for topic in topics:
            try:
                if source["type"] in {"arxiv", "semantic_scholar"}:
                    time.sleep(float(source.get("polite_delay_seconds", 1.5)))
                if source["type"] == "arxiv":
                    items.extend(collect_arxiv(source, topic))
                elif source["type"] == "semantic_scholar":
                    items.extend(collect_semantic_scholar(source, topic))
                elif source["type"] == "github":
                    items.extend(collect_github(source, topic))
                elif source["type"] == "rss":
                    items.extend(collect_rss(source, topic))
            except Exception as error:
                warnings.append(f"Skip {source['id']} for {topic.id}: {network_error_message(error)}")
    return items, warnings


def collect_arxiv(source: dict, topic: Topic) -> list[Item]:
    terms = list(topic.keywords[:6])
    query = " OR ".join(f'all:"{term}"' for term in terms)
    params = urlencode(
        {
            "search_query": query,
            "start": 0,
            "max_results": int(source.get("max_results_per_topic", 25)),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    url = f"https://export.arxiv.org/api/query?{params}"
    xml = fetch_bytes(url)
    root = ElementTree.fromstring(xml)
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    items: list[Item] = []
    for entry in root.findall("atom:entry", ns):
        title = clean(entry.findtext("atom:title", default="", namespaces=ns))
        abstract = clean(entry.findtext("atom:summary", default="", namespaces=ns))
        page_url = clean(entry.findtext("atom:id", default="", namespaces=ns))
        published = normalize_date(entry.findtext("atom:published", default="", namespaces=ns))
        authors = [clean(author.findtext("atom:name", default="", namespaces=ns)) for author in entry.findall("atom:author", ns)]
        arxiv_id = page_url.rsplit("/", 1)[-1]
        pdf_url = ""
        for link in entry.findall("atom:link", ns):
            if link.get("title") == "pdf" or link.get("type") == "application/pdf":
                pdf_url = link.get("href", "")
        doi = clean(entry.findtext("arxiv:doi", default="", namespaces=ns))
        items.append(
            Item(
                topic_id=topic.id,
                source_id=source["id"],
                title=title,
                url=page_url,
                abstract=abstract,
                published_at=published,
                authors=[a for a in authors if a],
                venue="arXiv",
                doi=doi,
                arxiv_id=arxiv_id,
                pdf_url=pdf_url or page_url.replace("/abs/", "/pdf/"),
                raw={"source_query": query},
            )
        )
    return items


def collect_semantic_scholar(source: dict, topic: Topic) -> list[Item]:
    query = " ".join(topic.keywords[:3])
    fields = "title,abstract,authors,year,venue,url,externalIds,openAccessPdf,publicationDate"
    params = urlencode({"query": query, "limit": int(source.get("max_results_per_topic", 15)), "fields": fields})
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"
    headers = {}
    key_env = source.get("api_key_env")
    if key_env and os.environ.get(key_env):
        headers["x-api-key"] = os.environ[key_env]
    data = fetch_json(url, headers=headers)
    items: list[Item] = []
    for paper in data.get("data", []):
        external = paper.get("externalIds") or {}
        pdf = paper.get("openAccessPdf") or {}
        year = str(paper.get("year") or "")
        published = paper.get("publicationDate") or (f"{year}-01-01" if year else "")
        items.append(
            Item(
                topic_id=topic.id,
                source_id=source["id"],
                title=clean(paper.get("title") or ""),
                url=paper.get("url") or "",
                abstract=clean(paper.get("abstract") or ""),
                published_at=normalize_date(published),
                authors=[a.get("name", "") for a in paper.get("authors", []) if a.get("name")],
                venue=paper.get("venue") or "Semantic Scholar",
                doi=external.get("DOI", ""),
                arxiv_id=external.get("ArXiv", ""),
                pdf_url=pdf.get("url") or "",
                raw=paper,
            )
        )
    return [item for item in items if item.title and item.url]


def collect_github(source: dict, topic: Topic) -> list[Item]:
    query = f'"{topic.keywords[0]}" OR "{topic.keywords[1]}"'
    params = urlencode({"q": query, "sort": "updated", "order": "desc", "per_page": int(source.get("max_results_per_topic", 10))})
    headers = {"Accept": "application/vnd.github+json"}
    headers.update(env_header(source.get("api_key_env"), "Bearer {value}"))
    data = fetch_json(f"https://api.github.com/search/repositories?{params}", headers=headers)
    items: list[Item] = []
    for repo in data.get("items", []):
        desc = clean(repo.get("description") or "")
        updated = normalize_date(repo.get("updated_at") or "")
        items.append(
            Item(
                topic_id=topic.id,
                source_id=source["id"],
                title=repo.get("full_name") or repo.get("name") or "",
                url=repo.get("html_url") or "",
                abstract=desc,
                published_at=updated,
                venue="GitHub",
                code_url=repo.get("html_url") or "",
                raw={"stars": repo.get("stargazers_count"), "language": repo.get("language")},
            )
        )
    return [item for item in items if item.title and item.url]


def collect_rss(source: dict, topic: Topic) -> list[Item]:
    xml = fetch_bytes(source["url"])
    root = ElementTree.fromstring(xml)
    channel = root.find("channel")
    raw_items = channel.findall("item") if channel is not None else []
    items: list[Item] = []
    for raw in raw_items:
        title = clean(raw.findtext("title", default=""))
        link = clean(raw.findtext("link", default=""))
        summary = clean(raw.findtext("description", default=""))
        text = f"{title} {summary}".lower()
        if not any(word.lower() in text for word in topic.keywords + topic.expanded_keywords):
            continue
        items.append(
            Item(
                topic_id=topic.id,
                source_id=source["id"],
                title=title,
                url=link,
                abstract=summary,
                published_at=normalize_date(raw.findtext("pubDate", default="")),
                venue=source.get("name", source["id"]),
            )
        )
    return [item for item in items if item.title and item.url]


def normalize_date(value: str) -> str:
    if not value:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    value = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return f"{value}T00:00:00Z"
    if value.endswith("Z") and "T" in value:
        return value
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return value


def clean(value: str) -> str:
    return " ".join(str(value).replace("\n", " ").split())
