from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional, Type

from pydantic import BaseModel, ConfigDict, Field

from .client import (
    call_azure_chat_completion_structured,
    extract_response_content,
    resolve_chat_credentials,
)
from .io_utils import extract_json_object
from .prompting import build_strict_structured_response_format


class DayHoursPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    OpenTime: str = "10:30"
    CloseTime: str = "21:00"
    DayShutOff: bool = False
    HourType: Literal["Business", "Carryout", "Delivery", "Pickup"] = "Business"
    UsedDefault: bool = False


class OperatingHoursPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    Monday: Optional[DayHoursPayload] = None
    Tuesday: Optional[DayHoursPayload] = None
    Wednesday: Optional[DayHoursPayload] = None
    Thursday: Optional[DayHoursPayload] = None
    Friday: Optional[DayHoursPayload] = None
    Saturday: Optional[DayHoursPayload] = None
    Sunday: Optional[DayHoursPayload] = None


class CategoryHoursEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_name: str
    hours: OperatingHoursPayload


class HoursBatchPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    global_hours: Optional[OperatingHoursPayload] = None
    category_hours: List[CategoryHoursEntry] = Field(default_factory=list)


def build_hours_input_payload(extracted: Dict[str, Any]) -> Dict[str, str]:
    payload: Dict[str, str] = {}

    global_hours = extracted.get("global_hours")
    if isinstance(global_hours, str) and global_hours.strip():
        payload["global_hours"] = global_hours.strip()

    categories = extracted.get("categories")
    if not isinstance(categories, list):
        return payload

    for category in categories:
        if not isinstance(category, dict):
            continue
        if category.get("category_role") != "normal_category":
            continue
        category_name = str(category.get("category_name") or "").strip()
        category_hours = category.get("category_hours")
        if not category_name or not isinstance(category_hours, str) or not category_hours.strip():
            continue
        payload[f"{category_name} hours"] = category_hours.strip()

    return payload


def build_hours_response_format(model: Type[HoursBatchPayload] = HoursBatchPayload) -> Dict[str, Any]:
    return build_strict_structured_response_format(
        model=model,
        schema_name="hours_batch_payload",
    )


def build_hours_messages(hours_input_payload: Dict[str, str]) -> List[Dict[str, str]]:
    payload_text = json.dumps(hours_input_payload, indent=2, ensure_ascii=False)
    system = (
        "You convert raw menu hours evidence into structured operating-hours JSON. "
        "Return only valid JSON."
    )
    user = (
        "You are given a JSON object containing raw extracted hours text from a menu.\n\n"
        "Input rules:\n"
        "- The key `global_hours` contains whole-menu hours when present.\n"
        "- Any other key ending with ` hours` contains hours that apply only to that individual category.\n"
        "- Do not duplicate whole-menu hours onto categories unless the category key explicitly has its own hours text.\n"
        "- Parse each non-empty hours string into day-by-day operating hours.\n"
        "- Use 24-hour `HH:MM` format.\n"
        "- Set `UsedDefault` to true only when you truly had to rely on defaults.\n"
        "- Preserve category identity exactly: for a key like `Lunch Specials hours`, return "
        "`category_name = \"Lunch Specials\"`.\n\n"
        "Return a JSON object with:\n"
        "- `global_hours`: parsed structured global hours or null\n"
        "- `category_hours`: a list of objects with `category_name` and parsed `hours`\n\n"
        f"Hours input JSON:\n{payload_text}\n"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def parse_hours_payload(
    *,
    hours_input_payload: Dict[str, str],
    model_name: str,
    temperature: float = 0.0,
    max_tokens: int = 4000,
) -> tuple[HoursBatchPayload, Dict[str, Any]]:
    endpoint, api_key = resolve_chat_credentials(model_name)
    raw_response = call_azure_chat_completion_structured(
        endpoint=endpoint,
        api_key=api_key,
        messages=build_hours_messages(hours_input_payload),
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=build_hours_response_format(),
    )
    content = extract_response_content(raw_response)
    output_obj = extract_json_object(content)
    validated = HoursBatchPayload.model_validate(output_obj)
    return validated, raw_response.get("usage") or {}


__all__ = [
    "CategoryHoursEntry",
    "DayHoursPayload",
    "HoursBatchPayload",
    "OperatingHoursPayload",
    "build_hours_input_payload",
    "parse_hours_payload",
]
