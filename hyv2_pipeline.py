from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

try:
    from .hyv2_subset_to_category_minimal_pipeline.io_utils import next_available_path
    from .hyv2_subset_to_category_minimal_pipeline.pipeline import transform_subset
    from .run_nl_extraction import (
        DEFAULT_OUTPUT_DIR,
        DEFAULT_PROMPT_PATH,
        build_extraction_payload,
        resolve_api_key,
    )
except ImportError:
    from hyv2_subset_to_category_minimal_pipeline.io_utils import next_available_path
    from hyv2_subset_to_category_minimal_pipeline.pipeline import transform_subset
    from run_nl_extraction import (
        DEFAULT_OUTPUT_DIR,
        DEFAULT_PROMPT_PATH,
        build_extraction_payload,
        resolve_api_key,
    )


SHARED_SECTION_ROLES = {
    "shared_sizes_section",
    "shared_options_section",
    "shared_toppings_section",
    "shared_modifiers_section",
    "mixed_shared_section",
}


ExtractionBuilder = Callable[..., Dict[str, Any]]
SubsetTransformer = Callable[..., Tuple[Any, Dict[str, Any]]]
Logger = Callable[[str], None]


def default_output_path(input_path: Path) -> Path:
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_OUTPUT_DIR / f"{input_path.stem}_hyv2_pipeline.json"


