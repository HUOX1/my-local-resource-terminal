# GIGA Cover Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe batch extraction of GIGA front covers from left-back / middle-spine / right-front full cover images.

**Architecture:** A Pillow-based service performs deterministic spine detection and cropping without Qt dependencies. A PySide6 dialog wraps the service for preview and batch execution, then invalidates the existing centralized cover index.

**Tech Stack:** Python 3.11+, Pillow, PySide6 Widgets, pytest.

## Global Constraints

- Preserve source images.
- Default to skip existing output covers.
- Front is always on the right for GIGA mode.
- Do not force a secondary aspect-ratio crop.
- Keep the existing centralized cover-directory matching convention.

---

### Task 1: Preserve latest ffprobe fix

**Files:** `app/services/media_probe.py`, `tests/test_media_probe.py`

- [ ] Add a UTF-8 non-ASCII filename regression test and verify RED.
- [ ] Decode ffprobe stdout bytes as UTF-8-SIG with replacement and verify GREEN.

### Task 2: GIGA cover crop service

**Files:** `app/services/giga_cover_cropper.py`, `tests/test_giga_cover_cropper.py`, `pyproject.toml`

- [ ] Add tests for detected spine, right-front extraction, single-cover skip, ambiguous-spine review, existing-output skip, and source preservation.
- [ ] Implement image scanning, spine detection, preview result statuses, and safe batch write.
- [ ] Add Pillow runtime dependency.

### Task 3: PySide6 batch dialog

**Files:** `app/ui/giga_cover_dialog.py`, `app/ui/main_window.py`, `tests/test_giga_cover_dialog.py`

- [ ] Add import/construction test guarded by pytest.importorskip("PySide6").
- [ ] Add source/output selection, margin, overwrite, preview table, and batch process actions.
- [ ] Add main-window “封面工具” entry and refresh cover index/catalog after processing.

### Task 4: Documentation and verification

**Files:** `README.md`

- [ ] Document GIGA batch workflow and safety behavior.
- [ ] Run full tests and compileall.
- [ ] Build a complete Windows ZIP that includes the prior ffprobe fix.
