# Cover Processing Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make cover processing color-independent, remember the last source directory and margin, and rename the visible tool to “封面处理”.

**Architecture:** Keep the existing PIL batch-processing service and Qt dialog boundaries. Replace dark-spine detection with vertical edge-pair detection plus Front aspect-ratio validation. Persist tool preferences through the existing `AppSettings`/`SettingsStore` flow.

**Tech Stack:** Python 3.11+, Pillow, PySide6 Widgets, pytest

## Global Constraints

- Do not modify movie metadata/database schemas.
- Do not modify poster-wall layout in this change.
- Never overwrite source cover images.
- Existing settings files must load without migration errors.
- Automatic processing must fail safe to “review” when confidence is insufficient.

---

### Task 1: Persist cover-tool preferences

**Files:**
- Modify: `app/config/settings.py`
- Modify: `app/bootstrap.py`
- Modify: `app/ui/main_window.py`
- Test: `tests/test_settings.py`
- Test: `tests/test_ui_behavior_source.py`

**Interfaces:**
- Produces: `AppSettings.cover_tool_source_dir: Path | None`, `AppSettings.cover_tool_margin_px: int`
- Produces: `MainWindow.cover_tool_state_changed(str, int)`

- [ ] Add failing tests for loading defaults, save/load round-trip, and source-level wiring.
- [ ] Run targeted tests and verify failure.
- [ ] Add the two settings fields, sanitize margin to 0..50, and save them to JSON.
- [ ] Pass saved values into the cover dialog and persist values after the dialog closes.
- [ ] Run targeted tests and verify pass.

### Task 2: Replace dark-spine detection with structural boundary detection

**Files:**
- Modify: `app/services/giga_cover_cropper.py`
- Test: `tests/test_giga_cover_cropper.py`

**Interfaces:**
- Consumes: existing `inspect_file`, `scan_directory` APIs.
- Produces: color-independent `spine_left`, `spine_right`, and `crop_box` values.

- [ ] Add failing tests for green, red, and patterned Spine samples.
- [ ] Add a failing test proving a wide image without reliable boundaries remains `review`.
- [ ] Run targeted tests and verify failure.
- [ ] Implement RGB vertical-edge scoring and symmetric edge-pair selection near the center.
- [ ] Compute a median Front aspect ratio from existing output covers and use it as a scoring/validation signal.
- [ ] Keep conservative fallbacks and return `review` on low confidence.
- [ ] Run targeted tests and verify pass.

### Task 3: Rename and update the cover-processing dialog

**Files:**
- Modify: `app/ui/giga_cover_dialog.py`
- Test: `tests/test_giga_cover_dialog.py`
- Test: `tests/test_ui_behavior_source.py`

**Interfaces:**
- Consumes: saved source path and margin passed by `MainWindow`.
- Produces: current source path and margin after the dialog closes.

- [ ] Add failing UI/source tests for “封面处理”, remembered values, and color-neutral help text.
- [ ] Run tests and verify failure/skip behavior as appropriate for PySide6 availability.
- [ ] Update title, explanatory copy, browse text, and initial values.
- [ ] Run tests and verify pass/skip behavior.

### Task 4: Regression verification and packaging

**Files:**
- Modify: `README.md`
- Create: release ZIP and patch ZIP in `/mnt/data`

**Interfaces:**
- Produces: full v0.2.3 package and v0.2.3 patch package.

- [ ] Run the full pytest suite.
- [ ] Compile all Python sources with Python 3.11-compatible syntax.
- [ ] Create a patch containing only changed runtime files.
- [ ] Overlay the patch on a clean v0.2.2 copy and re-run source compilation/tests.
- [ ] Create and integrity-test the full ZIP and patch ZIP.
