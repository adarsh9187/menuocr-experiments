from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

MENUOCR_DIR = Path(__file__).resolve().parent.parent / "menuocr"
if str(MENUOCR_DIR) not in sys.path:
    sys.path.insert(0, str(MENUOCR_DIR))

from app.pipeline.mapping import map_with_ir

try:
    from .hyv2_pipeline_categories import (
        build_category_sort_lookup,
        build_category_subsets,
        category_ref,
        preprocess_extracted_payload,
        summarize_categories,
    )
    from .hyv2_pipeline_paths import (
        build_expected_output_path,
        build_final_output_path,
        build_intermediate_output_path,
        build_postprocessed_minimal_output_path,
        build_run_output_dir,
        default_output_path,
        write_json,
    )
    from .hyv2_pipeline_postprocess import (
        apply_menuocr_style_postprocessing,
        build_category_hours_lookup,
        build_merged_final_payload,
    )
    from .hyv2_subset_to_category_minimal_pipeline.hours import (
        build_hours_input_payload,
        parse_hours_payload,
    )
    from .hyv2_subset_to_category_minimal_pipeline.io_utils import next_available_path
    from .hyv2_subset_to_category_minimal_pipeline.pipeline import transform_subset
    from .run_nl_extraction import (
        build_extraction_payload,
        resolve_api_key,
    )
except ImportError:
    from hyv2_pipeline_categories import (
        build_category_sort_lookup,
        build_category_subsets,
        category_ref,
        preprocess_extracted_payload,
        summarize_categories,
    )
    from hyv2_pipeline_paths import (
        build_expected_output_path,
        build_final_output_path,
        build_intermediate_output_path,
        build_postprocessed_minimal_output_path,
        build_run_output_dir,
        default_output_path,
        write_json,
    )
    from hyv2_pipeline_postprocess import (
        apply_menuocr_style_postprocessing,
        build_category_hours_lookup,
        build_merged_final_payload,
    )
    from hyv2_subset_to_category_minimal_pipeline.hours import (
        build_hours_input_payload,
        parse_hours_payload,
    )
    from hyv2_subset_to_category_minimal_pipeline.io_utils import next_available_path
    from hyv2_subset_to_category_minimal_pipeline.pipeline import transform_subset
    from run_nl_extraction import (
        build_extraction_payload,
        resolve_api_key,
    )

ExtractionBuilder = Callable[..., Dict[str, Any]]
SubsetTransformer = Callable[..., Tuple[Any, Dict[str, Any]]]
HoursTransformer = Callable[..., Tuple[Any, Dict[str, Any]]]
Logger = Callable[[str], None]

