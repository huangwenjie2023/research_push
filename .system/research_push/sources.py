from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urlencode
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
                if source["type"] in {"arxiv", "semantic_scholar", "openalex", "crossref", "huggingface_papers"}:
                    time.sleep(float(source.get("polite_delay_seconds", 1.5)))
                if source["type"] == "arxiv":
                    items.extend(collect_arxiv(source, topic))
                elif source["type"] == "semantic_scholar":
                    items.extend(collect_semantic_scholar(source, topic))
                elif source["type"] == "openalex":
                    items.extend(collect_openalex(source, topic))
                elif source["type"] == "crossref":
                    items.extend(collect_crossref(source, topic))
                elif source["type"] == "github":
                    items.extend(collect_github(source, topic))
                elif source["type"] == "huggingface_papers":
                    items.extend(collect_huggingface_papers(source, topic))
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


def collect_openalex(source: dict, topic: Topic) -> list[Item]:
    query = topic.keywords[0]
    params = {
        "search": query,
        "per-page": int(source.get("max_results_per_topic", 20)),
        "sort": "publication_date:desc",
        "filter": "type:article|preprint|proceedings-article",
    }
    mailto = env_or_value(source.get("mailto_env"))
    if mailto:
        params["mailto"] = mailto
    url = f"https://api.openalex.org/works?{urlencode(params)}"
    data = fetch_json(url)
    items: list[Item] = []
    for work in data.get("results", []):
        title = clean(work.get("title") or work.get("display_name") or "")
        primary = work.get("primary_location") or {}
        landing = primary.get("landing_page_url") or work.get("doi") or work.get("id") or ""
        pdf_url = primary.get("pdf_url") or best_openalex_pdf(work)
        doi = (work.get("doi") or "").replace("https://doi.org/", "")
        arxiv_id = arxiv_id_from_locations(work)
        abstract = clean(openalex_abstract(work.get("abstract_inverted_index") or {}))
        authors = [
            clean((authorship.get("author") or {}).get("display_name") or "")
            for authorship in work.get("authorships", [])
        ]
        venue = clean(((primary.get("source") or {}).get("display_name")) or work.get("host_venue", {}).get("display_name", "") or "OpenAlex")
        item = Item(
            topic_id=topic.id,
            source_id=source["id"],
            title=title,
            url=landing,
            abstract=abstract,
            published_at=normalize_date(work.get("publication_date") or ""),
            authors=[author for author in authors if author],
            venue=venue,
            doi=doi,
            arxiv_id=arxiv_id,
            pdf_url=pdf_url or "",
            raw={"openalex_id": work.get("id"), "cited_by_count": work.get("cited_by_count")},
        )
        if topic_matches(item, topic):
            items.append(item)
    return [item for item in items if item.title and item.url]


def collect_crossref(source: dict, topic: Topic) -> list[Item]:
    query = topic.keywords[0]
    params = {
        "query.title": query,
        "rows": int(source.get("max_results_per_topic", 12)),
        "sort": "published",
        "order": "desc",
        "select": "DOI,title,author,container-title,published-print,published-online,URL,link,abstract,type",
    }
    mailto = env_or_value(source.get("mailto_env"))
    headers = {"User-Agent": f"research_push/0.1 (mailto:{mailto})"} if mailto else {}
    data = fetch_json(f"https://api.crossref.org/works?{urlencode(params)}", headers=headers)
    items: list[Item] = []
    for work in (data.get("message") or {}).get("items", []):
        title = clean(first_string(work.get("title")))
        doi = work.get("DOI", "")
        url = work.get("URL") or (f"https://doi.org/{doi}" if doi else "")
        pdf_url = crossref_pdf(work)
        authors = [clean(" ".join(filter(None, [a.get("given", ""), a.get("family", "")]))) for a in work.get("author", [])]
        venue = clean(first_string(work.get("container-title")) or "Crossref")
        item = Item(
            topic_id=topic.id,
            source_id=source["id"],
            title=title,
            url=url,
            abstract=clean(strip_html(unescape(work.get("abstract") or ""))),
            published_at=normalize_date(crossref_date(work)),
            authors=[author for author in authors if author],
            venue=venue,
            doi=doi,
            pdf_url=pdf_url,
            raw={"type": work.get("type")},
        )
        if topic_matches(item, topic):
            items.append(item)
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


