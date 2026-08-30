from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class CreateGame:
    title: str
    executable_path: Path
    launch_args: str = ""
    working_directory: str = ""
    platform: str = ""


@dataclass(slots=True)
class GameRecord:
    id: str
    title: str
    sort_title: str
    description: str
    executable_path: Path
    launch_args: str
    working_directory: str
    platform: str
    playtime_seconds: int
    last_played_at: datetime | None
    installed_state: str


@dataclass(slots=True)
class MediaAsset:
    id: str
    owner_id: str
    kind: str
    path: Path
    cache_path: Path | None
    priority: int
    source: str
