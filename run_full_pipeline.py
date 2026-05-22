"""
CLI benchmark for the full menuocr extraction pipeline.

Purpose: isolate whether slowness in the deployed site comes from the data-science
pipeline itself (ADE parse → ADE extract → GPT-4o transforms → mapping → RMF) or
from backend/frontend overhead.

If this CLI finishes much faster than the deployed site, the bottleneck is in
backend/frontend (job queue, DB, worker polling, file upload/download).
If times are similar, the bottleneck is in the DS pipeline (ADE/GPT-4o calls).

Usage (use the menuocr virtualenv):
    menuocr/.venv/bin/python experiments/run_full_pipeline.py dev-testing/Lanna\\ Thai\\ Menu.pdf

    # with overrides
    menuocr/.venv/bin/python experiments/run_full_pipeline.py path/to/menu.pdf \\
        --output experiments/outputs/my_run.json \\
        --api-key <landing-ai-key> \\
        --save-markdown

Outputs (inside a folder beside --output):
    <stem>_pipeline.json  — timing summary
    <stem>_mr.json        — mapped menu JSON
    <stem>.rmf            — generated RMF file
    <stem>.md             — ADE markdown (only with --save-markdown)
    full_run.json         — full debug dump (when MENUOCR_DEBUG=true)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Path setup — make `app.*` importable from the menuocr package
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
MENUOCR_DIR = REPO_ROOT / "menuocr"
if str(MENUOCR_DIR) not in sys.path:
    sys.path.insert(0, str(MENUOCR_DIR))

# Load credentials before importing app modules (they read env at import time)
load_dotenv(SCRIPT_DIR / ".env")
load_dotenv(MENUOCR_DIR / ".env")

# ---------------------------------------------------------------------------
# Logging — configure BEFORE importing pipeline modules so all loggers
# inherit the same timestamped format. This mirrors what the deployed server
# emits so you can do a line-by-line comparison.
# ---------------------------------------------------------------------------
_LOG_FMT = "%(asctime)s.%(msecs)03d [%(levelname)-5s] %(name)s — %(message)s"
_DATE_FMT = "%H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=_LOG_FMT,
    datefmt=_DATE_FMT,
    stream=sys.stdout,
    force=True,
)

# The pipeline uses a dedicated 'menuocr.api' logger; make sure it propagates
# to root (the server configures it with propagate=False, but here we want
# everything on one stream for easy comparison)
_pipeline_logger = logging.getLogger("menuocr.api")
_pipeline_logger.setLevel(logging.INFO)
_pipeline_logger.propagate = True
# Remove any handlers the server-side configure_logging() may have added
_pipeline_logger.handlers.clear()

# ADE client uses logging.getLogger(__name__) = "app.pipeline.ade_client"
logging.getLogger("app.pipeline.ade_client").setLevel(logging.INFO)

# Silence noisy libraries
for _noisy in ("urllib3", "httpcore", "httpx", "asyncio"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

log = logging.getLogger("run_full_pipeline")

# ---------------------------------------------------------------------------
# Now safe to import from the menuocr package
# ---------------------------------------------------------------------------
from app.pipeline.ade_client import (  # noqa: E402
    ADEClientError,
    DEFAULT_PARSE_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
)
from app.pipeline.server_core.pipeline import (  # noqa: E402
    extract_minimal_payload,
    finalize_generated_outputs,
)
from app.pipeline.server_core.rmf_generator import RMFMetadata  # noqa: E402


DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "outputs"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_duration(seconds: float) -> str:
    if seconds >= 60:
        return f"{seconds / 60:.1f} min ({seconds:.1f}s)"
    return f"{seconds:.2f}s"


def _divider(char: str = "─", width: int = 72) -> None:
    print(char * width, flush=True)


def _section(title: str) -> None:
    _divider("═")
    log.info(">>> %s", title)
    _divider("─")


def _milestone(label: str, elapsed: Optional[float] = None) -> None:
    suffix = f"  [{_fmt_duration(elapsed)}]" if elapsed is not None else ""
    log.info("<<< %s%s", label, suffix)


# ---------------------------------------------------------------------------
# Progress callback — each step is printed with a timestamp so you can
# compare the exact cadence against what the deployed backend produces.
# ---------------------------------------------------------------------------

_last_pct: float = -1.0
_progress_start: float = 0.0


def _make_progress_callback(stage_label: str):
    global _last_pct, _progress_start
    _last_pct = -1.0
    _progress_start = time.perf_counter()

    def _callback(fraction: float, message: Optional[str]) -> None:
        global _last_pct
        pct = round(fraction * 100)
        if pct == _last_pct:
            return
        _last_pct = pct
        elapsed = time.perf_counter() - _progress_start
        msg = message or ""
        log.info("[%s] %3d%%  %s  (%.2fs elapsed)", stage_label, pct, msg, elapsed)

    return _callback


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the full menuocr pipeline end-to-end with verbose timestamped logs. "
            "Compare output against the deployed site to pinpoint where time is spent."
        )
    )
    parser.add_argument("input", type=Path, help="Path to the menu file (PDF, image, …).")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help=(
            "Destination JSON summary file. Outputs written into a same-named directory. "
            f"Defaults to {DEFAULT_OUTPUT_DIR}/<stem>_pipeline/<stem>_pipeline.json"
        ),
    )
    parser.add_argument("--api-key", default=None,
                        help="Landing AI API key override. Falls back to LANDING_AI_API_KEY env var.")
    parser.add_argument("--parse-model", default=DEFAULT_PARSE_MODEL,
                        help=f"ADE parse model. Default: {DEFAULT_PARSE_MODEL}")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS,
                        help=f"HTTP timeout for ADE calls in seconds. Default: {DEFAULT_TIMEOUT_SECONDS}")
    parser.add_argument("--save-markdown", action="store_true",
                        help="Write ADE markdown output alongside other run artifacts.")
    parser.add_argument("--restaurant-id", default=None,
                        help="Optional restaurant ID to embed in RMF metadata.")
    parser.add_argument("--debug", action="store_true",
                        help="Force MENUOCR_DEBUG=true so full_run.json debug dump is written.")
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)

    if args.debug:
        os.environ["MENUOCR_DEBUG"] = "true"

    input_path = args.input.resolve()
    if not input_path.exists():
        sys.exit(f"Input file not found: {input_path}")

    stem = input_path.stem
    if args.output:
        output_path = args.output.resolve()
    else:
        output_path = DEFAULT_OUTPUT_DIR / f"{stem}_pipeline" / f"{stem}_pipeline.json"
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    api_key = (
        args.api_key
        or os.environ.get("LANDING_AI_API_KEY")
        or os.environ.get("LANDING_AI_ADE_API_KEY")
        or ""
    )
    if not api_key:
        sys.exit(
            "No Landing AI API key found. "
            "Pass --api-key or set LANDING_AI_API_KEY in your .env file."
        )

    rmf_metadata = RMFMetadata(
        restaurant_id=args.restaurant_id,
        generated_at=datetime.now(tz=timezone.utc),
    )

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    _divider("═")
    log.info("menuocr full-pipeline CLI benchmark")
    log.info("Input        : %s", input_path)
    log.info("Output dir   : %s", output_dir)
    log.info("Parse model  : %s", args.parse_model)
    log.info("Timeout      : %ds", args.timeout)
    log.info("Debug dump   : %s", os.environ.get("MENUOCR_DEBUG", "false"))
    _divider("═")

    timings: Dict[str, float] = {}
    wall_start = time.perf_counter()

    # ------------------------------------------------------------------
    # Stage 1 — ADE parse → ADE extract → GPT-4o per-category transforms
    # ------------------------------------------------------------------
    _section("STAGE 1 — ADE parse / extract + GPT-4o category transforms")
    t1_start = time.perf_counter()
    try:
        minimal_payload, debug_payload = extract_minimal_payload(
            input_path,
            output_dir=output_dir,
            api_key=api_key,
            parse_model=args.parse_model,
            timeout_seconds=args.timeout,
            save_markdown=args.save_markdown,
            progress_callback=_make_progress_callback("S1"),
        )
    except ADEClientError as exc:
        log.error("Pipeline failed at Stage 1: %s", exc)
        sys.exit(1)

    timings["stage1_extraction"] = time.perf_counter() - t1_start
    _milestone("STAGE 1 COMPLETE", timings["stage1_extraction"])

    cats = minimal_payload.get("categories") or []
    total_items = sum(len(c.get("items") or []) for c in cats)
    log.info("Stage 1 result: categories=%d  total_items=%d", len(cats), total_items)

    # Token usage summary from debug payload
    summary = (debug_payload or {}).get("summary", {})
    usage = summary.get("usage", {})
    if usage:
        log.info(
            "Token usage (all calls): prompt=%s  completion=%s  total=%s",
            usage.get("prompt_tokens", "?"),
            usage.get("completion_tokens", "?"),
            usage.get("total_tokens", "?"),
        )
    cat_ok = summary.get("categories_success", "?")
    cat_err = summary.get("categories_error", "?")
    log.info("Category runs: success=%s  error=%s", cat_ok, cat_err)

    # ------------------------------------------------------------------
    # Stage 2 — mapping → premenu → intermediate → mapped JSON + prermf + RMF
    # ------------------------------------------------------------------
    _section("STAGE 2 — mapping / premenu / prermf / RMF generation")
    t2_start = time.perf_counter()
    try:
        (
            output_json_path,
            rmf_path,
            prermf_payload,
            premenu_payload,
            intermediate_payload,
            mapped_payload,
            rmf_content,
        ) = finalize_generated_outputs(
            minimal_payload,
            output_dir=output_dir,
            document_path=input_path,
            rmf_metadata=rmf_metadata,
            progress_callback=_make_progress_callback("S2"),
        )
    except ADEClientError as exc:
        log.error("Pipeline failed at Stage 2: %s", exc)
        sys.exit(1)

    timings["stage2_mapping_rmf"] = time.perf_counter() - t2_start
    _milestone("STAGE 2 COMPLETE", timings["stage2_mapping_rmf"])

    wall_elapsed = time.perf_counter() - wall_start
    timings["total_wall_time"] = wall_elapsed

    # ------------------------------------------------------------------
    # Timing summary
    # ------------------------------------------------------------------
    _divider("═")
    log.info("TIMING SUMMARY")
    _divider("─")
    log.info("  Stage 1  (ADE parse + extract + GPT-4o) : %s", _fmt_duration(timings["stage1_extraction"]))
    log.info("  Stage 2  (mapping + prermf + RMF)       : %s", _fmt_duration(timings["stage2_mapping_rmf"]))
    log.info("  ─────────────────────────────────────────────────────")
    log.info("  Total wall time                         : %s", _fmt_duration(timings["total_wall_time"]))
    _divider("─")
    log.info("  Mapped JSON : %s", output_json_path)
    log.info("  RMF file    : %s", rmf_path)
    _divider("═")

    # ------------------------------------------------------------------
    # Persist timing summary as JSON
    # ------------------------------------------------------------------
    summary_out: Dict[str, Any] = {
        "input": str(input_path),
        "output_dir": str(output_dir),
        "timings_seconds": timings,
        "categories": len(cats),
        "total_items": total_items,
        "category_runs_success": cat_ok,
        "category_runs_error": cat_err,
        "token_usage": usage,
        "mapped_json": str(output_json_path),
        "rmf_file": str(rmf_path),
    }
    output_path.write_text(json.dumps(summary_out, indent=2) + "\n", encoding="utf-8")
    log.info("Timing summary saved to: %s", output_path)


if __name__ == "__main__":
    main()