def _sanitize_filename(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return sanitized or "category"


def _is_shared_role(category_role: Any) -> bool:
    return isinstance(category_role, str) and category_role in SHARED_SECTION_ROLES


def _category_ref(category: Dict[str, Any]) -> Optional[str]:
    category_ref = category.get("category_ref")
    if isinstance(category_ref, str) and category_ref:
        return category_ref
    return None


def _category_items(category: Dict[str, Any]) -> List[Any]:
    items = category.get("items")
    return list(items) if isinstance(items, list) else []


def _category_refs_from(value: Any) -> List[str]:
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

    valid_refs = {_category_ref(category) for category in categories}
    valid_refs.discard(None)

    inbound_refs: Dict[str, set[str]] = {}
    for category in categories:
        source_ref = _category_ref(category)
        if not source_ref:
            continue
        for target_ref in _category_refs_from(category.get("modifiables_defined_in_category_refs")):
            inbound_refs.setdefault(target_ref, set()).add(source_ref)

    rewrites: List[Dict[str, Any]] = []
    for category in categories:
        category_ref = _category_ref(category)
        if not category_ref:
            continue
        if category.get("category_role") != "normal_category":
            continue
        if _category_items(category):
            continue
        inbound = sorted(ref for ref in inbound_refs.get(category_ref, set()) if ref in valid_refs)
        if not inbound:
            continue

        category["category_role"] = "shared_modifiers_section"
        category["applies_to_category_refs"] = inbound
        rewrites.append(
            {
                "category_ref": category_ref,
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
        category_ref = _category_ref(category)
        if category_ref:
            categories_by_ref[category_ref] = category

    subset_runs: List[Dict[str, Any]] = []
    for target_category in categories:
        if target_category.get("category_role") != "normal_category":
            continue
        target_ref = _category_ref(target_category)
        if not target_ref:
            continue

        included_refs = {target_ref}
        for category in categories:
            if not _is_shared_role(category.get("category_role")):
                continue
            if target_ref in _category_refs_from(category.get("applies_to_category_refs")):
                shared_ref = _category_ref(category)
                if shared_ref:
                    included_refs.add(shared_ref)

        for referenced_ref in _category_refs_from(target_category.get("modifiables_defined_in_category_refs")):
            referenced_category = categories_by_ref.get(referenced_ref)
            if referenced_category and _is_shared_role(referenced_category.get("category_role")):
                included_refs.add(referenced_ref)

        subset_categories = []
        subset_category_refs = []
        for category in categories:
            category_ref = _category_ref(category)
            if not category_ref or category_ref not in included_refs:
                continue
            subset_categories.append(copy.deepcopy(category))
            subset_category_refs.append(category_ref)

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
    shared_section_count = sum(1 for category in categories if _is_shared_role(category.get("category_role")))
    return {
        "total_category_count": len(categories),
        "normal_category_count": normal_category_count,
        "shared_section_count": shared_section_count,
    }


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_hyv2_pipeline(
    *,
    input_path: Path,
    output_path: Optional[Path],
    schema_path: Path,
    save_markdown: bool,
    parse_model: str,
    timeout_seconds: int,
    api_key_override: Optional[str],
    model_name: str,
    generation_mode: str,
    temperature: float,
    max_tokens: int,
    keep_intermediates: bool,
    extraction_builder: ExtractionBuilder = build_extraction_payload,
    subset_transformer: SubsetTransformer = transform_subset,
    logger: Logger = print,
) -> Tuple[Path, Dict[str, Any]]:
    input_path = input_path.resolve()
    requested_output_path = output_path.resolve() if output_path else default_output_path(input_path)
    final_output_path = next_available_path(requested_output_path)
    final_output_path.parent.mkdir(parents=True, exist_ok=True)

    logger(f"Parsing menu: {input_path}")
    logger(f"Extracting with schema: {schema_path}")
    api_key = resolve_api_key(api_key_override)
    stage1_payload = extraction_builder(
        input_path,
        schema_path=schema_path,
        api_key=api_key,
        parse_model=parse_model,
        timeout_seconds=timeout_seconds,
    )

    if save_markdown:
        markdown_path = final_output_path.with_suffix(".md")
        markdown_path.write_text(stage1_payload["markdown"], encoding="utf-8")
        logger(f"Wrote ADE markdown to {markdown_path}")

    stage1_extracted = copy.deepcopy(stage1_payload["extracted"])
    logger("Preprocessing categories")
    preprocessed_extracted, rewrites = preprocess_extracted_payload(stage1_extracted)
    preprocessed_summary = summarize_categories(preprocessed_extracted)
    logger(
        "Category summary:"
        f" total={preprocessed_summary['total_category_count']}"
        f", normal={preprocessed_summary['normal_category_count']}"
        f", shared={preprocessed_summary['shared_section_count']}"
        f", rewrites={len(rewrites)}"
    )
    for rewrite in rewrites:
        logger(
            "Rewrote zero-item referenced supercategory "
            f"{rewrite['category_ref']} -> {rewrite['to_role']}; applies to: "
            f"{', '.join(rewrite['applies_to_category_refs'])}"
        )

    logger("Building subsets")
    subset_runs = build_category_subsets(preprocessed_extracted)
    logger(f"Built {len(subset_runs)} category subsets")

    intermediates_dir: Optional[Path] = None
    if keep_intermediates:
        intermediates_dir = final_output_path.with_suffix("")
        intermediates_dir.mkdir(parents=True, exist_ok=True)
        _write_json(
            intermediates_dir / "preprocessed_extracted.json",
            {"extracted": preprocessed_extracted, "rewrites": rewrites},
        )
        logger(f"Wrote preprocessed extraction to {intermediates_dir / 'preprocessed_extracted.json'}")

    category_runs: List[Dict[str, Any]] = []
    success_count = 0
    failure_count = 0
    for index, subset_run in enumerate(subset_runs, start=1):
        category_ref = subset_run["category_ref"]
        category_name = subset_run["category_name"]
        subset_payload = subset_run["subset_payload"]
        subset_category_refs = subset_run["subset_category_refs"]

        logger(
            f"Transforming category {index}/{len(subset_runs)}: "
            f"{category_name} ({category_ref}) with {len(subset_category_refs)} subset categories"
        )

        if intermediates_dir is not None:
            safe_ref = _sanitize_filename(category_ref)
            _write_json(intermediates_dir / f"{safe_ref}_subset.json", subset_payload)

        try:
            validated, usage = subset_transformer(
                subset_payload=subset_payload,
                model_name=model_name,
                generation_mode=generation_mode,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            output = validated.model_dump(by_alias=True)
            category_run = {
                "category_ref": category_ref,
                "category_name": category_name,
                "subset_category_refs": subset_category_refs,
                "status": "success",
                "usage": usage,
                "output": output,
            }
            category_runs.append(category_run)
            success_count += 1
            total_tokens = usage.get("total_tokens")
            logger(
                f"Category succeeded: {category_ref}; "
                f"subset_size={len(subset_category_refs)}; "
                f"total_tokens={total_tokens if total_tokens is not None else 'unknown'}"
            )
            if intermediates_dir is not None:
                safe_ref = _sanitize_filename(category_ref)
                _write_json(intermediates_dir / f"{safe_ref}_category_item_minimal.json", output)
        except Exception as exc:
            category_runs.append(
                {
                    "category_ref": category_ref,
                    "category_name": category_name,
                    "subset_category_refs": subset_category_refs,
                    "status": "error",
                    "error": str(exc),
                }
            )
            failure_count += 1
            logger(f"Category failed: {category_ref} ({category_name}): {exc}")

    aggregate_payload = {
        "document_path": stage1_payload["document_path"],
        "stage1": {
            "schema_path": str(schema_path),
            "prompt_path": str(DEFAULT_PROMPT_PATH),
            "parse_model": parse_model,
            "extracted": stage1_extracted,
        },
        "preprocessing": {
            "rewrites": rewrites,
            "preprocessed_extracted": preprocessed_extracted,
        },
        "category_runs": category_runs,
        "summary": {
            "normal_category_count": preprocessed_summary["normal_category_count"],
            "shared_section_count": preprocessed_summary["shared_section_count"],
            "rewrite_count": len(rewrites),
            "successful_category_runs": success_count,
            "failed_category_runs": failure_count,
        },
    }

    logger(f"Writing aggregate output to {final_output_path}")
    _write_json(final_output_path, aggregate_payload)
    logger(
        "Pipeline summary:"
        f" successes={success_count}, failures={failure_count}, output={final_output_path}"
    )
    return final_output_path, aggregate_payload
