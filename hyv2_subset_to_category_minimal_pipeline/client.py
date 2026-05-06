from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

import requests

from .config import MODEL_CONFIG, ModelName


def resolve_chat_credentials(model_name: ModelName) -> Tuple[str, str]:
    config = MODEL_CONFIG[model_name]
    if config["kind"] != "chat":
        raise ValueError(
            f"The selected model '{model_name}' is an embeddings model and cannot generate "
            "category_item_minimal JSON. Use a chat model such as 'gpt-5-mini' or 'gpt-4o' for this pipeline."
        )

    endpoint = os.getenv(config["endpoint_env"])
    api_key = os.getenv(config["key_env"])
    if not endpoint or not api_key:
        raise ValueError(
            f"Missing Azure OpenAI configuration. Expected env vars: "
            f"{config['endpoint_env']} and {config['key_env']}."
        )
    return endpoint, api_key


def _post_azure_chat_completion(
    *,
    endpoint: str,
    api_key: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    response = requests.post(
        endpoint,
        headers={
            "Content-Type": "application/json",
            "api-key": api_key,
        },
        json=payload,
        timeout=300,
    )
    response.raise_for_status()
    return response.json()


def call_azure_chat_completion_json_mode(
    *,
    endpoint: str,
    api_key: str,
    messages: List[Dict[str, Any]],
    temperature: float,
    max_tokens: int,
) -> Dict[str, Any]:
    return _post_azure_chat_completion(
        endpoint=endpoint,
        api_key=api_key,
        payload={
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        },
    )


def call_azure_chat_completion_structured(
    *,
    endpoint: str,
    api_key: str,
    messages: List[Dict[str, Any]],
    temperature: float,
    max_tokens: int,
    response_format: Dict[str, Any],
) -> Dict[str, Any]:
    return _post_azure_chat_completion(
        endpoint=endpoint,
        api_key=api_key,
        payload={
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": response_format,
        },
    )


def extract_response_content(response_json: Dict[str, Any]) -> str:
    choices = response_json.get("choices") or []
    if not choices:
        raise ValueError("Azure OpenAI response did not include any choices.")

    message = choices[0].get("message") or {}
    refusal = message.get("refusal")
    if refusal:
        raise ValueError(f"Model refused the request: {refusal}")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Azure OpenAI response did not include textual JSON content.")
    return content
