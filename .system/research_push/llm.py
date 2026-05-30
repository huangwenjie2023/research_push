from __future__ import annotations

import json
import os

from . import db
from .net import post_json


def summarize_items(config: dict, topic_id: str | None, date_prefix: str | None, focus: str, limit: int | None = None, force: bool = False) -> int:
    focus_profiles = config["focus_profiles"].get("profiles", {})
    focus_instruction = focus_profiles.get(focus, focus_profiles.get("method_results", {})).get("instruction", "")
    rows = select_items_for_summary(topic_id, date_prefix, limit)
    count = 0
    with db.connect() as con:
        for row in rows:
            if not force:
                existing = con.execute("SELECT 1 FROM summaries WHERE item_id = ? AND focus = ?", (row["id"], focus)).fetchone()
                if existing:
                    continue
            summary, provider = summarize_one(config["llm"], row, focus, focus_instruction)
            con.execute(
                """
                INSERT INTO summaries (item_id, focus, provider, summary_text, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(item_id, focus) DO UPDATE SET
                    provider=excluded.provider,
                    summary_text=excluded.summary_text,
                    created_at=excluded.created_at
                """,
                (row["id"], focus, provider, summary, db.now_iso()),
            )
            count += 1
    return count


def select_items_for_summary(topic_id: str | None, date_prefix: str | None, limit: int | None) -> list:
    clauses: list[str] = []
    params: list[object] = []
    if topic_id:
        clauses.append("i.topic_id = ?")
        params.append(topic_id)
    if date_prefix:
        clauses.append("(i.published_at LIKE ? OR i.first_seen_at LIKE ?)")
        params.extend([f"{date_prefix}%", f"{date_prefix}%"])
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    sql = f"""
        SELECT i.*, s.total, s.reasons_json, p.status AS pdf_status, p.error AS pdf_error,
               p.path AS pdf_path, p.text_excerpt
        FROM items i
        LEFT JOIN scores s ON s.item_id = i.id
        LEFT JOIN pdfs p ON p.item_id = i.id
        {where}
        ORDER BY COALESCE(s.total, 0) DESC, i.published_at DESC
    """
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    with db.connect() as con:
        return con.execute(sql, params).fetchall()


def summarize_one(llm_config: dict, row, focus: str, focus_instruction: str) -> tuple[str, str]:
    prompt = build_prompt(row, focus_instruction)
    for provider in sorted(llm_config.get("providers", []), key=lambda p: p.get("priority", 99)):
        if not provider.get("enabled", True):
            continue
        api_key = os.environ.get(provider.get("api_key_env", ""))
        if not api_key:
            continue
        for model in provider.get("models", []):
            try:
                data = post_json(
                    provider["base_url"].rstrip("/") + "/chat/completions",
                    {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "你是帮助博士生筛选研究论文的中文研究助理。输出简洁、可溯源、重方法和结果。"},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.2,
                    },
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=90,
                )
                content = data["choices"][0]["message"]["content"].strip()
                if content:
                    return content, f"{provider['name']}:{model}"
            except Exception:
                continue
    return heuristic_summary(row, focus), "local_heuristic"


def build_prompt(row, focus_instruction: str) -> str:
    authors = ", ".join(json.loads(row["authors_json"])[:6])
    reasons = ", ".join(json.loads(row["reasons_json"] or "[]")) if "reasons_json" in row.keys() and row["reasons_json"] else ""
    pdf_status = row["pdf_status"] or "not_fetched"
    pdf_text = (row["text_excerpt"] or "")[:9000]
    return f"""请基于元数据和 PDF 摘录写一段中文研究推送总结。

关注点：{focus_instruction}

必须包含：
1. 方法：核心 idea、模型/编码框架或 RL/生成流程。
2. 结果：压缩率/失真/速度/数据集/baseline 或生成质量指标；没有则明确说未从材料中看到。
3. 可做方向：结合 4 张 48G RTX 4090，给一个可尝试的小实验或研究联想。
4. 溯源：同时说明直接信息源和最终论文/项目源头；如果直接信息源已经是最终源头，用几个字说明“最终源头”即可。

标题：{row['title']}
作者：{authors}
来源：{row['source_id']} / {row['venue']}
时间：{row['published_at']}
直接信息源：{row['url']}
DOI：{row['doi']}
arXiv：{row['arxiv_id']}
PDF：{row['pdf_url']} / {pdf_status}
评分理由：{reasons}
摘要：{row['abstract']}

PDF 摘录：
{pdf_text}
"""


def heuristic_summary(row, focus: str) -> str:
    pdf_status = row["pdf_status"] or "not_fetched"
    abstract = row["abstract"] or "暂无摘要。"
    code_hint = "有代码/项目链接，适合优先检查复现。" if row["code_url"] else "暂未发现代码链接。"
    origin = origin_sentence(row)
    return (
        f"**方法/结果速览**：{abstract[:500]}\n\n"
        f"**可做方向联想**：先检查论文实验设置、数据集和开源情况；若训练规模不大，可尝试在 4x48G RTX 4090 上复现核心模块或做小规模消融。{code_hint}\n\n"
        f"**溯源**：直接信息源 [{row['source_id']}]({row['url']})；{origin}；PDF 状态：{pdf_status}。"
    )


def origin_sentence(row) -> str:
    if row["arxiv_id"]:
        url = row["url"] if "arxiv.org" in row["url"] else f"https://arxiv.org/abs/{row['arxiv_id']}"
        return f"论文源头 [arXiv 最终源头]({url})"
    if row["doi"]:
        return f"论文源头 [DOI 最终源头](https://doi.org/{row['doi']})"
    if row["source_id"] == "github":
        return "项目源头：GitHub 最终源头"
    if row["pdf_url"]:
        return f"论文源头 [PDF 可追溯源]({row['pdf_url']})"
    return "暂无更上游源头"
