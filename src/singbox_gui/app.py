from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    try:
        from .ui.main_window import run
    except ModuleNotFoundError as exc:
        if exc.name == "PySide6":
            print("PySide6 is not installed. Run: pip install -e .", file=sys.stderr)
            return 1
        raise

    return run(sys.argv if argv is None else argv)
