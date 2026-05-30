from __future__ import annotations

import argparse
import sys

from . import db, exporter, feedback, llm, pdfs, scoring, server, sources
from .config import load_all, load_env, today_string
from .models import parse_topics
from .paths import ensure_dirs


def main(argv: list[str] | None = None) -> int:
    load_env()
    ensure_dirs()
    db.init_db()
    config = load_all()
    topics = parse_topics(config["topics"])

    parser = argparse.ArgumentParser(description="Research push knowledge base.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("collect", help="Collect metadata without LLM calls.")

    fetch_pdf = sub.add_parser("fetch-pdf", help="Download public PDFs for candidates.")
    fetch_pdf.add_argument("--date", default="today")
    fetch_pdf.add_argument("--topic")
    fetch_pdf.add_argument("--limit", type=int)
    fetch_pdf.add_argument("--force", action="store_true")

    rank = sub.add_parser("rank", help="Recompute transparent scores.")
    rank.add_argument("--date", default="today")

    summarize = sub.add_parser("summarize", help="Summarize items with PDF fusion.")
    summarize.add_argument("--date", default="today")
    summarize.add_argument("--topic")
    summarize.add_argument("--focus", default="method_results")
    summarize.add_argument("--limit", type=int)
    summarize.add_argument("--force", action="store_true")

    daily = sub.add_parser("daily", help="Run collect + pdf + rank + summarize + export.")
    daily.add_argument("--date", default="today")
    daily.add_argument("--focus", default="method_results")
    daily.add_argument("--pdf-limit", type=int, default=45)

    expand = sub.add_parser("expand", help="Show more ranked items for a topic.")
    expand.add_argument("--topic", required=True)
    expand.add_argument("--more", type=int, default=10)
    expand.add_argument("--date", default="today")

    refresh = sub.add_parser("refresh", help="Temporarily add search intent and update one topic.")
    refresh.add_argument("--topic", required=True)
    refresh.add_argument("--query", required=True)
    refresh.add_argument("--date", default="today")

    fb = sub.add_parser("feedback", help="Record feedback interactively or directly.")
    fb.add_argument("--date", default="today")
    fb.add_argument("--topic")
    fb.add_argument("--item-id")
    fb.add_argument("--label")
    fb.add_argument("--note", default="")

    serve = sub.add_parser("serve", help="Start local interface for Codex or other models.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)

    args = parser.parse_args(argv)
    date = today_string(getattr(args, "date", None))

    if args.command == "collect":
        items, warnings = sources.collect_all(config["sources"], topics)
        inserted = db.upsert_items(items)
        for warning in warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        print(f"Collected {len(items)} items, inserted {inserted} new items.")
        return 0

    if args.command == "fetch-pdf":
        count = pdfs.fetch_pdfs(args.topic, date, args.limit, args.force)
        print(f"Downloaded {count} PDFs.")
        return 0

    if args.command == "rank":
        count = scoring.score_all(topics, config["scoring"])
        print(f"Scored {count} items.")
        return 0

    if args.command == "summarize":
        count = llm.summarize_items(config, args.topic, date, args.focus, args.limit, args.force)
        exported = exporter.export_notes(topics, date, config["scoring"].get("version", "v1"))
        print(f"Summarized {count} items and exported {exported} note entries.")
        return 0

    if args.command == "daily":
        items, warnings = sources.collect_all(config["sources"], topics)
        inserted = db.upsert_items(items)
        scored = scoring.score_all(topics, config["scoring"])
        downloaded = pdfs.fetch_pdfs(date_prefix=date, limit=args.pdf_limit)
        summarized = llm.summarize_items(config, None, date, args.focus)
        exported = exporter.export_notes(topics, date, config["scoring"].get("version", "v1"))
        for warning in warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        print(f"Collected {len(items)} items ({inserted} new), scored {scored}, downloaded {downloaded} PDFs, summarized {summarized}, exported {exported}.")
        return 0

    if args.command == "expand":
        rows = scoring.top_ranked(args.topic, args.more, config["scoring"].get("version", "v1"), date)
        for index, row in enumerate(rows, start=1):
            print(f"{index}. {row['title']} | score={row.get('total')} | {row['url']}")
        return 0

    if args.command == "refresh":
        selected = [topic for topic in topics if topic.id == args.topic]
        if not selected:
            raise SystemExit(f"Unknown topic: {args.topic}")
        topic = selected[0]
        temp_topic = type(topic)(
            id=topic.id,
            name=topic.name,
            directory=topic.directory,
            daily_limit=topic.daily_limit,
            default_focus=topic.default_focus,
            keywords=(args.query, *topic.keywords),
            expanded_keywords=topic.expanded_keywords,
            negative_keywords=topic.negative_keywords,
        )
        items, warnings = sources.collect_all(config["sources"], [temp_topic])
        inserted = db.upsert_items(items)
        scoring.score_all(topics, config["scoring"])
        for warning in warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        print(f"Refreshed {args.topic} with query '{args.query}', inserted {inserted} new items.")
        return 0

    if args.command == "feedback":
        if args.item_id and args.label and args.topic:
            feedback.record_feedback(args.item_id, args.topic, args.label, args.note, config["scoring"])
            scoring.score_all(topics, config["scoring"])
            print("Feedback recorded and scores updated.")
            return 0
        return feedback.interactive_feedback(date, args.topic, config["scoring"])

    if args.command == "serve":
        server.run_server(args.host, args.port)
        return 0

    return 1

