from __future__ import annotations

import json
import os
import re
from urllib.parse import quote

from . import db
from .models import Topic
from .net import fetch_json, post_json


ZOTERO_API = "https://api.zotero.org"


def sync_daily(config: dict, topics: list[Topic], date_prefix: str | None = None, limit_per_topic: int | None = None) -> dict:
    zotero_config = config.get("zotero", {})
    if not zotero_config.get("enabled", False):
        return {"enabled": False, "created": 0, "updated": 0, "skipped": 0}
    client = ZoteroClient.from_config(zotero_config)
    root_key = client.ensure_collection(zotero_config.get("root_collection", "Research Push"))
    stats = {"enabled": True, "created": 0, "updated": 0, "skipped": 0}
    for topic in topics:
        topic_name = zotero_config.get("topic_collections", {}).get(topic.id, topic.name)
        collection_key = client.ensure_collection(topic_name, parent_key=root_key)
        rows = select_rows_for_topic(topic.id, date_prefix, limit_per_topic or int(zotero_config.get("sync_top_per_topic", topic.daily_limit)))
        for row in rows:
            result = sync_row(client, row, collection_key, topic, zotero_config)
            stats[result] = stats.get(result, 0) + 1
    return stats


def init_collections(config: dict, topics: list[Topic], include_topics: bool = False) -> dict:
    zotero_config = config.get("zotero", {})
    client = ZoteroClient.from_config(zotero_config)
    root_key = client.ensure_collection(zotero_config.get("root_collection", "Research Push"))
    result = {"root_collection": zotero_config.get("root_collection", "Research Push"), "root_key": root_key, "topic_collections": {}}
    if include_topics:
        for topic in topics:
            topic_name = zotero_config.get("topic_collections", {}).get(topic.id, topic.name)
            result["topic_collections"][topic.id] = client.ensure_collection(topic_name, parent_key=root_key)
    return result


