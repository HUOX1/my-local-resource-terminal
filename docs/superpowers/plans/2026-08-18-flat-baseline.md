# Flat Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 v0.3.4.7 主界面改造成现代深色扁平 Flat Baseline，同时保持第一阶段业务行为不回归。

**Architecture:** 新增集中主题 token/QSS 与轻量图标绘制模块；`MainWindow` 只调整布局和控件外观，继续复用现有模型、delegate、服务和信号。窗口保持标准 Windows frame，避免再次进入无边框/玻璃底层问题。

**Tech Stack:** Python 3.11+、PySide6 Widgets、Qt Fusion、现有 SQLite/JSON 体系。

**Spec:** `docs/superpowers/specs/2026-08-18-flat-baseline-design.md`

## Global Constraints

- 基线固定为 v0.3.4.7 第一阶段冻结版。
- 不改变影片/游戏 JSON、SQLite schema、Session、扫描、启动、备份恢复语义。
- 不新增第三方依赖。
- 不实现无边框、玻璃、透明或动画。
- 保留影片与游戏封面缓存。

---

### Task 1: Flat theme foundation

**Files:**
- Create: `app/ui/flat_theme.py`
- Modify: `app/bootstrap.py`
- Test: `tests/test_flat_baseline_source.py`

**Interfaces:**
- Produces: `FlatTokens`, `build_flat_stylesheet()`, `apply_flat_theme(app)`.

- [ ] Write source tests requiring centralized tokens and application-level theme setup.
- [ ] Run focused test and verify RED.
- [ ] Implement token class, palette/QSS, and apply it in `build_application()` after Fusion style selection.
- [ ] Run focused tests and compile.

### Task 2: Main shell layout

**Files:**
- Create: `app/ui/flat_icons.py`
- Modify: `app/ui/main_window.py`
- Modify: legacy shell tests to reflect the approved sidebar layout.

**Interfaces:**
- Preserve existing control attributes/signals: `movie_library_button`, `game_library_button`, `settings_button`, `search_edit`, `filter_combo`, `sort_combo`, `sort_direction_button`, `view_button`, `rescan_button`, `cover_tools_button`, `add_game_button`.

- [ ] Write/modify tests for sidebar + content toolbar while preserving all existing functional attributes.
- [ ] Run focused tests and verify RED.
- [ ] Build fixed sidebar, library heading/count row, toolbar, and content stack without changing business connections.
- [ ] Run shell and main-window tests.

### Task 3: Poster visual polish without behavior regression

**Files:**
- Modify: `app/ui/movie_delegate.py`
- Modify: `app/ui/game_delegate.py`
- Test: `tests/test_flat_baseline_source.py`

**Interfaces:**
- Preserve natural aspect ratio, poster-only display, cache dictionaries and GIF hover behavior.

- [ ] Add source tests for rounded clip and centralized token usage while keeping no-text expectations.
- [ ] Verify RED.
- [ ] Add rounded clipping plus subtle hover/selected outlines using cached pixmaps.
- [ ] Run poster performance/source tests.

### Task 4: Full regression and package

**Files:**
- Modify: `pyproject.toml` version to `0.4.0-flat1` only for this preview build.
- Create: preview notes.

- [ ] Run full pytest suite.
- [ ] Run `python -m compileall -q app tests`.
- [ ] Create ZIP from isolated workspace excluding caches.
- [ ] Verify ZIP integrity.
