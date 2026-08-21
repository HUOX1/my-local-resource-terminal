from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.models.movie import legacy_episode_uuid

CURRENT_SCHEMA_VERSION = 7


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _open_connection(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = self._open_connection()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        with self.connect() as connection:
            connection.executescript(schema)
            version_row = connection.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()
            previous_version = int(version_row["value"]) if version_row else 0
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(movies)")}
            if "added_at" not in columns:
                connection.execute("ALTER TABLE movies ADD COLUMN added_at TEXT")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_movies_added_at ON movies(added_at)")
            if "folder_id" not in columns:
                connection.execute("ALTER TABLE movies ADD COLUMN folder_id TEXT")
            if "total_play_seconds" not in columns:
                connection.execute("ALTER TABLE movies ADD COLUMN total_play_seconds INTEGER NOT NULL DEFAULT 0")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_movies_folder_id ON movies(folder_id)")
            game_columns = {row["name"] for row in connection.execute("PRAGMA table_info(games)")}
            if "description" not in game_columns:
                connection.execute("ALTER TABLE games ADD COLUMN description TEXT NOT NULL DEFAULT ''")
            if "archive_media_path" not in game_columns:
                connection.execute("ALTER TABLE games ADD COLUMN archive_media_path TEXT")
            if "folder_id" not in game_columns:
                connection.execute("ALTER TABLE games ADD COLUMN folder_id TEXT")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_games_folder_id ON games(folder_id)")
            if previous_version < 7:
                self._migrate_legacy_movie_runtime(connection)
            connection.execute(
                "INSERT INTO schema_meta(key, value) VALUES('schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(CURRENT_SCHEMA_VERSION),),
            )

    @staticmethod
    def _migrate_legacy_movie_runtime(connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            """
            SELECT m.*
            FROM movies m
            WHERE NOT EXISTS (
                SELECT 1 FROM movie_episodes e WHERE e.movie_uuid=m.uuid
            )
            """
        ).fetchall()
        for row in rows:
            video_path = row["video_path"]
            connection.execute(
                """
                INSERT INTO movie_episodes (
                    uuid, movie_uuid, display_order, episode_number, season_number,
                    source_name, video_path, library_id, availability_status,
                    subtitle_status, duration, width, height, video_codec,
                    audio_codec, file_size, last_scanned_at
                ) VALUES (?, ?, 1, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    legacy_episode_uuid(row["uuid"]),
                    row["uuid"],
                    _source_name(video_path),
                    video_path,
                    row["library_id"],
                    row["availability_status"],
                    row["subtitle_status"],
                    row["duration"],
                    row["width"],
                    row["height"],
                    row["video_codec"],
                    row["audio_codec"],
                    row["file_size"],
                    row["last_scanned_at"],
                ),
            )

    def schema_version(self) -> int:
        if not self.path.exists():
            return 0
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()
            return int(row["value"]) if row else 0

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._open_connection()
        try:
            connection.execute("BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def is_empty(self) -> bool:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM movies").fetchone()
            return bool(row and row["count"] == 0)


def _source_name(video_path: str | None) -> str:
    if not video_path:
        return ""
    return str(video_path).replace("\\", "/").rsplit("/", 1)[-1]
