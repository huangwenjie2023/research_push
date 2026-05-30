from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from . import db
from .models import Topic
from .paper_files import paper_note_path
from .paths import NOTES_DIR
from .provenance import build_provenance


def export_notes(topics: list[Topic], date_prefix: str, scoring_version: str = "v1", extra_limit: int = 0) -> int:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    daily_dir = NOTES_DIR / "Daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    daily_path = daily_dir / f"{date_prefix}.md"
    daily_lines = [
        f"# Research Push {date_prefix}",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "反馈标记建议：`有用` / `一般` / `无关` / `太难复现` / `想多看类似` / `想少看类似`。",
        "",
    ]
    total = 0
    for topic in topics:
        limit = topic.daily_limit + extra_limit
        rows = select_ranked(topic.id, limit, scoring_version, date_prefix)
        total += len(rows)
        topic_path = NOTES_DIR / "Topics" / topic.directory / "Daily" / f"{date_prefix}.md"
        topic_path.parent.mkdir(parents=True, exist_ok=True)
        topic_lines = topic_header(topic, date_prefix)
        for index, row in enumerate(rows, start=1):
            topic_lines.extend(format_item(index, row, topic_path))
        create_paper_notes(topic, rows, date_prefix)
        topic_lines.extend(feedback_block(topic.id))
        topic_path.write_text("\n".join(topic_lines), encoding="utf-8")

        daily_lines.extend([f"## {topic.name}", ""])
        if not rows:
            daily_lines.extend(["今日暂无候选。", ""])
            continue
        for index, row in enumerate(rows[: topic.daily_limit], start=1):
            score = row["total"] if row["total"] is not None else 0
            provenance = build_provenance(row)
            pdf_link = provenance.local_pdf_markdown(daily_path)
            pdf_suffix = f" · {pdf_link}" if pdf_link else ""
            daily_lines.append(f"{index}. **{row['title']}**（{score:.2f}） - {provenance.summary_markdown()}{pdf_suffix}")
        daily_lines.extend(["", f"更多：[[../Topics/{topic.directory}/Daily/{date_prefix}|{topic.name} 日报]]", ""])
    daily_lines.extend(["## 今日反馈区", "", "- 觉得有用：", "- 想多看：", "- 想少看：", "- 临时关注点：", ""])
    daily_path.write_text("\n".join(daily_lines), encoding="utf-8")
    return total


def create_paper_notes(topic: Topic, rows: list, date_prefix: str) -> None:
    papers_dir = NOTES_DIR / "Topics" / topic.directory / "Papers"
    papers_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        note_path = paper_note_path(row)
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(paper_note_text(topic, row, note_path, date_prefix), encoding="utf-8")


def paper_note_text(topic: Topic, row, note_path: Path, date_prefix: str) -> str:
    provenance = build_provenance(row)
    score = row["total"] if row["total"] is not None else 0
    authors = json.loads(row["authors_json"] or "[]")
    published_date = (row["published_at"] or date_prefix)[:10]
    pdf_link = provenance.local_pdf_markdown(note_path)
    code_status = "有" if row["code_url"] else "不知"
    origin = provenance.origin_url or provenance.origin_note
    direct = provenance.direct_url
    summary = row["summary_text"] or row["abstract"] or ""
    reading_notes = existing_reading_notes(note_path)
    local_pdf = pdf_link or "N/A"
    lines = [
        "---",
        'type: "paper_note"',
        f'title: "{yaml_escape(row["title"])}"',
        f'date: {published_date}',
        'read_status: "未读"',
        f'org: "{yaml_escape(row["venue"] or row["source_id"])}"',
        f'link: "{yaml_escape(direct)}"',
        f'code: "{code_status}"',
        'note: ""',
        f'url: "{yaml_escape(origin)}"',
        f'topic: "{topic.id}"',
        f'source_id: "{yaml_escape(row["source_id"])}"',
        f'doi: "{yaml_escape(row["doi"])}"',
        f'arxiv_id: "{yaml_escape(row["arxiv_id"])}"',
        f'pdf_status: "{yaml_escape(provenance.pdf_status)}"',
        f'pdf_source: "{yaml_escape(provenance.pdf_source_url)}"',
        f'pdf_local: "{yaml_escape(local_pdf)}"',
        f'score: {score:.2f}',
        "tags: [paper, research_push]",
        "---",
        "",
        f"# {row['title']}",
        "",
        f"- Topic: [[../../Daily/{date_prefix}|{topic.name} {date_prefix}]]",
        f"- Score: {score:.2f}",
        f"- Direct source: {provenance.direct_markdown}",
        f"- Final source: {provenance.origin_markdown}",
        f"- PDF source: {provenance.pdf_source_url or 'N/A'}",
        f"- Local PDF: {local_pdf}",
        f"- Code: {row['code_url'] or 'Unknown'}",
    ]
    if authors:
        lines.append(f"- Authors: {', '.join(authors[:12])}")
    lines.extend(["", "## Summary", "", summary, "", "## Reading Notes", "", reading_notes])
    return "\n".join(lines)


