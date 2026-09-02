from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from .database import Database
from .models import CreateGame, GameRecord, LaunchProfile, MediaAsset


_SOURCE_RANK = {"manual": 0, "auto": 1, "generated": 2}


class LibraryRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_game(self, command: CreateGame) -> GameRecord:
        title = command.title.strip()
        if not title:
            raise ValueError("title is required")
        profile = command.launch_profile()

        item_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        sort_title = title.casefold()

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
                    (item_id, profile_type, launch_exe, launch_args, working_directory,
                     content_path, monitor_exe, wait_timeout_s, run_as_admin, platform)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    profile.profile_type,
                    str(profile.launch_exe),
                    profile.launch_args,
                    str(profile.working_directory or ""),
                    str(profile.content_path) if profile.content_path else None,
                    str(profile.monitor_exe or profile.launch_exe),
                    profile.wait_timeout_s,
                    1 if profile.run_as_admin else 0,
                    command.platform,
                ),
            )
        record = self.get_game(item_id)
        if record is None:
            raise RuntimeError("created game could not be reloaded")
        return record

    @staticmethod
    def _game_select_sql(where_clause: str = "") -> str:
        return f"""
            SELECT li.id, li.title, li.sort_title, li.description,
                   g.profile_type, g.launch_exe, g.launch_args, g.working_directory,
                   g.content_path, g.monitor_exe, g.wait_timeout_s, g.run_as_admin,
                   g.platform, g.playtime_seconds, g.last_played_at, g.installed_state,
                   COALESCE(gm.developer, '') AS developer,
                   COALESCE(gm.publisher, '') AS publisher,
                   gm.release_year AS release_year,
                   COALESCE(gm.tags, '') AS tags,
                   COALESCE(gm.notes, '') AS notes
            FROM library_items li
            JOIN games g ON g.item_id = li.id
            LEFT JOIN game_metadata gm ON gm.item_id = li.id
            WHERE li.media_type = 'game' {where_clause}
        """

    def list_games(self) -> list[GameRecord]:
        with self.database.connect() as conn:
            rows = conn.execute(
                self._game_select_sql() + " ORDER BY li.sort_title, li.id"
            ).fetchall()
        return [self._game_from_row(row) for row in rows]

    def get_game(self, item_id: str) -> GameRecord | None:
        with self.database.connect() as conn:
            row = conn.execute(
                self._game_select_sql("AND li.id = ?"),
                (item_id,),
            ).fetchone()
        return self._game_from_row(row) if row is not None else None

    def get_launch_profile(self, item_id: str) -> LaunchProfile:
        game = self.get_game(item_id)
        if game is None:
            raise KeyError(item_id)
        return game.launch_profile

    def update_launch_profile(self, item_id: str, profile: LaunchProfile) -> LaunchProfile:
        normalized = profile.normalized()
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE games
                SET profile_type = ?, launch_exe = ?, launch_args = ?, working_directory = ?,
                    content_path = ?, monitor_exe = ?, wait_timeout_s = ?, run_as_admin = ?,
                    installed_state = 'installed'
                WHERE item_id = ?
                """,
                (
                    normalized.profile_type,
                    str(normalized.launch_exe),
                    normalized.launch_args,
                    str(normalized.working_directory or ""),
                    str(normalized.content_path) if normalized.content_path else None,
                    str(normalized.monitor_exe or normalized.launch_exe),
                    normalized.wait_timeout_s,
                    1 if normalized.run_as_admin else 0,
                    item_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(item_id)
            conn.execute(
                "UPDATE library_items SET updated_at = ? WHERE id = ?",
                (now, item_id),
            )
        return self.get_launch_profile(item_id)

    def update_game_metadata(
        self,
        item_id: str,
        *,
        title: str,
        platform: str = "",
        description: str = "",
        developer: str = "",
        publisher: str = "",
        release_year: int | None = None,
        tags: str = "",
        notes: str = "",
    ) -> GameRecord:
        clean_title = str(title).strip()
        if not clean_title:
            raise ValueError("title is required")
        year = None if release_year in (None, 0) else int(release_year)
        if year is not None and not 1000 <= year <= 9999:
            raise ValueError("release_year must be a four-digit year")
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connect() as conn:
            item_cursor = conn.execute(
                """
                UPDATE library_items
                SET title = ?, sort_title = ?, description = ?, updated_at = ?
                WHERE id = ? AND media_type = 'game'
                """,
                (clean_title, clean_title.casefold(), str(description).strip(), now, item_id),
            )
            if item_cursor.rowcount != 1:
                raise KeyError(item_id)
            game_cursor = conn.execute(
                "UPDATE games SET platform = ? WHERE item_id = ?",
                (str(platform).strip(), item_id),
            )
            if game_cursor.rowcount != 1:
                raise KeyError(item_id)
            conn.execute(
                """
                INSERT INTO game_metadata
                    (item_id, developer, publisher, release_year, tags, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    developer = excluded.developer,
                    publisher = excluded.publisher,
                    release_year = excluded.release_year,
                    tags = excluded.tags,
                    notes = excluded.notes
                """,
                (
                    item_id,
                    str(developer).strip(),
                    str(publisher).strip(),
                    year,
                    str(tags).strip(),
                    str(notes).strip(),
                ),
            )
        game = self.get_game(item_id)
        if game is None:
            raise KeyError(item_id)
        return game

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
            conn.execute(
                "UPDATE library_items SET updated_at = ? WHERE id = ?",
                (now_iso, item_id),
            )

    def get_state(self) -> dict[str, object]:
        with self.database.connect() as conn:
            rows = conn.execute("SELECT key, value_json FROM terminal_state ORDER BY key").fetchall()
        return {str(row["key"]): json.loads(str(row["value_json"])) for row in rows}

    def update_state(self, values: dict[str, object]) -> None:
        with self.database.connect() as conn:
            for key, value in values.items():
                conn.execute(
                    """
                    INSERT INTO terminal_state (key, value_json) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json
                    """,
                    (str(key), json.dumps(value, ensure_ascii=False)),
                )

    def add_media_asset(self, owner_id: str, kind: str, path: Path, *, source: str,
                        priority: int = 0, cache_path: Path | None = None) -> MediaAsset:
        if source not in _SOURCE_RANK:
            raise ValueError(f"invalid media source: {source}")
        source_path = Path(path).expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        asset = MediaAsset(
            id=str(uuid.uuid4()), owner_id=owner_id, kind=kind, path=source_path,
            cache_path=Path(cache_path).resolve() if cache_path else None,
            priority=int(priority), source=source,
        )
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO media_assets (id, owner_id, kind, path, cache_path, priority, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (asset.id, asset.owner_id, asset.kind, str(asset.path),
                 str(asset.cache_path) if asset.cache_path else None,
                 asset.priority, asset.source),
            )
        return asset

    def list_media_assets(self, owner_id: str, kind: str | None = None) -> list[MediaAsset]:
        with self.database.connect() as conn:
            if kind is None:
                rows = conn.execute(
                    "SELECT id, owner_id, kind, path, cache_path, priority, source FROM media_assets WHERE owner_id = ?",
                    (owner_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, owner_id, kind, path, cache_path, priority, source FROM media_assets WHERE owner_id = ? AND kind = ?",
                    (owner_id, kind),
                ).fetchall()
        assets = [self._asset_from_row(row) for row in rows]
        return sorted(assets, key=lambda item: (item.kind, _SOURCE_RANK[item.source], item.priority, item.id))

    def best_media_asset(self, owner_id: str, kind: str) -> MediaAsset | None:
        assets = self.list_media_assets(owner_id, kind)
        if not assets:
            return None
        return min(assets, key=lambda item: (_SOURCE_RANK[item.source], item.priority, item.id))

    @staticmethod
    def _game_from_row(row) -> GameRecord:
        last_played = datetime.fromisoformat(str(row["last_played_at"])) if row["last_played_at"] else None
        profile = LaunchProfile(
            profile_type=str(row["profile_type"]),
            launch_exe=Path(str(row["launch_exe"])),
            launch_args=str(row["launch_args"]),
            working_directory=Path(str(row["working_directory"])) if row["working_directory"] else None,
            content_path=Path(str(row["content_path"])) if row["content_path"] else None,
            monitor_exe=Path(str(row["monitor_exe"])) if row["monitor_exe"] else None,
            wait_timeout_s=int(row["wait_timeout_s"]),
            run_as_admin=bool(row["run_as_admin"]),
        )
        return GameRecord(
            id=str(row["id"]), title=str(row["title"]), sort_title=str(row["sort_title"]),
            description=str(row["description"]), launch_profile=profile,
            platform=str(row["platform"]), developer=str(row["developer"]),
            publisher=str(row["publisher"]),
            release_year=int(row["release_year"]) if row["release_year"] is not None else None,
            tags=str(row["tags"]), notes=str(row["notes"]),
            playtime_seconds=int(row["playtime_seconds"]),
            last_played_at=last_played, installed_state=str(row["installed_state"]),
        )

    @staticmethod
    def _asset_from_row(row) -> MediaAsset:
        return MediaAsset(
            id=str(row["id"]), owner_id=str(row["owner_id"]), kind=str(row["kind"]),
            path=Path(str(row["path"])),
            cache_path=Path(str(row["cache_path"])) if row["cache_path"] else None,
            priority=int(row["priority"]), source=str(row["source"]),
        )
