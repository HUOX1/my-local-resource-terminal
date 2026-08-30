from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TerminalPaths:
    root: Path
    database: Path
    assets: Path
    cache: Path
    themes: Path
    logs: Path
    settings: Path

    @classmethod
    def from_environment(cls) -> "TerminalPaths":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            local_app_data = str(Path.home() / "AppData" / "Local")
        root = Path(local_app_data) / "LocalResourceTerminal" / "v0.6"
        return cls(root=root,database=root / "library.db",assets=root / "assets",cache=root / "cache",themes=root / "themes",logs=root / "logs",settings=root / "settings.json")

    def ensure(self) -> "TerminalPaths":
        self.root.mkdir(parents=True, exist_ok=True)
        for directory in (self.assets, self.cache, self.themes, self.logs):
            directory.mkdir(parents=True, exist_ok=True)
        return self
