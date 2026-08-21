# Library Switch Size Jitter Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent visible main-window height/size jitter when rapidly switching between movie and game libraries at a small runtime window size.

**Architecture:** Keep v0.3.3's runtime-only window-size behavior, but replace deferred post-switch resize with a synchronous temporary fixed-size guard around library reconfiguration. Restore the original min/max constraints immediately after switching so normal resizing remains available.

**Tech Stack:** Python 3.11+, PySide6 Widgets, pytest.

## Global Constraints

- Default startup size remains 1320×840.
- Do not persist window geometry or size in settings.
- Do not change Movie/Game data, timing, screenshot, detail, or edit behavior.
- No new dependencies.

---

### Task 1: Reproduce the deferred-resize regression in a source test

**Files:**
- Modify: `tests/test_main_window_source_regression.py`

**Interfaces:**
- Consumes: `app/ui/main_window.py`
- Produces: a regression test requiring synchronous size locking and rejecting deferred resize.

- [ ] **Step 1:** Change the existing runtime-size test to require `setFixedSize(runtime_size)`, restoration of prior min/max sizes, and absence of `_restore_runtime_size` / deferred `singleShot` resize.
- [ ] **Step 2:** Run the focused test and confirm it fails on v0.3.3 for the expected missing behavior.

### Task 2: Replace deferred resize with synchronous size guard

**Files:**
- Modify: `app/ui/main_window.py`

**Interfaces:**
- Produces: `switch_library()` that preserves runtime size without a visible intermediate resize.

- [ ] **Step 1:** Capture current size and current min/max constraints at method entry.
- [ ] **Step 2:** Call `setFixedSize(runtime_size)` before mutating library UI.
- [ ] **Step 3:** Execute the existing library switch in `try`.
- [ ] **Step 4:** Restore original min/max sizes in `finally` and remove `_restore_runtime_size()`.
- [ ] **Step 5:** Run focused test and confirm pass.

### Task 3: Regression verification and release packaging

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Create: `升级说明_v0.3.3.1.txt`

**Interfaces:**
- Produces: v0.3.3.1 patch ZIP and full ZIP.

- [ ] **Step 1:** Set release version to 0.3.3.1 and document the one bug fix.
- [ ] **Step 2:** Run full pytest, Python 3.11 compatibility, and compileall.
- [ ] **Step 3:** Overlay the patch onto a clean v0.3.3 full copy and run the v0.3.3 test suite.
- [ ] **Step 4:** Build patch/full ZIPs and run ZIP integrity checks.
