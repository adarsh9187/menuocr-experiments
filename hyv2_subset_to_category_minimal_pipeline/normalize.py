from __future__ import annotations

from typing import Any, Dict, List


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def normalize_required_number(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def drop_none_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: drop_none_values(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [drop_none_values(v) for v in value]
    return value


def drop_description_properties(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: drop_description_properties(v)
            for k, v in value.items()
            if k != "description"
        }
    if isinstance(value, list):
        return [drop_description_properties(v) for v in value]
    return value


def normalize_output_obj(output_obj: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(output_obj)
    normalized.pop("category_description", None)
    normalized.pop("Description", None)
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
        normalized_size["Name"] = normalize_text(normalized_size.get("Name"))
        normalized_size["Price"] = normalize_required_number(normalized_size.get("Price"))
        normalized_category_sizes.append(drop_none_values(normalized_size))
    normalized["category_sizes"] = normalized_category_sizes

    normalized_category_options: List[Dict[str, Any]] = []
    for option in normalized["category_options"]:
        if not isinstance(option, dict):
            continue
        normalized_option = dict(option)
        normalized_option["choiceName"] = normalize_text(normalized_option.get("choiceName"))
        price_by_size = normalized_option.get("choicePriceBySize") or []
        normalized_choice_prices: List[Dict[str, Any]] = []
        for entry in price_by_size:
            if not isinstance(entry, dict):
                continue
            normalized_entry = dict(entry)
            normalized_entry["sizeName"] = normalize_text(normalized_entry.get("sizeName"))
            normalized_entry["price"] = normalize_required_number(normalized_entry.get("price"))
            normalized_choice_prices.append(drop_none_values(normalized_entry))
        normalized_option["choicePriceBySize"] = normalized_choice_prices
        normalized_category_options.append(drop_none_values(normalized_option))
    normalized["category_options"] = normalized_category_options

    normalized_items: List[Dict[str, Any]] = []
    for item in normalized["items"]:
        if not isinstance(item, dict):
            continue
        normalized_item = dict(item)
        normalized_item.pop("itemDescription", None)
        normalized_item.pop("Description", None)
        normalized_item["s_no"] = normalize_text(normalized_item.get("s_no", ""))
        normalized_item["name"] = normalize_text(normalized_item.get("name"))
        normalized_item["price"] = normalize_required_number(normalized_item.get("price"))

        item_options = list(normalized_item.get("options") or [])
        normalized_options: List[Dict[str, Any]] = []
        for option in item_options:
            if not isinstance(option, dict):
                continue
            normalized_option = dict(option)
            normalized_option["choiceName"] = normalize_text(normalized_option.get("choiceName"))
            price_by_size = normalized_option.get("choicePriceBySize") or []
            normalized_choice_prices: List[Dict[str, Any]] = []
            for entry in price_by_size:
                if not isinstance(entry, dict):
                    continue
                normalized_entry = dict(entry)
                normalized_entry["sizeName"] = normalize_text(normalized_entry.get("sizeName"))
                normalized_entry["price"] = normalize_required_number(normalized_entry.get("price"))
                normalized_choice_prices.append(drop_none_values(normalized_entry))
            normalized_option["choicePriceBySize"] = normalized_choice_prices
            normalized_options.append(drop_none_values(normalized_option))
        normalized_item["options"] = normalized_options

        item_sizes = list(normalized_item.get("ItemSizes") or [])
        normalized_item_sizes: List[Dict[str, Any]] = []
        for size in item_sizes:
            if not isinstance(size, dict):
                continue
            normalized_size = dict(size)
            normalized_size["Name"] = normalize_text(normalized_size.get("Name"))
            normalized_size["Price"] = normalize_required_number(normalized_size.get("Price"))
            normalized_item_sizes.append(drop_none_values(normalized_size))
        normalized_item["ItemSizes"] = normalized_item_sizes

        if normalized_item.get("toppings") is None:
            normalized_item.pop("toppings", None)
        normalized_items.append(drop_none_values(normalized_item))

    normalized["items"] = normalized_items
    return drop_none_values(normalized)
