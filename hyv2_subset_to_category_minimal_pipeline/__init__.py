from __future__ import annotations

from typing import List, Optional

__all__ = ["main"]


def main(argv: Optional[List[str]] = None) -> None:
    from .cli import main as cli_main

    cli_main(argv)
