# Game Cover Crop Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal “裁剪导入…” action to the Game Archive cover row that reuses the existing manual Front crop dialog and feeds its result into the existing game cover import flow.

**Architecture:** Keep the durable game asset pipeline unchanged. `GameDetailDialog` owns temporary crop outputs while the archive window is open; `ManualCoverCropDialog` writes a cropped Front into a unique temporary subdirectory, and the existing save path consumes that temporary file through `cover_source` and `GameAssetService.import_cover()`.

**Tech Stack:** Python 3.11+, PySide6 Widgets, Pillow, pytest.

## Global Constraints

- No database or JSON schema changes.
- No new dependencies.
- No batch game-cover tool or directory scanning.
- Never modify the selected original image.
- Keep existing Browse and Clear cover actions unchanged.
- Version is `0.3.4.5`.
- This project has no Git repository; use the isolated copied workspace and omit commit steps.

---

### Task 1: Game Archive crop-import entry and temporary output lifecycle

**Files:**
- Modify: `app/ui/game_detail.py`
- Test: `tests/test_game_ui_source.py`

**Interfaces:**
- Consumes: `ManualCoverCropDialog(source_path, output_dir, cropper, parent=...)` and its `saved_candidate.output_path`.
- Produces: existing `GameArchiveEditResult.cover_source: Path | None` populated with the cropped temporary Front path.

- [ ] **Step 1: Write the failing source regression test**

Add a test asserting that `game_detail.py` contains the “裁剪导入…” button path, imports `ManualCoverCropDialog` and `GigaCoverCropper`, implements `_crop_cover`, and passes `_crop_cover` only on the static cover row.

- [ ] **Step 2: Run the targeted test and verify RED**

Run: `python -m pytest tests/test_game_ui_source.py::test_game_archive_can_crop_import_cover_with_existing_manual_cropper -q`

Expected: FAIL because the crop-import wiring does not exist yet.

- [ ] **Step 3: Implement minimal UI and temp-file lifecycle**

In `GameDetailDialog`:

- import `TemporaryDirectory`, `GigaCoverCropper`, and `ManualCoverCropDialog`;
- keep a list of temporary directories alive while unsaved cropped covers may be referenced;
- extend `_path_row` with an optional crop callback and place “裁剪导入…” between Browse and Clear;
- add `_crop_cover()` that chooses JPG/JPEG/PNG/WebP, creates a unique temporary output directory, opens `ManualCoverCropDialog`, and on success assigns `saved_candidate.output_path` to `_cover_source`, clears `_remove_cover`, and displays a pending-crop label in `cover_edit`;
- cancel/error must not disturb the previous pending cover;
- after successful archive save (`set_record`), clean temporary crop directories because the durable asset has already been imported.

- [ ] **Step 4: Run targeted tests and verify GREEN**

Run: `python -m pytest tests/test_game_ui_source.py tests/test_giga_cover_cropper.py tests/test_game_asset_service.py -q`

Expected: all tests pass except environment-dependent Qt skips if applicable.

---

### Task 2: Version/docs and full verification

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Create: `升级说明_v0.3.4.5.txt`

**Interfaces:**
- No runtime interface changes beyond Task 1.

- [ ] **Step 1: Update version and release notes**

Set project version to `0.3.4.5`; document that this patch only adds single-game cover crop import and reuses the existing manual Front cropper.

- [ ] **Step 2: Run full regression suite**

Run: `python -m pytest -q`

Expected: zero failures.

- [ ] **Step 3: Run Python compatibility and compile verification**

Run: `python -m pytest tests/test_python_compatibility.py -q`

Run: `python -m compileall -q app tests`

Expected: both commands exit 0.

- [ ] **Step 4: Build clean overlay and full ZIP artifacts and verify integrity**

Create a patch ZIP containing only changed/new release files and a full ZIP excluding `__pycache__`, `.pytest_cache`, and `*.pyc`. Extract/overlay the patch onto a clean v0.3.4.4 copy, run full pytest there, and run `unzip -t` on both archives.
