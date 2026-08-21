from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid4, uuid5


@dataclass(slots=True, frozen=True)
class PlayEvent:
    played_at: datetime


def legacy_episode_uuid(movie_uuid: str) -> str:
    return str(
        uuid5(
            NAMESPACE_URL,
            f"local-resource-terminal:movie:{str(movie_uuid)}:legacy-main",
        )
    )


@dataclass(slots=True)
class MovieEpisodeMetadata:
    uuid: str
    display_order: int
    episode_number: int | None = None
    season_number: int | None = None
    source_name: str = ""

    def __post_init__(self) -> None:
        self.uuid = self.uuid.strip()
        if not self.uuid:
            raise ValueError("episode uuid must not be empty")
        self.display_order = int(self.display_order)
        if self.display_order < 1:
            raise ValueError("display_order must be at least 1")
        self.episode_number = (
            int(self.episode_number) if self.episode_number is not None else None
        )
        self.season_number = (
            int(self.season_number) if self.season_number is not None else None
        )
        self.source_name = self.source_name.strip()

    @classmethod
    def new(
        cls,
        display_order: int,
        *,
        episode_number: int | None = None,
        season_number: int | None = None,
        source_name: str = "",
    ) -> "MovieEpisodeMetadata":
        return cls(
            uuid=str(uuid4()),
            display_order=display_order,
            episode_number=episode_number,
            season_number=season_number,
            source_name=source_name,
        )


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
    episodes: list[MovieEpisodeMetadata] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0 <= self.rating <= 5:
            raise ValueError("rating must be between 0 and 5")
        self.cover_key = self.cover_key.strip()
        self.code = self.code.strip()
        self.actors = _normalize_list(self.actors)
        self.tags = _normalize_list(self.tags)
        self.folder_id = self.folder_id.strip() if self.folder_id else None
        self.total_play_seconds = max(0, int(self.total_play_seconds))
        self.episodes = sorted(
            self.episodes,
            key=lambda episode: (
                episode.display_order,
                episode.source_name.casefold(),
                episode.uuid,
            ),
        )

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
class MovieEpisodeRuntime:
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
    last_scanned_at: datetime | None = None


@dataclass(slots=True)
class MovieEpisodeRecord:
    metadata: MovieEpisodeMetadata
    runtime: MovieEpisodeRuntime


@dataclass(slots=True)
class MovieRecord:
    metadata: MovieMetadata
    runtime: MovieRuntime
    episodes: list[MovieEpisodeRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.episodes = sorted(
            self.episodes,
            key=lambda episode: (
                episode.metadata.display_order,
                episode.metadata.source_name.casefold(),
                episode.metadata.uuid,
            ),
        )

    def single_episode(self) -> MovieEpisodeRecord | None:
        return self.episodes[0] if len(self.episodes) == 1 else None

    def episode(self, episode_uuid: str) -> MovieEpisodeRecord | None:
        return next(
            (
                episode
                for episode in self.episodes
                if episode.metadata.uuid == episode_uuid
            ),
            None,
        )

    def playable_episodes(self) -> list[MovieEpisodeRecord]:
        return [
            episode
            for episode in self.episodes
            if episode.runtime.availability_status == "available"
            and bool(episode.runtime.video_path)
        ]


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
