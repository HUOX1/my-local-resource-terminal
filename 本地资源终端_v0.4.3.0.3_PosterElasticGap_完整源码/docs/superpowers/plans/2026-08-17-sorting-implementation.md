# Movie Sorting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent seven-field sorting with ascending/descending order to both poster and table views.

**Architecture:** Persist `added_at` with each archive, extend repository search with a validated sort key and direction, and expose sort controls in the main window. Persist sort preferences in `AppSettings` and update them through a dedicated main-window signal handled by bootstrap.

**Tech Stack:** Python 3.11+, PySide6 Widgets, SQLite, JSON, pytest

## Global Constraints
- Existing movie/video/archive behavior must not change.
- Old settings and metadata JSON files must remain readable.
- Default sort for upgraded installs is code ascending.
- Sort state must not require a rescan.

---

### Task 1: Persist archive added time
**Files:** `app/models/movie.py`, `app/services/metadata_service.py`, `app/db/schema.sql`, `app/db/database.py`, `app/repositories/movie_repository.py`, tests.
- [ ] Add failing tests for new archives, old metadata migration, DB migration/rebuild.
- [ ] Implement `added_at` and compatibility migration.
- [ ] Run focused tests.

### Task 2: Add repository sorting
**Files:** `app/repositories/movie_repository.py`, `app/services/catalog_service.py`, tests.
- [ ] Add failing tests for all sort keys and both directions.
- [ ] Implement validated sort key/direction.
- [ ] Run focused tests.

### Task 3: Persist sort preferences
**Files:** `app/config/settings.py`, `app/bootstrap.py`, tests.
- [ ] Add failing round-trip/default tests.
- [ ] Add `sort_key` and `sort_desc` with backward-compatible defaults.
- [ ] Add bootstrap persistence signal handler.

### Task 4: Add sort controls
**Files:** `app/ui/main_window.py`, tests.
- [ ] Add source/UI tests for selector, direction button, refresh, persistence signal.
- [ ] Implement controls and shared catalog ordering.
- [ ] Run focused and full test suite.

### Task 5: Package v0.2.4
- [ ] Compile all Python sources with Python 3.11-compatible syntax.
- [ ] Build patch and full ZIPs.
- [ ] Verify ZIP integrity.
