"""Allow ``python -m bot`` to launch the screener bot."""

from __future__ import annotations

import asyncio

from .main import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
