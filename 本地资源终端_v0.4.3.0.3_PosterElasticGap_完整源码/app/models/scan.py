from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True, frozen=True)
class MovieCandidate:
    folder: Path
    video_path: Path
    cover_key: str
    inferred_code: str
    subtitle_paths: list[Path] = field(default_factory=list)


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
