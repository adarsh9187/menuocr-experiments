"""
Minimal CLI for the Nova Pro natural-language menu extraction experiment.

Example:

    python experiments/run_nova_nl_extraction.py "path/to/menu.pdf"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional

from nova_nl_client import NovaNLClient


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ENV_PATH = SCRIPT_DIR / ".env"
DEFAULT_SCHEMA_PATH = SCRIPT_DIR / "nl_menu_extraction.schema.json"
DEFAULT_PROMPT_PATH = SCRIPT_DIR / "nl_menu_extraction_prompt.md"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "outputs"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the experimental Nova Pro natural-language menu extraction pipeline."
    )
    parser.add_argument("input", type=Path, help="Path to the menu file to analyze.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Destination JSON file. Defaults to experiments/outputs/<stem>_nova_nl.json",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Path to the extraction schema JSON.",
    )
    parser.add_argument(
        "--prompt",
        type=Path,
        default=DEFAULT_PROMPT_PATH,
        help="Path to the Nova prompt instructions markdown.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=8192,
        help="Bedrock max_new_tokens value.",
    )
    return parser.parse_args(argv)


def default_output_path(input_path: Path) -> Path:
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_OUTPUT_DIR / f"{input_path.stem}_nova_nl.json"


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


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    input_path = args.input.resolve()
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    requested_output_path = args.output.resolve() if args.output else default_output_path(input_path)
    output_path = next_available_path(requested_output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = NovaNLClient(env_path=DEFAULT_ENV_PATH)
    result = client.extract_menu(
        input_path=input_path,
        schema_path=args.schema.resolve(),
        prompt_path=args.prompt.resolve(),
        max_new_tokens=args.max_new_tokens,
    )

    output_data = {
        "document_path": str(input_path),
        "schema_path": str(args.schema.resolve()),
        "prompt_path": str(args.prompt.resolve()),
        "model_id": result["model_id"],
        "page_count": result["page_count"],
        "extracted": result["extracted"],
    }
    output_path.write_text(json.dumps(output_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote Nova extraction JSON to {output_path}")


if __name__ == "__main__":
    main()
