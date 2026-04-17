from __future__ import annotations

from pathlib import Path


def build_nova_extraction_prompt(*, schema_path: Path, prompt_path: Path) -> str:
    schema_text = schema_path.read_text(encoding="utf-8")
    prompt_text = prompt_path.read_text(encoding="utf-8")
    return (
        "You are an expert menu analyst using visual layout and text together.\n\n"
        "You will receive one or more menu page images.\n"
        "Return a JSON object that matches the schema exactly.\n"
        "Do not include markdown fences.\n"
        "Do not include any commentary outside the JSON object.\n\n"
        "Schema:\n"
        f"{schema_text}\n\n"
        "Prompt instructions:\n"
        f"{prompt_text}\n"
    )
