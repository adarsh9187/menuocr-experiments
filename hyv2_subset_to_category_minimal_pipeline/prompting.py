from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Type

from .config import GenerationMode
from .io_utils import load_text
from .normalize import drop_description_properties
from .models import CategoryItemMinimalPayload


def build_messages(
    subset_payload: Dict[str, Any],
    *,
    generation_mode: GenerationMode,
    prompt_path: Path,
    target_schema_path: Path,
) -> List[Dict[str, Any]]:
    prompt_text = load_text(prompt_path)
    subset_text = json.dumps(subset_payload, indent=2, ensure_ascii=False)

    system = (
        "You convert menu extraction subsets into structured menu JSON. "
        "Return only valid JSON."
    )
    if generation_mode == "structured":
        user = (
            f"{prompt_text}\n\n"
            f"Input subset JSON:\n{subset_text}\n"
        )
    else:
        raw_schema = json.loads(load_text(target_schema_path))
        schema_text = json.dumps(drop_description_properties(raw_schema), indent=2, ensure_ascii=False)
        user = (
            f"{prompt_text}\n\n"
            f"Target schema:\n{schema_text}\n\n"
            f"Input subset JSON:\n{subset_text}\n"
        )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _strip_nonessential_schema_metadata(value: Any, *, inside_properties: bool = False) -> Any:
    if isinstance(value, dict):
        stripped: Dict[str, Any] = {}
        for key, child in value.items():
            if not inside_properties and key in {"default", "title", "description", "examples"}:
                continue
            stripped[key] = _strip_nonessential_schema_metadata(
                child,
                inside_properties=(key == "properties"),
            )
        return stripped
    if isinstance(value, list):
        return [
            _strip_nonessential_schema_metadata(child, inside_properties=inside_properties)
            for child in value
        ]
    return value


def _coerce_schema_for_strict_structured_outputs(value: Any) -> Any:
    if isinstance(value, dict):
        coerced = {
            key: _coerce_schema_for_strict_structured_outputs(child)
            for key, child in value.items()
        }
        if coerced.get("type") == "object":
            properties = coerced.get("properties")
            if isinstance(properties, dict):
                coerced["required"] = list(properties.keys())
            coerced["additionalProperties"] = False
        return coerced
    if isinstance(value, list):
        return [_coerce_schema_for_strict_structured_outputs(child) for child in value]
    return value


def build_structured_response_format(
    model: Type[CategoryItemMinimalPayload] = CategoryItemMinimalPayload,
) -> Dict[str, Any]:
    schema = _strip_nonessential_schema_metadata(model.model_json_schema())
    schema = _coerce_schema_for_strict_structured_outputs(schema)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "category_item_minimal_payload",
            "strict": True,
            "schema": schema,
        },
    }