def collect_huggingface_papers(source: dict, topic: Topic) -> list[Item]:
    html = fetch_bytes(source.get("url", "https://huggingface.co/papers")).decode("utf-8", errors="ignore")
    cards = parse_hf_paper_cards(html)
    items: list[Item] = []
    for card in cards[: int(source.get("max_results_per_topic", 10)) * 4]:
        text = f"{card['title']} {card.get('summary', '')}".lower()
        if not any(word.lower() in text for word in topic.keywords + topic.expanded_keywords):
            continue
        items.append(
            Item(
                topic_id=topic.id,
                source_id=source["id"],
                title=card["title"],
                url=card["url"],
                abstract=card.get("summary", ""),
                published_at=normalize_date(card.get("date", "")),
                venue="Hugging Face Papers",
                arxiv_id=card.get("arxiv_id", ""),
                pdf_url=f"https://arxiv.org/pdf/{card['arxiv_id']}" if card.get("arxiv_id") else "",
                raw=card,
            )
        )
        if len(items) >= int(source.get("max_results_per_topic", 10)):
            break
    return items


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


def topic_matches(item: Item, topic: Topic) -> bool:
    text = f"{item.title} {item.abstract} {item.venue}".lower()
    positive = topic.keywords + topic.expanded_keywords
    return any(word.lower() in text for word in positive)


def env_or_value(env_name: str | None) -> str:
    return os.environ.get(env_name or "", "")


def openalex_abstract(index: dict) -> str:
    if not index:
        return ""
    words: list[tuple[int, str]] = []
    for word, positions in index.items():
        for position in positions:
            words.append((int(position), word))
    return " ".join(word for _, word in sorted(words))


def best_openalex_pdf(work: dict) -> str:
    for location in work.get("locations", []) or []:
        if location.get("pdf_url"):
            return location["pdf_url"]
    return ""


def arxiv_id_from_locations(work: dict) -> str:
    urls = []
    for location in work.get("locations", []) or []:
        urls.append(location.get("landing_page_url") or "")
        urls.append(location.get("pdf_url") or "")
    urls.append(work.get("doi") or "")
    for url in urls:
        match = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9.]+)(?:v\d+)?", url, re.I)
        if match:
            return match.group(1)
    return ""


def first_string(value) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def crossref_pdf(work: dict) -> str:
    for link in work.get("link", []) or []:
        content_type = link.get("content-type", "")
        url = link.get("URL", "")
        if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
            return url
    return ""


def crossref_date(work: dict) -> str:
    for key in ("published-online", "published-print", "published"):
        parts = (work.get(key) or {}).get("date-parts") or []
        if parts and parts[0]:
            values = list(parts[0]) + [1, 1]
            year, month, day = values[:3]
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return ""


def parse_hf_paper_cards(html: str) -> list[dict]:
    cards: list[dict] = []
    for match in re.finditer(r'href="(/papers/([0-9.]+))"[^>]*>(.*?)</a>', html, re.S):
        title = clean(strip_html(unescape(match.group(3))))
        if not title or len(title) < 8:
            continue
        url = "https://huggingface.co" + match.group(1)
        arxiv_id = match.group(2)
        if not any(card["url"] == url for card in cards):
            cards.append({"title": title, "url": url, "arxiv_id": arxiv_id})
    return cards


def strip_html(value: str) -> str:
    parser = TextExtractor()
    parser.feed(value)
    parser.close()
    return parser.text


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    @property
    def text(self) -> str:
        return " ".join(self._parts)

    def handle_data(self, data: str) -> None:
        if data.strip():
            self._parts.append(data.strip())
