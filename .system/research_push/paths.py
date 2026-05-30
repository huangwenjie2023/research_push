from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SYSTEM_DIR = ROOT / ".system"
CONFIG_DIR = SYSTEM_DIR / "config"
DATA_DIR = SYSTEM_DIR / "data"
NOTES_DIR = ROOT / "Knowledge"
PAPERS_DIR = NOTES_DIR / "Papers"
FEEDBACK_DIR = NOTES_DIR / "Feedback"
LOGS_DIR = SYSTEM_DIR / "logs"
DB_PATH = DATA_DIR / "research_push.sqlite3"


def ensure_dirs() -> None:
    for path in (DATA_DIR, NOTES_DIR, FEEDBACK_DIR, LOGS_DIR):
        path.mkdir(parents=True, exist_ok=True)
