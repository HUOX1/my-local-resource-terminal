from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path

from app.config.data_dirs import ensure_data_layout
from app.config.settings import AppSettings, SettingsStore
from app.services.backup_restore_service import BackupRestoreService
from app.services.collection_folder_service import CollectionFolderService


def _settings(tmp_path: Path) -> AppSettings:
    return AppSettings(data_dir=tmp_path / "data", cover_dir=tmp_path / "covers", libraries=[])


def _make_db(path: Path, value: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE marker(value TEXT)")
        connection.execute("INSERT INTO marker VALUES(?)", (value,))


def test_backup_v4_includes_and_restores_collection_folder_definitions(tmp_path: Path) -> None:
    source = _settings(tmp_path / "source")
    source_layout = ensure_data_layout(source.data_dir)
    _make_db(source_layout.database_path, "source")
    source_settings = tmp_path / "source" / "settings.json"
    SettingsStore(source_settings).save(source)
    folders = CollectionFolderService(source_layout.collection_folders_path)
    folder = folders.create("movies", "恐怖")

    backup = tmp_path / "folders.zip"
    BackupRestoreService().create_backup(source, source_settings, backup, include_visual_assets=False)

    with zipfile.ZipFile(backup) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["version"] == 4
        assert "data/collections/folders.json" in archive.namelist()

    current = _settings(tmp_path / "current")
    current_layout = ensure_data_layout(current.data_dir)
    _make_db(current_layout.database_path, "current")
    current_settings = tmp_path / "current" / "settings.json"
    SettingsStore(current_settings).save(current)
    CollectionFolderService(current_layout.collection_folders_path).create("games", "旧文件夹")

    BackupRestoreService().restore_backup(current, current_settings, backup)

    restored = CollectionFolderService(current_layout.collection_folders_path)
    assert [(item.id, item.name) for item in restored.list("movies")] == [(folder.id, "恐怖")]
    assert restored.list("games") == []


def test_restoring_legacy_v3_backup_clears_newer_collection_folders(tmp_path: Path) -> None:
    current = _settings(tmp_path / "current")
    current_layout = ensure_data_layout(current.data_dir)
    _make_db(current_layout.database_path, "current")
    current_settings = tmp_path / "current" / "settings.json"
    SettingsStore(current_settings).save(current)
    CollectionFolderService(current_layout.collection_folders_path).create("movies", "不应保留")

    source = _settings(tmp_path / "source")
    source_layout = ensure_data_layout(source.data_dir)
    _make_db(source_layout.database_path, "source")
    source_settings = tmp_path / "source" / "settings.json"
    SettingsStore(source_settings).save(source)
    backup = tmp_path / "legacy-v3.zip"
    with zipfile.ZipFile(backup, "w") as archive:
        archive.writestr(
            "manifest.json",
            json.dumps({"format": "local_movie_manager_backup", "version": 3, "created_at": "x", "includes_visual_assets": False}),
        )
        archive.write(source_layout.database_path, "data/library.db")
        archive.write(source_settings, "settings/settings.json")

    BackupRestoreService().restore_backup(current, current_settings, backup)

    assert CollectionFolderService(current_layout.collection_folders_path).list("movies") == []
