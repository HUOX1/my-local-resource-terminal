from __future__ import annotations

import logging
import os
from pathlib import Path


_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "g3.log"
    root = logging.getLogger("g3")
    root.setLevel(logging.INFO)
    formatter = logging.Formatter(_FORMAT)

    if not any(
        isinstance(handler, logging.FileHandler)
        and Path(handler.baseFilename) == log_path
        for handler in root.handlers
    ):
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(formatter)
        root.addHandler(handler)

    if os.environ.get("G3_DEBUG_CONSOLE") == "1" and not any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
        for handler in root.handlers
    ):
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)

    return log_path
