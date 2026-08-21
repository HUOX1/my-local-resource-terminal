from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True, frozen=True)
class EpisodeCandidate:
    video_path: Path
    source_name: str
    display_order: int
    episode_number: int | None
    season_number: int | None
    subtitle_paths: tuple[Path, ...] = ()


@dataclass(slots=True, frozen=True)
class MovieCandidate:
    folder: Path
    cover_key: str
    inferred_code: str
    episodes: tuple[EpisodeCandidate, ...]


@dataclass(slots=True, frozen=True)
class ScanError:
    path: Path | None
    message: str


@dataclass(slots=True, frozen=True)
class MatchAmbiguity:
    candidate: MovieCandidate
    movie_uuids: list[str]


@dataclass(slots=True)
class ScanSummary:
    new: int = 0
    updated: int = 0
    offline: int = 0
    errors: list[ScanError] = field(default_factory=list)
    ambiguities: list[MatchAmbiguity] = field(default_factory=list)
