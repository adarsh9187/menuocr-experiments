from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def next_available_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = path.parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_json_object(text: str) -> Dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end <= start:
        raise ValueError("No JSON object found in model response.")
    return json.loads(text[start:end])
