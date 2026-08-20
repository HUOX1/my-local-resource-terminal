from __future__ import annotations

import json
import sqlite3
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from app.config.data_dirs import ensure_data_layout
from app.config.settings import AppSettings, LibraryConfig, SettingsStore


def _settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        data_dir=tmp_path / "data",
        cover_dir=tmp_path / "covers",
        libraries=[LibraryConfig("main", "主收藏", tmp_path / "movies", True)],
        player_mode="custom",
        player_path=tmp_path / "Player.exe",
        ffprobe_path=str(tmp_path / "ffprobe.exe"),
        ffmpeg_path=str(tmp_path / "ffmpeg.exe"),
        auto_scan=True,
        sidebar_visible=False,
        sidebar_width=201,
        cover_tool_source_dir=tmp_path / "raw-covers",
        cover_tool_margin_px=3,
        sort_key="rating",
        sort_desc=True,
        startup_library="games",
        game_sort_key="total_play_seconds",
        game_sort_desc=False,
        movie_filter="favorite",
        game_filter="installed",
    )


def _create_db(path: Path, marker: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE marker (value TEXT NOT NULL)")
        connection.execute("INSERT INTO marker(value) VALUES (?)", (marker,))


def _read_db_marker(path: Path) -> str:
    with sqlite3.connect(path) as connection:
        row = connection.execute("SELECT value FROM marker").fetchone()
    assert row
    return str(row[0])


def test_create_backup_v2_contains_separated_archives_and_optional_visual_assets(tmp_path: Path) -> None:
    from app.services.backup_restore_service import BackupRestoreService

    settings = _settings(tmp_path)
    layout = ensure_data_layout(settings.data_dir)
    _create_db(layout.database_path, "backup-db")
    (layout.movie_metadata_dir / "movie-a.json").write_text('{"title":"A"}', encoding="utf-8")
    (layout.game_metadata_dir / "game-a.json").write_text('{"title":"Game A"}', encoding="utf-8")
    (layout.cache_dir / "ignore.cache").write_text("cache", encoding="utf-8")
    (layout.logs_dir / "app.log").write_text("log", encoding="utf-8")
    layout.active_game_session_path.write_text('{"active":true}', encoding="utf-8")
    settings.cover_dir.mkdir(parents=True)
    (settings.cover_dir / "MOVIE-A.jpg").write_bytes(b"cover-a")
    (settings.cover_dir / "notes.txt").write_text("ignore", encoding="utf-8")
    (layout.game_cover_dir / "game-a.png").write_bytes(b"game-cover")
    (layout.game_preview_dir / "game-a.gif").write_bytes(b"game-preview")
    (layout.game_archive_media_dir / "game-a.webp").write_bytes(b"game-archive-hero")
    settings_path = tmp_path / "config" / "settings.json"
    SettingsStore(settings_path).save(settings)

    output = tmp_path / "backup.zip"
    summary = BackupRestoreService().create_backup(
        settings,
        settings_path,
        output,
        include_visual_assets=True,
    )

    assert summary.path == output
    assert summary.metadata_files == 2
    assert summary.game_asset_files == 3
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert "manifest.json" in names
        assert "data/library.db" in names
        assert "data/metadata/movies/movie-a.json" in names
        assert "data/metadata/games/game-a.json" in names
        assert "settings/settings.json" in names
        assert "covers/MOVIE-A.jpg" in names
        assert "game_assets/covers/game-a.png" in names
        assert "game_assets/previews/game-a.gif" in names
        assert "game_assets/archive/game-a.webp" in names
        assert not any("cache" in name for name in names)
        assert not any("logs" in name for name in names)
        assert not any("active_game_session" in name for name in names)
        assert not any(name.endswith("notes.txt") for name in names)
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["format"] == "local_movie_manager_backup"
        assert manifest["version"] == 4
        assert manifest["includes_visual_assets"] is True


def test_create_backup_can_exclude_all_visual_assets(tmp_path: Path) -> None:
    from app.services.backup_restore_service import BackupRestoreService

    settings = _settings(tmp_path)
    layout = ensure_data_layout(settings.data_dir)
    _create_db(layout.database_path, "db")
    settings.cover_dir.mkdir(parents=True)
    (settings.cover_dir / "A.jpg").write_bytes(b"cover")
    (layout.game_cover_dir / "g.png").write_bytes(b"cover")
    (layout.game_preview_dir / "g.gif").write_bytes(b"preview")
    settings_path = tmp_path / "settings.json"
    SettingsStore(settings_path).save(settings)

    output = tmp_path / "no-assets.zip"
    BackupRestoreService().create_backup(settings, settings_path, output, include_visual_assets=False)

    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert not any(name.startswith("covers/") for name in names)
        assert not any(name.startswith("game_assets/") for name in names)
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["includes_visual_assets"] is False


def test_restore_replaces_movie_and_game_archives_merges_assets_and_preserves_machine_paths(tmp_path: Path) -> None:
    from app.services.backup_restore_service import BackupRestoreService

    service = BackupRestoreService()
    source_root = tmp_path / "source"
    source = _settings(source_root)
    source_layout = ensure_data_layout(source.data_dir)
    _create_db(source_layout.database_path, "backup-db")
    (source_layout.movie_metadata_dir / "movie-backup.json").write_text('{"state":"backup"}', encoding="utf-8")
    (source_layout.game_metadata_dir / "game-backup.json").write_text('{"state":"backup"}', encoding="utf-8")
    source.cover_dir.mkdir(parents=True)
    (source.cover_dir / "SAME.jpg").write_bytes(b"backup-same")
    (source.cover_dir / "BACKUP_ONLY.jpg").write_bytes(b"backup-only")
    (source_layout.game_cover_dir / "SAME.png").write_bytes(b"backup-game-cover")
    (source_layout.game_preview_dir / "BACKUP.gif").write_bytes(b"backup-preview")
    (source_layout.game_archive_media_dir / "BACKUP.webp").write_bytes(b"backup-archive-hero")
    source_settings_path = source_root / "config" / "settings.json"
    SettingsStore(source_settings_path).save(source)
    backup = tmp_path / "restore-me.zip"
    service.create_backup(source, source_settings_path, backup, include_visual_assets=True)

    current_root = tmp_path / "current"
    current = replace(
        _settings(current_root),
        auto_scan=False,
        sidebar_visible=True,
        sidebar_width=333,
        cover_tool_margin_px=11,
        sort_key="code",
        sort_desc=False,
        startup_library="movies",
        game_filter="all",
    )
    current_layout = ensure_data_layout(current.data_dir)
    _create_db(current_layout.database_path, "current-db")
    (current_layout.movie_metadata_dir / "current-only.json").write_text('{"state":"current"}', encoding="utf-8")
    (current_layout.game_metadata_dir / "current-game.json").write_text('{"state":"current"}', encoding="utf-8")
    current.cover_dir.mkdir(parents=True)
    (current.cover_dir / "SAME.jpg").write_bytes(b"current-same")
    (current.cover_dir / "CURRENT_ONLY.jpg").write_bytes(b"current-only")
    (current_layout.game_cover_dir / "SAME.png").write_bytes(b"current-game-cover")
    (current_layout.game_cover_dir / "CURRENT_ONLY.png").write_bytes(b"current-only-game-cover")
    current_settings_path = current_root / "config" / "settings.json"
    SettingsStore(current_settings_path).save(current)

    assessment = service.assess_restore(current, backup)
    assert assessment.data_will_overwrite is True
    assert assessment.cover_conflicts == 2

    service.restore_backup(current, current_settings_path, backup)

    assert _read_db_marker(current_layout.database_path) == "backup-db"
    assert (current_layout.movie_metadata_dir / "movie-backup.json").exists()
    assert (current_layout.game_metadata_dir / "game-backup.json").exists()
    assert not (current_layout.movie_metadata_dir / "current-only.json").exists()
    assert not (current_layout.game_metadata_dir / "current-game.json").exists()
    assert (current.cover_dir / "SAME.jpg").read_bytes() == b"backup-same"
    assert (current.cover_dir / "BACKUP_ONLY.jpg").read_bytes() == b"backup-only"
    assert (current.cover_dir / "CURRENT_ONLY.jpg").read_bytes() == b"current-only"
    assert (current_layout.game_cover_dir / "SAME.png").read_bytes() == b"backup-game-cover"
    assert (current_layout.game_cover_dir / "CURRENT_ONLY.png").read_bytes() == b"current-only-game-cover"
    assert (current_layout.game_preview_dir / "BACKUP.gif").read_bytes() == b"backup-preview"
    assert (current_layout.game_archive_media_dir / "BACKUP.webp").read_bytes() == b"backup-archive-hero"

    restored_settings = SettingsStore(current_settings_path).load()
    # Current-machine paths and executable choices are never imported from backup.
    assert restored_settings.data_dir == current.data_dir
    assert restored_settings.cover_dir == current.cover_dir
    assert restored_settings.libraries == current.libraries
    assert restored_settings.player_mode == current.player_mode
    assert restored_settings.player_path == current.player_path
    assert restored_settings.ffprobe_path == current.ffprobe_path
    assert restored_settings.ffmpeg_path == current.ffmpeg_path
    assert restored_settings.cover_tool_source_dir == current.cover_tool_source_dir
    # Portable preferences are restored from backup.
    assert restored_settings.auto_scan == source.auto_scan
    assert restored_settings.cover_tool_margin_px == source.cover_tool_margin_px
    assert restored_settings.sort_key == source.sort_key
    assert restored_settings.sort_desc == source.sort_desc
    assert restored_settings.startup_library == source.startup_library
    assert restored_settings.game_sort_key == source.game_sort_key
    assert restored_settings.game_filter == source.game_filter


def test_restore_accepts_v1_legacy_movie_metadata_backup(tmp_path: Path) -> None:
    from app.services.backup_restore_service import BackupRestoreService

    source = _settings(tmp_path / "source")
    source_settings_file = tmp_path / "source-settings.json"
    SettingsStore(source_settings_file).save(source)
    source_db = tmp_path / "source.db"
    _create_db(source_db, "v1-db")
    backup = tmp_path / "legacy-v1.zip"
    with zipfile.ZipFile(backup, "w") as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(
                {
                    "format": "local_movie_manager_backup",
                    "version": 1,
                    "created_at": "2025-01-01T00:00:00+00:00",
                    "includes_covers": False,
                }
            ),
        )
        archive.write(source_db, "data/library.db")
        archive.writestr("data/metadata/legacy-movie.json", '{"legacy":true}')
        archive.write(source_settings_file, "settings/settings.json")

    current = _settings(tmp_path / "current")
    current_layout = ensure_data_layout(current.data_dir)
    _create_db(current_layout.database_path, "current")
    current_settings_file = tmp_path / "current-settings.json"
    SettingsStore(current_settings_file).save(current)

    summary = BackupRestoreService().restore_backup(current, current_settings_file, backup)

    assert summary.metadata_files == 1
    assert _read_db_marker(current_layout.database_path) == "v1-db"
    assert (current_layout.movie_metadata_dir / "legacy-movie.json").read_text(encoding="utf-8") == '{"legacy":true}'
    assert not any(current_layout.game_metadata_dir.glob("*.json"))


