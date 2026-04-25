from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

from .client import call_azure_chat_completion, resolve_chat_credentials
from .config import PROMPT_PATH, TARGET_SCHEMA_PATH, ModelName
from .io_utils import extract_json_object
from .models import CategoryItemMinimalPayload
from .normalize import normalize_output_obj
from .prompting import build_messages


def transform_subset(
    *,
    subset_payload: Dict[str, Any],
    model_name: ModelName,
    temperature: float,
    max_tokens: int,
    prompt_path: Path = PROMPT_PATH,
    target_schema_path: Path = TARGET_SCHEMA_PATH,
) -> Tuple[CategoryItemMinimalPayload, Dict[str, Any]]:
    endpoint, api_key = resolve_chat_credentials(model_name)
    messages = build_messages(
        subset_payload,
        prompt_path=prompt_path,
        target_schema_path=target_schema_path,
    )
    raw_response = call_azure_chat_completion(
        endpoint=endpoint,
        api_key=api_key,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = raw_response["choices"][0]["message"]["content"]
    output_obj = extract_json_object(content)
    validated = CategoryItemMinimalPayload.model_validate(normalize_output_obj(output_obj))
    usage = raw_response.get("usage") or {}
    return validated, usage
