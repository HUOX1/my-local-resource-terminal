# Library UX / Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve poster-wall wheel feel, persist the user's runtime library UI state, and give movie posters a stronger but restrained archive-wall focus treatment.

**Architecture:** Keep business/domain code unchanged. Move mouse-wheel math into a tiny pure helper used by `PosterWallListView`; extend `AppSettings` with stable runtime UI fields and wire them in `bootstrap.py`; expose episode count through `MovieListModel` and render it in `MovieCardDelegate` without changing the movie archive/domain model.

**Tech Stack:** Python 3.11+, PySide6 Widgets, dataclasses, pytest.

**Spec:** `docs/superpowers/specs/2026-08-19-flat-pro-motion-foundation-design.md`, `docs/superpowers/specs/2026-08-21-movie-work-episodes-design.md`

## Global Constraints

- Do not change Movie/Game database or metadata schemas.
- Do not add QML or a new animation framework.
- Touchpad `pixelDelta()` scrolling remains native Qt behavior.
- Dynamic tag/library filters remain session-only; stable filters, selected collection folder, movie wall/list mode, and sidebar state persist.
- Movie poster additions must not decode covers on every paint beyond existing caches.

---

### Task 1: Target-based mouse wheel scrolling

**Files:**
- Create: `app/ui/poster_scroll.py`
- Modify: `app/ui/poster_view.py`
- Test: `tests/test_library_ux_persistence.py`

**Interfaces:**
- Produces: `accumulate_scroll_target(...) -> float`, `smooth_scroll_value(...) -> float`.
- `PosterWallListView` consumes both helpers from its existing 16 ms motion timer.

- [x] **Step 1: Write failing tests** for one-notch distance, accumulated wheel input, and non-overshooting convergence.
- [x] **Step 2: Run tests and confirm RED** because `poster_scroll.py` does not yet exist.
- [x] **Step 3: Implement the pure helpers and switch the view from velocity decay to a target position.**
- [x] **Step 4: Run tests and confirm GREEN.**

### Task 2: Runtime library UI persistence

**Files:**
- Modify: `app/config/settings.py`
- Modify: `app/bootstrap.py`
- Test: `tests/test_library_ux_persistence.py`

**Interfaces:**
- `AppSettings.movie_folder_id: str | None`
- `AppSettings.game_folder_id: str | None`
- `AppSettings.movie_view_mode: Literal["poster", "list"]`
- Existing `movie_filter`, `game_filter`, and `sidebar_width` continue to be used.

- [x] **Step 1: Write failing source-contract tests** for settings serialization and bootstrap wiring.
- [x] **Step 2: Run tests and confirm RED.**
- [x] **Step 3: Add fields with backward-compatible load defaults and atomic save output.**
- [x] **Step 4: Restore state after `MainWindow` construction, preserve it when Settings dialog is saved, and connect folder/view/sidebar runtime changes to atomic settings writes.**
- [x] **Step 5: Expand persisted movie filters to stable availability/subtitle filters while keeping dynamic library/tag filters session-only.**
- [x] **Step 6: Run tests and confirm GREEN.**

### Task 3: Movie archive-wall visual polish

**Files:**
- Modify: `app/ui/movie_models.py`
- Modify: `app/ui/movie_delegate.py`
- Test: `tests/test_library_ux_persistence.py`

**Interfaces:**
- Produces `MovieListModel.EpisodeCountRole`.
- Delegate consumes title, favorite, watched, availability, and episode count roles already carried by the list model.

- [x] **Step 1: Write failing source-contract test** for episode count role and restrained stronger hover treatment.
- [x] **Step 2: Run tests and confirm RED.**
- [x] **Step 3: Add episode count role without changing `MovieRecord`.**
- [x] **Step 4: Add 1.035 hover scale, 4 px lift, a small multi-episode pill, favorite marker, and hover-only bottom title veil.**
- [x] **Step 5: Run tests and syntax checks.**

### Task 4: Package and verify

**Files:**
- Create: `PATCH_NOTES.txt`
- Create: overwrite ZIP preserving repository-relative paths.

- [x] **Step 1: Run focused pytest.**
- [x] **Step 2: Run `compileall` on changed Python files (PySide6 import is not required for byte compilation).**
- [x] **Step 3: Inspect ZIP contents and checksums.**
