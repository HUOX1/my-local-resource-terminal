# Local Backup and Restore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add offline ZIP backup and safe restore to Settings, preserving current-machine paths and supporting optional cover backup.

**Architecture:** A pure-Python `BackupRestoreService` owns archive validation, SQLite snapshotting, ZIP creation, restore mapping, and rollback. The PySide6 settings dialog only collects file choices and confirmation and invokes the service. Settings merging is isolated in the service so it is testable without Qt.

**Tech Stack:** Python 3.11+, pathlib, zipfile, sqlite3 backup API, tempfile, shutil, PySide6 Widgets, pytest.

## Global Constraints
- No network access.
- No video files in backups.
- Current-machine path settings must survive restore.
- Covers restore by merge; app database/metadata restore by replacement.
- Restore must roll back on failure.

---

### Task 1: Pure-Python backup archive service
**Files:**
- Create: `app/services/backup_restore_service.py`
- Test: `tests/test_backup_restore_service.py`

**Interfaces:**
- Produces `BackupRestoreService.create_backup(settings, settings_path, output_zip, include_covers) -> BackupSummary`
- Produces `BackupRestoreService.inspect_backup(backup_zip) -> BackupManifest`

- [ ] Write failing tests for backup contents, cover opt-out, exclusion of cache/logs/videos, and valid manifest.
- [ ] Run the focused tests and confirm failure because the service does not exist.
- [ ] Implement SQLite-consistent backup and ZIP writing.
- [ ] Re-run focused tests and confirm pass.

### Task 2: Restore mapping, settings preservation, and rollback
**Files:**
- Modify: `app/services/backup_restore_service.py`
- Test: `tests/test_backup_restore_service.py`

**Interfaces:**
- Produces `restore_backup(settings, settings_path, backup_zip) -> RestoreSummary`
- Restored settings preserve all current location/executable fields.

- [ ] Write failing tests for data replacement, cover merge, current-path preservation, invalid ZIP rejection, and rollback on injected copy failure.
- [ ] Run tests and confirm the expected failures.
- [ ] Implement restore staging and rollback.
- [ ] Re-run focused tests and confirm pass.

### Task 3: Settings dialog integration
**Files:**
- Modify: `app/ui/settings_dialog.py`
- Modify: `app/bootstrap.py`
- Test: `tests/test_backup_restore_ui_source.py`

**Interfaces:**
- SettingsDialog receives `settings_path` and exposes backup/restore buttons.
- Successful restore requests application restart rather than hot reload.

- [ ] Write source-level/UI-optional tests for labels, default “包含封面”, and constructor wiring.
- [ ] Run tests and confirm failure.
- [ ] Add Settings-only backup/restore section and confirmations.
- [ ] Re-run tests and confirm pass.

### Task 4: Version, docs, and full verification
**Files:**
- Modify: `README.md`
- Modify: `pyproject.toml` if project version exists there.

- [ ] Document v0.2.5 backup/restore behavior and test procedure.
- [ ] Run the full pytest suite.
- [ ] Run Python 3.11 syntax compilation.
- [ ] Build patch and full ZIP and verify archive integrity.
