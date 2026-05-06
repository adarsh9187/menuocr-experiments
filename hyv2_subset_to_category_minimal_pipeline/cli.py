from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv
from pydantic import ValidationError

from .config import ENV_PATH, MODEL_CONFIG, PROMPT_PATH
from .io_utils import next_available_path
from .pipeline import transform_subset


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transform a hyv2 subset JSON into category_item_minimal JSON using Azure OpenAI."
    )
    parser.add_argument("input", type=Path, help="Path to the subset input JSON.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path for the transformed JSON.",
    )
    parser.add_argument(
        "--model",
        choices=list(MODEL_CONFIG.keys()),
        default="gpt-5-mini",
        help="Azure OpenAI deployment to use.",
    )
    parser.add_argument(
        "--generation-mode",
        choices=["json_mode", "structured"],
        default="structured",
        help=(
            "Generation strategy: 'json_mode' uses free JSON generation plus validation; "
            "'structured' constrains generation with the Pydantic-derived JSON schema."
        ),
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
        default=20000,
        help="Maximum completion tokens for the chat model.",
    )
    parser.add_argument(
        "--v4",
        action="store_true",
        help="Use promptv4.md instead of the default prompt.md.",
    )
    return parser.parse_args(argv)


def run(argv: Optional[List[str]] = None) -> None:
    load_dotenv(ENV_PATH)
    args = parse_args(argv)

    subset_payload = json.loads(args.input.read_text(encoding="utf-8"))
    
    prompt_path = Path(__file__).resolve().parent / "promptv4.md" if args.v4 else PROMPT_PATH
    
    validated, usage = transform_subset(
        subset_payload=subset_payload,
        model_name=args.model,
        generation_mode=args.generation_mode,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        prompt_path=prompt_path,
    )

    output_path = args.output or args.input.with_name(f"{args.input.stem}_category_item_minimal.json")
    output_path = next_available_path(output_path)
    output_path.write_text(
        json.dumps(validated.model_dump(by_alias=True), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote transformed payload to {output_path}")
    print(f"Generation mode: {args.generation_mode}")

    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")
    print(
        "Token usage:"
        f" prompt={prompt_tokens if prompt_tokens is not None else 'unknown'}"
        f", completion={completion_tokens if completion_tokens is not None else 'unknown'}"
        f", total={total_tokens if total_tokens is not None else 'unknown'}"
    )


def main(argv: Optional[List[str]] = None) -> None:
    try:
        run(argv)
    except ValidationError as exc:
        raise SystemExit(f"Pydantic validation failed: {exc}") from exc
    except requests.ConnectionError as exc:
        raise SystemExit(
            "Azure OpenAI connection failed. "
            "This is usually a DNS, network, VPN, proxy, or endpoint-host issue.\n"
            f"{exc}"
        ) from exc
    except requests.Timeout as exc:
        raise SystemExit(f"Azure OpenAI request timed out: {exc}") from exc
    except requests.HTTPError as exc:
        body = exc.response.text if exc.response is not None else ""
        raise SystemExit(f"Azure OpenAI request failed: {exc}\n{body}") from exc


if __name__ == "__main__":
    main()
