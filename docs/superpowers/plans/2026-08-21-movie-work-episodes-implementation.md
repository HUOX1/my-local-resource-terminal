# Movie Work Episodes v0.4.3.1.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to execute this plan task by task, with review checkpoints.

**Goal:** Replace the current one-video-per-movie behavior with one work per video folder, preserving a stable ordered episode list, work-level covers and metadata, and the existing single-movie experience.

**Architecture:** Keep `movies` and movie JSON as the work aggregate. Add deterministic episode metadata to JSON and a `movie_episodes` SQLite table for paths and probe data. Discovery emits one work candidate per folder; scanning reconciles that candidate with one work and its child episodes. UI consumers receive one `MovieRecord` per work and must explicitly choose an episode whenever the work has more than one.

**Tech Stack:** Python 3.11, dataclasses, SQLite, PySide6, pytest, pytest-qt.

**Spec:** `docs/superpowers/specs/2026-08-21-movie-work-episodes-design.md`

## Global Constraints

- Execute every production change with red-green-refactor: add one focused behavior test, run it and confirm the expected failure, then write the smallest production change and rerun the focused suite.
- Preserve all manually edited movie metadata and playback statistics.
- Never delete videos, subtitles, centralized covers, or other user media.
- Never merge duplicate archives when any candidate has non-default user metadata.
- A multi-episode work must never silently choose its first episode for playback.
- Existing single-video works keep direct play, direct folder opening, and the current archive layout.
- Keep the legacy runtime columns in `movies` for schema compatibility; `movie_episodes` is authoritative for video runtime after migration.
- Do not commit, push, merge, tag, or force-update a branch without a separate explicit user authorization for that GitHub action.
- Target version is exactly `0.4.3.1.1`; release archive is `本地资源终端_v0.4.3.1.1.zip` and excludes `.git`, `.venv`, caches, test caches, build output, and runtime data.

## Task 1: Episode identity parser and folder-level discovery

**Files:**

- Create: `app/services/episode_parser.py`
- Modify: `app/models/scan.py`
- Modify: `app/services/discovery_service.py`
- Modify: `tests/test_discovery_service.py`
- Create: `tests/test_episode_parser.py`

**Interfaces:**

```python
@dataclass(slots=True, frozen=True)
class EpisodeIdentity:
    season_number: int | None
    episode_number: int | None
    reliable: bool

parse_episode_identity(stem: str) -> EpisodeIdentity
natural_name_key(name: str) -> tuple[object, ...]

@dataclass(slots=True, frozen=True)
class EpisodeCandidate:
    video_path: Path
    source_name: str
    display_order: int
    episode_number: int | None
    season_number: int | None
    subtitle_paths: tuple[Path, ...] = ()

@dataclass(slots=True, frozen=True)
class MovieCandidate:
    folder: Path
    cover_key: str
    inferred_code: str
    episodes: tuple[EpisodeCandidate, ...]
```

**Steps:**

- [ ] Add literal parser cases for `01`, `作品_02`, `作品-E03`, `作品 EP04`, `S01E05`, mixed-case markers, unrelated embedded digits, duplicate parsed numbers, and natural ordering of `1`, `2`, `10`.
- [ ] Run `pytest -q tests/test_episode_parser.py`; confirm failure because the parser module does not exist.
- [ ] Implement anchored, case-insensitive parsing in the declared priority order. Treat unrelated embedded digits as unparsed. Use natural name ordering whenever identities conflict or cannot be parsed uniquely.
- [ ] Run the parser tests to green.
- [ ] Change discovery tests so a folder with three videos yields one `MovieCandidate` with three ordered `EpisodeCandidate` children, while recursion still stops at the first video-bearing folder and subtitle matching remains per video.
- [ ] Run `pytest -q tests/test_discovery_service.py`; confirm the old one-candidate-per-video assertions fail.
- [ ] Implement folder grouping, folder-name `cover_key`/`inferred_code`, deterministic `display_order`, and tuple-valued child candidates.
- [ ] Run `pytest -q tests/test_episode_parser.py tests/test_discovery_service.py`.

