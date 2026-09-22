"""Start the menu bar application."""

from __future__ import annotations

import sys


def main() -> int:
    from .app import run

    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
