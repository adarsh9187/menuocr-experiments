from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .io_utils import load_text
from .normalize import drop_description_properties


def build_messages(
    subset_payload: Dict[str, Any],
    *,
    prompt_path: Path,
    target_schema_path: Path,
) -> List[Dict[str, Any]]:
    prompt_text = load_text(prompt_path)
    raw_schema = json.loads(load_text(target_schema_path))
    schema_text = json.dumps(drop_description_properties(raw_schema), indent=2, ensure_ascii=False)
    subset_text = json.dumps(subset_payload, indent=2, ensure_ascii=False)

    system = (
        "You convert menu extraction subsets into structured menu JSON. "
        "Return only valid JSON."
    )
    user = (
        f"{prompt_text}\n\n"
        f"Target schema:\n{schema_text}\n\n"
        f"Input subset JSON:\n{subset_text}\n"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
