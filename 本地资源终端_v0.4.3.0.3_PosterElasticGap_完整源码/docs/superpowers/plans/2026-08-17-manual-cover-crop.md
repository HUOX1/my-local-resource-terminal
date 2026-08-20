# Manual Cover Crop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a manual Front-cover crop fallback to the existing cover-processing workflow without changing automatic detection.

**Architecture:** Keep image crop/write logic in `GigaCoverCropper` so it remains testable without Qt. Add a dedicated PySide6 dialog that previews the original wrap and cropped Front, with one draggable vertical split line represented by a slider/spin control. Integrate the dialog into the existing cover-processing results table via double-click and context menu; saving writes to the configured central cover directory and leaves source images untouched.

**Tech Stack:** Python 3.11+, PySide6 6.x, Pillow 10+

## Global Constraints

- Do not modify the source cover image.
- Do not change automatic cover-detection behavior.
- Manual crop always keeps the image area to the right of the chosen X coordinate.
- Respect the current safety margin value; allow temporary adjustment in the manual dialog.
- Existing formal cover is not overwritten without confirmation.
- No new third-party dependency.

---

### Task 1: Manual crop service
**Files:** Modify `app/services/giga_cover_cropper.py`; Test `tests/test_giga_cover_cropper.py`
- [ ] Add failing tests for manual crop validation, source preservation, and overwrite behavior.
- [ ] Implement `manual_candidate(...)` / `process_manual(...)` using the existing image writer.
- [ ] Run focused tests and commit.

### Task 2: Manual crop dialog
**Files:** Create `app/ui/manual_cover_crop_dialog.py`; Test `tests/test_manual_cover_crop_dialog.py`
- [ ] Add source-level/Qt tests for crop position, margin, preview update hooks, and output path behavior.
- [ ] Build a dialog showing original image and Front preview with an adjustable vertical split position.
- [ ] Run focused tests and commit.

### Task 3: Cover-processing integration
**Files:** Modify `app/ui/giga_cover_dialog.py`; Test `tests/test_giga_cover_dialog.py`
- [ ] Add tests/source assertions for double-click and context-menu manual-crop entry points.
- [ ] Allow manual crop for any readable scan result, especially `review`.
- [ ] Refresh row/result status and invalidate cover index after a saved manual crop.
- [ ] Run focused tests and commit.

### Task 4: Version, regression, packaging
**Files:** Modify `pyproject.toml`, `README.md`; package patch and full v0.2.7 ZIPs.
- [ ] Bump version to 0.2.7 and document usage.
- [ ] Run full pytest suite and Python 3.11 compile check.
- [ ] Verify v0.2.6 + patch upgrade and ZIP integrity.
