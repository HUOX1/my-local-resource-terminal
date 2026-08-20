# Library Folders + Movie Archive Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v0.4.1.9 with one-level virtual folders for Movie/Game and an in-content Movie Archive page using existing movie data.

**Architecture:** Folder definitions live in a dedicated permanent JSON store under `Data/collections/`; item membership is an optional `folder_id` persisted in each domain's existing JSON and SQLite row. MainWindow treats folder selection as an additional organization filter. Movie Archive mirrors the Game Archive navigation pattern while delegating editing to the existing `MovieDetailDialog`.

**Tech Stack:** Python 3.11+, PySide6 Widgets, SQLite, JSON.

**Spec:** `docs/superpowers/specs/2026-08-19-library-folders-movie-archive-design.md`

## Global Constraints

- Stage 1 business behavior remains frozen unless explicitly changed here.
- Movie and Game remain parallel domain models.
- JSON/permanent files are archival truth; SQLite remains rebuildable index/runtime state.
- Folder hierarchy depth is exactly one.
- No online scraper or new dependency.
- No video/GIF behavior changes in Game Archive.
- No television Season/Episode implementation in this release.
- Repository has no Git; use isolated copied working directory and omit commit steps.

---

### Task 1: Folder persistence and schema

**Files:**
- Create: `app/models/collection_folder.py`
- Create: `app/services/collection_folder_service.py`
- Modify: `app/config/data_dirs.py`
- Modify: `app/models/movie.py`
- Modify: `app/models/game.py`
- Modify: `app/services/metadata_service.py`
- Modify: `app/services/game_metadata_service.py`
- Modify: `app/db/schema.sql`
- Modify: `app/db/database.py`
- Modify: `app/repositories/movie_repository.py`
- Modify: `app/repositories/game_repository.py`
- Test: `tests/test_collection_folder_service.py`
- Test: `tests/test_database_migrations.py`
- Test: `tests/test_metadata_service.py`
- Test: `tests/test_game_metadata_service.py`

**Interfaces:**
- Produces `CollectionFolderService(path)` with `list(domain)`, `create(domain,name)`, `rename(folder_id,name)`, `delete(folder_id)`, `get(folder_id)`.
- Produces optional `MovieMetadata.folder_id` / `GameMetadata.folder_id`.
- SQLite schema version becomes 5.

- [ ] Write failing persistence/migration tests for folder definitions and `folder_id` round-trip.
- [ ] Run focused tests and confirm failures are because the new APIs/columns do not exist.
- [ ] Implement the minimal model/service/data-layout/metadata/schema/repository support.
- [ ] Run focused tests until green.

### Task 2: Catalog folder assignment/filtering + backup v4

**Files:**
- Modify: `app/services/catalog_service.py`
- Modify: `app/services/game_catalog_service.py`
- Modify: `app/services/backup_restore_service.py`
- Modify: `app/bootstrap.py`
- Test: `tests/test_catalog_service.py`
- Test: `tests/test_game_catalog_service.py`
- Test: `tests/test_backup_restore_v2.py`
- Test: `tests/test_backup_restore_identity.py`
- Create: `tests/test_collection_folder_backup_v0419.py`

**Interfaces:**
- `MovieFilter.folder_id` filters movie list.
- `GameCatalogService.list_games(..., folder_id=...)` filters game list.
- `CatalogService.set_folder(uuids, folder_id)` and `GameCatalogService.set_folder(uuids, folder_id)` persist membership including clear-to-None.
- `ServiceBundle.collection_folders` exposes folder definitions to UI.
- Backup version 4 stores/restores `data/collections/folders.json`.

- [ ] Write failing tests for filtering, assignment/clear, and backup v4 restore/rollback behavior.
- [ ] Verify RED.
- [ ] Implement catalog/bootstrap/backup behavior.
- [ ] Verify focused tests GREEN.

### Task 3: Folder UI in the existing magnifier workflow

**Files:**
- Modify: `app/ui/flat_icons.py`
- Modify: `app/ui/main_window.py`
- Modify: `app/ui/flat_theme.py` only if a small existing token/QSS hook is needed.
- Create: `tests/test_collection_folder_ui_v0419.py`

**Interfaces:**
- `flat_icon("search_add")` renders a magnifier with plus sign inside lens.
- Magnifier popup exposes folder selection/create/rename/delete for the active domain.
- Context menus expose move-to-folder actions.

- [ ] Write source-level failing tests for icon and UI wiring/text.
- [ ] Verify RED.
- [ ] Implement popup folder controls, per-domain selected folder state, status text, move menus and deletion cleanup.
- [ ] Verify focused tests GREEN.

### Task 4: Movie Archive in-content page

**Files:**
- Create: `app/ui/movie_archive_page.py`
- Modify: `app/ui/main_window.py`
- Modify: `app/ui/flat_theme.py`
- Create: `tests/test_movie_archive_page_v0419.py`

**Interfaces:**
- `MovieArchivePage` signals: `back_requested`, `play_requested(str)`, `edit_requested(str)`.
- `set_record(MovieRecord)` updates all existing movie information.
- MainWindow context action “影片档案” opens this page.
- Existing `MovieDetailDialog` remains the editor.

- [ ] Write failing source tests for page existence, fields, signals, and MainWindow stack integration.
- [ ] Verify RED.
- [ ] Implement the page and integration.
- [ ] Verify focused tests GREEN.

### Task 5: Release/version/integrity

**Files:**
- Modify: `pyproject.toml`
- Modify: version assertions/tests referring to latest version.
- Create: `升级说明_v0.4.1.9.txt`

**Interfaces:**
- Visible application version is `v0.4.1.9`.

- [ ] Write/update version regression test to expect v0.4.1.9 and verify it fails first.
- [ ] Bump version and add release notes.
- [ ] Run full `python -m pytest -q`.
- [ ] Run `python -m compileall -q app tests`.
- [ ] Build full source ZIP and cumulative overlay ZIP against frozen v0.3.4.7.
- [ ] Apply overlay to a fresh v0.3.4.7 baseline and compare runtime files with the full-source tree.
- [ ] Run `unzip -t` on both ZIPs.
