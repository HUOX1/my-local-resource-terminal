from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.db.database import Database
from app.models.game import GameMetadata, GameRecord, GameSession


class GameRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def upsert_game(self, game: GameMetadata) -> None:
        game.normalize()
        with self.database.transaction() as connection:
            self._upsert_game(connection, game)
            self._replace_sessions(connection, game.uuid, game.sessions, preserve_active=True)

    def _upsert_game(self, connection, game: GameMetadata) -> None:
        connection.execute(
            """
            INSERT INTO games (
                uuid, title, series, developer, publisher, release_date, rating,
                favorite, description, notes, added_at, launch_exe, launch_args, working_directory,
                timing_exe, cover_path, preview_gif_path, archive_media_path, screenshot_directory, folder_id,
                total_play_seconds, play_count, first_played_at, last_played_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(uuid) DO UPDATE SET
                title=excluded.title,
                series=excluded.series,
                developer=excluded.developer,
                publisher=excluded.publisher,
                release_date=excluded.release_date,
                rating=excluded.rating,
                favorite=excluded.favorite,
                description=excluded.description,
                notes=excluded.notes,
                added_at=excluded.added_at,
                launch_exe=excluded.launch_exe,
                launch_args=excluded.launch_args,
                working_directory=excluded.working_directory,
                timing_exe=excluded.timing_exe,
                cover_path=excluded.cover_path,
                preview_gif_path=excluded.preview_gif_path,
                archive_media_path=excluded.archive_media_path,
                screenshot_directory=excluded.screenshot_directory,
                folder_id=excluded.folder_id,
                total_play_seconds=excluded.total_play_seconds,
                play_count=excluded.play_count,
                first_played_at=excluded.first_played_at,
                last_played_at=excluded.last_played_at
            """,
            (
                game.uuid,
                game.title,
                game.series,
                game.developer,
                game.publisher,
                game.release_date,
                game.rating,
                int(game.favorite),
                game.description,
                game.notes,
                _dt(game.added_at),
                game.launch_exe,
                game.launch_args,
                game.working_directory,
                game.timing_exe,
                game.cover_path,
                game.preview_gif_path,
                game.archive_media_path,
                game.screenshot_directory,
                game.folder_id,
                game.total_play_seconds,
                game.play_count,
                _dt(game.first_played_at),
                _dt(game.last_played_at),
            ),
        )
        connection.execute("DELETE FROM game_tags WHERE game_uuid=?", (game.uuid,))
        connection.executemany(
            "INSERT INTO game_tags(game_uuid, tag_name) VALUES (?, ?)",
            [(game.uuid, tag) for tag in game.tags],
        )

    def _replace_sessions(
        self,
        connection,
        game_uuid: str,
        sessions: Iterable[GameSession],
        *,
        preserve_active: bool = False,
    ) -> None:
        if preserve_active:
            connection.execute(
                "DELETE FROM game_sessions WHERE game_uuid=? AND status IN ('completed','recovered')",
                (game_uuid,),
            )
        else:
            connection.execute("DELETE FROM game_sessions WHERE game_uuid=?", (game_uuid,))
        connection.executemany(
            """
            INSERT INTO game_sessions(
                id, game_uuid, started_at, ended_at, duration_seconds, last_checkpoint_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    session.id,
                    game_uuid,
                    _dt(session.started_at),
                    _dt(session.ended_at),
                    int(session.duration_seconds),
                    _dt(session.last_checkpoint_at),
                    session.status,
                )
                for session in sessions
            ],
        )

    def replace_sessions(self, game_uuid: str, sessions: Iterable[GameSession]) -> None:
        with self.database.transaction() as connection:
            self._replace_sessions(connection, game_uuid, sessions)

    def upsert_active_session(self, session: GameSession) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO game_sessions(
                    id, game_uuid, started_at, ended_at, duration_seconds, last_checkpoint_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    ended_at=excluded.ended_at,
                    duration_seconds=excluded.duration_seconds,
                    last_checkpoint_at=excluded.last_checkpoint_at,
                    status=excluded.status
                """,
                (
                    session.id,
                    session.game_uuid,
                    _dt(session.started_at),
                    _dt(session.ended_at),
                    session.duration_seconds,
                    _dt(session.last_checkpoint_at),
                    session.status,
                ),
            )

    def complete_session(self, game: GameMetadata, session: GameSession) -> None:
        with self.database.transaction() as connection:
            self._upsert_game(connection, game)
            connection.execute(
                """
                INSERT INTO game_sessions(
                    id, game_uuid, started_at, ended_at, duration_seconds, last_checkpoint_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    ended_at=excluded.ended_at,
                    duration_seconds=excluded.duration_seconds,
                    last_checkpoint_at=excluded.last_checkpoint_at,
                    status=excluded.status
                """,
                (
                    session.id,
                    session.game_uuid,
                    _dt(session.started_at),
                    _dt(session.ended_at),
                    session.duration_seconds,
                    _dt(session.last_checkpoint_at),
                    session.status,
                ),
            )

    def get(self, uuid: str) -> GameRecord | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM games WHERE uuid=?", (uuid,)).fetchone()
            if row is None:
                return None
            tags = [
                item["tag_name"]
                for item in connection.execute(
                    "SELECT tag_name FROM game_tags WHERE game_uuid=? ORDER BY tag_name COLLATE NOCASE",
                    (uuid,),
                ).fetchall()
            ]
            session_rows = connection.execute(
                "SELECT * FROM game_sessions WHERE game_uuid=? AND status IN ('completed','recovered') ORDER BY started_at, id",
                (uuid,),
            ).fetchall()
        sessions = [_session_from_row(item) for item in session_rows]
        game = GameMetadata(
            uuid=row["uuid"],
            title=row["title"],
            series=row["series"],
            developer=row["developer"],
            publisher=row["publisher"],
            release_date=row["release_date"],
            tags=tags,
            rating=row["rating"],
            favorite=bool(row["favorite"]),
            description=row["description"],
            notes=row["notes"],
            added_at=_parse_dt(row["added_at"]) or datetime.now(timezone.utc),
            launch_exe=row["launch_exe"],
            launch_args=row["launch_args"],
            working_directory=row["working_directory"],
            timing_exe=row["timing_exe"],
            cover_path=row["cover_path"],
            preview_gif_path=row["preview_gif_path"],
            archive_media_path=row["archive_media_path"],
            screenshot_directory=row["screenshot_directory"],
            folder_id=row["folder_id"],
            total_play_seconds=row["total_play_seconds"],
            play_count=row["play_count"],
            first_played_at=_parse_dt(row["first_played_at"]),
            last_played_at=_parse_dt(row["last_played_at"]),
            sessions=sessions,
        )
        return GameRecord.from_metadata(game)

    def list_all(self) -> list[GameRecord]:
        return self.search(sort="title")

    def list_tags(self, limit: int = 30) -> list[str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT tag_name, COUNT(*) AS uses
                FROM game_tags
                GROUP BY tag_name
                ORDER BY uses DESC, tag_name COLLATE NOCASE
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [row["tag_name"] for row in rows]

    def search(
        self,
        search: str = "",
        *,
        favorite: bool | None = None,
        installed: bool | None = None,
        tag: str | None = None,
        recently_played: bool | None = None,
        folder_id: str | None = None,
        sort: str = "added_at",
        descending: bool = False,
    ) -> list[GameRecord]:
        clauses: list[str] = []
        params: list[object] = []
        term = search.strip()
        if term:
            like = f"%{term}%"
            clauses.append(
                "(g.title LIKE ? COLLATE NOCASE OR g.series LIKE ? COLLATE NOCASE OR "
                "g.developer LIKE ? COLLATE NOCASE OR g.publisher LIKE ? COLLATE NOCASE OR "
                "g.notes LIKE ? COLLATE NOCASE OR EXISTS (SELECT 1 FROM game_tags gt WHERE gt.game_uuid=g.uuid AND gt.tag_name LIKE ? COLLATE NOCASE))"
            )
            params.extend([like] * 6)
        if favorite is not None:
            clauses.append("g.favorite=?")
            params.append(int(favorite))
        if tag is not None:
            clauses.append("EXISTS (SELECT 1 FROM game_tags gt2 WHERE gt2.game_uuid=g.uuid AND gt2.tag_name=? COLLATE NOCASE)")
            params.append(tag)
        if recently_played:
            clauses.append("g.last_played_at IS NOT NULL")
        if folder_id is not None:
            clauses.append("g.folder_id=?")
            params.append(folder_id)
        direction = "DESC" if descending else "ASC"
        secondary = "g.title COLLATE NOCASE ASC"
        sort_sql = {
            "added_at": f"g.added_at {direction}, {secondary}",
            "title": f"g.title COLLATE NOCASE {direction}",
            "release_date": f"(g.release_date='') ASC, g.release_date {direction}, {secondary}",
            "rating": f"g.rating {direction}, {secondary}",
            "total_play_seconds": f"g.total_play_seconds {direction}, {secondary}",
            "last_played_at": f"(g.last_played_at IS NULL) ASC, g.last_played_at {direction}, {secondary}",
            "play_count": f"g.play_count {direction}, {secondary}",
        }.get(sort, f"g.title COLLATE NOCASE {direction}")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.database.connect() as connection:
            rows = connection.execute(
                f"SELECT g.uuid FROM games g{where} ORDER BY {sort_sql}", params
            ).fetchall()
        result = [record for row in rows if (record := self.get(row["uuid"])) is not None]
        if installed is not None:
            result = [record for record in result if record.installed is installed]
        return result

    def list_uuids_by_folder(self, folder_id: str) -> list[str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT uuid FROM games WHERE folder_id=? ORDER BY uuid",
                (folder_id,),
            ).fetchall()
        return [str(row["uuid"]) for row in rows]

    def rebuild_from_archives(self, games: Iterable[GameMetadata]) -> None:
        games = list(games)
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM games")
            for game in games:
                self._upsert_game(connection, game)
                self._replace_sessions(connection, game.uuid, game.sessions)

    def delete(self, uuid: str) -> None:
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM games WHERE uuid=?", (uuid,))

    def is_empty(self) -> bool:
        with self.database.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM games").fetchone()
            return bool(row and row["count"] == 0)


def _session_from_row(row) -> GameSession:
    return GameSession(
        id=row["id"],
        game_uuid=row["game_uuid"],
        started_at=_parse_dt(row["started_at"]) or datetime.now(timezone.utc),
        ended_at=_parse_dt(row["ended_at"]),
        duration_seconds=row["duration_seconds"],
        last_checkpoint_at=_parse_dt(row["last_checkpoint_at"]),
        status=row["status"],
    )


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None
