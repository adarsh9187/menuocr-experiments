from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple


SHARED_SECTION_ROLES = {
    "shared_sizes_section",
    "shared_options_section",
    "shared_toppings_section",
    "shared_modifiers_section",
    "mixed_shared_section",
}


def is_shared_role(category_role: Any) -> bool:
    return isinstance(category_role, str) and category_role in SHARED_SECTION_ROLES


def category_ref(category: Dict[str, Any]) -> Optional[str]:
    value = category.get("category_ref")
    if isinstance(value, str) and value:
        return value
    return None


def category_items(category: Dict[str, Any]) -> List[Any]:
    items = category.get("items")
    return list(items) if isinstance(items, list) else []


def category_refs_from(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    refs: List[str] = []
    for entry in value:
        if isinstance(entry, str) and entry:
            refs.append(entry)
    return refs


def preprocess_extracted_payload(extracted: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    preprocessed = copy.deepcopy(extracted)
    categories = preprocessed.get("categories")
    if not isinstance(categories, list):
        preprocessed["categories"] = []
        return preprocessed, []

    valid_refs = {category_ref(category) for category in categories}
    valid_refs.discard(None)

    inbound_refs: Dict[str, set[str]] = {}
    for category in categories:
        source_ref = category_ref(category)
        if not source_ref:
            continue
        for target_ref in category_refs_from(category.get("modifiables_defined_in_category_refs")):
            inbound_refs.setdefault(target_ref, set()).add(source_ref)

    rewrites: List[Dict[str, Any]] = []
    for category in categories:
        current_ref = category_ref(category)
        if not current_ref:
            continue
        if category.get("category_role") != "normal_category":
            continue
        if category_items(category):
            continue
        inbound = sorted(ref for ref in inbound_refs.get(current_ref, set()) if ref in valid_refs)
        if not inbound:
            continue

        category["category_role"] = "shared_modifiers_section"
        category["applies_to_category_refs"] = inbound
        rewrites.append(
            {
                "category_ref": current_ref,
                "from_role": "normal_category",
                "to_role": "shared_modifiers_section",
                "applies_to_category_refs": inbound,
                "reason": "zero-item referenced supercategory",
            }
        )

    return preprocessed, rewrites


def build_category_subsets(extracted: Dict[str, Any]) -> List[Dict[str, Any]]:
    categories = extracted.get("categories")
    if not isinstance(categories, list):
        return []

    categories_by_ref: Dict[str, Dict[str, Any]] = {}
    for category in categories:
        current_ref = category_ref(category)
        if current_ref:
            categories_by_ref[current_ref] = category

    subset_runs: List[Dict[str, Any]] = []
    for target_category in categories:
        if target_category.get("category_role") != "normal_category":
            continue
        target_ref = category_ref(target_category)
        if not target_ref:
            continue

        included_refs = {target_ref}
        for category in categories:
            if not is_shared_role(category.get("category_role")):
                continue
            if target_ref in category_refs_from(category.get("applies_to_category_refs")):
                shared_ref = category_ref(category)
                if shared_ref:
                    included_refs.add(shared_ref)

        for referenced_ref in category_refs_from(target_category.get("modifiables_defined_in_category_refs")):
            referenced_category = categories_by_ref.get(referenced_ref)
            if referenced_category and is_shared_role(referenced_category.get("category_role")):
                included_refs.add(referenced_ref)

        subset_categories = []
        subset_category_refs = []
        for category in categories:
            current_ref = category_ref(category)
            if not current_ref or current_ref not in included_refs:
                continue
            subset_categories.append(copy.deepcopy(category))
            subset_category_refs.append(current_ref)

        subset_runs.append(
            {
                "category_ref": target_ref,
                "category_name": target_category.get("category_name") or target_ref,
                "subset_category_refs": subset_category_refs,
                "subset_payload": {
                    "categories": subset_categories,
                },
            }
        )

    return subset_runs


def summarize_categories(extracted: Dict[str, Any]) -> Dict[str, int]:
    categories = extracted.get("categories")
    if not isinstance(categories, list):
        return {
            "total_category_count": 0,
            "normal_category_count": 0,
            "shared_section_count": 0,
        }

    normal_category_count = sum(1 for category in categories if category.get("category_role") == "normal_category")
    shared_section_count = sum(1 for category in categories if is_shared_role(category.get("category_role")))
    return {
        "total_category_count": len(categories),
        "normal_category_count": normal_category_count,
        "shared_section_count": shared_section_count,
    }


def build_category_sort_lookup(extracted: Dict[str, Any]) -> Dict[str, int]:
    lookup: Dict[str, int] = {}
    categories = extracted.get("categories")
    if not isinstance(categories, list):
        return lookup
    for index, category in enumerate(categories):
        current_ref = category_ref(category)
        if current_ref:
            lookup[current_ref] = index
    return lookup


__all__ = [
    "SHARED_SECTION_ROLES",
    "build_category_sort_lookup",
    "build_category_subsets",
    "category_items",
    "category_ref",
    "category_refs_from",
    "is_shared_role",
    "preprocess_extracted_payload",
    "summarize_categories",
]