def yaml_escape(value: object) -> str:
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"')


def existing_reading_notes(note_path: Path) -> str:
    if not note_path.exists():
        return ""
    marker = "## Reading Notes"
    text = note_path.read_text(encoding="utf-8")
    if marker not in text:
        return ""
    return text.split(marker, 1)[1].strip()


def select_ranked(topic_id: str, limit: int, version: str, date_prefix: str) -> list:
    with db.connect() as con:
        return con.execute(
            """
            SELECT i.*, s.total, s.features_json, s.reasons_json, p.path AS pdf_path, p.status AS pdf_status,
                   p.error AS pdf_error, sm.summary_text, sm.provider, z.zotero_key, z.citation_key
            FROM items i
            LEFT JOIN scores s ON s.item_id = i.id AND s.version = ?
            LEFT JOIN pdfs p ON p.item_id = i.id
            LEFT JOIN summaries sm ON sm.item_id = i.id
            LEFT JOIN zotero_items z ON z.item_id = i.id
            WHERE i.topic_id = ? AND (i.published_at LIKE ? OR i.first_seen_at LIKE ?)
            ORDER BY COALESCE(s.total, 0) DESC, i.published_at DESC
            LIMIT ?
            """,
            (version, topic_id, f"{date_prefix}%", f"{date_prefix}%", limit),
        ).fetchall()


def topic_header(topic: Topic, date_prefix: str) -> list[str]:
    return [
        f"# {topic.name} - {date_prefix}",
        "",
        f"- Topic ID: `{topic.id}`",
        f"- 默认关注点: `{topic.default_focus}`",
        f"- 每日精选: {topic.daily_limit}",
        "",
    ]


def format_item(index: int, row, note_path: Path) -> list[str]:
    score = row["total"] if row["total"] is not None else 0
    reasons = json.loads(row["reasons_json"] or "[]")
    features = json.loads(row["features_json"] or "{}")
    provenance = build_provenance(row)
    pdf_link = provenance.local_pdf_markdown(note_path)
    lines = [
        f"## {index}. {row['title']}",
        "",
        f"- 评分：{score:.2f}",
        f"- 来源：{row['source_id']} / {row['venue']}",
        f"- 时间：{row['published_at']}",
        f"- 直接信息源：{provenance.direct_markdown}",
        f"- 溯源信息：{provenance.origin_markdown}",
        f"- PDF 源链接：{provenance.pdf_source_url or 'N/A'}",
        f"- PDF 本地状态：{provenance.pdf_status}",
    ]
    if pdf_link:
        lines.append(f"- PDF 本地链接：{pdf_link}")
    elif row["pdf_path"]:
        lines.append(f"- PDF 本地路径：{row['pdf_path']}")
    if row["pdf_error"]:
        lines.append(f"- PDF 错误：{row['pdf_error']}")
    if row["code_url"]:
        lines.append(f"- 代码：{row['code_url']}")
    lines.extend(
        [
            f"- 评分理由：{'; '.join(reasons) if reasons else '暂无'}",
            f"- 特征：`{json.dumps(features, ensure_ascii=False)}`",
            "",
            row["summary_text"] or f"**摘要**：{row['abstract'] or '暂无摘要。'}",
            "",
            "反馈：`未标记`",
            "",
        ]
    )
    return lines
def feedback_block(topic_id: str) -> list[str]:
    return [
        "## 反馈区",
        "",
        f"可用命令（仓库根目录）：`$env:PYTHONPATH='.system'; python -m research_push feedback --date today --topic {topic_id}`",
        "",
    ]
