from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Sequence

from app.db.database import Database
from app.models.movie import MovieMetadata, MovieRecord, MovieRuntime, PlayEvent


class MovieRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def upsert_metadata(self, movie: MovieMetadata) -> None:
        with self.database.transaction() as connection:
            self._upsert_metadata(connection, movie)

    def _upsert_metadata(self, connection, movie: MovieMetadata) -> None:
        connection.execute(
            """
            INSERT INTO movies (
                uuid, cover_key, code, title, series, studio, release_date,
                rating, watched, play_count, total_play_seconds, favorite, notes, folder_id,
                first_watched_at, last_watched_at, added_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(uuid) DO UPDATE SET
                cover_key=excluded.cover_key,
                code=excluded.code,
                title=excluded.title,
                series=excluded.series,
                studio=excluded.studio,
                release_date=excluded.release_date,
                rating=excluded.rating,
                watched=excluded.watched,
                play_count=excluded.play_count,
                total_play_seconds=excluded.total_play_seconds,
                favorite=excluded.favorite,
                notes=excluded.notes,
                folder_id=excluded.folder_id,
                first_watched_at=excluded.first_watched_at,
                last_watched_at=excluded.last_watched_at,
                added_at=excluded.added_at
            """,
            (
                movie.uuid,
                movie.cover_key,
                movie.code,
                movie.title,
                movie.series,
                movie.studio,
                movie.release_date,
                movie.rating,
                int(movie.watched),
                movie.play_count,
                movie.total_play_seconds,
                int(movie.favorite),
                movie.notes,
                movie.folder_id,
                _dt(movie.first_watched_at),
                _dt(movie.last_watched_at),
                _dt(movie.added_at),
            ),
        )
        connection.execute("DELETE FROM movie_actors WHERE movie_uuid = ?", (movie.uuid,))
        for position, actor in enumerate(movie.actors):
            connection.execute("INSERT OR IGNORE INTO actors(name) VALUES (?)", (actor,))
            connection.execute(
                "INSERT INTO movie_actors(movie_uuid, actor_name, position) VALUES (?, ?, ?)",
                (movie.uuid, actor, position),
            )
        connection.execute("DELETE FROM movie_tags WHERE movie_uuid = ?", (movie.uuid,))
        for tag in movie.tags:
            connection.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (tag,))
            connection.execute(
                "INSERT INTO movie_tags(movie_uuid, tag_name) VALUES (?, ?)",
                (movie.uuid, tag),
            )

    def update_runtime(
        self,
        uuid: str,
        *,
        video_path: str | None,
        library_id: str | None,
        availability_status: str,
        subtitle_status: bool,
        duration: float | None = None,
        width: int | None = None,
        height: int | None = None,
        video_codec: str | None = None,
        audio_codec: str | None = None,
        file_size: int | None = None,
        cover_path: str | None = None,
        last_scanned_at: datetime | None = None,
    ) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE movies SET
                    video_path=?, library_id=?, availability_status=?, subtitle_status=?,
                    duration=?, width=?, height=?, video_codec=?, audio_codec=?,
                    file_size=?, cover_path=?, last_scanned_at=?
                WHERE uuid=?
                """,
                (
                    video_path,
                    library_id,
                    availability_status,
                    int(subtitle_status),
                    duration,
                    width,
                    height,
                    video_codec,
                    audio_codec,
                    file_size,
                    cover_path,
                    _dt(last_scanned_at),
                    uuid,
                ),
            )

    def mark_offline(self, uuid: str) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE movies SET availability_status='offline' WHERE uuid=?",
                (uuid,),
            )

    def mark_library_offline(self, library_id: str, except_uuids: Sequence[str] = ()) -> int:
        with self.database.transaction() as connection:
            if except_uuids:
                placeholders = ",".join("?" for _ in except_uuids)
                params = [library_id, *except_uuids]
                cursor = connection.execute(
                    f"UPDATE movies SET availability_status='offline' WHERE library_id=? AND availability_status='available' AND uuid NOT IN ({placeholders})",
                    params,
                )
            else:
                cursor = connection.execute(
                    "UPDATE movies SET availability_status='offline' WHERE library_id=? AND availability_status='available'",
                    (library_id,),
                )
            return cursor.rowcount

    def record_play_event(self, uuid: str, played_at: datetime) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO play_events(movie_uuid, played_at) VALUES (?, ?)",
                (uuid, played_at.isoformat()),
            )

    def replace_play_events(self, uuid: str, events: Iterable[PlayEvent]) -> None:
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM play_events WHERE movie_uuid=?", (uuid,))
            connection.executemany(
                "INSERT INTO play_events(movie_uuid, played_at) VALUES (?, ?)",
                [(uuid, event.played_at.isoformat()) for event in events],
            )

    def list_play_events(self, uuid: str) -> list[datetime]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT played_at FROM play_events WHERE movie_uuid=? ORDER BY played_at, id",
                (uuid,),
            ).fetchall()
        return [datetime.fromisoformat(row["played_at"]) for row in rows]

    def rebuild_from_archives(self, movies: Iterable[MovieMetadata]) -> None:
        movies = list(movies)
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM movies")
            for movie in movies:
                self._upsert_metadata(connection, movie)
                connection.executemany(
                    "INSERT INTO play_events(movie_uuid, played_at) VALUES (?, ?)",
                    [(movie.uuid, event.played_at.isoformat()) for event in movie.play_history],
                )

    def get(self, uuid: str) -> MovieRecord | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM movies WHERE uuid=?", (uuid,)).fetchone()
            if row is None:
                return None
            actors = [
                item["actor_name"]
                for item in connection.execute(
                    "SELECT actor_name FROM movie_actors WHERE movie_uuid=? ORDER BY position",
                    (uuid,),
                )
            ]
            tags = [
                item["tag_name"]
                for item in connection.execute(
                    "SELECT tag_name FROM movie_tags WHERE movie_uuid=? ORDER BY tag_name COLLATE NOCASE",
                    (uuid,),
                )
            ]
            events = [
                PlayEvent(datetime.fromisoformat(item["played_at"]))
                for item in connection.execute(
                    "SELECT played_at FROM play_events WHERE movie_uuid=? ORDER BY played_at, id",
                    (uuid,),
                )
            ]
        metadata = MovieMetadata(
            uuid=row["uuid"],
            cover_key=row["cover_key"],
            code=row["code"],
            title=row["title"],
            actors=actors,
            series=row["series"],
            studio=row["studio"],
            release_date=row["release_date"],
            tags=tags,
            rating=row["rating"],
            watched=bool(row["watched"]),
            play_count=row["play_count"],
            total_play_seconds=row["total_play_seconds"],
            favorite=bool(row["favorite"]),
            notes=row["notes"],
            folder_id=row["folder_id"],
            first_watched_at=_parse_dt(row["first_watched_at"]),
            last_watched_at=_parse_dt(row["last_watched_at"]),
            added_at=_parse_dt(row["added_at"]) or datetime.now(timezone.utc),
            play_history=events,
        )
        runtime = MovieRuntime(
            video_path=row["video_path"],
            library_id=row["library_id"],
            availability_status=row["availability_status"],
            subtitle_status=bool(row["subtitle_status"]),
            duration=row["duration"],
            width=row["width"],
            height=row["height"],
            video_codec=row["video_codec"],
            audio_codec=row["audio_codec"],
            file_size=row["file_size"],
            cover_path=row["cover_path"],
            last_scanned_at=_parse_dt(row["last_scanned_at"]),
        )
        return MovieRecord(metadata=metadata, runtime=runtime)




    def list_tags(self, limit: int = 30) -> list[str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT tag_name, COUNT(*) AS uses
                FROM movie_tags
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
        library_id: str | None = None,
        favorite: bool | None = None,
        watched: bool | None = None,
        subtitle_status: bool | None = None,
        availability_status: str | None = None,
        tag: str | None = None,
        folder_id: str | None = None,
        sort: str = "code",
        descending: bool = False,
    ) -> list[MovieRecord]:
        clauses: list[str] = []
        params: list[object] = []
        term = search.strip()
        if term:
            like = f"%{term}%"
            clauses.append(
                "("
                "m.code LIKE ? COLLATE NOCASE OR m.title LIKE ? COLLATE NOCASE OR "
                "m.series LIKE ? COLLATE NOCASE OR m.studio LIKE ? COLLATE NOCASE OR "
                "m.notes LIKE ? COLLATE NOCASE OR "
                "EXISTS (SELECT 1 FROM movie_actors ma WHERE ma.movie_uuid=m.uuid AND ma.actor_name LIKE ? COLLATE NOCASE) OR "
                "EXISTS (SELECT 1 FROM movie_tags mt WHERE mt.movie_uuid=m.uuid AND mt.tag_name LIKE ? COLLATE NOCASE)"
                ")"
            )
            params.extend([like] * 7)
        if library_id is not None:
            clauses.append("m.library_id = ?")
            params.append(library_id)
        if favorite is not None:
            clauses.append("m.favorite = ?")
            params.append(int(favorite))
        if watched is not None:
            clauses.append("m.watched = ?")
            params.append(int(watched))
        if subtitle_status is not None:
            clauses.append("m.subtitle_status = ?")
            params.append(int(subtitle_status))
        if availability_status is not None:
            clauses.append("m.availability_status = ?")
            params.append(availability_status)
        if tag is not None:
            clauses.append("EXISTS (SELECT 1 FROM movie_tags mt2 WHERE mt2.movie_uuid=m.uuid AND mt2.tag_name = ? COLLATE NOCASE)")
            params.append(tag)
        if folder_id is not None:
            clauses.append("m.folder_id = ?")
            params.append(folder_id)
        direction = "DESC" if descending else "ASC"
        secondary = "m.code COLLATE NOCASE ASC, m.title COLLATE NOCASE ASC"
        sort_sql = {
            "added_at": f"(m.added_at IS NULL) ASC, m.added_at {direction}, {secondary}",
            "code": f"m.code COLLATE NOCASE {direction}, m.title COLLATE NOCASE {direction}",
            "title": f"m.title COLLATE NOCASE {direction}, m.code COLLATE NOCASE {direction}",
            "release_date": f"(m.release_date = '') ASC, m.release_date {direction}, {secondary}",
            "rating": f"m.rating {direction}, {secondary}",
            "last_watched_at": f"(m.last_watched_at IS NULL) ASC, m.last_watched_at {direction}, {secondary}",
            "play_count": f"m.play_count {direction}, {secondary}",
        }.get(sort)
        if sort_sql is None:
            sort_sql = "m.code COLLATE NOCASE ASC, m.title COLLATE NOCASE ASC"
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.database.connect() as connection:
            rows = connection.execute(
                f"SELECT m.uuid FROM movies m{where} ORDER BY {sort_sql}",
                params,
            ).fetchall()
        return [record for row in rows if (record := self.get(row["uuid"])) is not None]


    def list_uuids_by_folder(self, folder_id: str) -> list[str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT uuid FROM movies WHERE folder_id=? ORDER BY uuid",
                (folder_id,),
            ).fetchall()
        return [str(row["uuid"]) for row in rows]

    def find_by_code(self, code: str) -> list[MovieRecord]:
        return self._find_by_column("code", code)

    def find_by_cover_key(self, cover_key: str) -> list[MovieRecord]:
        return self._find_by_column("cover_key", cover_key)

    def find_by_video_path(self, video_path: str) -> list[MovieRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT uuid FROM movies WHERE video_path = ?",
                (video_path,),
            ).fetchall()
        return [record for row in rows if (record := self.get(row["uuid"])) is not None]

    def list_by_library(self, library_id: str) -> list[MovieRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT uuid FROM movies WHERE library_id = ? ORDER BY code COLLATE NOCASE",
                (library_id,),
            ).fetchall()
        return [record for row in rows if (record := self.get(row["uuid"])) is not None]

    def list_all(self) -> list[MovieRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT uuid FROM movies ORDER BY code COLLATE NOCASE, title COLLATE NOCASE"
            ).fetchall()
        return [record for row in rows if (record := self.get(row["uuid"])) is not None]

    def _find_by_column(self, column: str, value: str) -> list[MovieRecord]:
        if column not in {"code", "cover_key"}:
            raise ValueError(column)
        with self.database.connect() as connection:
            rows = connection.execute(
                f"SELECT uuid FROM movies WHERE {column} = ? COLLATE NOCASE",
                (value,),
            ).fetchall()
        return [record for row in rows if (record := self.get(row["uuid"])) is not None]

    def delete_archive(self, uuid: str) -> None:
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM movies WHERE uuid=?", (uuid,))


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None
