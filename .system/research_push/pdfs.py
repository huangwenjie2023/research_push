from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from . import db
from .net import fetch_bytes, network_error_message
from .paths import PAPERS_DIR


def fetch_pdfs(topic_id: str | None = None, date_prefix: str | None = None, limit: int | None = None, force: bool = False) -> int:
    rows = db.list_items(topic_id=topic_id, date_prefix=date_prefix, limit=limit)
    count = 0
    with db.connect() as con:
        for row in rows:
            pdf_url = row["pdf_url"]
            if not pdf_url:
                upsert_pdf(con, row["id"], "", "unavailable", "No PDF URL", "")
                continue
            existing = con.execute("SELECT status FROM pdfs WHERE item_id = ?", (row["id"],)).fetchone()
            if existing and existing["status"] == "downloaded" and not force:
                continue
            target = pdf_path_for(row)
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                data = fetch_bytes(pdf_url, timeout=45)
                if not data.startswith(b"%PDF"):
                    raise ValueError("Downloaded content is not a PDF")
                target.write_bytes(data)
                excerpt = extract_pdf_excerpt(target)
                upsert_pdf(con, row["id"], str(target), "downloaded", "", excerpt)
                count += 1
            except Exception as error:
                upsert_pdf(con, row["id"], str(target), "failed", network_error_message(error), "")
    return count


def pdf_path_for(row) -> Path:
    topic_dir = PAPERS_DIR / row["topic_id"]
    year = "unknown"
    if row["published_at"]:
        match = re.search(r"(19|20)\d{2}", row["published_at"])
        if match:
            year = match.group(0)
    author = "unknown"
    try:
        import json

        authors = json.loads(row["authors_json"])
        if authors:
            author = slugify(authors[0].split()[-1])
    except Exception:
        pass
    title_slug = slugify(row["title"])[:70] or "paper"
    ident = row["arxiv_id"] or row["doi"] or row["id"][:8]
    ident = slugify(ident.replace("/", "_"))
    return topic_dir / f"{year}_{author}_{title_slug}_{ident}.pdf"


def extract_pdf_excerpt(path: Path, max_chars: int = 16000) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return "PDF downloaded. Install pypdf to extract text."
    try:
        reader = PdfReader(str(path))
        parts: list[str] = []
        for page in reader.pages[:8]:
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text.strip())
            if sum(len(part) for part in parts) >= max_chars:
                break
        return "\n\n".join(parts)[:max_chars]
    except Exception as error:
        return f"PDF downloaded, but text extraction failed: {error}"


def upsert_pdf(con, item_id: str, path: str, status: str, error: str, text_excerpt: str) -> None:
    con.execute(
        """
        INSERT INTO pdfs (item_id, path, status, error, text_excerpt, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(item_id) DO UPDATE SET
            path=excluded.path,
            status=excluded.status,
            error=excluded.error,
            text_excerpt=excluded.text_excerpt,
            updated_at=excluded.updated_at
        """,
        (item_id, path, status, error, text_excerpt, db.now_iso()),
    )


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return value.strip("-").lower()

