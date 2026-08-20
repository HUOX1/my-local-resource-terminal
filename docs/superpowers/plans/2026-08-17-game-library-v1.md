# Game Library v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend v0.2.7 from a movie-only manager into a local resource terminal with an independent manually-managed game library, reliable single-session play-time tracking, GIF hover previews, external screenshot browsing, separated movie/game archives, and integrated backup/restore.

**Architecture:** Keep `MovieRecord` and existing movie services intact as a separate domain. Add a parallel game domain (`GameRecord`, game metadata/repository/services/UI`) and share only the application shell, settings, database file, backup framework, and top-level library switcher. Permanent JSON archives remain the durable source of truth; SQLite remains the query/index layer; active game timing is checkpointed separately every 30 seconds and merged into permanent JSON only when the session ends.

**Tech Stack:** Python >=3.11, PySide6 >=6,<7, Pillow >=10,<13, SQLite, JSON, pytest. Windows desktop; no server/browser.

## Global Constraints

- Existing movie behavior and v0.2.7 regression tests must remain passing.
- Game executables are always selected manually; never scan or guess EXEs.
- Only a game launch initiated by this terminal can acquire timing eligibility.
- At most one active timed game exists; later launches are allowed but silently untracked.
- Timing UI is second-level; current session checkpoint overwrites every 30 seconds; completed session duration is exact to the second.
- External screenshot originals are never copied, deleted, or included in normal backups.
- Game cover and GIF preview are permanent assets and are included when “包含视觉资源” is enabled.
- Movie/game archives are physically separated under `metadata/movies/` and `metadata/games/`.
- Do not add a generic `ResourceRecord`/`resources` table.
- Remove the functional left sidebar; use a top-level `影片 / 游戏` switcher.
- Search text is never persisted.
- Existing central movie poster directory is not migrated.
- Python 3.11 source compatibility must continue to pass.
- The current build environment may not have PySide6; Qt runtime tests may be skipped, but source-level and core tests must still pass.

---

### Task 1: Data layout, movie archive migration, and database schema versioning

**Files:**
- Modify: `app/config/data_dirs.py`
- Modify: `app/db/database.py`
- Modify: `app/db/schema.sql`
- Modify: `app/services/metadata_service.py`
- Modify: `tests/test_metadata_service.py`
- Create: `tests/test_data_layout_migration.py`
- Create: `tests/test_database_migrations.py`

**Interfaces:**
- Produces: `DataLayout.movie_metadata_dir`, `game_metadata_dir`, `game_assets_dir`, `game_cover_dir`, `game_preview_dir`, `state_dir`, `active_game_session_path`, `game_screenshot_cache_dir`.
- Produces: `MovieMetadataMigrator.migrate(layout: DataLayout) -> MovieMetadataMigrationSummary`.
- Produces: `Database.schema_version() -> int` and transactional migration to schema version 2.
- Changes: callers must instantiate `MetadataService(layout.movie_metadata_dir)` instead of root `metadata_dir`.

- [ ] **Step 1: Write failing data-layout/migration tests**

```python
from app.config.data_dirs import ensure_data_layout, MovieMetadataMigrator


def test_layout_separates_movie_and_game_archives(tmp_path):
    layout = ensure_data_layout(tmp_path / "data")
    assert layout.movie_metadata_dir == layout.root / "metadata" / "movies"
    assert layout.game_metadata_dir == layout.root / "metadata" / "games"
    assert layout.game_cover_dir == layout.root / "game_assets" / "covers"
    assert layout.game_preview_dir == layout.root / "game_assets" / "previews"
    assert layout.active_game_session_path == layout.root / "state" / "active_game_session.json"


def test_movie_metadata_migration_is_copy_verify_then_remove_and_idempotent(tmp_path):
    layout = ensure_data_layout(tmp_path / "data")
    legacy = layout.metadata_dir / "movie-1.json"
    legacy.write_text('{"schema_version":1,"uuid":"movie-1","cover_key":"ABC"}', encoding="utf-8")
    first = MovieMetadataMigrator().migrate(layout)
    assert first.migrated == 1
    assert not legacy.exists()
    assert (layout.movie_metadata_dir / legacy.name).exists()
    second = MovieMetadataMigrator().migrate(layout)
    assert second.migrated == 0
```

- [ ] **Step 2: Run targeted tests and verify failure**

Run: `pytest -q tests/test_data_layout_migration.py tests/test_metadata_service.py`
Expected: FAIL because the new layout properties/migrator do not exist and MetadataService still targets the legacy root.

- [ ] **Step 3: Implement separated layout and safe movie metadata migration**

Implement `DataLayout` properties/direct fields for all game paths. `ensure_data_layout()` creates the new directories. Implement `MovieMetadataMigrator` so it only migrates root-level `metadata/*.json`, validates JSON as a movie archive by decoding with `MetadataService`, writes destination atomically/copy-verifies, and removes the legacy source only after successful verification. Leave unreadable/non-movie files in place and report them as errors.

- [ ] **Step 4: Write failing schema migration tests**

```python
from app.db.database import Database


def test_initialize_migrates_database_to_schema_version_2(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()
    assert db.schema_version() == 2
    with db.connect() as con:
        names = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"games", "game_sessions", "schema_meta"} <= names
```

- [ ] **Step 5: Run migration test and verify failure**

Run: `pytest -q tests/test_database_migrations.py`
Expected: FAIL because schema versioning and game tables do not exist.

- [ ] **Step 6: Implement schema version 2**

Add `schema_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)`, `games`, `game_tags`, and `game_sessions`. `Database.initialize()` must execute existing base schema, then run versioned migrations inside a transaction and set `schema_version=2` only after success. Add indexes for title, favorite, added_at, last_played_at, total_play_seconds, installed-query-relevant launch path if useful, and sessions by game/start.

- [ ] **Step 7: Run Task 1 tests plus existing metadata/database-sensitive tests**

Run: `pytest -q tests/test_data_layout_migration.py tests/test_database_migrations.py tests/test_metadata_service.py tests/test_movie_repository.py tests/test_acceptance_archive_lifecycle.py`
Expected: PASS.

---

### Task 2: Game domain model, permanent JSON archive, and SQLite repository

**Files:**
- Create: `app/models/game.py`
- Create: `app/services/game_metadata_service.py`
- Create: `app/repositories/game_repository.py`
- Modify: `app/models/__init__.py`
- Modify: `app/repositories/__init__.py`
- Create: `tests/test_game_model.py`
- Create: `tests/test_game_metadata_service.py`
- Create: `tests/test_game_repository.py`

**Interfaces:**
- Produces: `GameMetadata`, `GameSession`, `GameRecord`, `GameMetadataPatch`.
- Produces: `GameMetadataService.create/save/load/load_all/delete` and atomic JSON writes.
- Produces: `GameRepository.upsert_game`, `get`, `list_games`, `delete`, `replace_sessions`, `upsert_active_session`, `complete_session`, `rebuild_from_archives`.

- [ ] **Step 1: Write failing model/archive tests**

```python
from app.models.game import GameMetadata, GameSession


def test_game_metadata_normalizes_tags_and_rating():
    game = GameMetadata.new("Demo")
    game.tags = ["RPG", " rpg ", "单机"]
    game.rating = 5
    game.normalize()
    assert game.tags == ["RPG", "单机"]


def test_game_archive_round_trip_preserves_completed_sessions(tmp_path):
    service = GameMetadataService(tmp_path)
    game = GameMetadata.new("Demo")
    game.sessions.append(GameSession.completed(game.uuid, 100, 160))
    service.save(game)
    restored = service.load(game.uuid)
    assert restored.total_play_seconds == 60
    assert restored.sessions[0].duration_seconds == 60
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest -q tests/test_game_model.py tests/test_game_metadata_service.py`
Expected: FAIL because game model/service do not exist.

- [ ] **Step 3: Implement game model and JSON service**

Use UUID strings; timestamps are timezone-aware ISO-8601 strings in JSON. Keep completed/recovered sessions in permanent JSON. Do not persist a derived `installed` boolean. Validate ratings `0..5`, normalize tags case-insensitively, and compute/synchronize aggregate fields from completed sessions when needed. Save by writing a temp JSON, decoding/validating it, then `replace()`.

- [ ] **Step 4: Write failing repository CRUD/query tests**

Test upsert/get/delete, tags, session replacement, sorting by recent added/title/release/rating/total play/last played/play count, and filtering favorite/installed/uninstalled/recently played. Installed filtering is computed from `Path(launch_exe).exists()` after row materialization, not permanently stored.

- [ ] **Step 5: Run repository tests and verify failure**

Run: `pytest -q tests/test_game_repository.py`
Expected: FAIL because repository does not exist.

- [ ] **Step 6: Implement repository**

Store durable game summary fields in `games`, tags in `game_tags`, sessions in `game_sessions`. Keep repository API independent from Qt. Ensure delete cascades sessions/tags. `rebuild_from_archives()` restores game rows and completed/recovered sessions from JSON archives.

- [ ] **Step 7: Run Task 2 tests**

Run: `pytest -q tests/test_game_model.py tests/test_game_metadata_service.py tests/test_game_repository.py`
Expected: PASS.

---

### Task 3: Game assets and external screenshot browsing

**Files:**
- Create: `app/services/game_asset_service.py`
- Create: `app/services/screenshot_service.py`
- Create: `tests/test_game_asset_service.py`
- Create: `tests/test_screenshot_service.py`

**Interfaces:**
- Produces: `GameAssetService.import_cover(game_uuid, source) -> Path | None`, `import_preview`, `remove_game_assets`.
- Produces: `ScreenshotService.list_images(directory) -> list[ScreenshotItem]`, `thumbnail_for(game_uuid, image_path) -> Path`.

- [ ] **Step 1: Write failing asset tests**

Verify cover/GIF are copied into game permanent asset directories using stable game UUID filenames/extensions, source is never modified, replacement is atomic, and removal only deletes terminal-owned assets.

- [ ] **Step 2: Run and verify failure**

Run: `pytest -q tests/test_game_asset_service.py`
Expected: FAIL.

- [ ] **Step 3: Implement `GameAssetService`**

Accept common static image types for covers and `.gif` for previews. Never auto-crop. Return `None` when source is omitted; raise a clear error for unreadable/unsupported assets.

- [ ] **Step 4: Write failing screenshot tests**

Verify supported images are read from an external folder, sorted newest-first by mtime, missing directories return an unavailable result/empty list without modifying archives, and thumbnails are generated under `cache/games/screenshots/<game-uuid>/`.

- [ ] **Step 5: Run and verify failure**

Run: `pytest -q tests/test_screenshot_service.py`
Expected: FAIL.

- [ ] **Step 6: Implement screenshot service**

Use Pillow for thumbnails. Cache key must incorporate full source path + mtime + size so changed images rebuild. Never delete or copy screenshot originals.

- [ ] **Step 7: Run Task 3 tests**

Run: `pytest -q tests/test_game_asset_service.py tests/test_screenshot_service.py`
Expected: PASS.

---

### Task 4: Launcher, single active session timer, 30-second checkpoints, and recovery

**Files:**
- Create: `app/services/game_launcher.py`
- Create: `app/services/game_session_service.py`
- Create: `tests/test_game_launcher.py`
- Create: `tests/test_game_session_service.py`

**Interfaces:**
- Produces: `GameLauncher.launch(game: GameMetadata) -> subprocess.Popen | os.startfile result wrapper`.
- Produces: `GameSessionService.request_launch(game)`, `poll()`, `checkpoint()`, `finish_active()`, `recover()`, `active_game_uuid`, `elapsed_seconds`.
- Dependency injection: process spawning, process-path inspection, and clock functions are injectable for deterministic tests.

- [ ] **Step 1: Write failing launcher tests**

Verify missing launch EXE rejects before spawning, args/workdir are respected, and no session is created merely because the launcher starts.

- [ ] **Step 2: Run and verify failure**

Run: `pytest -q tests/test_game_launcher.py`
Expected: FAIL.

- [ ] **Step 3: Implement launcher**

Use `subprocess.Popen` with explicit executable/args and `cwd`; do not use shell expansion. Windows paths with spaces must work. Return process start information only; timing remains in session service.

- [ ] **Step 4: Write failing session state-machine tests**

Cover:
- first terminal-launched game obtains waiting/timing eligibility;
- session starts only when injected process inspector reports the exact timing executable path;
- 5-minute waiting timeout returns to idle without history;
- second terminal launch while A is active is allowed by caller but `GameSessionService` refuses timing ownership silently;
- `poll()` advances elapsed time without database writes every second;
- `checkpoint()` at 30 seconds overwrites one active row/state file;
- process disappearance completes exact duration and updates aggregates/archive;
- external process appearance without `request_launch()` does nothing;
- recovery continues same session when timing process still exists;
- recovery closes at last checkpoint with `recovered` when process is gone;
- explicit app shutdown completes to current second and clears active state.

- [ ] **Step 5: Run and verify failure**

Run: `pytest -q tests/test_game_session_service.py`
Expected: FAIL.

- [ ] **Step 6: Implement state machine**

Keep `waiting_game_uuid` separate from `active_session`. `request_launch` reserves eligibility only if idle. `poll()` checks exact normalized executable path through an injectable inspector. Persist active checkpoint to `game_sessions` and `state/active_game_session.json`; use one atomic state file. On completion save permanent game JSON and repository aggregates, then remove state file.

- [ ] **Step 7: Run Task 4 tests**

Run: `pytest -q tests/test_game_launcher.py tests/test_game_session_service.py`
Expected: PASS.

---

### Task 5: Settings state for resource switching and independent movie/game view preferences

**Files:**
- Modify: `app/config/settings.py`
- Modify: `app/bootstrap.py`
- Modify: `tests/test_settings.py`
- Create: `tests/test_resource_view_settings.py`

**Interfaces:**
- Adds: `startup_library: Literal["movies", "games"] = "movies"`.
- Adds: game sort state fields `game_sort_key`, `game_sort_desc`, and separate movie/game filter state strings.
- Retains old movie `sort_key/sort_desc` compatibility.

- [ ] **Step 1: Write failing settings migration tests**

Verify old v0.2.7 settings load with `startup_library="movies"`, invalid values fall back to movies, game sort keys are validated, and search text is absent from persisted JSON.

- [ ] **Step 2: Run and verify failure**

Run: `pytest -q tests/test_settings.py tests/test_resource_view_settings.py`
Expected: FAIL because new settings do not exist.

- [ ] **Step 3: Implement settings fields and backward-compatible load/save**

Persist startup library and independent view state. Preserve deprecated sidebar keys on load if desired for compatibility, but stop using/persisting them once the UI is migrated.

- [ ] **Step 4: Run settings tests**

Run: `pytest -q tests/test_settings.py tests/test_resource_view_settings.py`
Expected: PASS.

---

### Task 6: Backup/restore v2 with separated archives and game visual assets

**Files:**
- Modify: `app/services/backup_restore_service.py`
- Modify: `app/ui/settings_dialog.py`
- Modify: `tests/test_backup_restore_service.py`
- Modify: `tests/test_backup_restore_ui_source.py`

**Interfaces:**
- Backup manifest version increments to 2 while restore may accept version 1 for backward compatibility.
- `create_backup(..., include_visual_assets: bool = True)` replaces/aliases `include_covers`.
- Summary distinguishes movie metadata, game metadata, movie covers, game covers/previews where practical.

- [ ] **Step 1: Write failing backup tests**

Verify v2 ZIP contains `data/metadata/movies/`, `data/metadata/games/`, DB snapshot, settings snapshot, central movie covers and `game_assets/covers`, `game_assets/previews` only when visual assets enabled; excludes cache, logs, state/active session, game EXEs, screenshots.

Also verify a v1 backup with legacy `data/metadata/*.json` can still restore and then be migrated on next service build.

- [ ] **Step 2: Run and verify failure**

Run: `pytest -q tests/test_backup_restore_service.py`
Expected: FAIL against old backup structure.

- [ ] **Step 3: Implement backup/restore v2**

During restore, replace database + movie/game metadata archive trees to backup state, merge movie/game visual assets with backup same-name overwrite and unrelated current assets preserved, preserve current machine data root/movie cover/libraries/player/FFmpeg configuration, and rollback both archive trees/assets/settings/DB on error.

- [ ] **Step 4: Update settings UI wording**

Change “包含封面” to “包含视觉资源”; update note to say movie/game binaries and external screenshots are excluded. Add `启动默认资源库` combo under general settings. Keep default visual-resource backup checked.

- [ ] **Step 5: Run Task 6 tests**

Run: `pytest -q tests/test_backup_restore_service.py tests/test_backup_restore_ui_source.py tests/test_settings.py`
Expected: PASS (Qt-dependent tests may skip if PySide6 is absent).

---

### Task 7: Game UI components (model/delegate, add/edit, detail, screenshots)

**Files:**
- Create: `app/ui/game_models.py`
- Create: `app/ui/game_delegate.py`
- Create: `app/ui/game_edit_dialog.py`
- Create: `app/ui/game_detail.py`
- Create: `tests/test_game_models.py`
- Create: `tests/test_game_ui_source.py`

**Interfaces:**
- `GameListModel.set_games(list[GameMetadata])`; data roles expose game object, cover path, preview GIF path, installed state.
- `GamePosterDelegate`/view handles natural-aspect static cover and 250 ms hover preview while ensuring only one QMovie is active.
- `GameEditDialog.result_game` returns validated edited `GameMetadata` plus selected asset sources if needed.
- `GameDetailDialog` shows exact-to-second aggregate/session history and screenshot grid.

- [ ] **Step 1: Write non-Qt/source tests plus Qt tests guarded by availability**

Test game sort/filter model helpers without needing a display. Source regression tests must assert 250 ms hover delay, one active GIF strategy, external screenshot double-click open, and absence of auto EXE scanning.

- [ ] **Step 2: Run and verify failure**

Run: `pytest -q tests/test_game_models.py tests/test_game_ui_source.py`
Expected: FAIL because components do not exist.

- [ ] **Step 3: Implement game models/delegate**

Follow existing movie poster sizing behavior: static cover is primary, no permanent title overlay. Implement hover timer and `QMovie` lifecycle defensively; broken GIF falls back to static image.

- [ ] **Step 4: Implement add/edit dialog**

Sections: metadata; launch EXE/timing EXE/args/workdir; cover/GIF/screenshot dir. Selecting launch EXE defaults workdir and timing EXE only if those fields have not been explicitly changed.

- [ ] **Step 5: Implement game detail dialog**

Show metadata, launch button signal, aggregate play information, chronological session table/list, screenshot grid with refresh/open-dir/reselect behavior. Double-click screenshot uses system default opener.

- [ ] **Step 6: Run Task 7 tests**

Run: `pytest -q tests/test_game_models.py tests/test_game_ui_source.py`
Expected: PASS; Qt runtime tests skip if unavailable.

---

### Task 8: Main window shell: remove sidebar, top-level library switching, game wall, and live timer status

**Files:**
- Modify: `app/ui/main_window.py`
- Modify: `app/ui/movie_models.py` only if needed for top-level filter compatibility
- Modify: `tests/test_main_window.py`
- Modify: `tests/test_main_window_source_regression.py`
- Modify: `tests/test_ui_behavior_source.py`
- Create: `tests/test_resource_shell_source.py`

**Interfaces:**
- MainWindow receives both movie and game services or a small `GameUiServices` bundle.
- Emits view-state changes separately for movie/game sort/filter.
- Public slot/method `switch_library("movies"|"games")`.

- [ ] **Step 1: Write failing shell/source tests**

Assert no functional sidebar/splitter navigation remains; top controls include `影片` and `游戏`; filter options change per library; `+ 添加游戏` appears only in game mode; game double-click launches; right-click routes to game detail/edit/delete; live active timer label only appears while timing; search is cleared when switching domains.

- [ ] **Step 2: Run and verify failure**

Run: `pytest -q tests/test_resource_shell_source.py tests/test_main_window_source_regression.py tests/test_ui_behavior_source.py`
Expected: FAIL against movie-only sidebar UI.

- [ ] **Step 3: Refactor shell without changing movie domain behavior**

Replace sidebar/splitter with a top resource switcher and single central poster stack/view. Keep movie scan/settings/cover-processing controls available in movie mode. Use a filter combo instead of left categories. Preserve movie double-click play and context menus.

- [ ] **Step 4: Integrate game wall operations**

Add manual game creation/editing, details, favorite/tag actions as supported, open game/screenshot folders, and archive deletion with confirmation explicitly stating game files/screenshots are untouched.

- [ ] **Step 5: Integrate live timer UI**

A 1-second Qt timer calls/presents session-service elapsed state; a 30-second cadence calls checkpoint. Process polling can be on the same 1-second timer. Closing while active prompts cancel/exit; exit finishes active session to current second.

- [ ] **Step 6: Run shell tests**

Run: `pytest -q tests/test_main_window.py tests/test_main_window_source_regression.py tests/test_ui_behavior_source.py tests/test_resource_shell_source.py`
Expected: PASS/Qt skips only for unavailable PySide6.

---

### Task 9: Bootstrap/service wiring and archive rebuild

**Files:**
- Modify: `app/bootstrap.py`
- Modify: `app/main.py` if application naming changes
- Create: `tests/test_bootstrap_game_services_source.py`
- Modify: `tests/test_python_compatibility.py`

**Interfaces:**
- `ServiceBundle` gains game repository/metadata/assets/screenshots/launcher/session service.
- `build_services()` performs safe movie archive migration before constructing `MetadataService(layout.movie_metadata_dir)`; loads/rebuilds both domains.
- Startup library setting is applied after MainWindow construction.

- [ ] **Step 1: Write failing bootstrap source tests**

Assert movie migration executes before movie archive load; game metadata loads from `game_metadata_dir`; database rebuild/upsert covers game archives; recovery of active game session happens after services exist; startup library is applied from settings.

- [ ] **Step 2: Run and verify failure**

Run: `pytest -q tests/test_bootstrap_game_services_source.py`
Expected: FAIL.

- [ ] **Step 3: Wire services and persistence callbacks**

Build game services, pass them to MainWindow, persist independent movie/game view states and startup library through SettingsStore. Remove obsolete sidebar persistence callbacks from active use.

- [ ] **Step 4: Run bootstrap and Python 3.11 compatibility tests**

Run: `pytest -q tests/test_bootstrap_game_services_source.py tests/test_python_compatibility.py`
Expected: PASS.

---

### Task 10: Documentation, versioning, full regression, and deliverables

**Files:**
- Modify: `README.md`
- Modify: `pyproject.toml`
- Modify: launcher text/names only if needed; preserve existing silent launcher behavior
- Create/update: release ZIP/patch ZIP outside source tree

**Interfaces:**
- Version: `0.3.0` (first local-resource-terminal/game-library release).

- [ ] **Step 1: Update docs/version**

Document movie/game top switcher, manual game adding, launch/timing EXE distinction, 30-second recovery checkpoint, GIF hover, screenshot-folder behavior, archive permanence, separated metadata, backup exclusions, and default startup library setting. Explain movie metadata migration is automatic and central movie cover directory is unchanged.

- [ ] **Step 2: Run compile and full tests**

Run:

```bash
python -m compileall -q app tests
pytest -q
pytest -q tests/test_python_compatibility.py
```

Expected: full suite passes except explicitly PySide6-dependent skips in this build environment.

- [ ] **Step 3: Run old v0.2.7 regression suite against the upgraded source where applicable**

Confirm movie archive lifecycle, scanner, cover tool, sorting, batch edit, backup/restore compatibility, and Windows launcher tests remain green. If an old source-regression test asserts the intentionally removed sidebar, replace that assertion with the new approved shell requirement rather than preserving obsolete UI.

- [ ] **Step 4: Create patch and full ZIPs**

Patch ZIP must contain only files required to overlay a clean v0.2.7 installation plus README/release notes; full ZIP contains the complete v0.3.0 project without `.pytest_cache`, `__pycache__`, local test artifacts, or user data.

Suggested filenames:

```text
v0.3.0_游戏库补丁.zip
本地资源终端_MVP_v0.3.0_游戏库版.zip
```

- [ ] **Step 5: Verify ZIP integrity**

Run `unzip -t` on both archives and inspect archive member lists for accidental user data/cache files.

## Self-review

- Spec coverage: all 26 design sections are assigned to Tasks 1–10; no music/comic/resource abstraction work is included.
- No placeholders/TODO implementation steps remain.
- Core names are consistent: `GameMetadata`, `GameSession`, `GameMetadataService`, `GameRepository`, `GameLauncher`, `GameSessionService`, and `startup_library`.
- Intentional change from early discussion is preserved: the sidebar is removed and resource switching is top-level.
