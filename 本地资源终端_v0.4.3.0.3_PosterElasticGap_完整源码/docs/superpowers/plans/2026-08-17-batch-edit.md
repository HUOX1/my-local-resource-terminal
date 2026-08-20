# Batch Edit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-select batch editing for tags, studio, series, favorite state, and watched state without adding new main-window buttons.

**Architecture:** Extend `CatalogService` with rollback-capable batch metadata operations so JSON archives and SQLite stay aligned. Update the existing grid/table selection modes and context menu to surface batch actions only when multiple movies are selected. Keep single-selection behavior unchanged.

**Tech Stack:** Python 3.11+, PySide6 6.x, SQLite, JSON metadata, pytest.

## Global Constraints

- Do not add main-window toolbar buttons.
- Preserve existing single-item right-click behavior.
- Ctrl-click and Shift-click must work in both poster and table views.
- Studio/series batch edits overwrite existing values after confirmation.
- Batch tag add/remove is case-insensitive and de-duplicated.
- Batch failures must raise an error and roll back already-modified archives/database rows.
- No new runtime dependency.

---

### Task 1: Batch metadata service

**Files:**
- Modify: `app/services/catalog_service.py`
- Test: `tests/test_catalog_service.py`

**Interfaces:**
- Produces: `CatalogService.batch_update_metadata(uuids: list[str], patch: MovieMetadataPatch) -> list[MovieRecord]`
- Produces: `CatalogService.batch_update_tags(uuids: list[str], tags: list[str], *, remove: bool = False) -> list[MovieRecord]`

- [ ] Write failing tests covering overwrite fields, tag add/remove, and rollback.
- [ ] Run targeted tests and confirm they fail because the batch APIs are absent.
- [ ] Implement batch helpers by snapshotting original metadata, applying updates, and restoring all originals if any update fails.
- [ ] Run targeted tests and confirm they pass.

### Task 2: Multi-selection and batch context menu

**Files:**
- Modify: `app/ui/main_window.py`
- Test: `tests/test_main_window_source_regression.py`
- Create: `tests/test_batch_edit_helpers.py`

**Interfaces:**
- Consumes: batch APIs from Task 1.
- Produces: helper parsing for comma/Chinese punctuation separated tags and multi-selection context actions.

- [ ] Write failing source/helper tests for `ExtendedSelection`, batch submenu labels, and tag parsing.
- [ ] Run targeted tests and confirm failure.
- [ ] Implement grid/table extended selection, selected-record collection, confirmation prompts, and batch action handlers.
- [ ] Keep single-selection context menu unchanged.
- [ ] Run targeted tests and confirm pass.

### Task 3: Version, regression, and packaging

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`

**Interfaces:**
- Produces: v0.2.6 patch package and full package.

- [ ] Bump version to 0.2.6 and document batch edit behavior.
- [ ] Run the full pytest suite.
- [ ] Compile all Python sources with Python 3.11-compatible syntax checks.
- [ ] Build patch from v0.2.5 and a clean full ZIP, then validate both ZIP archives.
