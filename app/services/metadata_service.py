from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models.movie import MovieMetadata, PlayEvent

SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class MetadataLoadError:
    path: Path
    message: str


class MetadataService:
    def __init__(self, metadata_dir: Path) -> None:
        self.metadata_dir = Path(metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def create(self, cover_key: str, code: str = "") -> MovieMetadata:
        movie = MovieMetadata.new(cover_key=cover_key, code=code)
        self.save(movie)
        return movie

    def path_for(self, uuid: str) -> Path:
        return self.metadata_dir / f"{uuid}.json"

    def load(self, uuid: str) -> MovieMetadata:
        path = self.path_for(uuid)
        payload = json.loads(path.read_text(encoding="utf-8"))
        movie = self._decode(payload, fallback_added_at=_file_timestamp(path))
        if not payload.get("added_at"):
            self.save(movie)
        return movie

    def save(self, movie: MovieMetadata) -> None:
        target = self.path_for(movie.uuid)
        temporary = target.with_name(f"{target.name}.tmp")
        temporary.write_text(
            json.dumps(self._encode(movie), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(target)

    def delete(self, uuid: str) -> None:
        self.path_for(uuid).unlink(missing_ok=True)

    def load_all(self) -> tuple[list[MovieMetadata], list[MetadataLoadError]]:
        movies: list[MovieMetadata] = []
        errors: list[MetadataLoadError] = []
        for path in sorted(self.metadata_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                movie = self._decode(payload, fallback_added_at=_file_timestamp(path))
                if not payload.get("added_at"):
                    self.save(movie)
                movies.append(movie)
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                errors.append(MetadataLoadError(path=path, message=str(exc)))
        return movies, errors

    @staticmethod
    def _encode(movie: MovieMetadata) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "uuid": movie.uuid,
            "cover_key": movie.cover_key,
            "code": movie.code,
            "title": movie.title,
            "actors": movie.actors,
            "series": movie.series,
            "studio": movie.studio,
            "release_date": movie.release_date,
            "tags": movie.tags,
            "rating": movie.rating,
            "watched": movie.watched,
            "play_count": movie.play_count,
            "total_play_seconds": movie.total_play_seconds,
            "favorite": movie.favorite,
            "notes": movie.notes,
            "folder_id": movie.folder_id,
            "first_watched_at": _encode_datetime(movie.first_watched_at),
            "last_watched_at": _encode_datetime(movie.last_watched_at),
            "added_at": _encode_datetime(movie.added_at),
            "play_history": [
                {"played_at": _encode_datetime(event.played_at)} for event in movie.play_history
            ],
        }

    @staticmethod
    def _decode(payload: dict[str, Any], fallback_added_at: datetime | None = None) -> MovieMetadata:
        version = int(payload.get("schema_version", 1))
        if version != SCHEMA_VERSION:
            raise ValueError(f"unsupported metadata schema_version: {version}")
        return MovieMetadata(
            uuid=str(payload["uuid"]),
            cover_key=str(payload["cover_key"]),
            code=str(payload.get("code", "")),
            title=str(payload.get("title", "")),
            actors=list(payload.get("actors", [])),
            series=str(payload.get("series", "")),
            studio=str(payload.get("studio", "")),
            release_date=str(payload.get("release_date", "")),
            tags=list(payload.get("tags", [])),
            rating=int(payload.get("rating", 0)),
            watched=bool(payload.get("watched", False)),
            play_count=int(payload.get("play_count", 0)),
            total_play_seconds=int(payload.get("total_play_seconds", 0)),
            favorite=bool(payload.get("favorite", False)),
            notes=str(payload.get("notes", "")),
            folder_id=str(payload["folder_id"]) if payload.get("folder_id") else None,
            first_watched_at=_decode_datetime(payload.get("first_watched_at")),
            last_watched_at=_decode_datetime(payload.get("last_watched_at")),
            added_at=_decode_datetime(payload.get("added_at")) or fallback_added_at or datetime.now(timezone.utc),
            play_history=[
                PlayEvent(_decode_required_datetime(item.get("played_at")))
                for item in payload.get("play_history", [])
            ],
        )


def _encode_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _decode_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    return datetime.fromisoformat(str(value))


def _decode_required_datetime(value: Any) -> datetime:
    decoded = _decode_datetime(value)
    if decoded is None:
        raise ValueError("play_history item is missing played_at")
    return decoded


def _file_timestamp(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