EXPERIMENTS_DIR = Path(__file__).resolve().parent
HYV2_SCHEMA_PATH = EXPERIMENTS_DIR / "hyv2.schema.json"
HYV3_SCHEMA_PATH = EXPERIMENTS_DIR / "hyv3.schema.json"
HYV2_PROMPT_PATH = EXPERIMENTS_DIR / "hyv2_subset_to_category_minimal_pipeline" / "prompt.md"
HYV3_PROMPT_PATH = EXPERIMENTS_DIR / "hyv2_subset_to_category_minimal_pipeline" / "promptv3.md"
def run_hyv2_pipeline(
    *,
    input_path: Path,
    output_path: Optional[Path],
    schema_path: Path,
    prompt_path: Path,
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
    hours_transformer: HoursTransformer = parse_hours_payload,
    logger: Logger = print,
) -> Tuple[Path, Dict[str, Any]]:
    input_path = input_path.resolve()
    requested_output_path = output_path.resolve() if output_path else default_output_path(input_path)
    run_output_dir = next_available_path(build_run_output_dir(requested_output_path))
    descriptive_output_path = run_output_dir / f"{run_output_dir.name}{requested_output_path.suffix}"
    final_output_path = next_available_path(build_final_output_path(descriptive_output_path))
    postprocessed_minimal_output_path = next_available_path(
        build_postprocessed_minimal_output_path(descriptive_output_path)
    )
    intermediate_output_path = next_available_path(build_intermediate_output_path(descriptive_output_path))
    expected_output_path = next_available_path(build_expected_output_path(descriptive_output_path))
    run_output_dir.mkdir(parents=True, exist_ok=True)
    final_output_path.parent.mkdir(parents=True, exist_ok=True)
    postprocessed_minimal_output_path.parent.mkdir(parents=True, exist_ok=True)
    intermediate_output_path.parent.mkdir(parents=True, exist_ok=True)
    expected_output_path.parent.mkdir(parents=True, exist_ok=True)

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
        markdown_path = descriptive_output_path.with_suffix(".md")
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
        reason = rewrite.get("reason", "rewrite")
        if reason == "zero-item referenced supercategory":
            logger(
                "Rewrote zero-item referenced supercategory "
                f"{rewrite.get('category_ref')} -> {rewrite.get('to_role')}; applies to: "
                f"{', '.join(rewrite.get('applies_to_category_refs', []))}"
            )
        elif reason == "removed shared toppings references from non-pizza category":
            logger(
                "Removed shared toppings refs from non-pizza category "
                f"{rewrite.get('category_ref')}: "
                f"{', '.join(rewrite.get('removed_category_refs', []))}"
            )
        elif reason == "removed non-pizza applies_to refs from shared toppings section":
            logger(
                "Removed non-pizza applies-to refs from shared toppings section "
                f"{rewrite.get('category_ref')}: "
                f"{', '.join(rewrite.get('removed_applies_to_category_refs', []))}"
            )
        else:
            logger(f"Applied preprocessing rewrite for {rewrite.get('category_ref')}: {reason}")

    logger("Building subsets")
    subset_runs = build_category_subsets(preprocessed_extracted)
    logger(f"Built {len(subset_runs)} category subsets")
    category_sort_lookup = build_category_sort_lookup(preprocessed_extracted)
    categories_by_ref = {
        current_ref: category
        for category in preprocessed_extracted.get("categories", [])
        if isinstance(category, dict) and (current_ref := category_ref(category))
    }

    hours_input_payload = build_hours_input_payload(preprocessed_extracted)
    hours_result = None
    hours_usage: Dict[str, Any] = {}
    hours_error: Optional[str] = None
    if hours_input_payload:
        logger(f"Structuring hours for {len(hours_input_payload)} raw hours entries")
        try:
            hours_result, hours_usage = hours_transformer(
                hours_input_payload=hours_input_payload,
                model_name=model_name,
                temperature=0.0,
                max_tokens=max_tokens,
            )
            logger("Hours structuring succeeded")
        except Exception as exc:
            hours_error = str(exc)
            logger(f"Hours structuring failed: {exc}")

    intermediates_dir: Optional[Path] = None
    if keep_intermediates:
        intermediates_dir = descriptive_output_path.parent
        write_json(
            intermediates_dir / "preprocessed_extracted.json",
            {"extracted": preprocessed_extracted, "rewrites": rewrites},
        )
        logger(f"Wrote preprocessed extraction to {intermediates_dir / 'preprocessed_extracted.json'}")

    category_runs: List[Dict[str, Any]] = []
    success_count = 0
    failure_count = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    hours_prompt_tokens = hours_usage.get("prompt_tokens")
    hours_completion_tokens = hours_usage.get("completion_tokens")
    hours_total_tokens = hours_usage.get("total_tokens")
    if isinstance(hours_prompt_tokens, int):
        total_prompt_tokens += hours_prompt_tokens
    if isinstance(hours_completion_tokens, int):
        total_completion_tokens += hours_completion_tokens
    if isinstance(hours_total_tokens, int):
        total_tokens += hours_total_tokens
    for index, subset_run in enumerate(subset_runs, start=1):
        current_category_ref = subset_run["category_ref"]
        current_category_name = subset_run["category_name"]
        subset_payload = subset_run["subset_payload"]
        subset_category_refs = subset_run["subset_category_refs"]

        logger(
            f"Transforming category {index}/{len(subset_runs)}: "
            f"{current_category_name} ({current_category_ref}) with {len(subset_category_refs)} subset categories"
        )
        try:
            validated, usage = subset_transformer(
                subset_payload=subset_payload,
                model_name=model_name,
                generation_mode=generation_mode,
                temperature=temperature,
                max_tokens=max_tokens,
                prompt_path=prompt_path,
            )
            output = validated.model_dump(by_alias=True)
            category_run = {
                "category_ref": current_category_ref,
                "category_name": current_category_name,
                "subset_category_refs": subset_category_refs,
                "status": "success",
                "usage": usage,
                "output": output,
            }
            category_runs.append(category_run)
            success_count += 1
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            run_total_tokens = usage.get("total_tokens")
            if isinstance(prompt_tokens, int):
                total_prompt_tokens += prompt_tokens
            if isinstance(completion_tokens, int):
                total_completion_tokens += completion_tokens
            if isinstance(run_total_tokens, int):
                total_tokens += run_total_tokens
            logger(
                f"Category succeeded: {current_category_ref}; "
                f"subset_size={len(subset_category_refs)}; "
                f"total_tokens={run_total_tokens if run_total_tokens is not None else 'unknown'}"
            )
        except Exception as exc:
            category_runs.append(
                {
                    "category_ref": current_category_ref,
                    "category_name": current_category_name,
                    "subset_category_refs": subset_category_refs,
                    "status": "error",
                    "error": str(exc),
                }
            )
            failure_count += 1
            logger(f"Category failed: {current_category_ref} ({current_category_name}): {exc}")

    aggregate_payload = {
        "document_path": stage1_payload["document_path"],
        "stage1": {
            "schema_path": str(schema_path),
            "prompt_path": stage1_payload.get("prompt_path", ""),
            "parse_model": parse_model,
            "extracted": stage1_extracted,
        },
        "stage2": {
            "prompt_path": str(prompt_path),
            "hours_input": hours_input_payload,
            "hours_usage": hours_usage,
            "hours_output": hours_result.model_dump() if hours_result is not None else None,
            "hours_error": hours_error,
        },
        "stage3": {
            "postprocessing": "menuocr_minimal_to_ir_to_expected",
            "postprocessed_minimal_output_path": str(postprocessed_minimal_output_path),
            "intermediate_output_path": str(intermediate_output_path),
            "expected_output_path": str(expected_output_path),
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
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
        },
    }

    structured_global_hours, category_hours_lookup = build_category_hours_lookup(hours_result)
    merged_final_payload = build_merged_final_payload(
        document_path=stage1_payload["document_path"],
        category_runs=category_runs,
        categories_by_ref=categories_by_ref,
        category_sort_lookup=category_sort_lookup,
        category_hours_lookup=category_hours_lookup,
    )
    merged_final_payload["menu_hours"] = structured_global_hours

    logger("Applying menuocr postprocessing")
    postprocessed_minimal_payload = apply_menuocr_style_postprocessing(merged_final_payload)
    intermediate_payload, expected_payload = map_with_ir(postprocessed_minimal_payload)

    logger(f"Writing descriptive output to {descriptive_output_path}")
    write_json(descriptive_output_path, aggregate_payload)
    logger(f"Writing final merged output to {final_output_path}")
    write_json(final_output_path, merged_final_payload)
    logger(f"Writing postprocessed minimal output to {postprocessed_minimal_output_path}")
    write_json(postprocessed_minimal_output_path, postprocessed_minimal_payload)
    logger(f"Writing intermediate output to {intermediate_output_path}")
    write_json(intermediate_output_path, intermediate_payload)
    logger(f"Writing expected output to {expected_output_path}")
    write_json(expected_output_path, expected_payload)
    logger(
        "Pipeline summary:"
        f" successes={success_count}, failures={failure_count},"
        f" total_tokens={total_tokens}, descriptive_output={descriptive_output_path},"
        f" final_output={final_output_path},"
        f" postprocessed_minimal_output={postprocessed_minimal_output_path},"
        f" expected_output={expected_output_path}"
    )
    return descriptive_output_path, aggregate_payload
