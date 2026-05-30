from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .paths import CONFIG_DIR, ROOT


def load_env(path: Path | None = None) -> None:
    env_path = path or ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_structured(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
    except Exception:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object at the top level")
    return data


def load_all() -> dict[str, Any]:
    return {
        "topics": load_structured(CONFIG_DIR / "topics.yaml"),
        "sources": load_structured(CONFIG_DIR / "sources.yaml"),
        "scoring": load_structured(CONFIG_DIR / "scoring.yaml"),
        "focus_profiles": load_structured(CONFIG_DIR / "focus_profiles.yaml"),
        "llm": load_structured(CONFIG_DIR / "llm.yaml"),
    }


def today_string(value: str | None) -> str:
    from datetime import datetime

    if not value or value == "today":
        return datetime.now().strftime("%Y-%m-%d")
    return value

