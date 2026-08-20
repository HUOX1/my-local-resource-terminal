from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path

from app.config.data_dirs import ensure_data_layout
from app.config.settings import AppSettings, SettingsStore


def _settings(tmp_path: Path) -> AppSettings:
    return AppSettings(data_dir=tmp_path / "data", cover_dir=tmp_path / "covers", libraries=[])


def _make_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE marker(value TEXT)")
        connection.execute("INSERT INTO marker VALUES('x')")


def test_new_backup_includes_identity_tree_even_when_visual_assets_are_excluded(tmp_path: Path) -> None:
    from app.services.backup_restore_service import BackupRestoreService

    settings = _settings(tmp_path)
    layout = ensure_data_layout(settings.data_dir)
    _make_db(layout.database_path)
    settings_path = tmp_path / "config" / "settings.json"
    SettingsStore(settings_path).save(settings)
    identity_root = settings_path.parent / "identity"
    (identity_root / "assets").mkdir(parents=True)
    (identity_root / "profile.json").write_text('{"username":"User"}', encoding="utf-8")
    (identity_root / "assets" / "avatar.gif").write_bytes(b"gif")

    output = tmp_path / "backup.zip"
    BackupRestoreService().create_backup(settings, settings_path, output, include_visual_assets=False)

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["version"] == 4
    assert "identity/profile.json" in names
    assert "identity/assets/avatar.gif" in names


def test_restoring_legacy_v2_backup_without_identity_preserves_current_identity(tmp_path: Path) -> None:
    from app.services.backup_restore_service import BackupRestoreService

    current = _settings(tmp_path / "current")
    layout = ensure_data_layout(current.data_dir)
    _make_db(layout.database_path)
    current_settings = tmp_path / "current" / "config" / "settings.json"
    SettingsStore(current_settings).save(current)
    identity_root = current_settings.parent / "identity"
    (identity_root / "assets").mkdir(parents=True)
    (identity_root / "profile.json").write_text('{"username":"Keep Me"}', encoding="utf-8")
    (identity_root / "assets" / "avatar.png").write_bytes(b"keep")

    source = _settings(tmp_path / "source")
    source_layout = ensure_data_layout(source.data_dir)
    source_db = source_layout.database_path
    _make_db(source_db)
    source_settings = tmp_path / "source" / "config" / "settings.json"
    SettingsStore(source_settings).save(source)
    backup = tmp_path / "legacy-v2.zip"
    with zipfile.ZipFile(backup, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"format": "local_movie_manager_backup", "version": 2, "created_at": "x", "includes_visual_assets": False}))
        archive.write(source_db, "data/library.db")
        archive.write(source_settings, "settings/settings.json")

    BackupRestoreService().restore_backup(current, current_settings, backup)

    assert (identity_root / "profile.json").read_text(encoding="utf-8") == '{"username":"Keep Me"}'
    assert (identity_root / "assets" / "avatar.png").read_bytes() == b"keep"


def test_restoring_v3_backup_replaces_identity_tree(tmp_path: Path) -> None:
    from app.services.backup_restore_service import BackupRestoreService

    source = _settings(tmp_path / "source")
    source_layout = ensure_data_layout(source.data_dir)
    _make_db(source_layout.database_path)
    source_settings = tmp_path / "source" / "config" / "settings.json"
    SettingsStore(source_settings).save(source)
    source_identity = source_settings.parent / "identity"
    (source_identity / "assets").mkdir(parents=True)
    (source_identity / "profile.json").write_text('{"username":"Backup"}', encoding="utf-8")
    (source_identity / "assets" / "avatar.png").write_bytes(b"backup-avatar")
    backup = tmp_path / "v3.zip"
    BackupRestoreService().create_backup(source, source_settings, backup)

    current = _settings(tmp_path / "current")
    current_layout = ensure_data_layout(current.data_dir)
    _make_db(current_layout.database_path)
    current_settings = tmp_path / "current" / "config" / "settings.json"
    SettingsStore(current_settings).save(current)
    current_identity = current_settings.parent / "identity"
    (current_identity / "assets").mkdir(parents=True)
    (current_identity / "profile.json").write_text('{"username":"Current"}', encoding="utf-8")
    (current_identity / "assets" / "old.png").write_bytes(b"old")

    BackupRestoreService().restore_backup(current, current_settings, backup)

    assert (current_identity / "profile.json").read_text(encoding="utf-8") == '{"username":"Backup"}'
    assert (current_identity / "assets" / "avatar.png").read_bytes() == b"backup-avatar"
    assert not (current_identity / "assets" / "old.png").exists()