def select_rows_for_topic(topic_id: str, date_prefix: str | None, limit: int) -> list:
    clauses = ["i.topic_id = ?"]
    params: list[object] = [topic_id]
    if date_prefix:
        clauses.append("(i.published_at LIKE ? OR i.first_seen_at LIKE ?)")
        params.extend([f"{date_prefix}%", f"{date_prefix}%"])
    with db.connect() as con:
        return con.execute(
            f"""
            SELECT i.*, s.total, sm.summary_text, p.path AS pdf_path, p.status AS pdf_status
            FROM items i
            LEFT JOIN scores s ON s.item_id = i.id
            LEFT JOIN summaries sm ON sm.item_id = i.id
            LEFT JOIN pdfs p ON p.item_id = i.id
            WHERE {" AND ".join(clauses)}
            ORDER BY COALESCE(s.total, 0) DESC, i.published_at DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()


def sync_row(client: "ZoteroClient", row, collection_key: str, topic: Topic, config: dict) -> str:
    with db.connect() as con:
        existing = con.execute("SELECT zotero_key FROM zotero_items WHERE item_id = ?", (row["id"],)).fetchone()
    if existing:
        client.add_to_collection(existing["zotero_key"], collection_key)
        return "skipped"

    existing_key = client.find_existing(row)
    if existing_key:
        client.add_to_collection(existing_key, collection_key)
        upsert_zotero_row(row["id"], existing_key, 0, collection_key, citation_key(row))
        return "updated"

    payload = item_payload(row, collection_key, topic, config)
    created = client.create_item(payload)
    item_key = created["key"]
    upsert_zotero_row(row["id"], item_key, int(created.get("version", 0)), collection_key, citation_key(row))
    note = note_payload(row, item_key, config)
    if note:
        client.create_item(note)
    return "created"


def upsert_zotero_row(item_id: str, zotero_key: str, version: int, collection_key: str, cite_key: str) -> None:
    with db.connect() as con:
        con.execute(
            """
            INSERT INTO zotero_items (item_id, zotero_key, zotero_version, collection_key, citation_key, synced_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                zotero_key=excluded.zotero_key,
                zotero_version=excluded.zotero_version,
                collection_key=excluded.collection_key,
                citation_key=excluded.citation_key,
                synced_at=excluded.synced_at
            """,
            (item_id, zotero_key, version, collection_key, cite_key, db.now_iso()),
        )


class ZoteroClient:
    def __init__(self, api_key: str, user_id: str):
        self.api_key = api_key
        self.user_id = user_id
        self.base = f"{ZOTERO_API}/users/{user_id}"

    @classmethod
    def from_config(cls, config: dict) -> "ZoteroClient":
        api_key = os.environ.get(config.get("api_key_env", "ZOTERO_API_KEY"), "").strip()
        user_id = os.environ.get(config.get("user_id_env", "ZOTERO_USER_ID"), "").strip()
        if not api_key:
            raise RuntimeError("ZOTERO_API_KEY is not set")
        if not user_id or not user_id.isdigit():
            raise RuntimeError("ZOTERO_USER_ID must be the numeric Zotero user ID")
        return cls(api_key, user_id)

    @property
    def headers(self) -> dict[str, str]:
        return {"Zotero-API-Key": self.api_key, "Zotero-API-Version": "3"}

    def get(self, path: str) -> dict | list:
        return fetch_json(self.base + path, headers=self.headers, timeout=60)

    def create_item(self, payload: dict) -> dict:
        data = post_json(self.base + "/items", [payload], headers={**self.headers, "Content-Type": "application/json"}, timeout=60)
        success = data.get("successful", {})
        if not success:
            raise RuntimeError(f"Zotero create failed: {data}")
        first = success[sorted(success.keys(), key=int)[0]]
        return first

    def ensure_collection(self, name: str, parent_key: str | None = None) -> str:
        for collection in self.get("/collections?format=json&limit=100"):
            data = collection.get("data", {})
            if data.get("name") == name and data.get("parentCollection") == parent_key:
                return collection["key"]
        payload = {"name": name}
        if parent_key:
            payload["parentCollection"] = parent_key
        data = post_json(self.base + "/collections", [payload], headers={**self.headers, "Content-Type": "application/json"}, timeout=60)
        success = data.get("successful", {})
        if not success:
            raise RuntimeError(f"Zotero collection create failed: {data}")
        first = success[sorted(success.keys(), key=int)[0]]
        return first["key"]

    def find_existing(self, row) -> str:
        queries = []
        if row["doi"]:
            queries.append(row["doi"])
        if row["arxiv_id"]:
            queries.append(row["arxiv_id"])
        queries.append(row["title"])
        for query in queries:
            encoded = quote(query)
            try:
                results = self.get(f"/items/top?format=json&limit=5&q={encoded}&qmode=everything")
            except Exception:
                continue
            for result in results:
                data = result.get("data", {})
                if same_item(row, data):
                    return result["key"]
        return ""

    def add_to_collection(self, item_key: str, collection_key: str) -> None:
        try:
            item = self.get(f"/items/{item_key}?format=json")
        except Exception:
            return
        data = item.get("data", {})
        collections = set(data.get("collections", []))
        if collection_key in collections:
            return
        collections.add(collection_key)
        data["collections"] = list(collections)
        headers = {**self.headers, "If-Unmodified-Since-Version": str(item.get("version", 0)), "Content-Type": "application/json"}
        request_json(self.base + f"/items/{item_key}", data, headers=headers, method="PUT")


def item_payload(row, collection_key: str, topic: Topic, config: dict) -> dict:
    item_type = "journalArticle" if row["doi"] else "preprint"
    if row["source_id"] == "github":
        item_type = "webpage"
    payload = {
        "itemType": item_type,
        "title": row["title"],
        "abstractNote": row["abstract"] or "",
        "url": row["url"],
        "date": row["published_at"][:10] if row["published_at"] else "",
        "collections": [collection_key],
        "tags": [{"tag": tag} for tag in config.get("tags", []) + [topic.id, row["source_id"]]],
        "creators": creators_from_json(row["authors_json"]),
        "extra": extra_field(row),
    }
    if item_type == "webpage":
        payload["websiteTitle"] = row["venue"] or row["source_id"]
    else:
        payload["publicationTitle"] = row["venue"] or ""
        payload["DOI"] = row["doi"] or ""
        payload["archive"] = "arXiv" if row["arxiv_id"] else ""
        payload["archiveLocation"] = row["arxiv_id"] or ""
    return {key: value for key, value in payload.items() if value not in ("", [], None)}


def note_payload(row, parent_key: str, config: dict) -> dict:
    summary = row["summary_text"] or ""
    if not summary and not row["pdf_path"]:
        return {}
    body = [
        "<h2>Research Push Summary</h2>",
        f"<p><b>Topic:</b> {row['topic_id']}</p>",
        f"<p><b>Direct source:</b> <a href=\"{row['url']}\">{row['source_id']}</a></p>",
    ]
    if row["doi"]:
        body.append(f"<p><b>DOI:</b> {row['doi']}</p>")
    if row["arxiv_id"]:
        body.append(f"<p><b>arXiv:</b> {row['arxiv_id']}</p>")
    if row["pdf_path"]:
        body.append(f"<p><b>Local PDF:</b> {row['pdf_path']}</p>")
    if summary:
        body.append("<h3>Summary</h3>")
        body.append("<p>" + summary.replace("\n", "<br/>") + "</p>")
    return {
        "itemType": "note",
        "parentItem": parent_key,
        "note": "\n".join(body),
        "tags": [{"tag": "research_push_note"}],
    }


def creators_from_json(authors_json: str) -> list[dict]:
    creators = []
    for author in json.loads(authors_json or "[]")[:20]:
        parts = author.split()
        if len(parts) >= 2:
            creators.append({"creatorType": "author", "firstName": " ".join(parts[:-1]), "lastName": parts[-1]})
        elif author:
            creators.append({"creatorType": "author", "name": author})
    return creators


def extra_field(row) -> str:
    lines = ["research_push: true"]
    if row["arxiv_id"]:
        lines.append(f"arXiv: {row['arxiv_id']}")
    if row["pdf_url"]:
        lines.append(f"PDF: {row['pdf_url']}")
    if row["code_url"]:
        lines.append(f"Code: {row['code_url']}")
    return "\n".join(lines)


def citation_key(row) -> str:
    authors = json.loads(row["authors_json"] or "[]")
    first = authors[0].split()[-1].lower() if authors else "source"
    year = re.search(r"(19|20)\d{2}", row["published_at"] or "")
    title_word = re.sub(r"[^a-z0-9]", "", row["title"].split()[0].lower()) if row["title"] else "item"
    return f"{first}{year.group(0) if year else 'nd'}{title_word}"


def same_item(row, data: dict) -> bool:
    if row["doi"] and data.get("DOI", "").lower() == row["doi"].lower():
        return True
    extra = data.get("extra", "")
    if row["arxiv_id"] and row["arxiv_id"] in extra:
        return True
    return normalize_title(data.get("title", "")) == normalize_title(row["title"])


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def request_json(url: str, payload: dict, headers: dict, method: str) -> dict:
    import json as json_module
    from urllib.request import Request, urlopen

    request = Request(url, data=json_module.dumps(payload).encode("utf-8"), headers=headers, method=method)
    with urlopen(request, timeout=60) as response:
        body = response.read()
    return json_module.loads(body.decode("utf-8")) if body else {}
