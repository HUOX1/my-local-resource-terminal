from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def restart_application() -> None:
    """Launch a fresh copy of the application after the current one exits."""
    project_root = Path(__file__).resolve().parents[1]
    if getattr(sys, "frozen", False):
        command = [sys.executable]
    else:
        command = [sys.executable, "-m", "app.main"]

    kwargs: dict[str, object] = {"cwd": str(project_root)}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(command, **kwargs)
