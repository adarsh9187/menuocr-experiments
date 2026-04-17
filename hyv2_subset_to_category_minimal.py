"""
Transform a hyv2 subset into category_item_minimal JSON using Azure OpenAI.

The input JSON should contain a subset of hyv2 category responses consisting of:
- one category with category_role = "normal_category"
- zero or more shared sections that apply to that category
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError


SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / ".env"
TARGET_SCHEMA_PATH = SCRIPT_DIR.parent / "menuocr" / "schemas" / "category_item_minimal.schema.json"
PROMPT_PATH = SCRIPT_DIR / "hyv2_to_category_item_minimal_prompt.md"


class SizePriceEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    Name: str
    Price: Optional[float] = None


class ChoicePriceBySize(BaseModel):
    model_config = ConfigDict(extra="allow")

    sizeName: Optional[str] = None
    price: float


class ModifierChoice(BaseModel):
    model_config = ConfigDict(extra="allow")

    optionName: Optional[str] = None
    minRequired: Optional[int] = None
    maxAllowed: Optional[int] = None
    choiceName: str
    choicePrice: Optional[float] = None
    choicePriceBySize: List[ChoicePriceBySize] = []


class ToppingEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    group: Optional[str] = None
    price: Optional[float] = None
    priceHalf: Optional[float] = None


class ToppingsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default: List[str] = []
    available: List[ToppingEntry] = []


class ItemPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    s_no: Optional[str] = ""
    name: str
    price: Optional[float] = None
    options: List[ModifierChoice] = []
    itemDescription: Optional[str] = ""
    toppings: Optional[ToppingsPayload] = None
    ItemSizes: List[SizePriceEntry] = Field(default_factory=list)


class CategoryItemMinimalPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_description: str
    category_sizes: List[SizePriceEntry] = []
    category_options: List[ModifierChoice] = []
    category_toppings: Optional[ToppingsPayload] = None
    items: List[ItemPayload]


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _normalize_required_number(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _drop_none_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _drop_none_values(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_drop_none_values(v) for v in value]
    return value


def normalize_output_obj(output_obj: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(output_obj)
    normalized["category_description"] = _normalize_text(normalized.get("category_description"))
    normalized["items"] = list(normalized.get("items") or [])
    if normalized.get("category_toppings") is None:
        normalized.pop("category_toppings", None)
    normalized["category_sizes"] = list(normalized.get("category_sizes") or [])
    normalized["category_options"] = list(normalized.get("category_options") or [])

    normalized_category_sizes: List[Dict[str, Any]] = []
    for size in normalized["category_sizes"]:
        if not isinstance(size, dict):
            continue
        normalized_size = dict(size)
        normalized_size["Name"] = _normalize_text(normalized_size.get("Name"))
        normalized_size["Price"] = _normalize_required_number(normalized_size.get("Price"))
        normalized_category_sizes.append(_drop_none_values(normalized_size))
    normalized["category_sizes"] = normalized_category_sizes

    normalized_category_options: List[Dict[str, Any]] = []
    for option in normalized["category_options"]:
        if not isinstance(option, dict):
            continue
        normalized_option = dict(option)
        normalized_option["choiceName"] = _normalize_text(normalized_option.get("choiceName"))
        cps = normalized_option.get("choicePriceBySize") or []
        normalized_cpbs: List[Dict[str, Any]] = []
        for entry in cps:
            if not isinstance(entry, dict):
                continue
            normalized_entry = dict(entry)
            normalized_entry["sizeName"] = _normalize_text(normalized_entry.get("sizeName"))
            normalized_entry["price"] = _normalize_required_number(normalized_entry.get("price"))
            normalized_cpbs.append(_drop_none_values(normalized_entry))
        normalized_option["choicePriceBySize"] = normalized_cpbs
        normalized_category_options.append(_drop_none_values(normalized_option))
    normalized["category_options"] = normalized_category_options

    normalized_items: List[Dict[str, Any]] = []
    for item in normalized["items"]:
        if not isinstance(item, dict):
            continue
        normalized_item = dict(item)
        normalized_item["s_no"] = _normalize_text(normalized_item.get("s_no", ""))
        normalized_item["name"] = _normalize_text(normalized_item.get("name"))
        normalized_item["price"] = _normalize_required_number(normalized_item.get("price"))
        normalized_item["itemDescription"] = _normalize_text(normalized_item.get("itemDescription"))
        item_options = list(normalized_item.get("options") or [])
        normalized_options: List[Dict[str, Any]] = []
        for option in item_options:
            if not isinstance(option, dict):
                continue
            normalized_option = dict(option)
            normalized_option["choiceName"] = _normalize_text(normalized_option.get("choiceName"))
            cps = normalized_option.get("choicePriceBySize") or []
            normalized_cpbs: List[Dict[str, Any]] = []
            for entry in cps:
                if not isinstance(entry, dict):
                    continue
                normalized_entry = dict(entry)
                normalized_entry["sizeName"] = _normalize_text(normalized_entry.get("sizeName"))
                normalized_entry["price"] = _normalize_required_number(normalized_entry.get("price"))
                normalized_cpbs.append(_drop_none_values(normalized_entry))
            normalized_option["choicePriceBySize"] = normalized_cpbs
            normalized_options.append(_drop_none_values(normalized_option))
        normalized_item["options"] = normalized_options

        item_sizes = list(normalized_item.get("ItemSizes") or [])
        normalized_item_sizes: List[Dict[str, Any]] = []
        for size in item_sizes:
            if not isinstance(size, dict):
                continue
            normalized_size = dict(size)
            normalized_size["Name"] = _normalize_text(normalized_size.get("Name"))
            normalized_size["Price"] = _normalize_required_number(normalized_size.get("Price"))
            normalized_item_sizes.append(_drop_none_values(normalized_size))
        normalized_item["ItemSizes"] = normalized_item_sizes
        if normalized_item.get("toppings") is None:
            normalized_item.pop("toppings", None)
        normalized_items.append(_drop_none_values(normalized_item))

    normalized["items"] = normalized_items
    return _drop_none_values(normalized)


MODEL_NAME = Literal["gpt-4o", "text-embedding-ada-002"]

MODEL_CONFIG: Dict[str, Dict[str, str]] = {
    "gpt-4o": {
        "endpoint_env": "AZURE_OPENAI_GPT4O_ENDPOINT",
        "key_env": "AZURE_OPENAI_GPT4O_API_KEY",
        "kind": "chat",
    },
    "text-embedding-ada-002": {
        "endpoint_env": "AZURE_OPENAI_EMBEDDING_ENDPOINT",
        "key_env": "AZURE_OPENAI_EMBEDDING_API_KEY",
        "kind": "embedding",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transform a hyv2 subset JSON into category_item_minimal JSON using Azure OpenAI."
    )
    parser.add_argument("input", type=Path, help="Path to the subset input JSON.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path for the transformed JSON.",
    )
    parser.add_argument(
        "--model",
        choices=list(MODEL_CONFIG.keys()),
        default="gpt-4o",
        help="Azure OpenAI deployment to use.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature for the chat model.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4000,
        help="Maximum completion tokens for the chat model.",
    )
    return parser.parse_args()


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


def build_messages(subset_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    prompt_text = load_text(PROMPT_PATH)
    schema_text = load_text(TARGET_SCHEMA_PATH)
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


def call_azure_chat_completion(
    *,
    endpoint: str,
    api_key: str,
    messages: List[Dict[str, Any]],
    temperature: float,
    max_tokens: int,
) -> Dict[str, Any]:
    response = requests.post(
        endpoint,
        headers={
            "Content-Type": "application/json",
            "api-key": api_key,
        },
        json={
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        },
        timeout=300,
    )
    response.raise_for_status()
    return response.json()


def transform_subset(
    *,
    subset_payload: Dict[str, Any],
    model_name: MODEL_NAME,
    temperature: float,
    max_tokens: int,
) -> Tuple[CategoryItemMinimalPayload, Dict[str, Any]]:
    config = MODEL_CONFIG[model_name]
    if config["kind"] != "chat":
        raise ValueError(
            f"The selected model '{model_name}' is an embeddings model and cannot generate "
            "category_item_minimal JSON. Use 'gpt-4o' for this pipeline."
        )

    endpoint = os.getenv(config["endpoint_env"])
    api_key = os.getenv(config["key_env"])
    if not endpoint or not api_key:
        raise ValueError(
            f"Missing Azure OpenAI configuration. Expected env vars: "
            f"{config['endpoint_env']} and {config['key_env']}."
        )

    messages = build_messages(subset_payload)
    raw_response = call_azure_chat_completion(
        endpoint=endpoint,
        api_key=api_key,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = raw_response["choices"][0]["message"]["content"]
    output_obj = extract_json_object(content)

    output_obj = normalize_output_obj(output_obj)
    payload = CategoryItemMinimalPayload.model_validate(output_obj)
    usage = raw_response.get("usage") or {}
    return payload, usage


def main() -> None:
    load_dotenv(ENV_PATH)
    args = parse_args()

    subset_payload = json.loads(args.input.read_text(encoding="utf-8"))
    validated, usage = transform_subset(
        subset_payload=subset_payload,
        model_name=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )

    output_path = args.output or args.input.with_name(f"{args.input.stem}_category_item_minimal.json")
    output_path = next_available_path(output_path)
    output_path.write_text(
        json.dumps(validated.model_dump(by_alias=True), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote transformed payload to {output_path}")
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")
    print(
        "Token usage:"
        f" prompt={prompt_tokens if prompt_tokens is not None else 'unknown'}"
        f", completion={completion_tokens if completion_tokens is not None else 'unknown'}"
        f", total={total_tokens if total_tokens is not None else 'unknown'}"
    )


if __name__ == "__main__":
    try:
        main()
    except ValidationError as exc:
        raise SystemExit(f"Pydantic validation failed: {exc}") from exc
    except requests.HTTPError as exc:
        body = exc.response.text if exc.response is not None else ""
        raise SystemExit(f"Azure OpenAI request failed: {exc}\n{body}") from exc
