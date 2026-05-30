from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import datetime, timezone

from . import db
from .models import Item, RankedItem, Topic


def score_all(topics: list[Topic], scoring_config: dict) -> int:
    version = scoring_config.get("version", "v1")
    topic_by_id = {topic.id: topic for topic in topics}
    count = 0
    with db.connect() as con:
        rows = con.execute("SELECT * FROM items").fetchall()
        for row in rows:
            topic = topic_by_id.get(row["topic_id"])
            if not topic:
                continue
            item = db.row_to_item(row)
            score, features, reasons = score_item(item, topic, scoring_config, load_feedback_state(row["topic_id"]))
            con.execute(
                """
                INSERT INTO scores (item_id, version, total, features_json, reasons_json, scored_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_id, version) DO UPDATE SET
                    total=excluded.total,
                    features_json=excluded.features_json,
                    reasons_json=excluded.reasons_json,
                    scored_at=excluded.scored_at
                """,
                (row["id"], version, score, json.dumps(features, ensure_ascii=False), json.dumps(reasons, ensure_ascii=False), db.now_iso()),
            )
            count += 1
    return count


def score_item(item: Item, topic: Topic, config: dict, feedback_state: dict | None = None) -> tuple[float, dict[str, float], list[str]]:
    feedback_state = feedback_state or {}
    text = f"{item.title} {item.abstract} {item.venue}".lower()
    features: dict[str, float] = {}
    reasons: list[str] = []

    primary_hits = keyword_hits(text, topic.keywords)
    expanded_hits = keyword_hits(text, topic.expanded_keywords)
    negative_hits = keyword_hits(text, topic.negative_keywords)
    features["topic_relevance"] = min(1.0, primary_hits * 0.22 + expanded_hits * 0.12)
    features["negative_match"] = min(1.0, negative_hits * 0.5)
    if primary_hits:
        reasons.append(f"主题关键词命中 {primary_hits} 个")
    if expanded_hits:
        reasons.append(f"扩展关键词命中 {expanded_hits} 个")
    if negative_hits:
        reasons.append(f"负关键词命中 {negative_hits} 个")

    features["novelty"] = novelty_score(item.published_at)
    if features["novelty"] > 0.7:
        reasons.append("近期内容")

    source_quality = config.get("source_quality", {}).get(item.source_id, 0.5)
    features["source_quality"] = float(source_quality)
    features["research_value"] = research_value(item)
    features["actionability"] = actionability(item)
    features["hardware_fit"] = hardware_fit(item, config.get("hardware", {}))
    features["representativeness"] = representativeness(item)
    features["diversity"] = 0.7

    if item.pdf_url:
        reasons.append("有可追溯 PDF 链接")
    if item.code_url or "github" in text:
        reasons.append("可能有代码或项目页")
    if features["hardware_fit"] < 0.4:
        reasons.append("可能需要较大算力，作为扩展视野")

    weights = dict(config.get("weights", {}))
    for key, multiplier in feedback_state.get("feature_multipliers", {}).items():
        if key in weights:
            weights[key] = weights[key] * float(multiplier)

    total = sum(features.get(name, 0.0) * float(weight) for name, weight in weights.items())
    method_bonus = feedback_method_bonus(text, feedback_state)
    if method_bonus:
        total += method_bonus
        reasons.append(f"符合近期反馈偏好 +{method_bonus:.2f}")
    return round(total, 4), features, reasons


def top_ranked(topic_id: str, limit: int, version: str = "v1", date_prefix: str | None = None) -> list[dict]:
    with db.connect() as con:
        clauses = ["i.topic_id = ?"]
        params: list[object] = [topic_id]
        if date_prefix:
            clauses.append("(i.published_at LIKE ? OR i.first_seen_at LIKE ?)")
            params.extend([f"{date_prefix}%", f"{date_prefix}%"])
        rows = con.execute(
            f"""
            SELECT i.*, s.total, s.features_json, s.reasons_json, p.path AS pdf_path, p.status AS pdf_status,
                   p.error AS pdf_error, p.text_excerpt, sm.summary_text
            FROM items i
            LEFT JOIN scores s ON s.item_id = i.id AND s.version = ?
            LEFT JOIN pdfs p ON p.item_id = i.id
            LEFT JOIN summaries sm ON sm.item_id = i.id
            WHERE {" AND ".join(clauses)}
            ORDER BY COALESCE(s.total, 0) DESC, i.published_at DESC
            LIMIT ?
            """,
            [version, *params, limit],
        ).fetchall()
    return [dict(row) for row in rows]


def keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for word in keywords if word.lower() in text)


def novelty_score(value: str) -> float:
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 0.4
    days = max(0, (datetime.now(timezone.utc) - date).days)
    return max(0.1, math.exp(-days / 120))


def research_value(item: Item) -> float:
    source = item.source_id.lower()
    text = f"{item.title} {item.abstract}".lower()
    if source in {"arxiv", "semantic_scholar", "ieee"}:
        return 0.85
    if any(word in text for word in ["paper", "benchmark", "dataset", "experiment"]):
        return 0.65
    return 0.4


def actionability(item: Item) -> float:
    text = f"{item.title} {item.abstract} {item.url} {item.code_url}".lower()
    score = 0.25
    if item.pdf_url:
        score += 0.2
    if item.code_url or "github" in text or "code" in text:
        score += 0.25
    if any(word in text for word in ["dataset", "implementation", "training", "open source"]):
        score += 0.2
    return min(1.0, score)


def hardware_fit(item: Item, hardware_config: dict) -> float:
    text = f"{item.title} {item.abstract}".lower()
    score = 0.65
    for word in hardware_config.get("positive_keywords", []):
        if word.lower() in text:
            score += 0.12
    for word in hardware_config.get("negative_keywords", []):
        if word.lower() in text:
            score -= 0.2
    return min(1.0, max(0.1, score))


def representativeness(item: Item) -> float:
    text = f"{item.title} {item.abstract}".lower()
    if any(word in text for word in ["survey", "benchmark", "state-of-the-art", "sota", "comprehensive"]):
        return 0.9
    if item.source_id in {"arxiv", "semantic_scholar", "ieee"}:
        return 0.65
    return 0.45


def load_feedback_state(topic_id: str) -> dict:
    with db.connect() as con:
        row = con.execute("SELECT state_json FROM feedback_state WHERE topic_id = ?", (topic_id,)).fetchone()
    return json.loads(row["state_json"]) if row else {}


def apply_feedback(topic_id: str, item_id: str, label: str, note: str, scoring_config: dict) -> None:
    with db.connect() as con:
        row = con.execute("SELECT title, abstract FROM items WHERE id = ?", (item_id,)).fetchone()
        state_row = con.execute("SELECT state_json FROM feedback_state WHERE topic_id = ?", (topic_id,)).fetchone()
        state = json.loads(state_row["state_json"]) if state_row else {"feature_multipliers": {}, "preferred_terms": {}}
        con.execute(
            "INSERT INTO feedback (item_id, topic_id, label, note, created_at) VALUES (?, ?, ?, ?, ?)",
            (item_id, topic_id, label, note, db.now_iso()),
        )
        if row:
            update_state_from_feedback(state, f"{row['title']} {row['abstract']} {note}", label, scoring_config)
        con.execute(
            """
            INSERT INTO feedback_state (topic_id, state_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(topic_id) DO UPDATE SET state_json=excluded.state_json, updated_at=excluded.updated_at
            """,
            (topic_id, json.dumps(state, ensure_ascii=False), db.now_iso()),
        )


def update_state_from_feedback(state: dict, text: str, label: str, config: dict) -> None:
    feedback_cfg = config.get("feedback", {})
    lr = float(feedback_cfg.get("learning_rate", 0.12))
    min_w = float(feedback_cfg.get("min_weight", 0.2))
    max_w = float(feedback_cfg.get("max_weight", 3.0))
    sign = 1 if label in {"有用", "想多看类似", "useful", "more_like_this"} else -1
    multipliers = state.setdefault("feature_multipliers", {})
    for feature in ("topic_relevance", "actionability", "hardware_fit"):
        current = float(multipliers.get(feature, 1.0))
        multipliers[feature] = round(min(max_w, max(min_w, current + sign * lr)), 4)
    terms = Counter(re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", text.lower()))
    preferred = state.setdefault("preferred_terms", {})
    for term, count in terms.most_common(8):
        current = float(preferred.get(term, 0.0))
        preferred[term] = round(current + sign * min(0.4, count * lr), 4)


def feedback_method_bonus(text: str, state: dict) -> float:
    bonus = 0.0
    for term, value in state.get("preferred_terms", {}).items():
        if term in text:
            bonus += float(value)
    return max(-1.5, min(1.5, bonus))

