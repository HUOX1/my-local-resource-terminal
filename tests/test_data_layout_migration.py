from __future__ import annotations

import json

from app.config.data_dirs import MovieMetadataMigrator, ensure_data_layout


def test_layout_separates_movie_and_game_archives(tmp_path):
    layout = ensure_data_layout(tmp_path / "data")

    assert layout.movie_metadata_dir == layout.root / "metadata" / "movies"
    assert layout.game_metadata_dir == layout.root / "metadata" / "games"
    assert layout.game_cover_dir == layout.root / "game_assets" / "covers"
    assert layout.game_preview_dir == layout.root / "game_assets" / "previews"
    assert layout.game_archive_media_dir == layout.root / "game_assets" / "archive"
    assert layout.active_game_session_path == layout.root / "state" / "active_game_session.json"
    assert layout.game_screenshot_cache_dir == layout.root / "cache" / "games" / "screenshots"


def test_movie_metadata_migration_is_idempotent(tmp_path):
    layout = ensure_data_layout(tmp_path / "data")
    legacy = layout.metadata_dir / "movie-1.json"
    legacy.write_text(
        json.dumps({"schema_version": 1, "uuid": "movie-1", "cover_key": "ABC"}),
        encoding="utf-8",
    )

    first = MovieMetadataMigrator().migrate(layout)

    assert first.migrated == 1
    assert not legacy.exists()
    assert (layout.movie_metadata_dir / legacy.name).exists()

    second = MovieMetadataMigrator().migrate(layout)
    assert second.migrated == 0
    assert second.errors == ()


def test_movie_metadata_migration_accepts_schema_v2(tmp_path):
    layout = ensure_data_layout(tmp_path / "data")
    source = layout.metadata_dir / "movie-v2.json"
    source.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "uuid": "movie-v2",
                "cover_key": "SERIES",
                "episodes": [],
            }
        ),
        encoding="utf-8",
    )

    summary = MovieMetadataMigrator().migrate(layout)

    assert summary.migrated == 1
    assert summary.errors == ()
    assert (layout.movie_metadata_dir / source.name).is_file()


def test_movie_metadata_migration_leaves_invalid_legacy_file_in_place(tmp_path):
    layout = ensure_data_layout(tmp_path / "data")
    legacy = layout.metadata_dir / "broken.json"
    legacy.write_text("{", encoding="utf-8")

    summary = MovieMetadataMigrator().migrate(layout)

    assert summary.migrated == 0
    assert len(summary.errors) == 1
    assert legacy.exists()
    assert not (layout.movie_metadata_dir / legacy.name).exists()
