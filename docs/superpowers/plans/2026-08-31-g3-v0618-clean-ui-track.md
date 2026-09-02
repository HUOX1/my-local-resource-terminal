# G3 v0.6.1.8 Clean UI / Four-Slot Track Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Rebuild the Games browse shell around a four-slot directional track, hide persistent UI chrome, add a right-edge icon drawer, and separate default start section from last-session state.

**Architecture:** Replace relative wrap positioning with slot-role assignment and explicit directional spawn/exit behavior inside `game_carousel.gd`. Keep existing Godot/Python boundaries; add a focused navigation drawer control and persist `default_start_section` through the existing settings service. Browser/presentation state remains local to Godot while user settings remain in Python Core.

**Tech Stack:** Godot 4.7.2 GDScript, Python 3.11, SQLite/settings JSON, localhost WebSocket protocol v1, pytest.

**Spec:** `docs/superpowers/specs/2026-08-31-g3-games-clean-ui-track-design.md`

## Global Constraints

- Games browse renders at most 4 visible boxes; selected box is visual slot 2.
- Browse mode hides persistent title/status/help chrome.
- Focus mode background boxes are visual-only and non-interactive.
- Default start section is independent of last active top-level section.
- Last selected game remains restorable.
- Existing launcher/core/protocol boundaries stay intact.

---

### Task 1: Directional four-slot carousel

**Files:**
- Modify: `g3_frontend/scripts/game_carousel.gd`
- Test: `g3_tests/test_g3_v0618_clean_ui_track.py`

**Interfaces:**
- Consumes: `set_games(Array[Dictionary])`, `select_relative(int)`, `set_preview_mode(bool)`
- Produces: four slot-role constants, directional spawn/exit layout, no cross-screen wrap reuse

- [x] Write tests that require four visible slots, selected slot 2, explicit offscreen left/right positions, and preview hit testing limited to selected box.
- [x] Run the tests and verify RED against v0.6.1.7.
- [x] Implement slot roles and directional transition bookkeeping without changing the public carousel signals.
- [x] Run focused tests and verify GREEN.

### Task 2: Browse/focus composition and hidden chrome

**Files:**
- Modify: `g3_frontend/scripts/main.gd`
- Modify: `g3_frontend/scripts/preview_panel.gd`
- Test: `g3_tests/test_g3_v0618_clean_ui_track.py`

**Interfaces:**
- Produces: browse caption hidden, focus content positioned with breathing room, top/right/bottom persistent chrome hidden outside System.

- [x] Add failing assertions for hidden browse caption, focus-only details, and System-only diagnostics/help.
- [x] Verify RED.
- [x] Implement UI visibility state helpers and move help/status content into System.
- [x] Verify GREEN.

### Task 3: Right-bottom icon navigation drawer

**Files:**
- Create: `g3_frontend/scripts/navigation_drawer.gd`
- Modify: `g3_frontend/scripts/main.gd`
- Test: `g3_tests/test_g3_v0618_clean_ui_track.py`

**Interfaces:**
- Produces signal `section_requested(section_id: String)` and `set_active_section(section_id: String)`.

- [x] Add failing tests for content/system groups, edge-reveal behavior, icon-only buttons, and hover animation constants.
- [x] Verify RED.
- [x] Implement the drawer control and connect it to `_set_section`.
- [x] Verify GREEN.

### Task 4: Default start section setting

**Files:**
- Modify: `g3_core/settings.py`
- Modify: `g3_core/backend_app.py`
- Modify: `g3_frontend/scripts/main.gd`
- Test: `g3_tests/test_settings_theme.py`
- Test: `g3_tests/test_g3_v0618_clean_ui_track.py`

**Interfaces:**
- Setting key: `default_start_section: str`
- Allowed: `games`, `movies`, `comics`, `music`, `search`, `system`
- Default: `games`

- [x] Add failing Python and GDScript contract tests for the new setting and for ignoring last top-level section at startup.
- [x] Verify RED.
- [x] Add settings normalization/default and a System UI selector; startup applies this setting before restoring selected game.
- [x] Verify GREEN.

### Task 5: Background/value hierarchy and docs/release

**Files:**
- Modify: `g3_frontend/shaders/ambient.gdshader`
- Modify: `g3_frontend/themes/classic_cyan/theme.json`
- Modify: `g3_core/__init__.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Create: `PATCH_NOTES_v0.6.1.8.md`
- Create: `docs/v0.6/G3_Handoff_v0.6.1.8.md`
- Modify: `docs/v0.6/Phase1_Feature_Status.md`
- Modify: `docs/development-logs/G3_v0.6_Development.md`

- [x] Add/update contract tests for v0.6.1.8 and darker Classic Cyan browse background.
- [x] Verify RED where applicable.
- [x] Implement theme/shader values and release docs, including this implementation checklist for future handoff.
- [x] Run full pytest, protocol smoke, compileall, static GDScript hazard checks, ZIP integrity, then package patch/full ZIPs.
