"""
Minimal CLI pipeline for the natural-language-first menu extraction experiment.

This script mirrors the existing MenuOCR environment pattern:

- loads `.env` credentials
- parses a source menu file with Landing AI ADE
- extracts against the experimental natural-language schema

Run from the repo root, for example:

    python experiments/run_nl_extraction.py path/to/menu.pdf
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
MENUOCR_DIR = REPO_ROOT / "menuocr"
if str(MENUOCR_DIR) not in sys.path:
    sys.path.insert(0, str(MENUOCR_DIR))

from ade_client import (  # noqa: E402
    ADEClientError,
    DEFAULT_PARSE_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    extract_with_schema,
    load_schema,
    parse_document,
)


DEFAULT_SCHEMA_PATH = SCRIPT_DIR / "hyv2.schema.json"
DEFAULT_PROMPT_PATH = SCRIPT_DIR / "nl_menu_extraction_prompt.md"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "outputs"
DEFAULT_ENV_PATH = SCRIPT_DIR / ".env"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the experimental natural-language-first menu extraction pipeline."
    )
    parser.add_argument("input", type=Path, help="Path to the menu file to parse and extract.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Destination JSON file. Defaults to experiments/outputs/<stem>_nl.json",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Path to the extraction schema JSON.",
    )
    parser.add_argument(
        "--save-markdown",
        action="store_true",
        help="Also write ADE markdown beside the JSON output.",
    )
    parser.add_argument(
        "--print-markdown",
        action="store_true",
        help="Print the parsed ADE markdown to stdout after extraction.",
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
    return parser.parse_args(argv)


def resolve_api_key(override: Optional[str] = None) -> str:
    if override:
        return override
    api_key = os.getenv("LANDING_AI_API_KEY")
    if not api_key:
        raise ADEClientError(
            "LANDING_AI_API_KEY environment variable is not set. "
            "Set it in experiments/.env, menuocr/.env, or pass --api-key."
        )
    return api_key


def default_output_path(input_path: Path) -> Path:
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_OUTPUT_DIR / f"{input_path.stem}_nl.json"


def next_available_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def build_extraction_payload(
    document_path: Path,
    *,
    schema_path: Path,
    api_key: str,
    parse_model: str,
    timeout_seconds: int,
) -> Dict[str, Any]:
    schema = load_schema(schema_path)
    parse_payload = parse_document(
        document_path,
        api_key=api_key,
        model=parse_model,
        timeout_seconds=timeout_seconds,
    )
    markdown = parse_payload.get("markdown")
    if not isinstance(markdown, str):
        raise ADEClientError("ADE parse response missing 'markdown' field.")

    extract_kwargs = {
        "api_key": api_key,
        "timeout_seconds": timeout_seconds,
    }
    if "markdown_filename" in inspect.signature(extract_with_schema).parameters:
        extract_kwargs["markdown_filename"] = f"{document_path.stem}.md"

    extraction_payload = extract_with_schema(markdown, schema, **extract_kwargs)

    extracted = extraction_payload.get("extraction", extraction_payload)
    return {
        "document_path": str(document_path),
        "schema_path": str(schema_path),
        "prompt_path": str(DEFAULT_PROMPT_PATH),
        "parse_model": parse_model,
        "markdown": markdown,
        "parse_payload": parse_payload,
        "raw_extraction_payload": extraction_payload,
        "extracted": extracted,
    }


def main(argv: Optional[List[str]] = None) -> None:
    load_dotenv(DEFAULT_ENV_PATH)
    load_dotenv(MENUOCR_DIR / ".env")

    args = parse_args(argv)
    input_path = args.input.resolve()
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    requested_output_path = args.output.resolve() if args.output else default_output_path(input_path)
    output_path = next_available_path(requested_output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    api_key = resolve_api_key(args.api_key)
    payload = build_extraction_payload(
        input_path,
        schema_path=args.schema.resolve(),
        api_key=api_key,
        parse_model=args.parse_model,
        timeout_seconds=args.timeout,
    )

    output_data = {
        "document_path": payload["document_path"],
        "schema_path": payload["schema_path"],
        "prompt_path": payload["prompt_path"],
        "parse_model": payload["parse_model"],
        "extracted": payload["extracted"],
    }
    output_path.write_text(json.dumps(output_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.save_markdown:
        markdown_path = output_path.with_suffix(".md")
        markdown_path.write_text(payload["markdown"], encoding="utf-8")

    print(f"Wrote extraction JSON to {output_path}")
    if args.save_markdown:
        print(f"Wrote ADE markdown to {output_path.with_suffix('.md')}")
    if args.print_markdown:
        print(payload["markdown"])


if __name__ == "__main__":
    main()
