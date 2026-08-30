from __future__ import annotations

import asyncio
import ctypes
import logging
import os

from .runtime import run_terminal


def _show_startup_error(message: str) -> None:
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(
            None,
            message,
            "G3",
            0x10,
        )


def main() -> int:
    try:
        return asyncio.run(run_terminal())
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        logging.getLogger("g3.launcher").exception("Startup failed")
        _show_startup_error(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
