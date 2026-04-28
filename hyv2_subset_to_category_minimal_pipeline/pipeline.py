from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

from .client import (
    call_azure_chat_completion_json_mode,
    call_azure_chat_completion_structured,
    extract_response_content,
    resolve_chat_credentials,
)
from .config import PROMPT_PATH, TARGET_SCHEMA_PATH, GenerationMode, ModelName
from .io_utils import extract_json_object
from .models import CategoryItemMinimalPayload
from .normalize import normalize_output_obj
from .prompting import build_messages, build_structured_response_format


GENERATION_MODE = ("json_mode", "structured")


def _generate_output_obj(
    *,
    endpoint: str,
    api_key: str,
    messages: list[dict[str, Any]],
    generation_mode: GenerationMode,
    temperature: float,
    max_tokens: int,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if generation_mode == "structured":
        raw_response = call_azure_chat_completion_structured(
            endpoint=endpoint,
            api_key=api_key,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=build_structured_response_format(),
        )
    elif generation_mode == "json_mode":
        raw_response = call_azure_chat_completion_json_mode(
            endpoint=endpoint,
            api_key=api_key,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        raise ValueError(
            f"Unsupported generation mode '{generation_mode}'. "
            f"Expected one of: {', '.join(GENERATION_MODE)}."
        )

    content = extract_response_content(raw_response)
    return extract_json_object(content), raw_response.get("usage") or {}


def transform_subset(
    *,
    subset_payload: Dict[str, Any],
    model_name: ModelName,
    generation_mode: GenerationMode = "json_mode",
    temperature: float,
    max_tokens: int,
    prompt_path: Path = PROMPT_PATH,
    target_schema_path: Path = TARGET_SCHEMA_PATH,
) -> Tuple[CategoryItemMinimalPayload, Dict[str, Any]]:
    endpoint, api_key = resolve_chat_credentials(model_name)
    messages = build_messages(
        subset_payload,
        generation_mode=generation_mode,
        prompt_path=prompt_path,
        target_schema_path=target_schema_path,
    )
    output_obj, usage = _generate_output_obj(
        endpoint=endpoint,
        api_key=api_key,
        messages=messages,
        generation_mode=generation_mode,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    validated = CategoryItemMinimalPayload.model_validate(normalize_output_obj(output_obj))
    return validated, usage
