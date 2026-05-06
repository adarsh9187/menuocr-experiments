from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Optional

try:
    from .hyv2_pipeline_categories import category_items
except ImportError:
    from hyv2_pipeline_categories import category_items


def drop_none_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: drop_none_values(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [drop_none_values(v) for v in value]
    return value


def normalize_name_key(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def build_item_source_lookup(source_items: List[Dict[str, Any]]) -> tuple[Dict[str, List[int]], List[bool]]:
    lookup: Dict[str, List[int]] = {}
    used: List[bool] = [False] * len(source_items)
    for index, item in enumerate(source_items):
        key = normalize_name_key(item.get("item_name"))
        if not key:
            continue
        lookup.setdefault(key, []).append(index)
    return lookup, used


def consume_source_item_index(
    *,
    generated_name: str,
    generated_index: int,
    source_items: List[Dict[str, Any]],
    source_lookup: Dict[str, List[int]],
    source_used: List[bool],
) -> Optional[int]:
    key = normalize_name_key(generated_name)
    for candidate_index in source_lookup.get(key, []):
        if not source_used[candidate_index]:
            source_used[candidate_index] = True
            return candidate_index

    if generated_index < len(source_items) and not source_used[generated_index]:
        source_used[generated_index] = True
        return generated_index

    for candidate_index in range(len(source_items)):
        if not source_used[candidate_index]:
            source_used[candidate_index] = True
            return candidate_index
    return None


def build_merged_items(
    *,
    generated_items: List[Dict[str, Any]],
    source_category: Dict[str, Any],
) -> List[Dict[str, Any]]:
    source_items = category_items(source_category)
    source_lookup, source_used = build_item_source_lookup(source_items)
    merged_items: List[Dict[str, Any]] = []

    for item_index, item in enumerate(generated_items):
        source_index = consume_source_item_index(
            generated_name=str(item.get("name") or ""),
            generated_index=item_index,
            source_items=source_items,
            source_lookup=source_lookup,
            source_used=source_used,
        )
        source_item = source_items[source_index] if source_index is not None and source_index < len(source_items) else {}
        merged_items.append(
            drop_none_values(
                {
                    **item,
                    "itemDescription": str(source_item.get("item_description") or ""),
                }
            )
        )
    return merged_items


def merge_category_toppings_into_item(
    item: Dict[str, Any],
    category_toppings: Dict[str, Any],
) -> Dict[str, Any]:
    merged_item = copy.deepcopy(item)
    item_toppings = copy.deepcopy(merged_item.get("toppings") or {})

    category_defaults = list(category_toppings.get("default") or [])
    if category_defaults:
        current_defaults = list(item_toppings.get("default") or [])
        seen_defaults = {normalize_name_key(name) for name in current_defaults}
        for topping_name in category_defaults:
            if normalize_name_key(topping_name) not in seen_defaults:
                current_defaults.append(topping_name)
                seen_defaults.add(normalize_name_key(topping_name))
        item_toppings["default"] = current_defaults

    category_available = list(category_toppings.get("available") or [])
    if category_available:
        current_available = list(item_toppings.get("available") or [])
        seen_available = {normalize_name_key(entry.get("name")) for entry in current_available if isinstance(entry, dict)}
        for topping_entry in category_available:
            if not isinstance(topping_entry, dict):
                continue
            topping_key = normalize_name_key(topping_entry.get("name"))
            if topping_key and topping_key not in seen_available:
                current_available.append(copy.deepcopy(topping_entry))
                seen_available.add(topping_key)
        item_toppings["available"] = current_available

    if item_toppings:
        merged_item["toppings"] = item_toppings
    return merged_item


def merge_named_entries(existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]], *, key_field: str) -> List[Dict[str, Any]]:
    merged = [copy.deepcopy(entry) for entry in existing if isinstance(entry, dict)]
    seen = {normalize_name_key(entry.get(key_field)) for entry in merged}
    for entry in incoming:
        if not isinstance(entry, dict):
            continue
        key = normalize_name_key(entry.get(key_field))
        if key and key not in seen:
            merged.append(copy.deepcopy(entry))
            seen.add(key)
    return merged


