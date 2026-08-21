from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone

from app.db.database import Database
from app.models.movie import (
    MovieEpisodeMetadata,
    MovieEpisodeRecord,
    MovieEpisodeRuntime,
    MovieMetadata,
    MovieRecord,
    MovieRuntime,
    PlayEvent,
    legacy_episode_uuid,
)


class MovieRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def upsert_metadata(self, movie: MovieMetadata) -> None:
        with self.database.transaction() as connection:
            self._upsert_metadata(connection, movie)
            self._sync_parent_runtime(connection, movie.uuid)

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
        for episode in movie.episodes:
            self._upsert_episode_metadata(connection, movie.uuid, episode)

    @staticmethod
    def _upsert_episode_metadata(connection, movie_uuid: str, episode: MovieEpisodeMetadata) -> None:
        connection.execute(
            """
            INSERT INTO movie_episodes (
                uuid, movie_uuid, display_order, episode_number, season_number, source_name
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(uuid) DO UPDATE SET
                movie_uuid=excluded.movie_uuid,
                display_order=excluded.display_order,
                episode_number=excluded.episode_number,
                season_number=excluded.season_number,
                source_name=excluded.source_name
            """,
            (
                episode.uuid,
                movie_uuid,
                episode.display_order,
                episode.episode_number,
                episode.season_number,
                episode.source_name,
            ),
        )

    @staticmethod
    def _upsert_episode_runtime_row(
        connection,
        movie_uuid: str,
        episode: MovieEpisodeMetadata,
        runtime: MovieEpisodeRuntime,
    ) -> None:
        MovieRepository._upsert_episode_metadata(connection, movie_uuid, episode)
        connection.execute(
            """
            UPDATE movie_episodes SET
                video_path=?, library_id=?, availability_status=?, subtitle_status=?,
                duration=?, width=?, height=?, video_codec=?, audio_codec=?,
                file_size=?, last_scanned_at=?
            WHERE uuid=? AND movie_uuid=?
            """,
            (
                runtime.video_path,
                runtime.library_id,
                runtime.availability_status,
                int(runtime.subtitle_status),
                runtime.duration,
                runtime.width,
                runtime.height,
                runtime.video_codec,
                runtime.audio_codec,
                runtime.file_size,
                _dt(runtime.last_scanned_at),
                episode.uuid,
                movie_uuid,
            ),
        )

    def upsert_episode_runtime(
        self,
        movie_uuid: str,
        episode: MovieEpisodeMetadata,
        runtime: MovieEpisodeRuntime,
    ) -> None:
        with self.database.transaction() as connection:
            exists = connection.execute(
                "SELECT 1 FROM movies WHERE uuid=?", (movie_uuid,)
            ).fetchone()
            if exists is None:
                raise KeyError(movie_uuid)
            self._upsert_episode_runtime_row(connection, movie_uuid, episode, runtime)
            self._sync_parent_runtime(connection, movie_uuid)

    def replace_work(
        self,
        movie: MovieMetadata,
        episode_runtimes: Mapping[str, MovieEpisodeRuntime],
        *,
        cover_path: str | None,
        duplicate_movie_uuids: Sequence[str] = (),
    ) -> None:
        episode_ids = {episode.uuid for episode in movie.episodes}
        unknown_runtime_ids = set(episode_runtimes) - episode_ids
        if unknown_runtime_ids:
            raise ValueError(
                f"runtime supplied for unknown episode: {sorted(unknown_runtime_ids)[0]}"
            )
        duplicate_ids = list(dict.fromkeys(duplicate_movie_uuids))
        if movie.uuid in duplicate_ids:
            raise ValueError("parent movie cannot be deleted as a duplicate")

        with self.database.transaction() as connection:
            self._upsert_metadata(connection, movie)
            if episode_ids:
                placeholders = ",".join("?" for _ in episode_ids)
                connection.execute(
                    f"DELETE FROM movie_episodes WHERE movie_uuid=? AND uuid NOT IN ({placeholders})",
                    (movie.uuid, *sorted(episode_ids)),
                )
            else:
                connection.execute(
                    "DELETE FROM movie_episodes WHERE movie_uuid=?", (movie.uuid,)
                )
            for episode in movie.episodes:
                runtime = episode_runtimes.get(episode.uuid)
                if runtime is not None:
                    self._upsert_episode_runtime_row(
                        connection, movie.uuid, episode, runtime
                    )
            connection.execute(
                "UPDATE movies SET cover_path=? WHERE uuid=?",
                (cover_path, movie.uuid),
            )
            for duplicate_uuid in duplicate_ids:
                connection.execute(
                    "DELETE FROM movies WHERE uuid=?", (duplicate_uuid,)
                )
            self._sync_parent_runtime(connection, movie.uuid)

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
            rows = connection.execute(
                """
                SELECT uuid, display_order, episode_number, season_number, source_name
                FROM movie_episodes WHERE movie_uuid=? ORDER BY display_order, uuid
                """,
                (uuid,),
            ).fetchall()
            if len(rows) > 1:
                raise ValueError("multi-episode work requires an explicit episode uuid")
            if rows:
                row = rows[0]
                episode = MovieEpisodeMetadata(
                    uuid=row["uuid"],
                    display_order=row["display_order"],
                    episode_number=row["episode_number"],
                    season_number=row["season_number"],
                    source_name=row["source_name"] or _source_name(video_path),
                )
            else:
                exists = connection.execute(
                    "SELECT 1 FROM movies WHERE uuid=?", (uuid,)
                ).fetchone()
                if exists is None:
                    raise KeyError(uuid)
                episode = MovieEpisodeMetadata(
                    uuid=legacy_episode_uuid(uuid),
                    display_order=1,
                    source_name=_source_name(video_path),
                )
            runtime = MovieEpisodeRuntime(
                video_path=video_path,
                library_id=library_id,
                availability_status=availability_status,
                subtitle_status=subtitle_status,
                duration=duration,
                width=width,
                height=height,
                video_codec=video_codec,
                audio_codec=audio_codec,
                file_size=file_size,
                last_scanned_at=last_scanned_at,
            )
            self._upsert_episode_runtime_row(connection, uuid, episode, runtime)
            connection.execute(
                "UPDATE movies SET cover_path=? WHERE uuid=?",
                (cover_path, uuid),
            )
            self._sync_parent_runtime(connection, uuid)

    def update_cover_path(self, uuid: str, cover_path: str | None) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "UPDATE movies SET cover_path=? WHERE uuid=?", (cover_path, uuid)
            )
            if cursor.rowcount == 0:
                raise KeyError(uuid)

    def mark_offline(self, uuid: str) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE movie_episodes SET availability_status='offline' WHERE movie_uuid=?",
                (uuid,),
            )
            self._sync_parent_runtime(connection, uuid)

    def mark_library_offline(
        self, library_id: str, except_uuids: Sequence[str] = ()
    ) -> int:
        with self.database.transaction() as connection:
            movie_ids = self._movie_ids_for_library_update(
                connection, library_id, except_movie_uuids=except_uuids
            )
            if except_uuids:
                placeholders = ",".join("?" for _ in except_uuids)
                cursor = connection.execute(
                    f"""
                    UPDATE movie_episodes SET availability_status='offline'
                    WHERE library_id=? AND availability_status='available'
                    AND movie_uuid NOT IN ({placeholders})
                    """,
                    (library_id, *except_uuids),
                )
            else:
                cursor = connection.execute(
                    """
                    UPDATE movie_episodes SET availability_status='offline'
                    WHERE library_id=? AND availability_status='available'
                    """,
                    (library_id,),
                )
            for movie_uuid in movie_ids:
                self._sync_parent_runtime(connection, movie_uuid)
            return cursor.rowcount

    def mark_library_episodes_offline(
        self, library_id: str, except_episode_uuids: Sequence[str] = ()
    ) -> int:
        with self.database.transaction() as connection:
            movie_ids = self._movie_ids_for_library_update(
                connection,
                library_id,
                except_episode_uuids=except_episode_uuids,
            )
            if except_episode_uuids:
                placeholders = ",".join("?" for _ in except_episode_uuids)
                cursor = connection.execute(
                    f"""
                    UPDATE movie_episodes SET availability_status='offline'
                    WHERE library_id=? AND availability_status='available'
                    AND uuid NOT IN ({placeholders})
                    """,
                    (library_id, *except_episode_uuids),
                )
            else:
                cursor = connection.execute(
                    """
                    UPDATE movie_episodes SET availability_status='offline'
                    WHERE library_id=? AND availability_status='available'
                    """,
                    (library_id,),
                )
            for movie_uuid in movie_ids:
                self._sync_parent_runtime(connection, movie_uuid)
            return cursor.rowcount

    @staticmethod
    def _movie_ids_for_library_update(
        connection,
        library_id: str,
        *,
        except_movie_uuids: Sequence[str] = (),
        except_episode_uuids: Sequence[str] = (),
    ) -> list[str]:
        clauses = ["library_id=?", "availability_status='available'"]
        params: list[object] = [library_id]
        if except_movie_uuids:
            placeholders = ",".join("?" for _ in except_movie_uuids)
            clauses.append(f"movie_uuid NOT IN ({placeholders})")
            params.extend(except_movie_uuids)
        if except_episode_uuids:
            placeholders = ",".join("?" for _ in except_episode_uuids)
            clauses.append(f"uuid NOT IN ({placeholders})")
            params.extend(except_episode_uuids)
        rows = connection.execute(
            "SELECT DISTINCT movie_uuid FROM movie_episodes WHERE " + " AND ".join(clauses),
            params,
        ).fetchall()
        return [row["movie_uuid"] for row in rows]

    @staticmethod
    def _sync_parent_runtime(connection, movie_uuid: str) -> None:
        rows = connection.execute(
            """
            SELECT * FROM movie_episodes
            WHERE movie_uuid=? ORDER BY display_order, source_name COLLATE NOCASE, uuid
            """,
            (movie_uuid,),
        ).fetchall()
        values = _aggregate_runtime_values(rows)
        connection.execute(
            """
            UPDATE movies SET
                video_path=?, library_id=?, availability_status=?, subtitle_status=?,
                duration=?, width=?, height=?, video_codec=?, audio_codec=?,
                file_size=?, last_scanned_at=?
            WHERE uuid=?
            """,
            (*values, movie_uuid),
        )

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
        archived = list(movies)
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM movies")
            for movie in archived:
                self._upsert_metadata(connection, movie)
                connection.executemany(
                    "INSERT INTO play_events(movie_uuid, played_at) VALUES (?, ?)",
                    [(movie.uuid, event.played_at.isoformat()) for event in movie.play_history],
                )
                self._sync_parent_runtime(connection, movie.uuid)

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
            episode_rows = connection.execute(
                """
                SELECT * FROM movie_episodes
                WHERE movie_uuid=? ORDER BY display_order, source_name COLLATE NOCASE, uuid
                """,
                (uuid,),
            ).fetchall()

        episode_records = [_episode_record(item) for item in episode_rows]
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
            episodes=[episode.metadata for episode in episode_records],
        )
        runtime = _aggregate_movie_runtime(row, episode_records)
        return MovieRecord(metadata=metadata, runtime=runtime, episodes=episode_records)

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
                "EXISTS (SELECT 1 FROM movie_tags mt WHERE mt.movie_uuid=m.uuid AND mt.tag_name LIKE ? COLLATE NOCASE) OR "
                "EXISTS (SELECT 1 FROM movie_episodes me WHERE me.movie_uuid=m.uuid AND me.source_name LIKE ? COLLATE NOCASE)"
                ")"
            )
            params.extend([like] * 8)
        if library_id is not None:
            clauses.append(
                "EXISTS (SELECT 1 FROM movie_episodes me WHERE me.movie_uuid=m.uuid AND me.library_id=?)"
            )
            params.append(library_id)
        if favorite is not None:
            clauses.append("m.favorite = ?")
            params.append(int(favorite))
        if watched is not None:
            clauses.append("m.watched = ?")
            params.append(int(watched))
        if subtitle_status is True:
            clauses.append(
                "EXISTS (SELECT 1 FROM movie_episodes me WHERE me.movie_uuid=m.uuid AND me.subtitle_status=1)"
            )
        elif subtitle_status is False:
            clauses.append(
                "NOT EXISTS (SELECT 1 FROM movie_episodes me WHERE me.movie_uuid=m.uuid AND me.subtitle_status=1)"
            )
        if availability_status == "available":
            clauses.append(
                "EXISTS (SELECT 1 FROM movie_episodes me WHERE me.movie_uuid=m.uuid AND me.availability_status='available')"
            )
        elif availability_status == "offline":
            clauses.append(
                "NOT EXISTS (SELECT 1 FROM movie_episodes me WHERE me.movie_uuid=m.uuid AND me.availability_status='available')"
            )
        elif availability_status is not None:
            raise ValueError(f"unsupported availability status: {availability_status}")
        if tag is not None:
            clauses.append(
                "EXISTS (SELECT 1 FROM movie_tags mt2 WHERE mt2.movie_uuid=m.uuid AND mt2.tag_name = ? COLLATE NOCASE)"
            )
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

    def find_by_episode_video_path(self, video_path: str) -> list[MovieRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT movie_uuid FROM movie_episodes
                WHERE video_path=? ORDER BY movie_uuid
                """,
                (video_path,),
            ).fetchall()
        return [
            record
            for row in rows
            if (record := self.get(row["movie_uuid"])) is not None
        ]

    def find_by_episode_source_name(self, source_name: str) -> list[MovieRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT movie_uuid FROM movie_episodes
                WHERE source_name=? COLLATE NOCASE ORDER BY movie_uuid
                """,
                (source_name,),
            ).fetchall()
        return [
            record
            for row in rows
            if (record := self.get(row["movie_uuid"])) is not None
        ]

    def find_by_episode_identity(
        self,
        season_number: int | None,
        episode_number: int | None,
    ) -> list[MovieRecord]:
        if episode_number is None:
            return []
        with self.database.connect() as connection:
            if season_number is None:
                rows = connection.execute(
                    """
                    SELECT DISTINCT movie_uuid FROM movie_episodes
                    WHERE season_number IS NULL AND episode_number=? ORDER BY movie_uuid
                    """,
                    (episode_number,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT DISTINCT movie_uuid FROM movie_episodes
                    WHERE season_number=? AND episode_number=? ORDER BY movie_uuid
                    """,
                    (season_number, episode_number),
                ).fetchall()
        return [
            record
            for row in rows
            if (record := self.get(row["movie_uuid"])) is not None
        ]

    def find_by_video_path(self, video_path: str) -> list[MovieRecord]:
        return self.find_by_episode_video_path(video_path)

    def list_by_library(self, library_id: str) -> list[MovieRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT m.uuid FROM movies m
                WHERE EXISTS (
                    SELECT 1 FROM movie_episodes me
                    WHERE me.movie_uuid=m.uuid AND me.library_id=?
                )
                ORDER BY m.code COLLATE NOCASE
                """,
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


def _episode_record(row) -> MovieEpisodeRecord:
    return MovieEpisodeRecord(
        metadata=MovieEpisodeMetadata(
            uuid=row["uuid"],
            display_order=row["display_order"],
            episode_number=row["episode_number"],
            season_number=row["season_number"],
            source_name=row["source_name"],
        ),
        runtime=MovieEpisodeRuntime(
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
            last_scanned_at=_parse_dt(row["last_scanned_at"]),
        ),
    )


def _aggregate_movie_runtime(parent_row, episodes: Sequence[MovieEpisodeRecord]) -> MovieRuntime:
    if len(episodes) == 1:
        runtime = episodes[0].runtime
        return MovieRuntime(
            video_path=runtime.video_path,
            library_id=runtime.library_id,
            availability_status=runtime.availability_status,
            subtitle_status=runtime.subtitle_status,
            duration=runtime.duration,
            width=runtime.width,
            height=runtime.height,
            video_codec=runtime.video_codec,
            audio_codec=runtime.audio_codec,
            file_size=runtime.file_size,
            cover_path=parent_row["cover_path"],
            last_scanned_at=runtime.last_scanned_at,
        )
    if episodes:
        libraries = {
            episode.runtime.library_id
            for episode in episodes
            if episode.runtime.library_id is not None
        }
        durations = [
            episode.runtime.duration
            for episode in episodes
            if episode.runtime.duration is not None
        ]
        sizes = [
            episode.runtime.file_size
            for episode in episodes
            if episode.runtime.file_size is not None
        ]
        scanned = [
            episode.runtime.last_scanned_at
            for episode in episodes
            if episode.runtime.last_scanned_at is not None
        ]
        return MovieRuntime(
            video_path=None,
            library_id=next(iter(libraries)) if len(libraries) == 1 else None,
            availability_status=(
                "available"
                if any(
                    episode.runtime.availability_status == "available"
                    for episode in episodes
                )
                else "offline"
            ),
            subtitle_status=any(
                episode.runtime.subtitle_status for episode in episodes
            ),
            duration=sum(durations) if durations else None,
            file_size=sum(sizes) if sizes else None,
            cover_path=parent_row["cover_path"],
            last_scanned_at=max(scanned) if scanned else None,
        )
    return MovieRuntime(
        video_path=parent_row["video_path"],
        library_id=parent_row["library_id"],
        availability_status=parent_row["availability_status"],
        subtitle_status=bool(parent_row["subtitle_status"]),
        duration=parent_row["duration"],
        width=parent_row["width"],
        height=parent_row["height"],
        video_codec=parent_row["video_codec"],
        audio_codec=parent_row["audio_codec"],
        file_size=parent_row["file_size"],
        cover_path=parent_row["cover_path"],
        last_scanned_at=_parse_dt(parent_row["last_scanned_at"]),
    )


def _aggregate_runtime_values(rows) -> tuple[object, ...]:
    if len(rows) == 1:
        row = rows[0]
        return (
            row["video_path"], row["library_id"], row["availability_status"],
            row["subtitle_status"], row["duration"], row["width"], row["height"],
            row["video_codec"], row["audio_codec"], row["file_size"],
            row["last_scanned_at"],
        )
    if rows:
        libraries = {row["library_id"] for row in rows if row["library_id"] is not None}
        durations = [row["duration"] for row in rows if row["duration"] is not None]
        sizes = [row["file_size"] for row in rows if row["file_size"] is not None]
        scanned = [row["last_scanned_at"] for row in rows if row["last_scanned_at"] is not None]
        return (
            None,
            next(iter(libraries)) if len(libraries) == 1 else None,
            "available" if any(row["availability_status"] == "available" for row in rows) else "offline",
            int(any(bool(row["subtitle_status"]) for row in rows)),
            sum(durations) if durations else None,
            None, None, None, None,
            sum(sizes) if sizes else None,
            max(scanned) if scanned else None,
        )
    return (None, None, "offline", 0, None, None, None, None, None, None, None)


def _source_name(video_path: str | None) -> str:
    if not video_path:
        return ""
    return str(video_path).replace("\\", "/").rsplit("/", 1)[-1]


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None
