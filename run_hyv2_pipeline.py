from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

try:
    from .hyv2_pipeline import HYV2_PROMPT_PATH, HYV3_PROMPT_PATH, HYV3_SCHEMA_PATH, run_hyv2_pipeline
    from .hyv2_subset_to_category_minimal_pipeline.config import MODEL_CONFIG
    from .run_nl_extraction import (
        DEFAULT_ENV_PATH,
        DEFAULT_PARSE_MODEL,
        DEFAULT_SCHEMA_PATH,
        DEFAULT_TIMEOUT_SECONDS,
        MENUOCR_DIR,
    )
except ImportError:
    from hyv2_pipeline import HYV2_PROMPT_PATH, HYV3_PROMPT_PATH, HYV3_SCHEMA_PATH, run_hyv2_pipeline
    from hyv2_subset_to_category_minimal_pipeline.config import MODEL_CONFIG
    from run_nl_extraction import (
        DEFAULT_ENV_PATH,
        DEFAULT_PARSE_MODEL,
        DEFAULT_SCHEMA_PATH,
        DEFAULT_TIMEOUT_SECONDS,
        MENUOCR_DIR,
    )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the end-to-end hyv2/hyv3 extraction and category transformation pipeline."
    )
    parser.add_argument("input", type=Path, help="Path to the menu file to parse and transform.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help=(
            "Destination descriptive/debug JSON file. Defaults to "
            "experiments/hyv2_subset_to_category_minimal_pipeline/outputs/"
            "<stem>_hyv2_pipeline.json. A merged final JSON is also written beside it as "
            "<stem>_hyv2_final.json."
        ),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=None,
        help="Path to the stage-1 extraction schema JSON. If omitted, uses hyv2 by default or hyv3 when --v3 is set.",
    )
    parser.add_argument(
        "--save-markdown",
        action="store_true",
        help="Also write ADE markdown beside the aggregate JSON output.",
    )
    parser.add_argument(
        "--parse-model",
        default=DEFAULT_PARSE_MODEL,
        help=f"ADE parse model to use. Default: {DEFAULT_PARSE_MODEL}",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Request timeout in seconds. Default: {DEFAULT_TIMEOUT_SECONDS}",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Landing AI API key override. Defaults to LANDING_AI_API_KEY from the environment.",
    )
    parser.add_argument(
        "--model",
        choices=list(MODEL_CONFIG.keys()),
        default="gpt-4o",
        help="Azure OpenAI deployment to use for per-category transformation.",
    )
    parser.add_argument(
        "--generation-mode",
        choices=["json_mode", "structured"],
        default="json_mode",
        help="Generation strategy for the per-category transformer.",
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
        default=8000,
        help="Maximum completion tokens for the chat model.",
    )
    parser.add_argument(
        "--v3",
        action="store_true",
        help="Use hyv3 stage-1 extraction schema and promptv3 stage-2 transformation prompt.",
    )
    parser.add_argument(
        "--keep-intermediates",
        action="store_true",
        help="Persist the preprocessed extraction plus per-category subset JSON files.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    load_dotenv(DEFAULT_ENV_PATH)
    load_dotenv(MENUOCR_DIR / ".env")

    args = parse_args(argv)
    input_path = args.input.resolve()
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    default_schema_path = HYV3_SCHEMA_PATH if args.v3 else DEFAULT_SCHEMA_PATH
    schema_path = args.schema.resolve() if args.schema else default_schema_path.resolve()
    prompt_path = HYV3_PROMPT_PATH if args.v3 else HYV2_PROMPT_PATH

    run_hyv2_pipeline(
        input_path=input_path,
        output_path=args.output,
        schema_path=schema_path,
        prompt_path=prompt_path,
        save_markdown=args.save_markdown,
        parse_model=args.parse_model,
        timeout_seconds=args.timeout,
        api_key_override=args.api_key,
        model_name=args.model,
        generation_mode=args.generation_mode,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        keep_intermediates=args.keep_intermediates,
    )


if __name__ == "__main__":
    main()