## Task 2: Domain model and JSON schema v2 migration

**Files:**

- Modify: `app/models/movie.py`
- Modify: `app/models/__init__.py`
- Modify: `app/services/metadata_service.py`
- Modify: `app/config/data_dirs.py`
- Modify: `tests/test_movie_models.py`
- Modify: `tests/test_metadata_service.py`
- Modify: `tests/test_data_layout_migration.py`

**Interfaces:**

```python
def legacy_episode_uuid(movie_uuid: str) -> str: ...

@dataclass(slots=True)
class MovieEpisodeMetadata:
    uuid: str
    display_order: int
    episode_number: int | None = None
    season_number: int | None = None
    source_name: str = ""

@dataclass(slots=True)
class MovieEpisodeRuntime:
    video_path: str | None = None
    library_id: str | None = None
    availability_status: str = "offline"
    subtitle_status: bool = False
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    file_size: int | None = None
    last_scanned_at: datetime | None = None

@dataclass(slots=True)
class MovieEpisodeRecord:
    metadata: MovieEpisodeMetadata
    runtime: MovieEpisodeRuntime

@dataclass(slots=True)
class MovieRecord:
    metadata: MovieMetadata
    runtime: MovieRuntime
    episodes: list[MovieEpisodeRecord] = field(default_factory=list)

    single_episode() -> MovieEpisodeRecord | None
    episode(episode_uuid: str) -> MovieEpisodeRecord | None
    playable_episodes() -> list[MovieEpisodeRecord]
```

**Steps:**

- [ ] Add model tests proving episode ordering normalization, one-episode compatibility, multi-episode refusal to expose a single implicit video, and work availability aggregation.
- [ ] Run `pytest -q tests/test_movie_models.py`; confirm failures against the old two-dataclass model.
- [ ] Add episode dataclasses, deterministic UUID5 helper with a fixed namespace string, `MovieMetadata.episodes`, and explicit `MovieRecord` lookup/playability helpers.
- [ ] Run model tests to green.
- [ ] Add metadata tests with a hand-written schema-v1 payload containing edited fields, playback history, folder assignment, and timestamps; assert the exact deterministic legacy episode UUID and a schema-v2 save payload. Add a v2 round-trip test with multiple episodes.
- [ ] Run `pytest -q tests/test_metadata_service.py`; confirm failures because only schema 1 is accepted.
- [ ] Set `SCHEMA_VERSION = 2`, decode both v1 and v2, encode only v2, and resave a loaded v1 file once migrated. Accept schema 1 or 2 in `MovieMetadataMigrator` validation.
- [ ] Run `pytest -q tests/test_metadata_service.py tests/test_data_layout_migration.py tests/test_movie_models.py`.

## Task 3: SQLite schema 7 and repository episode persistence

**Files:**

- Modify: `app/db/schema.sql`
- Modify: `app/db/database.py`
- Modify: `app/repositories/movie_repository.py`
- Modify: `tests/test_database_migrations.py`
- Modify: `tests/test_movie_repository.py`

**Table contract:**

```sql
CREATE TABLE movie_episodes (
    uuid TEXT PRIMARY KEY,
    movie_uuid TEXT NOT NULL REFERENCES movies(uuid) ON DELETE CASCADE,
    display_order INTEGER NOT NULL,
    episode_number INTEGER,
    season_number INTEGER,
    source_name TEXT NOT NULL DEFAULT '',
    video_path TEXT,
    library_id TEXT,
    availability_status TEXT NOT NULL DEFAULT 'offline',
    subtitle_status INTEGER NOT NULL DEFAULT 0,
    duration REAL,
    width INTEGER,
    height INTEGER,
    video_codec TEXT,
    audio_codec TEXT,
    file_size INTEGER,
    last_scanned_at TEXT
);
```

**Repository interfaces:**

