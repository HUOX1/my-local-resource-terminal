from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(slots=True, frozen=True)
class PlayEvent:
    played_at: datetime


@dataclass(slots=True)
class MovieMetadata:
    uuid: str
    cover_key: str
    code: str = ""
    title: str = ""
    actors: list[str] = field(default_factory=list)
    series: str = ""
    studio: str = ""
    release_date: str = ""
    tags: list[str] = field(default_factory=list)
    rating: int = 0
    watched: bool = False
    play_count: int = 0
    total_play_seconds: int = 0
    favorite: bool = False
    notes: str = ""
    folder_id: str | None = None
    first_watched_at: datetime | None = None
    last_watched_at: datetime | None = None
    added_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    play_history: list[PlayEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0 <= self.rating <= 5:
            raise ValueError("rating must be between 0 and 5")
        self.cover_key = self.cover_key.strip()
        self.code = self.code.strip()
        self.actors = _normalize_list(self.actors)
        self.tags = _normalize_list(self.tags)
        self.folder_id = self.folder_id.strip() if self.folder_id else None
        self.total_play_seconds = max(0, int(self.total_play_seconds))

    @classmethod
    def new(
        cls,
        cover_key: str,
        code: str = "",
        *,
        added_at: datetime | None = None,
    ) -> "MovieMetadata":
        return cls(
            uuid=str(uuid4()),
            cover_key=cover_key,
            code=code,
            added_at=added_at or datetime.now(timezone.utc),
        )


def _normalize_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        item = value.strip()
        if item and item.casefold() not in seen:
            normalized.append(item)
            seen.add(item.casefold())
    return normalized


@dataclass(slots=True)
class MovieRuntime:
    video_path: str | None = None
    library_id: str | None = None
    availability_status: str = "offline"
    subtitle_status: bool = False
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    file_size: int | None = None
    cover_path: str | None = None
    last_scanned_at: datetime | None = None


@dataclass(slots=True)
class MovieRecord:
    metadata: MovieMetadata
    runtime: MovieRuntime


@dataclass(slots=True)
class MovieMetadataPatch:
    code: str | None = None
    title: str | None = None
    actors: list[str] | None = None
    series: str | None = None
    studio: str | None = None
    release_date: str | None = None
    tags: list[str] | None = None
    rating: int | None = None
    watched: bool | None = None
    favorite: bool | None = None
    notes: str | None = None
    cover_key: str | None = None
