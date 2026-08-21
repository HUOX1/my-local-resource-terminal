from __future__ import annotations

from app.db.database import Database


def test_initialize_migrates_database_to_schema_version_7(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()

    assert db.schema_version() == 7
    with db.connect() as connection:
        names = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert {"games", "game_sessions", "game_tags", "movie_episodes", "schema_meta"} <= names


def test_initialize_is_idempotent(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()
    db.initialize()
    assert db.schema_version() == 7


def test_initialize_migrates_v2_games_table_with_description_archive_media_and_folder_columns(tmp_path):
    import sqlite3

    path = tmp_path / "library.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO schema_meta(key, value) VALUES('schema_version', '2');
        CREATE TABLE games (
            uuid TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            series TEXT NOT NULL DEFAULT '',
            developer TEXT NOT NULL DEFAULT '',
            publisher TEXT NOT NULL DEFAULT '',
            release_date TEXT NOT NULL DEFAULT '',
            rating INTEGER NOT NULL DEFAULT 0,
            favorite INTEGER NOT NULL DEFAULT 0,
            notes TEXT NOT NULL DEFAULT '',
            added_at TEXT NOT NULL,
            launch_exe TEXT NOT NULL DEFAULT '',
            launch_args TEXT NOT NULL DEFAULT '',
            working_directory TEXT NOT NULL DEFAULT '',
            timing_exe TEXT NOT NULL DEFAULT '',
            cover_path TEXT,
            preview_gif_path TEXT,
            screenshot_directory TEXT,
            total_play_seconds INTEGER NOT NULL DEFAULT 0,
            play_count INTEGER NOT NULL DEFAULT 0,
            first_played_at TEXT,
            last_played_at TEXT
        );
        """
    )
    connection.commit()
    connection.close()

    db = Database(path)
    db.initialize()

    assert db.schema_version() == 7
    with db.connect() as migrated:
        columns = {row["name"] for row in migrated.execute("PRAGMA table_info(games)")}
    assert "description" in columns
    assert "archive_media_path" in columns


def test_database_connect_context_closes_connection_deterministically(tmp_path):
    import sqlite3

    db = Database(tmp_path / "library.db")
    db.initialize()

    with db.connect() as connection:
        connection.execute("SELECT 1").fetchone()

    try:
        connection.execute("SELECT 1").fetchone()
    except sqlite3.ProgrammingError as exc:
        assert "closed" in str(exc).lower()
    else:
        raise AssertionError("database connection remained open after leaving db.connect() context")


def test_initialize_migrates_v3_games_table_with_archive_media_and_folder_columns(tmp_path):
    import sqlite3

    path = tmp_path / "library.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO schema_meta(key, value) VALUES('schema_version', '3');
        CREATE TABLE games (
            uuid TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            series TEXT NOT NULL DEFAULT '',
            developer TEXT NOT NULL DEFAULT '',
            publisher TEXT NOT NULL DEFAULT '',
            release_date TEXT NOT NULL DEFAULT '',
            rating INTEGER NOT NULL DEFAULT 0,
            favorite INTEGER NOT NULL DEFAULT 0,
            description TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            added_at TEXT NOT NULL,
            launch_exe TEXT NOT NULL DEFAULT '',
            launch_args TEXT NOT NULL DEFAULT '',
            working_directory TEXT NOT NULL DEFAULT '',
            timing_exe TEXT NOT NULL DEFAULT '',
            cover_path TEXT,
            preview_gif_path TEXT,
            screenshot_directory TEXT,
            total_play_seconds INTEGER NOT NULL DEFAULT 0,
            play_count INTEGER NOT NULL DEFAULT 0,
            first_played_at TEXT,
            last_played_at TEXT
        );
        """
    )
    connection.commit()
    connection.close()

    db = Database(path)
    db.initialize()

    assert db.schema_version() == 7
    with db.connect() as migrated:
        columns = {row["name"] for row in migrated.execute("PRAGMA table_info(games)")}
    assert "archive_media_path" in columns


def test_initialize_adds_folder_id_columns_to_existing_movie_and_game_tables(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()
    with db.connect() as connection:
        movie_columns = {row["name"] for row in connection.execute("PRAGMA table_info(movies)")}
        game_columns = {row["name"] for row in connection.execute("PRAGMA table_info(games)")}
    assert "folder_id" in movie_columns
    assert "folder_id" in game_columns


def test_initialize_migrates_v6_movie_runtime_to_deterministic_episode(tmp_path):
    import sqlite3

    path = tmp_path / "library.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO schema_meta(key, value) VALUES('schema_version', '6');
        CREATE TABLE movies (
            uuid TEXT PRIMARY KEY,
            cover_key TEXT NOT NULL,
            code TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            series TEXT NOT NULL DEFAULT '',
            studio TEXT NOT NULL DEFAULT '',
            release_date TEXT NOT NULL DEFAULT '',
            rating INTEGER NOT NULL DEFAULT 0,
            watched INTEGER NOT NULL DEFAULT 0,
            play_count INTEGER NOT NULL DEFAULT 0,
            total_play_seconds INTEGER NOT NULL DEFAULT 0,
            favorite INTEGER NOT NULL DEFAULT 0,
            description TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            folder_id TEXT,
            first_watched_at TEXT,
            last_watched_at TEXT,
            added_at TEXT,
            video_path TEXT,
            library_id TEXT,
            availability_status TEXT NOT NULL DEFAULT 'offline',
            subtitle_status INTEGER NOT NULL DEFAULT 0,
            duration REAL,
            width INTEGER,
            height INTEGER,
            video_codec TEXT,
            audio_codec TEXT,
            file_size INTEGER,
            cover_path TEXT,
            last_scanned_at TEXT
        );
        INSERT INTO movies (
            uuid, cover_key, code, video_path, library_id, availability_status,
            subtitle_status, duration, width, height, video_codec, audio_codec,
            file_size, cover_path, last_scanned_at
        ) VALUES (
            'movie-1', 'SHOW', 'SHOW', 'D:\\Media\\SHOW\\SHOW.mkv', 'main',
            'available', 1, 120.5, 1920, 1080, 'h264', 'aac', 987654,
            'D:\\Covers\\SHOW.jpg', '2026-08-21T10:00:00+00:00'
        );
        """
    )
    connection.commit()
    connection.close()

    db = Database(path)
    db.initialize()
    db.initialize()

    assert db.schema_version() == 7
    with db.connect() as migrated:
        episodes = migrated.execute(
            "SELECT * FROM movie_episodes WHERE movie_uuid='movie-1'"
        ).fetchall()
        parent = migrated.execute(
            "SELECT cover_path FROM movies WHERE uuid='movie-1'"
        ).fetchone()
        indexes = {
            row["name"] for row in migrated.execute("PRAGMA index_list(movie_episodes)")
        }

    assert len(episodes) == 1
    episode = episodes[0]
    assert episode["uuid"] == "23403593-f39c-5c12-9468-89aff196324c"
    assert episode["source_name"] == "SHOW.mkv"
    assert episode["video_path"] == r"D:\Media\SHOW\SHOW.mkv"
    assert episode["library_id"] == "main"
    assert episode["availability_status"] == "available"
    assert episode["subtitle_status"] == 1
    assert episode["duration"] == 120.5
    assert episode["width"] == 1920
    assert episode["height"] == 1080
    assert episode["video_codec"] == "h264"
    assert episode["audio_codec"] == "aac"
    assert episode["file_size"] == 987654
    assert parent["cover_path"] == r"D:\Covers\SHOW.jpg"
    assert {
        "idx_movie_episodes_movie",
        "idx_movie_episodes_video_path",
        "idx_movie_episodes_library_status",
        "idx_movie_episodes_order",
    } <= indexes
