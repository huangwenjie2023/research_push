from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import db, exporter, feedback, llm, pdfs, scoring, sources, zotero_sync
from .config import load_all, today_string
from .models import parse_topics


def run_server(host: str, port: int) -> None:
    config = load_all()
    db.init_db()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            if parsed.path == "/topics":
                topics = [topic.__dict__ for topic in parse_topics(config["topics"])]
                self.write_json({"topics": topics, "focus_profiles": config["focus_profiles"].get("profiles", {})})
                return
            if parsed.path == "/items":
                topic = first(query, "topic")
                date = today_string(first(query, "date"))
                limit = int(first(query, "limit") or 20)
                rows = db.list_items(topic_id=topic, date_prefix=date, limit=limit)
                self.write_json({"items": [dict(row) for row in rows]})
                return
            self.write_json({"error": "not found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            body = self.read_body()
            topics = parse_topics(config["topics"])
            if parsed.path == "/collect":
                items, warnings = sources.collect_all(config["sources"], topics)
                inserted = db.upsert_items(items)
                self.write_json({"inserted": inserted, "warnings": warnings})
                return
            if parsed.path == "/fetch_pdf":
                count = pdfs.fetch_pdfs(body.get("topic"), today_string(body.get("date")), body.get("limit"), body.get("force", False))
                self.write_json({"downloaded": count})
                return
            if parsed.path == "/summarize":
                count = llm.summarize_items(config, body.get("topic"), today_string(body.get("date")), body.get("focus", "method_results"), body.get("limit"), body.get("force", False))
                self.write_json({"summarized": count})
                return
            if parsed.path == "/expand":
                topic = body.get("topic")
                more = int(body.get("more", 10))
                date = today_string(body.get("date"))
                rows = scoring.top_ranked(topic, more, config["scoring"].get("version", "v1"), date)
                self.write_json({"items": rows})
                return
            if parsed.path == "/feedback":
                feedback.record_feedback(body["item_id"], body["topic_id"], body["label"], body.get("note", ""), config["scoring"])
                scoring.score_all(topics, config["scoring"])
                self.write_json({"ok": True})
                return
            if parsed.path == "/zotero_sync":
                selected = [topic for topic in topics if not body.get("topic") or topic.id == body.get("topic")]
                config["zotero"]["enabled"] = True
                stats = zotero_sync.sync_daily(config, selected, today_string(body.get("date")), body.get("limit"))
                self.write_json({"zotero": stats})
                return
            if parsed.path == "/zotero_init":
                result = zotero_sync.init_collections(config, topics, bool(body.get("include_topic_folders", False)))
                self.write_json({"zotero": result})
                return
            if parsed.path == "/focus":
                # Temporary focus preferences are intentionally returned to caller only.
                self.write_json({"focus": body.get("focus", "method_results"), "temporary": True})
                return
            self.write_json({"error": "not found"}, status=404)

        def read_body(self) -> dict:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))

        def write_json(self, payload: dict, status: int = 200) -> None:
            data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    print(f"Serving research_push on http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


def first(query: dict, key: str) -> str | None:
    values = query.get(key)
    return values[0] if values else None
