from __future__ import annotations

from . import db, scoring


VALID_LABELS = {"有用", "一般", "无关", "太难复现", "想多看类似", "想少看类似", "useful", "irrelevant", "more_like_this", "less_like_this"}


def record_feedback(item_id: str, topic_id: str, label: str, note: str, scoring_config: dict) -> None:
    if label not in VALID_LABELS:
        raise ValueError(f"Unsupported feedback label: {label}")
    scoring.apply_feedback(topic_id, item_id, label, note, scoring_config)


def interactive_feedback(date_prefix: str | None, topic_id: str | None, scoring_config: dict) -> int:
    rows = db.list_items(topic_id=topic_id, date_prefix=date_prefix, limit=30)
    if not rows:
        print("No items found for feedback.")
        return 0
    for index, row in enumerate(rows, start=1):
        print(f"{index}. [{row['topic_id']}] {row['title']}")
    raw = input("Item number (blank to cancel): ").strip()
    if not raw:
        return 0
    index = int(raw) - 1
    row = rows[index]
    label = input("Label (有用/一般/无关/太难复现/想多看类似/想少看类似): ").strip()
    note = input("Note (optional): ").strip()
    record_feedback(row["id"], row["topic_id"], label, note, scoring_config)
    print("Feedback recorded.")
    return 1

