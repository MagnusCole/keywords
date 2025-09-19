from __future__ import annotations

import asyncio

from main import main as _async_main


def run() -> None:
    """Synchronous entrypoint for packaging scripts.

    This wraps the async `main()` from `main.py` so the script declared in pyproject works.
    """
    asyncio.run(_async_main())


if __name__ == "__main__":
    run()