```python
upsert_episode_runtime(
    self, movie_uuid: str, episode: MovieEpisodeMetadata, runtime: MovieEpisodeRuntime
) -> None
find_by_episode_video_path(self, normalized_path: str) -> list[MovieRecord]
mark_library_episodes_offline(
    self, library_id: str, except_episode_uuids: Sequence[str] = ()
) -> int
replace_work(
    self,
    movie: MovieMetadata,
    episode_runtimes: Mapping[str, MovieEpisodeRuntime],
    *,
    cover_path: str | None,
    duplicate_movie_uuids: Sequence[str] = (),
) -> None
```

**Steps:**

- [ ] Add a schema-v6 fixture containing one populated legacy `movies` runtime row and prove initialize upgrades to 7, creates all indexes, copies the row into a deterministic child episode, keeps the parent cover, and remains unchanged on a second initialize.
- [ ] Run `pytest -q tests/test_database_migrations.py`; confirm schema/version/table assertions fail.
- [ ] Add the table and indexes; migrate only rows that do not already have an episode; set `CURRENT_SCHEMA_VERSION = 7` only after migration statements succeed.
- [ ] Run database migration tests to green.
- [ ] Add repository tests for multi-episode round trips, work-level aggregated availability/subtitle/file size, path lookup through child rows, per-episode offline marking, search filters via `EXISTS`, cascade delete, archive rebuild with offline child rows, and atomic duplicate-parent replacement.
- [ ] Run `pytest -q tests/test_movie_repository.py`; confirm failures against parent runtime storage.
- [ ] Make `upsert_metadata` mirror episode metadata without destroying existing runtime values. Make `get` join ordered child rows and derive a parent `MovieRuntime`: mirror the child only for exactly one episode, return `video_path=None` for multiple episodes, keep parent `cover_path`, aggregate status/subtitle/file size, and never imply a multi-episode playback target.
- [ ] Move path/library/availability/subtitle search predicates and list-by-library behavior to `movie_episodes` `EXISTS` queries. Keep legacy `update_runtime` as a one-episode compatibility wrapper during migration.
- [ ] Run `pytest -q tests/test_database_migrations.py tests/test_movie_repository.py`.

## Task 4: Scanner reconciliation, rescan stability, and safe duplicate consolidation

**Files:**

- Modify: `app/services/scanner.py`
- Modify: `tests/test_scanner.py`
- Modify: `tests/test_acceptance_archive_lifecycle.py`

**Interfaces and invariants:**

- `_match_or_create_work(candidate)` resolves by any child path, then child identity/name, then offline folder `cover_key`, then offline folder code.
- `_reconcile_episodes(movie, candidate)` preserves matched child UUIDs, creates UUIDs only for new files, and returns ordered metadata plus runtime values.
- `_is_unedited_generated(movie)` checks every user-editable metadata field and all playback/folder fields against defaults.
- `_consolidate_generated_duplicates(parent, duplicates, candidate, runtimes)` only deletes redundant JSON after the parent JSON save and repository transaction have both succeeded; on failure, restore the previous parent JSON and retain all redundant files.

**Steps:**

- [ ] Replace per-video tests with one-folder/three-video acceptance tests. Assert one work, folder key cover lookup, three unique children, exact play order, and one new count.
- [ ] Add rescan tests proving no duplicate work/children, renaming by equivalent episode identity preserves UUID where unique, removing one file marks only that child offline, and a probe failure retains the child path while other episodes persist.
- [ ] Add consolidation tests for three untouched v0.4.3.1.0 duplicates, preferred parent selection, full rollback on repository failure, and ambiguity when any duplicate has edited metadata.
- [ ] Run `pytest -q tests/test_scanner.py tests/test_acceptance_archive_lifecycle.py`; confirm failures because scanner still iterates individual candidates.
- [ ] Rework scan to process work candidates, probe children independently, resolve the cover once using the first available video, upsert all children transactionally, and mark unseen child UUIDs offline after each library.
- [ ] Implement conservative duplicate consolidation and ambiguity reporting exactly as specified.
- [ ] Run `pytest -q tests/test_scanner.py tests/test_acceptance_archive_lifecycle.py`.

