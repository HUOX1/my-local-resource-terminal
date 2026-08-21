from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def _normalize_terms(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value).strip()
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
    return result


@dataclass(slots=True)
class GameSession:
    id: str
    game_uuid: str
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: int = 0
    last_checkpoint_at: datetime | None = None
    status: str = "active"

    def __post_init__(self) -> None:
        if self.status not in {"active", "completed", "recovered"}:
            raise ValueError(f"invalid game session status: {self.status}")
        self.duration_seconds = max(0, int(self.duration_seconds))

    @classmethod
    def active(cls, game_uuid: str, started_at: datetime) -> "GameSession":
        return cls(
            id=str(uuid4()),
            game_uuid=game_uuid,
            started_at=started_at,
            last_checkpoint_at=started_at,
            status="active",
        )

    @classmethod
    def completed(
        cls,
        game_uuid: str,
        started_at: datetime,
        ended_at: datetime,
        *,
        status: str = "completed",
        session_id: str | None = None,
    ) -> "GameSession":
        duration = max(0, int((ended_at - started_at).total_seconds()))
        return cls(
            id=session_id or str(uuid4()),
            game_uuid=game_uuid,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration,
            last_checkpoint_at=ended_at,
            status=status,
        )


@dataclass(slots=True)
class GameMetadata:
    uuid: str
    title: str
    series: str = ""
    developer: str = ""
    publisher: str = ""
    release_date: str = ""
    tags: list[str] = field(default_factory=list)
    rating: int = 0
    favorite: bool = False
    description: str = ""
    notes: str = ""
    added_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    launch_exe: str = ""
    launch_args: str = ""
    working_directory: str = ""
    timing_exe: str = ""
    cover_path: str | None = None
    preview_gif_path: str | None = None
    archive_media_path: str | None = None
    screenshot_directory: str | None = None
    folder_id: str | None = None
    total_play_seconds: int = 0
    play_count: int = 0
    first_played_at: datetime | None = None
    last_played_at: datetime | None = None
    sessions: list[GameSession] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.normalize()

    @classmethod
    def new(
        cls,
        title: str,
        *,
        added_at: datetime | None = None,
        rating: int = 0,
    ) -> "GameMetadata":
        return cls(
            uuid=str(uuid4()),
            title=title,
            rating=rating,
            added_at=added_at or datetime.now(timezone.utc),
        )

    def normalize(self) -> None:
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("game title is required")
        if not 0 <= int(self.rating) <= 5:
            raise ValueError("rating must be between 0 and 5")
        self.rating = int(self.rating)
        self.series = self.series.strip()
        self.developer = self.developer.strip()
        self.publisher = self.publisher.strip()
        self.release_date = self.release_date.strip()
        self.tags = _normalize_terms(self.tags)
        self.description = self.description.strip()
        self.notes = self.notes.strip()
        self.launch_exe = self.launch_exe.strip()
        self.launch_args = self.launch_args.strip()
        self.working_directory = self.working_directory.strip()
        self.timing_exe = self.timing_exe.strip()
        self.cover_path = self.cover_path.strip() if self.cover_path else None
        self.preview_gif_path = self.preview_gif_path.strip() if self.preview_gif_path else None
        self.archive_media_path = self.archive_media_path.strip() if self.archive_media_path else None
        self.screenshot_directory = self.screenshot_directory.strip() if self.screenshot_directory else None
        self.folder_id = self.folder_id.strip() if self.folder_id else None
        self.total_play_seconds = max(0, int(self.total_play_seconds))
        self.play_count = max(0, int(self.play_count))

    def recalculate_play_stats(self) -> None:
        completed = [s for s in self.sessions if s.status in {"completed", "recovered"}]
        self.total_play_seconds = sum(max(0, int(s.duration_seconds)) for s in completed)
        self.play_count = len(completed)
        if completed:
            by_start = sorted(completed, key=lambda item: item.started_at)
            self.first_played_at = by_start[0].started_at
            ended = [s.ended_at for s in completed if s.ended_at is not None]
            self.last_played_at = max(ended) if ended else by_start[-1].started_at
        else:
            self.first_played_at = None
            self.last_played_at = None


@dataclass(slots=True)
class GameRecord:
    metadata: GameMetadata
    installed: bool

    @classmethod
    def from_metadata(cls, metadata: GameMetadata) -> "GameRecord":
        installed = bool(metadata.launch_exe and Path(metadata.launch_exe).is_file())
        return cls(metadata=metadata, installed=installed)


@dataclass(slots=True)
class GameMetadataPatch:
    title: str | None = None
    series: str | None = None
    developer: str | None = None
    publisher: str | None = None
    release_date: str | None = None
    tags: list[str] | None = None
    rating: int | None = None
    favorite: bool | None = None
    description: str | None = None
    notes: str | None = None
    launch_exe: str | None = None
    launch_args: str | None = None
    working_directory: str | None = None
    timing_exe: str | None = None
    cover_path: str | None = None
    preview_gif_path: str | None = None
    screenshot_directory: str | None = None
