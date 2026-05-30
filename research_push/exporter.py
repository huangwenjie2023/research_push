from __future__ import annotations

import json
from datetime import datetime

from . import db
from .models import Topic
from .paths import NOTES_DIR


def export_notes(topics: list[Topic], date_prefix: str, scoring_version: str = "v1", extra_limit: int = 0) -> int:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    daily_dir = NOTES_DIR / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
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
        topic_path = NOTES_DIR / topic.directory / f"{date_prefix}.md"
        topic_path.parent.mkdir(parents=True, exist_ok=True)
        topic_lines = topic_header(topic, date_prefix)
        for index, row in enumerate(rows, start=1):
            topic_lines.extend(format_item(index, row))
        topic_lines.extend(feedback_block(topic.id))
        topic_path.write_text("\n".join(topic_lines), encoding="utf-8")

        daily_lines.extend([f"## {topic.name}", ""])
        if not rows:
            daily_lines.extend(["今日暂无候选。", ""])
            continue
        for index, row in enumerate(rows[: topic.daily_limit], start=1):
            score = row["total"] if row["total"] is not None else 0
            daily_lines.append(f"{index}. **{row['title']}**（{score:.2f}） - {row['url']}")
        daily_lines.extend(["", f"更多：[[../{topic.directory}/{date_prefix}|{topic.name} 日报]]", ""])
    daily_lines.extend(["## 今日反馈区", "", "- 觉得有用：", "- 想多看：", "- 想少看：", "- 临时关注点：", ""])
    (daily_dir / f"{date_prefix}.md").write_text("\n".join(daily_lines), encoding="utf-8")
    return total


def select_ranked(topic_id: str, limit: int, version: str, date_prefix: str) -> list:
    with db.connect() as con:
        return con.execute(
            """
            SELECT i.*, s.total, s.features_json, s.reasons_json, p.path AS pdf_path, p.status AS pdf_status,
                   p.error AS pdf_error, sm.summary_text, sm.provider
            FROM items i
            LEFT JOIN scores s ON s.item_id = i.id AND s.version = ?
            LEFT JOIN pdfs p ON p.item_id = i.id
            LEFT JOIN summaries sm ON sm.item_id = i.id
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


def format_item(index: int, row) -> list[str]:
    score = row["total"] if row["total"] is not None else 0
    reasons = json.loads(row["reasons_json"] or "[]")
    features = json.loads(row["features_json"] or "{}")
    lines = [
        f"## {index}. {row['title']}",
        "",
        f"- 评分：{score:.2f}",
        f"- 来源：{row['source_id']} / {row['venue']}",
        f"- 时间：{row['published_at']}",
        f"- 链接：{row['url']}",
        f"- PDF：{row['pdf_url'] or 'N/A'}",
        f"- PDF 本地状态：{row['pdf_status'] or 'not_fetched'}",
    ]
    if row["pdf_path"]:
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
        f"可用命令：`python -m research_push feedback --date today --topic {topic_id}`",
        "",
    ]

