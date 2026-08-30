from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import uuid

from .database import Database
from .models import CreateGame, GameRecord, MediaAsset


_SOURCE_RANK = {"manual": 0, "auto": 1, "generated": 2}


class LibraryRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_game(self, command: CreateGame) -> GameRecord:
        title = command.title.strip()
        if not title:
            raise ValueError("title is required")
        executable = Path(command.executable_path).expanduser().resolve()
        if not executable.exists():
            raise FileNotFoundError(executable)
        item_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        sort_title = title.casefold()
        working_directory = command.working_directory or str(executable.parent)
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO library_items
                    (id, media_type, title, sort_title, description, created_at, updated_at)
                VALUES (?, 'game', ?, ?, '', ?, ?)
                """,
                (item_id, title, sort_title, now, now),
            )
            conn.execute(
                """
                INSERT INTO games
                    (item_id, executable_path, launch_args, working_directory, platform)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item_id, str(executable), command.launch_args, working_directory, command.platform),
            )
        record = self.get_game(item_id)
        if record is None:
            raise RuntimeError("created game could not be reloaded")
        return record

    def list_games(self) -> list[GameRecord]:
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT li.id, li.title, li.sort_title, li.description,
                       g.executable_path, g.launch_args, g.working_directory,
                       g.platform, g.playtime_seconds, g.last_played_at, g.installed_state
                FROM library_items li
                JOIN games g ON g.item_id = li.id
                WHERE li.media_type = 'game'
                ORDER BY li.sort_title, li.id
                """
            ).fetchall()
        return [self._game_from_row(row) for row in rows]

    def get_game(self, item_id: str) -> GameRecord | None:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT li.id, li.title, li.sort_title, li.description,
                       g.executable_path, g.launch_args, g.working_directory,
                       g.platform, g.playtime_seconds, g.last_played_at, g.installed_state
                FROM library_items li
                JOIN games g ON g.item_id = li.id
                WHERE li.id = ? AND li.media_type = 'game'
                """,
                (item_id,),
            ).fetchone()
        return self._game_from_row(row) if row is not None else None

    def update_play_stats(self, item_id: str, seconds: int, ended_at: datetime) -> None:
        now_iso = ended_at.astimezone(timezone.utc).isoformat()
        with self.database.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE games
                SET playtime_seconds = playtime_seconds + ?, last_played_at = ?
                WHERE item_id = ?
                """,
                (max(0, int(seconds)), now_iso, item_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(item_id)
            conn.execute("UPDATE library_items SET updated_at = ? WHERE id = ?", (now_iso, item_id))

    def add_media_asset(
        self,
        owner_id: str,
        kind: str,
        path: Path,
        *,
        source: str,
        priority: int = 0,
        cache_path: Path | None = None,
    ) -> MediaAsset:
        if source not in _SOURCE_RANK:
            raise ValueError(f"invalid media source: {source}")
        source_path = Path(path).expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        asset = MediaAsset(
            id=str(uuid.uuid4()),
            owner_id=owner_id,
            kind=kind,
            path=source_path,
            cache_path=Path(cache_path).resolve() if cache_path else None,
            priority=int(priority),
            source=source,
        )
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO media_assets
                    (id, owner_id, kind, path, cache_path, priority, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset.id,
                    asset.owner_id,
                    asset.kind,
                    str(asset.path),
                    str(asset.cache_path) if asset.cache_path else None,
                    asset.priority,
                    asset.source,
                ),
            )
        return asset

    def best_media_asset(self, owner_id: str, kind: str) -> MediaAsset | None:
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, owner_id, kind, path, cache_path, priority, source
                FROM media_assets
                WHERE owner_id = ? AND kind = ?
                """,
                (owner_id, kind),
            ).fetchall()
        assets = [self._asset_from_row(row) for row in rows]
        if not assets:
            return None
        return min(assets, key=lambda item: (_SOURCE_RANK[item.source], item.priority, item.id))

    @staticmethod
    def _game_from_row(row) -> GameRecord:
        last_played = datetime.fromisoformat(str(row["last_played_at"])) if row["last_played_at"] else None
        return GameRecord(
            id=str(row["id"]),
            title=str(row["title"]),
            sort_title=str(row["sort_title"]),
            description=str(row["description"]),
            executable_path=Path(str(row["executable_path"])),
            launch_args=str(row["launch_args"]),
            working_directory=str(row["working_directory"]),
            platform=str(row["platform"]),
            playtime_seconds=int(row["playtime_seconds"]),
            last_played_at=last_played,
            installed_state=str(row["installed_state"]),
        )

    @staticmethod
    def _asset_from_row(row) -> MediaAsset:
        return MediaAsset(
            id=str(row["id"]),
            owner_id=str(row["owner_id"]),
            kind=str(row["kind"]),
            path=Path(str(row["path"])),
            cache_path=Path(str(row["cache_path"])) if row["cache_path"] else None,
            priority=int(row["priority"]),
            source=str(row["source"]),
        )