## Task 5: Catalog operations, cover tool keys, and episode-specific playback contract

**Files:**

- Modify: `app/services/catalog_service.py`
- Modify: `app/ui/giga_cover_dialog.py`
- Modify: `tests/test_catalog_service.py`
- Modify: `tests/test_giga_cover_dialog.py`
- Modify: `tests/test_viewing_service.py`

**Interfaces:**

```python
@dataclass(slots=True, frozen=True)
class DeletedArchive:
    video_paths: tuple[str, ...]
    cover_path: str | None

relink_episode(self, movie_uuid: str, episode_uuid: str, path: Path) -> MovieRecord
episode_for_playback(self, movie_uuid: str, episode_uuid: str | None = None) -> MovieEpisodeRecord
```

**Steps:**

- [ ] Add tests proving metadata edits preserve episodes; single relink remains compatible; multi relink requires a child UUID; cover refresh uses the first available child only as a cover fallback; delete reports every path without deleting media; play selection rejects missing, offline, and ambiguous targets.
- [ ] Run `pytest -q tests/test_catalog_service.py`; confirm the new behaviors fail.
- [ ] Implement episode-preserving metadata updates, explicit child relink/play selection, aggregate cover refresh, and multi-path deletion result.
- [ ] Add cover-tool candidate tests containing the folder/work key, code, title, source filenames, and stems with case-insensitive de-duplication. Preserve the single-Front copy regression test.
- [ ] Run `pytest -q tests/test_giga_cover_dialog.py`; confirm source-file candidate assertions fail, then update `_movie_keys` to use all episodes.
- [ ] Keep `ViewingService` statistics keyed by work UUID; add/adjust tests showing playback of different episode UUIDs increments only the parent work statistics.
- [ ] Run `pytest -q tests/test_catalog_service.py tests/test_giga_cover_dialog.py tests/test_viewing_service.py`.

## Task 6: Archive page episode controls and compact details dialog

**Files:**

- Create: `app/ui/movie_episode_dialog.py`
- Modify: `app/ui/movie_archive_page.py`
- Modify: `app/ui/flat_icons.py`
- Modify: `app/ui/flat_theme.py`
- Modify: `tests/test_movie_archive_page_v0419.py`
- Create: `tests/test_movie_episode_ui.py`

**Signals:**

```python
episode_play_requested = Signal(str, str)       # movie UUID, episode UUID
episode_relink_requested = Signal(str, str)     # movie UUID, episode UUID
episode_folder_requested = Signal(str, str)     # movie UUID, episode UUID
```

**Steps:**

- [ ] Add Qt tests for one child hiding the episode area and keeping the existing primary play button/media card; three children showing only `第 1 集`… buttons plus one icon-only details button; offline child disabled; click emits exact work/child IDs.
- [ ] Add dialog tests for ordered technical details and explicit per-child folder/relink signals. Assert the details control has empty text, an `info` icon, and tooltip `剧集详情`.
- [ ] Run `pytest -q tests/test_movie_archive_page_v0419.py tests/test_movie_episode_ui.py`; confirm missing widgets/signals fail.
- [ ] Add an `info` glyph to `flat_icon`, a compact episodes card to `MovieArchivePage`, and a details dialog that keeps file name/path/technical parameters out of the main archive page.
- [ ] Ensure multi-episode works hide/disable ambiguous parent play/relink/media actions while single works render exactly as before.
- [ ] Run the focused UI tests under `QT_QPA_PLATFORM=offscreen`.

## Task 7: Main-window right-click submenu and explicit episode actions

**Files:**

- Modify: `app/ui/main_window.py`
- Modify: `tests/test_main_window.py`
- Modify: `tests/test_main_window_source_regression.py`

**Steps:**

