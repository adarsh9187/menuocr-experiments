from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


PIPELINE_OUTPUT_DIR = Path(__file__).resolve().parent / "hyv2_subset_to_category_minimal_pipeline" / "outputs"


def default_output_path(input_path: Path) -> Path:
    PIPELINE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return PIPELINE_OUTPUT_DIR / f"{input_path.stem}_hyv2_pipeline.json"


def build_final_output_path(descriptive_output_path: Path) -> Path:
    if descriptive_output_path.stem.endswith("_pipeline"):
        final_name = f"{descriptive_output_path.stem[:-len('_pipeline')]}_final{descriptive_output_path.suffix}"
    else:
        final_name = f"{descriptive_output_path.stem}_final{descriptive_output_path.suffix}"
    return descriptive_output_path.with_name(final_name)


def build_postprocessed_minimal_output_path(descriptive_output_path: Path) -> Path:
    stem = descriptive_output_path.stem
    if stem.endswith("_pipeline"):
        stem = stem[: -len("_pipeline")]
    return descriptive_output_path.with_name(f"{stem}_postprocessed_minimal{descriptive_output_path.suffix}")


def build_intermediate_output_path(descriptive_output_path: Path) -> Path:
    stem = descriptive_output_path.stem
    if stem.endswith("_pipeline"):
        stem = stem[: -len("_pipeline")]
    return descriptive_output_path.with_name(f"{stem}_intermediate{descriptive_output_path.suffix}")


def build_expected_output_path(descriptive_output_path: Path) -> Path:
    stem = descriptive_output_path.stem
    if stem.endswith("_pipeline"):
        stem = stem[: -len("_pipeline")]
    return descriptive_output_path.with_name(f"{stem}_expected{descriptive_output_path.suffix}")


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


__all__ = [
    "PIPELINE_OUTPUT_DIR",
    "build_expected_output_path",
    "build_final_output_path",
    "build_intermediate_output_path",
    "build_postprocessed_minimal_output_path",
    "default_output_path",
    "write_json",
]
