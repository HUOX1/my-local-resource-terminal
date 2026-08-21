# Flat Pro Motion Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first Flat Pro motion layer while preserving business behavior and poster performance.

**Architecture:** Theme registry exposes a motion level. `PosterWallListView` owns hover/reflow/scroll motion state and delegates only consume motion values during paint. Page transitions live in a small UI motion helper so MainWindow does not duplicate animation plumbing.

**Tech Stack:** Python 3.11+, PySide6 Widgets, existing Flat Pro theme system.

**Spec:** `docs/superpowers/specs/2026-08-19-flat-pro-motion-foundation-design.md`

## Global Constraints

- Motion is Flat Pro only in this release.
- Do not change Stage 1 data/business behavior.
- Do not change database schema or backup format.
- Do not invalidate poster image caches on animation frames.
- Do not add sidebar animation yet.

---

### Task 1: Motion theme profile
- [ ] Add failing tests for theme-owned motion level.
- [ ] Verify tests fail.
- [ ] Add `motion_level` to `ThemeSpec`, set Flat Pro to `full`, and expose it through `FlatTokens`.
- [ ] Verify tests pass.

### Task 2: Poster wall motion controller
- [ ] Add failing source/behavior tests for continuous inertial scrolling, hover progress, and reflow offsets.
- [ ] Verify tests fail.
- [ ] Implement one 16 ms motion timer in `PosterWallListView`, with velocity decay, hover interpolation, and settled-resize reflow offsets.
- [ ] Update Movie/Game delegates to consume hover progress and per-row reflow offsets without changing `sizeHint` or image caches.
- [ ] Verify tests pass.

### Task 3: Archive transitions
- [ ] Add failing tests for a shared stack-page transition helper and MainWindow usage.
- [ ] Verify tests fail.
- [ ] Implement short Flat Pro fade/slide transitions and use them only when changing pages.
- [ ] Verify tests pass.

### Task 4: Movie menu cleanup and release
- [ ] Add failing tests that Movie single/batch context menus no longer expose 收藏/已观看 and that version is 0.4.2.0.
- [ ] Verify tests fail.
- [ ] Remove the obsolete actions and bump visible/package version.
- [ ] Run the complete suite and `compileall`.
