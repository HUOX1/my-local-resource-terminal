from __future__ import annotations

from app.db.database import Database


def test_initialize_migrates_database_to_schema_version_5(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()

    assert db.schema_version() == 6
    with db.connect() as connection:
        names = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert {"games", "game_sessions", "game_tags", "schema_meta"} <= names


def test_initialize_is_idempotent(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()
    db.initialize()
    assert db.schema_version() == 6


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

    assert db.schema_version() == 6
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

    assert db.schema_version() == 6
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
