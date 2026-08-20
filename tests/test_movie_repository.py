from datetime import datetime, timezone
from pathlib import Path

from app.db.database import Database
from app.models.movie import MovieMetadata, PlayEvent
from app.repositories.movie_repository import MovieRepository


def make_repo(tmp_path: Path) -> MovieRepository:
    db = Database(tmp_path / "library.db")
    db.initialize()
    return MovieRepository(db)


def test_rebuild_from_archives_restores_permanent_fields(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    when = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    movie = MovieMetadata.new("SPSD-62", "SPSD-62")
    movie.favorite = True
    movie.play_count = 3
    movie.play_history = [PlayEvent(when)]

    repo.rebuild_from_archives([movie])

    record = repo.get(movie.uuid)
    assert record is not None
    assert record.metadata.favorite is True
    assert record.metadata.play_count == 3
    assert record.runtime.availability_status == "offline"
    assert repo.list_play_events(movie.uuid) == [when]


def test_mark_offline_keeps_last_known_path(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    movie = MovieMetadata.new("X", "X")
    repo.upsert_metadata(movie)
    repo.update_runtime(
        movie.uuid,
        video_path="D:/Movies/X/X.mp4",
        library_id="main",
        availability_status="available",
        subtitle_status=True,
    )

    repo.mark_offline(movie.uuid)

    record = repo.get(movie.uuid)
    assert record is not None
    assert record.runtime.video_path == "D:/Movies/X/X.mp4"
    assert record.runtime.availability_status == "offline"
    assert record.runtime.subtitle_status is True


def test_database_migrates_added_at_column_and_repository_restores_it(tmp_path: Path) -> None:
    import sqlite3

    db_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE movies (uuid TEXT PRIMARY KEY, cover_key TEXT NOT NULL, code TEXT NOT NULL DEFAULT '', title TEXT NOT NULL DEFAULT '', series TEXT NOT NULL DEFAULT '', studio TEXT NOT NULL DEFAULT '', release_date TEXT NOT NULL DEFAULT '', rating INTEGER NOT NULL DEFAULT 0, watched INTEGER NOT NULL DEFAULT 0, play_count INTEGER NOT NULL DEFAULT 0, favorite INTEGER NOT NULL DEFAULT 0, notes TEXT NOT NULL DEFAULT '', first_watched_at TEXT, last_watched_at TEXT, video_path TEXT, library_id TEXT, availability_status TEXT NOT NULL DEFAULT 'offline', subtitle_status INTEGER NOT NULL DEFAULT 0, duration REAL, width INTEGER, height INTEGER, video_codec TEXT, audio_codec TEXT, file_size INTEGER, cover_path TEXT, last_scanned_at TEXT)")
    connection.commit()
    connection.close()

    db = Database(db_path)
    db.initialize()
    with db.connect() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(movies)")}
    assert "added_at" in columns


def test_repository_sorts_all_supported_fields_and_direction(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 2, 1, tzinfo=timezone.utc)
    a = MovieMetadata.new("A", "B-002", added_at=t1)
    a.title = "Zulu"
    a.release_date = "2024-01-01"
    a.rating = 2
    a.play_count = 8
    a.last_watched_at = t2
    b = MovieMetadata.new("B", "A-001", added_at=t2)
    b.title = "Alpha"
    b.release_date = "2025-01-01"
    b.rating = 5
    b.play_count = 1
    b.last_watched_at = t1
    repo.upsert_metadata(a)
    repo.upsert_metadata(b)

    assert [r.metadata.uuid for r in repo.search(sort="added_at", descending=True)] == [b.uuid, a.uuid]
    assert [r.metadata.uuid for r in repo.search(sort="code", descending=False)] == [b.uuid, a.uuid]
    assert [r.metadata.uuid for r in repo.search(sort="title", descending=False)] == [b.uuid, a.uuid]
    assert [r.metadata.uuid for r in repo.search(sort="release_date", descending=True)] == [b.uuid, a.uuid]
    assert [r.metadata.uuid for r in repo.search(sort="rating", descending=True)] == [b.uuid, a.uuid]
    assert [r.metadata.uuid for r in repo.search(sort="last_watched_at", descending=True)] == [a.uuid, b.uuid]
    assert [r.metadata.uuid for r in repo.search(sort="play_count", descending=True)] == [a.uuid, b.uuid]
