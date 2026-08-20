# Local Identity Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single persistent local identity entrance that appears on every startup and collapses into the Flat Baseline sidebar after entry.

**Architecture:** Keep identity persistence independent of movie/game/settings data, add a focused `IdentityShellWidget` for setup/entry/sidebar rendering, and let `MainWindow` switch between identity and main-shell pages. Extend backup format compatibly so identity survives backup/restore without breaking v1/v2 archives.

**Tech Stack:** Python 3.11+, PySide6 Widgets/QMovie, JSON/managed local files, existing SQLite/JSON application stack.

**Spec:** `docs/superpowers/specs/2026-08-19-local-identity-shell-design.md`

## Global Constraints
- Base implementation is v0.4.0.7 Flat Baseline.
- Version becomes v0.4.0.8.
- Keep `LocalMovieManager` organization/application identity unchanged.
- Do not change movie/game SQLite schema, JSON fields, session semantics, launch behavior, poster caching, or playback behavior.
- No password, online account, multi-user system, glass shell, or custom window chrome.
- Every application launch starts at the identity shell and requires an avatar/badge click before entering the main shell.

---

### Task 1: Local identity persistence
**Files:** create `app/models/identity.py`, `app/services/identity_service.py`; test `tests/test_identity_service.py`.
**Interfaces:** `LocalIdentity`, `IdentityService.load/create_or_update/avatar_path/frame_path/clear_avatar/clear_frame`.
- [ ] Write identity service tests first and verify RED.
- [ ] Implement atomic JSON + managed asset copies.
- [ ] Verify focused tests GREEN.

### Task 2: Identity shell UI and sidebar room
**Files:** create `app/ui/identity_shell.py`; modify `app/ui/flat_theme.py`; test `tests/test_identity_shell_source.py`.
**Interfaces:** `IdentityShellWidget`, `IdentitySidebarRoom`, setup/entry states, QMovie avatar rendering.
- [ ] Write source-structure tests first and verify RED.
- [ ] Implement setup/entry/editor/sidebar widgets using Theme tokens.
- [ ] Verify source tests and compile.

### Task 3: Main-window/bootstrap integration
**Files:** modify `app/ui/main_window.py`, `app/bootstrap.py`, `pyproject.toml`; test `tests/test_identity_bootstrap_source.py`.
**Interfaces:** MainWindow receives `identity_service`; root stack starts on identity page; entering reveals current Flat main shell; sidebar identity click edits identity.
- [ ] Write integration source tests first and verify RED.
- [ ] Remove pre-window no-library SettingsDialog startup path.
- [ ] Wire identity service and stack transitions.
- [ ] Update version to v0.4.0.8.
- [ ] Verify focused regression tests.

### Task 4: Backup compatibility
**Files:** modify `app/services/backup_restore_service.py`; create `tests/test_backup_restore_identity.py`.
**Interfaces:** backup format v3 includes optional identity tree; v1/v2 restores preserve current identity.
- [ ] Write backup identity tests first and verify RED.
- [ ] Implement v3 archive/restore/rollback handling.
- [ ] Verify existing backup tests and WinError-5 regression tests.

### Task 5: Full verification and package
- [ ] Run full pytest suite.
- [ ] Run `python -m compileall -q app tests`.
- [ ] Build cumulative v0.4.0.8 overlay ZIP from changed files only.
- [ ] Test ZIP integrity.
