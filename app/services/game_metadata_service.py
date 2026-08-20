from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.models.game import GameMetadata, GameSession

GAME_METADATA_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class GameMetadataLoadError:
    path: Path
    message: str


class GameMetadataService:
    def __init__(self, metadata_dir: Path) -> None:
        self.metadata_dir = Path(metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, uuid: str) -> Path:
        return self.metadata_dir / f"{uuid}.json"

    def create(self, title: str) -> GameMetadata:
        game = GameMetadata.new(title)
        self.save(game)
        return game

    def save(self, game: GameMetadata) -> None:
        game.normalize()
        target = self.path_for(game.uuid)
        temporary = target.with_name(f".{target.name}.tmp")
        encoded = self._encode(game)
        temporary.write_text(json.dumps(encoded, ensure_ascii=False, indent=2), encoding="utf-8")
        verified = json.loads(temporary.read_text(encoding="utf-8"))
        self._decode(verified)
        temporary.replace(target)

    def load(self, uuid: str) -> GameMetadata:
        payload = json.loads(self.path_for(uuid).read_text(encoding="utf-8"))
        return self._decode(payload)

    def load_all(self) -> tuple[list[GameMetadata], list[GameMetadataLoadError]]:
        games: list[GameMetadata] = []
        errors: list[GameMetadataLoadError] = []
        for path in sorted(self.metadata_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                games.append(self._decode(payload))
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                errors.append(GameMetadataLoadError(path, str(exc)))
        return games, errors

    def delete(self, uuid: str) -> None:
        self.path_for(uuid).unlink(missing_ok=True)

    @staticmethod
    def _encode(game: GameMetadata) -> dict[str, Any]:
        return {
            "schema_version": GAME_METADATA_SCHEMA_VERSION,
            "uuid": game.uuid,
            "title": game.title,
            "series": game.series,
            "developer": game.developer,
            "publisher": game.publisher,
            "release_date": game.release_date,
            "tags": game.tags,
            "rating": game.rating,
            "favorite": game.favorite,
            "description": game.description,
            "notes": game.notes,
            "added_at": _dt(game.added_at),
            "launch_exe": game.launch_exe,
            "launch_args": game.launch_args,
            "working_directory": game.working_directory,
            "timing_exe": game.timing_exe,
            "cover_path": game.cover_path,
            "preview_gif_path": game.preview_gif_path,
            "archive_media_path": game.archive_media_path,
            "screenshot_directory": game.screenshot_directory,
            "folder_id": game.folder_id,
            "total_play_seconds": game.total_play_seconds,
            "play_count": game.play_count,
            "first_played_at": _dt(game.first_played_at),
            "last_played_at": _dt(game.last_played_at),
            "sessions": [
                {
                    "id": session.id,
                    "game_uuid": session.game_uuid,
                    "started_at": _dt(session.started_at),
                    "ended_at": _dt(session.ended_at),
                    "duration_seconds": session.duration_seconds,
                    "last_checkpoint_at": _dt(session.last_checkpoint_at),
                    "status": session.status,
                }
                for session in game.sessions
                if session.status in {"completed", "recovered"}
            ],
        }

    @staticmethod
    def _decode(payload: dict[str, Any]) -> GameMetadata:
        version = int(payload.get("schema_version", 1))
        if version != GAME_METADATA_SCHEMA_VERSION:
            raise ValueError(f"unsupported game metadata schema_version: {version}")
        uuid = str(payload["uuid"])
        sessions = [
            GameSession(
                id=str(item["id"]),
                game_uuid=str(item.get("game_uuid") or uuid),
                started_at=_required_dt(item.get("started_at")),
                ended_at=_parse_dt(item.get("ended_at")),
                duration_seconds=int(item.get("duration_seconds", 0)),
                last_checkpoint_at=_parse_dt(item.get("last_checkpoint_at")),
                status=str(item.get("status", "completed")),
            )
            for item in payload.get("sessions", [])
        ]
        return GameMetadata(
            uuid=uuid,
            title=str(payload["title"]),
            series=str(payload.get("series", "")),
            developer=str(payload.get("developer", "")),
            publisher=str(payload.get("publisher", "")),
            release_date=str(payload.get("release_date", "")),
            tags=list(payload.get("tags", [])),
            rating=int(payload.get("rating", 0)),
            favorite=bool(payload.get("favorite", False)),
            description=str(payload.get("description", "")),
            notes=str(payload.get("notes", "")),
            added_at=_required_dt(payload.get("added_at")),
            launch_exe=str(payload.get("launch_exe", "")),
            launch_args=str(payload.get("launch_args", "")),
            working_directory=str(payload.get("working_directory", "")),
            timing_exe=str(payload.get("timing_exe", "")),
            cover_path=str(payload["cover_path"]) if payload.get("cover_path") else None,
            preview_gif_path=str(payload["preview_gif_path"]) if payload.get("preview_gif_path") else None,
            archive_media_path=str(payload["archive_media_path"]) if payload.get("archive_media_path") else None,
            screenshot_directory=str(payload["screenshot_directory"]) if payload.get("screenshot_directory") else None,
            folder_id=str(payload["folder_id"]) if payload.get("folder_id") else None,
            total_play_seconds=int(payload.get("total_play_seconds", 0)),
            play_count=int(payload.get("play_count", 0)),
            first_played_at=_parse_dt(payload.get("first_played_at")),
            last_played_at=_parse_dt(payload.get("last_played_at")),
            sessions=sessions,
        )


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_dt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    return datetime.fromisoformat(str(value))


def _required_dt(value: Any) -> datetime:
    parsed = _parse_dt(value)
    if parsed is None:
        raise ValueError("required datetime is missing")
    return parsed
