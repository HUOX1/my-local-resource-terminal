from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path

from app.config.data_dirs import ensure_data_layout
from app.config.settings import AppSettings, SettingsStore
from app.services.backup_restore_service import BackupRestoreService


def make_settings(tmp_path: Path) -> AppSettings:
    return AppSettings(data_dir=tmp_path / "data", cover_dir=tmp_path / "movie-covers", libraries=[])


def make_db(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE marker(value TEXT)")
        con.execute("INSERT INTO marker VALUES('x')")


def test_v2_backup_separates_movie_game_archives_and_visual_assets(tmp_path):
    settings = make_settings(tmp_path)
    layout = ensure_data_layout(settings.data_dir)
    make_db(layout.database_path)
    (layout.movie_metadata_dir / "movie.json").write_text("{}", encoding="utf-8")
    (layout.game_metadata_dir / "game.json").write_text("{}", encoding="utf-8")
    settings.cover_dir.mkdir()
    (settings.cover_dir / "movie.jpg").write_bytes(b"m")
    (layout.game_cover_dir / "game.png").write_bytes(b"g")
    (layout.game_preview_dir / "game.gif").write_bytes(b"gif")
    (layout.active_game_session_path).write_text("{}", encoding="utf-8")
    (layout.game_screenshot_cache_dir / "thumb.jpg").write_bytes(b"thumb")
    settings_path = tmp_path / "settings.json"
    SettingsStore(settings_path).save(settings)

    output = tmp_path / "backup.zip"
    BackupRestoreService().create_backup(settings, settings_path, output, include_visual_assets=True)

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["version"] == 4
    assert manifest["includes_visual_assets"] is True
    assert "data/metadata/movies/movie.json" in names
    assert "data/metadata/games/game.json" in names
    assert "covers/movie.jpg" in names
    assert "game_assets/covers/game.png" in names
    assert "game_assets/previews/game.gif" in names
    assert not any("active_game_session" in name for name in names)
    assert not any("thumb.jpg" in name for name in names)


def test_v2_backup_can_exclude_all_visual_assets(tmp_path):
    settings = make_settings(tmp_path)
    layout = ensure_data_layout(settings.data_dir)
    make_db(layout.database_path)
    settings.cover_dir.mkdir()
    (settings.cover_dir / "movie.jpg").write_bytes(b"m")
    (layout.game_cover_dir / "game.png").write_bytes(b"g")
    settings_path = tmp_path / "settings.json"
    SettingsStore(settings_path).save(settings)

    output = tmp_path / "backup.zip"
    BackupRestoreService().create_backup(settings, settings_path, output, include_visual_assets=False)

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
    assert not any(name.startswith("covers/") for name in names)
    assert not any(name.startswith("game_assets/") for name in names)