def merge_toppings_payload(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(existing) if isinstance(existing, dict) else {}
    existing_defaults = list(merged.get("default") or [])
    seen_defaults = {normalize_name_key(name) for name in existing_defaults}
    for topping_name in incoming.get("default") or []:
        topping_key = normalize_name_key(topping_name)
        if topping_key and topping_key not in seen_defaults:
            existing_defaults.append(topping_name)
            seen_defaults.add(topping_key)
    if existing_defaults:
        merged["default"] = existing_defaults
    merged["available"] = merge_named_entries(
        list(merged.get("available") or []),
        list(incoming.get("available") or []),
        key_field="name",
    )
    return merged


def merge_item_records(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(existing)
    if not merged.get("itemDescription") and incoming.get("itemDescription"):
        merged["itemDescription"] = incoming.get("itemDescription")
    if merged.get("price") in (None, 0, 0.0, "") and incoming.get("price") not in (None, ""):
        merged["price"] = incoming.get("price")
    merged["options"] = merge_named_entries(
        list(merged.get("options") or []),
        list(incoming.get("options") or []),
        key_field="choiceName",
    )
    merged["ItemSizes"] = merge_named_entries(
        list(merged.get("ItemSizes") or []),
        list(incoming.get("ItemSizes") or []),
        key_field="Name",
    )
    merged["toppings"] = merge_toppings_payload(
        merged.get("toppings") or {},
        incoming.get("toppings") or {},
    )
    return merged


def merge_duplicate_categories_local(categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged_by_name: Dict[str, Dict[str, Any]] = {}
    ordered_keys: List[str] = []

    for category in categories:
        if not isinstance(category, dict):
            continue
        category_name = str(category.get("category_name") or "").strip()
        category_key = normalize_name_key(category_name)
        if not category_key:
            continue

        if category_key not in merged_by_name:
            merged_by_name[category_key] = copy.deepcopy(category)
            ordered_keys.append(category_key)
            continue

        dest = merged_by_name[category_key]
        if not dest.get("Description") and category.get("Description"):
            dest["Description"] = category.get("Description")
        if dest.get("sort") is None and category.get("sort") is not None:
            dest["sort"] = category.get("sort")
        if not dest.get("category_type") and category.get("category_type"):
            dest["category_type"] = category.get("category_type")
        if not dest.get("hours") and category.get("hours"):
            dest["hours"] = copy.deepcopy(category.get("hours"))

        dest["category_sizes"] = merge_named_entries(
            list(dest.get("category_sizes") or []),
            list(category.get("category_sizes") or []),
            key_field="Name",
        )
        dest["category_options"] = merge_named_entries(
            list(dest.get("category_options") or []),
            list(category.get("category_options") or []),
            key_field="choiceName",
        )
        dest["category_toppings"] = merge_toppings_payload(
            dest.get("category_toppings") or {},
            category.get("category_toppings") or {},
        )

        existing_items = list(dest.get("items") or [])
        item_index_by_name = {
            normalize_name_key(item.get("name")): index
            for index, item in enumerate(existing_items)
            if isinstance(item, dict) and normalize_name_key(item.get("name"))
        }
        for item in category.get("items") or []:
            if not isinstance(item, dict):
                continue
            item_key = normalize_name_key(item.get("name"))
            if item_key and item_key in item_index_by_name:
                existing_index = item_index_by_name[item_key]
                existing_items[existing_index] = merge_item_records(existing_items[existing_index], item)
            else:
                item_index_by_name[item_key] = len(existing_items)
                existing_items.append(copy.deepcopy(item))
        dest["items"] = existing_items

    return [merged_by_name[key] for key in ordered_keys]


def apply_menuocr_style_postprocessing(minimal_payload: Dict[str, Any]) -> Dict[str, Any]:
    processed = copy.deepcopy(minimal_payload)
    categories = processed.get("Categories")
    if not isinstance(categories, list):
        processed["Categories"] = []
        return processed

    postprocessed_categories: List[Dict[str, Any]] = []
    for category in categories:
        if not isinstance(category, dict):
            continue
        postprocessed_category = copy.deepcopy(category)
        category_sizes = list(postprocessed_category.get("category_sizes") or [])
        category_toppings = postprocessed_category.get("category_toppings") or {}

        postprocessed_items: List[Dict[str, Any]] = []
        for item in postprocessed_category.get("items") or []:
            if not isinstance(item, dict):
                continue
            postprocessed_item = copy.deepcopy(item)
            if category_sizes and not postprocessed_item.get("ItemSizes"):
                postprocessed_item["ItemSizes"] = copy.deepcopy(category_sizes)
            if category_toppings:
                postprocessed_item = merge_category_toppings_into_item(postprocessed_item, category_toppings)
            postprocessed_items.append(postprocessed_item)

        postprocessed_category["items"] = postprocessed_items
        postprocessed_categories.append(postprocessed_category)

    return {
        "menu_hours": copy.deepcopy(processed.get("menu_hours")),
        "Categories": merge_duplicate_categories_local(postprocessed_categories),
    }


def build_category_hours_lookup(hours_result: Any) -> tuple[Optional[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    structured_global_hours = None
    category_hours_lookup: Dict[str, Dict[str, Any]] = {}
    if hours_result is not None:
        structured_global_hours = (
            hours_result.global_hours.model_dump(exclude_none=True) if hours_result.global_hours else None
        )
        for entry in hours_result.category_hours:
            category_hours_lookup[normalize_name_key(entry.category_name)] = entry.hours.model_dump(exclude_none=True)
    return structured_global_hours, category_hours_lookup


def build_merged_final_payload(
    *,
    document_path: str,
    category_runs: List[Dict[str, Any]],
    categories_by_ref: Dict[str, Dict[str, Any]],
    category_sort_lookup: Dict[str, int],
    category_hours_lookup: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "document_path": document_path,
        "Categories": [
            drop_none_values(
                {
                    "category_name": category_run["category_name"],
                    "Description": str(
                        (categories_by_ref.get(category_run["category_ref"], {}) or {}).get("category_description")
                        or ""
                    ),
                    "sort": category_sort_lookup.get(category_run["category_ref"]),
                    "category_type": (
                        (categories_by_ref.get(category_run["category_ref"], {}) or {}).get("category_type")
                    ),
                    "category_sizes": category_run["output"].get("category_sizes") or [],
                    "category_options": category_run["output"].get("category_options") or [],
                    "category_toppings": category_run["output"].get("category_toppings"),
                    "hours": category_hours_lookup.get(normalize_name_key(category_run["category_name"])),
                    "items": build_merged_items(
                        generated_items=category_run["output"].get("items") or [],
                        source_category=categories_by_ref.get(category_run["category_ref"], {}) or {},
                    ),
                }
            )
            for category_run in category_runs
            if category_run.get("status") == "success"
        ],
    }


__all__ = [
    "apply_menuocr_style_postprocessing",
    "build_category_hours_lookup",
    "build_merged_final_payload",
    "build_merged_items",
    "drop_none_values",
    "normalize_name_key",
]
