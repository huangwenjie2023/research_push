from __future__ import annotations

import re
from pathlib import Path

from .paths import NOTES_DIR


def paper_slug(row) -> str:
    year = row_get(row, "published_at")[:4]
    if not year.isdigit():
        year = "undated"
    source_key = row_get(row, "arxiv_id") or row_get(row, "doi") or row_get(row, "id")
    source_key = slugify(source_key.replace("/", "_")) or "source"
    title = slugify(row_get(row, "title"))[:72].strip("-") or "paper"
    return f"{year}_{title}_{source_key}"


def paper_dir_for_row(row) -> Path:
    return NOTES_DIR / "Topics" / row_get(row, "topic_id") / "Papers" / paper_slug(row)


def paper_note_path(row) -> Path:
    return paper_dir_for_row(row) / "index.md"


def pdf_path_for_row(row) -> Path:
    return paper_dir_for_row(row) / "paper.pdf"


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "-", str(value).strip())
    return value.strip("-").lower()


def row_get(row, key: str) -> str:
    try:
        if key in row.keys():
            value = row[key]
        else:
            value = ""
    except AttributeError:
        value = row.get(key, "") if isinstance(row, dict) else ""
    return str(value or "")
