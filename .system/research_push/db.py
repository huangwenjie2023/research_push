from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .models import Item
from .paths import DB_PATH


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def item_id(topic_id: str, stable_key: str) -> str:
    return hashlib.sha1(f"{topic_id}|{stable_key}".encode("utf-8")).hexdigest()


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(path: Path = DB_PATH) -> None:
    with connect(path) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                topic_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                stable_key TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                abstract TEXT NOT NULL,
                published_at TEXT NOT NULL,
                authors_json TEXT NOT NULL,
                venue TEXT NOT NULL,
                doi TEXT NOT NULL,
                arxiv_id TEXT NOT NULL,
                pdf_url TEXT NOT NULL,
                code_url TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(topic_id, stable_key)
            );
            CREATE TABLE IF NOT EXISTS scores (
                item_id TEXT NOT NULL,
                version TEXT NOT NULL,
                total REAL NOT NULL,
                features_json TEXT NOT NULL,
                reasons_json TEXT NOT NULL,
                scored_at TEXT NOT NULL,
                PRIMARY KEY(item_id, version)
            );
            CREATE TABLE IF NOT EXISTS pdfs (
                item_id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT NOT NULL,
                text_excerpt TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS summaries (
                item_id TEXT NOT NULL,
                focus TEXT NOT NULL,
                provider TEXT NOT NULL,
                summary_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(item_id, focus)
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                topic_id TEXT NOT NULL,
                label TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS feedback_state (
                topic_id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS zotero_items (
                item_id TEXT PRIMARY KEY,
                zotero_key TEXT NOT NULL,
                zotero_version INTEGER NOT NULL,
                collection_key TEXT NOT NULL,
                citation_key TEXT NOT NULL,
                synced_at TEXT NOT NULL
            );
            """
        )


def upsert_items(items: Iterable[Item], path: Path = DB_PATH) -> int:
    inserted = 0
    with connect(path) as con:
        for item in items:
            stable = item.stable_key
            iid = item_id(item.topic_id, stable)
            exists = con.execute("SELECT 1 FROM items WHERE id = ?", (iid,)).fetchone()
            con.execute(
                """
                INSERT INTO items
                (id, topic_id, source_id, stable_key, title, url, abstract, published_at,
                 authors_json, venue, doi, arxiv_id, pdf_url, code_url, raw_json,
                 first_seen_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    source_id=excluded.source_id,
                    title=excluded.title,
                    url=excluded.url,
                    abstract=excluded.abstract,
                    published_at=excluded.published_at,
                    authors_json=excluded.authors_json,
                    venue=excluded.venue,
                    doi=excluded.doi,
                    arxiv_id=excluded.arxiv_id,
                    pdf_url=excluded.pdf_url,
                    code_url=excluded.code_url,
                    raw_json=excluded.raw_json,
                    updated_at=excluded.updated_at
                """,
                (
                    iid,
                    item.topic_id,
                    item.source_id,
                    stable,
                    item.title,
                    item.url,
                    item.abstract,
                    item.published_at,
                    json.dumps(item.authors, ensure_ascii=False),
                    item.venue,
                    item.doi,
                    item.arxiv_id,
                    item.pdf_url,
                    item.code_url,
                    json.dumps(item.raw, ensure_ascii=False),
                    now_iso(),
                    now_iso(),
                ),
            )
            if exists is None:
                inserted += 1
    return inserted


def row_to_item(row: sqlite3.Row) -> Item:
    return Item(
        topic_id=row["topic_id"],
        source_id=row["source_id"],
        title=row["title"],
        url=row["url"],
        abstract=row["abstract"],
        published_at=row["published_at"],
        authors=json.loads(row["authors_json"]),
        venue=row["venue"],
        doi=row["doi"],
        arxiv_id=row["arxiv_id"],
        pdf_url=row["pdf_url"],
        code_url=row["code_url"],
        raw=json.loads(row["raw_json"]),
    )


def list_items(topic_id: str | None = None, date_prefix: str | None = None, limit: int | None = None) -> list[sqlite3.Row]:
    query = "SELECT * FROM items"
    clauses: list[str] = []
    params: list[object] = []
    if topic_id:
        clauses.append("topic_id = ?")
        params.append(topic_id)
    if date_prefix:
        clauses.append("(published_at LIKE ? OR first_seen_at LIKE ?)")
        params.extend([f"{date_prefix}%", f"{date_prefix}%"])
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY published_at DESC, first_seen_at DESC"
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    with connect() as con:
        return con.execute(query, params).fetchall()
