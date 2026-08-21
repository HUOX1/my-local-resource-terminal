from datetime import datetime, timezone
from pathlib import Path

from app.db.database import Database
from app.models.movie import (
    MovieEpisodeMetadata,
    MovieEpisodeRuntime,
    MovieMetadata,
    PlayEvent,
)
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


def test_multi_episode_round_trip_aggregates_work_without_implicit_video(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    movie = MovieMetadata(
        uuid="work-1",
        cover_key="SHOW",
        code="SHOW",
        episodes=[
            MovieEpisodeMetadata("episode-2", 2, episode_number=2, source_name="SHOW_02.mkv"),
            MovieEpisodeMetadata("episode-1", 1, episode_number=1, source_name="SHOW_01.mkv"),
        ],
    )
    repo.replace_work(
        movie,
        {
            "episode-1": MovieEpisodeRuntime(
                video_path="D:/Media/SHOW/SHOW_01.mkv",
                library_id="main",
                availability_status="available",
                subtitle_status=False,
                duration=60.0,
                file_size=100,
            ),
            "episode-2": MovieEpisodeRuntime(
                video_path="D:/Media/SHOW/SHOW_02.mkv",
                library_id="main",
                availability_status="offline",
                subtitle_status=True,
                duration=70.0,
                file_size=200,
            ),
        },
        cover_path="D:/Covers/SHOW.jpg",
    )

    record = repo.get(movie.uuid)

    assert record is not None
    assert [episode.metadata.uuid for episode in record.episodes] == ["episode-1", "episode-2"]
    assert record.episodes[0].runtime.video_path == "D:/Media/SHOW/SHOW_01.mkv"
    assert record.episodes[1].runtime.availability_status == "offline"
    assert record.runtime.video_path is None
    assert record.runtime.availability_status == "available"
    assert record.runtime.subtitle_status is True
    assert record.runtime.duration == 130.0
    assert record.runtime.file_size == 300
    assert record.runtime.cover_path == "D:/Covers/SHOW.jpg"


def test_repository_path_lookup_and_library_offline_operate_on_episodes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    movie = MovieMetadata(
        uuid="work-lookup",
        cover_key="LOOKUP",
        episodes=[
            MovieEpisodeMetadata("lookup-1", 1),
            MovieEpisodeMetadata("lookup-2", 2),
        ],
    )
    repo.replace_work(
        movie,
        {
            "lookup-1": MovieEpisodeRuntime(
                video_path="D:/Media/LOOKUP/01.mkv",
                library_id="main",
                availability_status="available",
            ),
            "lookup-2": MovieEpisodeRuntime(
                video_path="D:/Media/LOOKUP/02.mkv",
                library_id="main",
                availability_status="available",
            ),
        },
        cover_path=None,
    )

    found = repo.find_by_episode_video_path("D:/Media/LOOKUP/02.mkv")
    changed = repo.mark_library_episodes_offline("main", ["lookup-2"])
    record = repo.get(movie.uuid)

    assert [item.metadata.uuid for item in found] == [movie.uuid]
    assert changed == 1
    assert record is not None
    assert [episode.runtime.availability_status for episode in record.episodes] == [
        "offline",
        "available",
    ]
    assert record.runtime.availability_status == "available"


def test_repository_filters_use_episode_aggregate_semantics(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    partial = MovieMetadata(
        uuid="partial",
        cover_key="PARTIAL",
        episodes=[MovieEpisodeMetadata("partial-1", 1), MovieEpisodeMetadata("partial-2", 2)],
    )
    offline = MovieMetadata(
        uuid="offline",
        cover_key="OFFLINE",
        episodes=[MovieEpisodeMetadata("offline-1", 1)],
    )
    repo.replace_work(
        partial,
        {
            "partial-1": MovieEpisodeRuntime(
                library_id="main", availability_status="available", subtitle_status=True
            ),
            "partial-2": MovieEpisodeRuntime(
                library_id="main", availability_status="offline", subtitle_status=False
            ),
        },
        cover_path=None,
    )
    repo.replace_work(
        offline,
        {
            "offline-1": MovieEpisodeRuntime(
                library_id="archive", availability_status="offline", subtitle_status=False
            )
        },
        cover_path=None,
    )

    assert [item.metadata.uuid for item in repo.search(library_id="main")] == ["partial"]
    assert [item.metadata.uuid for item in repo.search(subtitle_status=True)] == ["partial"]
    assert [item.metadata.uuid for item in repo.search(subtitle_status=False)] == ["offline"]
    assert [item.metadata.uuid for item in repo.search(availability_status="available")] == ["partial"]
    assert [item.metadata.uuid for item in repo.search(availability_status="offline")] == ["offline"]


def test_rebuild_restores_episode_metadata_as_offline_children(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    movie = MovieMetadata(
        uuid="archive-work",
        cover_key="ARCHIVE",
        episodes=[
            MovieEpisodeMetadata("archive-1", 1, episode_number=1, source_name="01.mkv"),
            MovieEpisodeMetadata("archive-2", 2, episode_number=2, source_name="02.mkv"),
        ],
    )

    repo.rebuild_from_archives([movie])
    record = repo.get(movie.uuid)

    assert record is not None
    assert [episode.metadata.source_name for episode in record.episodes] == ["01.mkv", "02.mkv"]
    assert [episode.runtime.availability_status for episode in record.episodes] == [
        "offline",
        "offline",
    ]


def test_replace_work_deletes_only_declared_duplicate_parents(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    parent = MovieMetadata(
        uuid="parent",
        cover_key="SHOW",
        episodes=[MovieEpisodeMetadata("parent-1", 1)],
    )
    duplicate = MovieMetadata.new("SHOW_01", "SHOW_01")
    untouched = MovieMetadata.new("OTHER", "OTHER")
    repo.upsert_metadata(duplicate)
    repo.upsert_metadata(untouched)

    repo.replace_work(
        parent,
        {"parent-1": MovieEpisodeRuntime(availability_status="offline")},
        cover_path=None,
        duplicate_movie_uuids=[duplicate.uuid],
    )

    assert repo.get(parent.uuid) is not None
    assert repo.get(duplicate.uuid) is None
    assert repo.get(untouched.uuid) is not None


def test_delete_archive_cascades_episode_rows(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    movie = MovieMetadata(
        uuid="delete-work",
        cover_key="DELETE",
        episodes=[MovieEpisodeMetadata("delete-episode", 1)],
    )
    repo.upsert_metadata(movie)

    repo.delete_archive(movie.uuid)

    with repo.database.connect() as connection:
        count = connection.execute(
            "SELECT COUNT(*) AS count FROM movie_episodes WHERE movie_uuid=?",
            (movie.uuid,),
        ).fetchone()["count"]
    assert count == 0