def test_restore_rejects_invalid_or_unsafe_backup_before_touching_targets(tmp_path: Path) -> None:
    from app.services.backup_restore_service import BackupRestoreService, InvalidBackupError

    settings = _settings(tmp_path)
    layout = ensure_data_layout(settings.data_dir)
    _create_db(layout.database_path, "untouched")
    settings_path = tmp_path / "settings.json"
    SettingsStore(settings_path).save(settings)
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as archive:
        archive.writestr("../escape.txt", "bad")
        archive.writestr("manifest.json", json.dumps({"format": "local_movie_manager_backup", "version": 1}))

    with pytest.raises(InvalidBackupError):
        BackupRestoreService().restore_backup(settings, settings_path, bad)

    assert _read_db_marker(layout.database_path) == "untouched"


def test_restore_rolls_back_database_both_archive_trees_settings_and_assets_when_apply_fails(tmp_path: Path, monkeypatch) -> None:
    from app.services.backup_restore_service import BackupRestoreService

    service = BackupRestoreService()
    source = _settings(tmp_path / "source")
    source_layout = ensure_data_layout(source.data_dir)
    _create_db(source_layout.database_path, "backup-db")
    (source_layout.movie_metadata_dir / "backup-movie.json").write_text("backup-movie", encoding="utf-8")
    (source_layout.game_metadata_dir / "backup-game.json").write_text("backup-game", encoding="utf-8")
    source.cover_dir.mkdir(parents=True)
    (source.cover_dir / "SAME.jpg").write_bytes(b"backup-cover")
    (source_layout.game_cover_dir / "GAME.png").write_bytes(b"backup-game-cover")
    source_settings_path = tmp_path / "source-settings.json"
    SettingsStore(source_settings_path).save(source)
    backup = tmp_path / "backup.zip"
    service.create_backup(source, source_settings_path, backup, include_visual_assets=True)

    current = _settings(tmp_path / "current")
    current_layout = ensure_data_layout(current.data_dir)
    _create_db(current_layout.database_path, "current-db")
    (current_layout.movie_metadata_dir / "current-movie.json").write_text("current-movie", encoding="utf-8")
    (current_layout.game_metadata_dir / "current-game.json").write_text("current-game", encoding="utf-8")
    current.cover_dir.mkdir(parents=True)
    (current.cover_dir / "SAME.jpg").write_bytes(b"current-cover")
    current_settings_path = tmp_path / "current-settings.json"
    SettingsStore(current_settings_path).save(current)
    original_settings_bytes = current_settings_path.read_bytes()

    original_apply = service._apply_covers
    calls = 0

    def fail_during_visual_restore(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated game asset restore failure")
        return original_apply(*args, **kwargs)

    monkeypatch.setattr(service, "_apply_covers", fail_during_visual_restore)

    with pytest.raises(OSError, match="simulated game asset restore failure"):
        service.restore_backup(current, current_settings_path, backup)

    assert _read_db_marker(current_layout.database_path) == "current-db"
    assert (current_layout.movie_metadata_dir / "current-movie.json").read_text(encoding="utf-8") == "current-movie"
    assert (current_layout.game_metadata_dir / "current-game.json").read_text(encoding="utf-8") == "current-game"
    assert not (current_layout.movie_metadata_dir / "backup-movie.json").exists()
    assert not (current_layout.game_metadata_dir / "backup-game.json").exists()
    assert (current.cover_dir / "SAME.jpg").read_bytes() == b"current-cover"
    assert not (current_layout.game_cover_dir / "GAME.png").exists()
    assert current_settings_path.read_bytes() == original_settings_bytes


def test_restore_recreates_deleted_local_data_from_backup(tmp_path: Path) -> None:
    from app.services.backup_restore_service import BackupRestoreService

    service = BackupRestoreService()
    settings = _settings(tmp_path)
    layout = ensure_data_layout(settings.data_dir)
    _create_db(layout.database_path, "archived-db")
    (layout.movie_metadata_dir / "movie.json").write_text('{"title":"kept"}', encoding="utf-8")
    (layout.game_metadata_dir / "game.json").write_text('{"title":"game"}', encoding="utf-8")
    settings.cover_dir.mkdir(parents=True)
    (settings.cover_dir / "MOVIE.jpg").write_bytes(b"archived-cover")
    settings_path = tmp_path / "settings.json"
    SettingsStore(settings_path).save(settings)
    backup = tmp_path / "backup.zip"
    service.create_backup(settings, settings_path, backup, include_visual_assets=True)

    layout.database_path.unlink()
    (layout.movie_metadata_dir / "movie.json").unlink()
    (layout.game_metadata_dir / "game.json").unlink()
    (settings.cover_dir / "MOVIE.jpg").unlink()

    assessment = service.assess_restore(settings, backup)
    assert assessment.data_will_overwrite is False
    assert assessment.cover_conflicts == 0

    service.restore_backup(settings, settings_path, backup)

    assert _read_db_marker(layout.database_path) == "archived-db"
    assert (layout.movie_metadata_dir / "movie.json").read_text(encoding="utf-8") == '{"title":"kept"}'
    assert (layout.game_metadata_dir / "game.json").read_text(encoding="utf-8") == '{"title":"game"}'
    assert (settings.cover_dir / "MOVIE.jpg").read_bytes() == b"archived-cover"
