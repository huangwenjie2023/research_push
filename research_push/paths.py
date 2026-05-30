from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
NOTES_DIR = ROOT / "notes"
PAPERS_DIR = ROOT / "papers"
FEEDBACK_DIR = ROOT / "feedback"
LOGS_DIR = ROOT / "logs"
DB_PATH = DATA_DIR / "research_push.sqlite3"


def ensure_dirs() -> None:
    for path in (DATA_DIR, NOTES_DIR, PAPERS_DIR, FEEDBACK_DIR, LOGS_DIR):
        path.mkdir(parents=True, exist_ok=True)

