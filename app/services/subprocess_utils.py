from __future__ import annotations

import subprocess
import sys


def hidden_console_kwargs() -> dict[str, int]:
    """Return subprocess options that suppress internal console windows on Windows."""
    if sys.platform != "win32":
        return {}
    flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return {"creationflags": flag} if flag else {}