- [ ] Add behavior tests that double-click still opens the archive; a single work context menu contains a direct enabled Play action; a multi work contains a Play submenu ordered by display order with offline entries disabled; triggering an entry launches that exact file.
- [ ] Add tests that archive episode signals route to episode playback/folder/relink, and that invoking parent playback for a multi work produces a clear selection message rather than launching the first child.
- [ ] Run `QT_QPA_PLATFORM=offscreen pytest -q tests/test_main_window.py tests/test_main_window_source_regression.py`; confirm failures against the direct parent-runtime handlers.
- [ ] Implement `_play_episode(movie_uuid, episode_uuid)`, `_open_episode_folder(movie_uuid, episode_uuid)`, `_relink_movie_episode(movie_uuid, episode_uuid)`, submenu construction, and signal wiring. Keep work-level `ViewingService.start_playback(movie_uuid, handle)`.
- [ ] Refresh the visible archive after launch or relink without navigating away.
- [ ] Run the focused main-window tests.

## Task 8: Compatibility pass and version v0.4.3.1.1

**Files:**

- Modify: `pyproject.toml`
- Modify: `app/ui/main_window.py`
- Modify: `app/ui/app_chrome.py`
- Modify: all historical tests that intentionally assert the currently shipped visible version
- Create: `tests/test_release_v04311.py`
- Modify: any tests constructing `MovieMetadata`, `MovieRecord`, `MovieCandidate`, or direct database rows that break only because the public interfaces intentionally changed

**Steps:**

- [ ] Add a release test asserting the exact package version, window title, and chrome label are all `0.4.3.1.1`/`v0.4.3.1.1`.
- [ ] Run `pytest -q tests/test_release_v04311.py`; confirm failure against `0.4.3.0.3`.
- [ ] Update all three production version surfaces and mechanically update obsolete historical version assertions so they continue to assert the current visible release, not an abandoned intermediate value.
- [ ] Run `rg -n '0\.4\.3\.0\.3|0\.4\.3\.1\.0' app pyproject.toml tests` and require no stale shipped-version expectations.
- [ ] Run `python -m compileall -q app` and the full `QT_QPA_PLATFORM=offscreen pytest -q` suite. Fix compatibility regressions through additional failing tests before production changes.

## Task 9: Release verification and source archive

**Files:**

- Create: `docs/development-logs/开发交接日志_2026-08-21_v0.4.3.1.1.md`
- Create outside repository: `本地资源终端_v0.4.3.1.1.zip`

**Steps:**

- [ ] Write the development log with the final data model, migration rules, changed files, test evidence, known limitations, and exact next starting point.
- [ ] Re-read every requirement in the design spec and record a requirement-to-test checklist in the development log.
- [ ] Run `git diff --check`, `python -m compileall -q app`, and `QT_QPA_PLATFORM=offscreen pytest -q` fresh; record exact command outputs and test count.
- [ ] Inspect `git status --short`, `git diff --stat`, and the full diff for accidental generated files, credentials, paths, media, or unrelated edits.
- [ ] Build the zip from the reviewed tracked-source set plus intended uncommitted release files, excluding `.git`, `.venv`, `__pycache__`, `.pytest_cache`, caches, databases, logs, covers, media, build, and dist.
- [ ] List the archive contents and extract it into a temporary directory; run `python -m compileall -q app` and the full offscreen pytest suite from the extracted copy.
- [ ] Present the source archive and the exact verification result. If the user wants the branch committed/pushed/merged or `main` force-updated, request explicit authorization for those separate GitHub writes at that time.

## Plan Self-Review

- [ ] No task uses a child filename as the default work cover key.
- [ ] No multi-episode path can reach playback without an explicit child UUID.
- [ ] JSON v1 and SQLite v6 use the same deterministic legacy child UUID.
- [ ] Offline reconciliation operates on child UUIDs, not work UUIDs.
- [ ] Duplicate consolidation has a conservative edited-data gate and rollback behavior.
- [ ] Single-video compatibility is covered at model, repository, catalog, and UI levels.
- [ ] Main archive UI contains only episode labels and an icon-only details entry for multi works.
- [ ] Cover-tool source names and single-Front behavior have regression coverage.
- [ ] Version changes include package metadata, title bar, chrome, tests, log, and archive name.
- [ ] No `TODO`, `TBD`, placeholder interface, or unspecified test command remains in this plan.
