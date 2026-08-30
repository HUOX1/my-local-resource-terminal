# G3 Games Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current v0.6 technical checkpoint into the first usable G3 Games vertical slice with G3 naming, real 3D-case asset loading, discoverable game actions, and launch profiles that cover direct executables, launcher/mod chains, and emulators.

**Architecture:** Python remains the local Core/supervisor and Godot remains the GPU frontend. G3 introduces a launch-profile model in Python and a reusable GLB case scene in Godot; the frontend keeps only a small carousel window instantiated. The current clean v0.6 data is intentionally reset into `%LOCALAPPDATA%\G3` rather than migrated.

**Tech Stack:** Python 3.11+, SQLite, websockets, Godot 4.7.2, GDScript, glTF/GLB.

**Spec:** `docs/v0.6/G3_Games_Vertical_Slice_Design.md`

## Global Constraints

- Windows-only for this milestone.
- Keep `run_windows.vbs` as the user-visible launcher.
- Bind backend WebSocket only to `127.0.0.1`.
- Do not import v0.5 `app.*` runtime code.
- `Classic Cyan` is the default theme.
- User-visible feature status text is Chinese.
- Real game cases must use true 3D geometry/GLB pipeline, not a final 2D card.

---

### Task 1: Rename runtime namespace to G3

**Files:** Rename `g3_core/` → `g3_core/`, `g3_launcher/` → `g3_launcher/`, `g3_frontend/` → `g3_frontend/`; modify `run_windows.vbs`, `run_windows_debug.bat`, `setup_windows.bat`, `pyproject.toml`, tests, and all Python/Godot paths.

**Interfaces:** `python -m g3_launcher`; data root `%LOCALAPPDATA%\G3`.

- [ ] Write failing tests asserting no runtime directories/modules named `terminal_*` or `g3_frontend` remain, launcher imports `g3_launcher`, and `TerminalPaths.from_environment().root == LOCALAPPDATA / "G3"`.
- [ ] Run the rename tests and verify RED.
- [ ] Rename directories and update imports/resources/package discovery.
- [ ] Rename runtime log to `g3.log`; default project/window title to `G3`.
- [ ] Run rename tests and packaging/editable-install checks; verify GREEN.

### Task 2: Add launch-profile data model and database

**Files:** Modify `g3_core/schema.sql`, `models.py`, `repository.py`, `backend_app.py`; create `g3_core/services/process_monitor.py`; add `g3_tests/test_launch_profiles.py`.

**Interfaces:** `LaunchProfile(profile_type, launch_exe, launch_args, working_directory, content_path, monitor_exe, wait_timeout_s, run_as_admin)`; backend commands `game.launch_profile.get/update`.

- [ ] Write failing repository round-trip tests for direct/launcher/emulator profiles.
- [ ] Add launch-profile columns to the new clean G3 schema and typed dataclass validation.
- [ ] Add repository get/update methods.
- [ ] Add JSON protocol serialization and commands.
- [ ] Verify invalid profile types, missing launch executable, negative timeout, and invalid paths are rejected.

### Task 3: Monitor the actual gameplay executable

**Files:** Modify `g3_core/services/game_runtime.py`; add `process_monitor.py`; modify backend launch events; add `g3_tests/test_game_session_monitor.py`.

**Interfaces:** launch starts `launch_exe`; session becomes active when `monitor_exe` is observed; session exits when `monitor_exe` disappears.

- [ ] Write failing tests with injected process-path snapshots for launcher→game transition.
- [ ] Implement Windows running-executable enumeration based on full normalized paths, conceptually reusing the proven v0.5 approach without importing old code.
- [ ] Direct profiles default `monitor_exe` to `launch_exe`.
- [ ] Launcher/emulator profiles wait up to `wait_timeout_s` for monitor process.
- [ ] Emit detailed `game.started`, `game.session_started`, `game.exited`, and timeout/error events.
- [ ] Keep launch diagnostics in console + `%LOCALAPPDATA%\G3\logs\g3.log`.

### Task 4: Real 3D GLB case pipeline

**Files:** Create `g3_frontend/assets/models/README.md`; create temporary `game_case_placeholder.glb` only if a final user model is not present; replace `scripts/game_case_3d.gd` with a loader/controller; modify carousel tests.

**Interfaces:** case controller loads `res://assets/models/game_case.glb` when present, otherwise a true-3D placeholder GLB; exposes `configure(game)`, `set_selected()`, `set_hover()`, `set_accent()`.

- [ ] Write failing structural tests requiring `.glb` loading and rejecting the old final BoxMesh/card construction path.
- [ ] Implement shared PackedScene/resource loading so the mesh is cached once.
- [ ] Bind cover texture to `cover_front` material slot when a cover exists.
- [ ] Keep only 7–11 carousel case instances alive around selection.
- [ ] Preserve subtle physical hover rotation but do not fake depth in 2D.

### Task 5: Move case unit to the approved left-side composition

**Files:** Modify `g3_frontend/scripts/game_carousel.gd`, `main.gd`; add `g3_tests/test_games_layout_g3.py`.

**Interfaces:** selected case visual anchor around x=22–26%, y=42–48% at 1600×900; case title/meta positioned from projected selected-case screen position.

- [ ] Write failing tests proving geometric screen center is not used as the browse anchor.
- [ ] Set 3D carousel anchor left and slightly upward relative to the previous checkpoint.
- [ ] Remove the duplicate module `title_label` entirely.
- [ ] Reposition title/meta every frame from `camera.unproject_position(selected_case_anchor)` with fixed vertical offsets.
- [ ] Verify Preview opening keeps case/title relationship stable.

### Task 6: Surface Preview and Manage actions

**Files:** Modify `g3_frontend/scripts/main.gd`, `game_carousel.gd`, `preview_panel.gd`; create `manage_menu.gd` and launch-profile dialog UI.

**Interfaces:** left single click Preview, double click Launch, right click Manage menu; Manage includes 启动/预览/编辑资料/媒体素材/启动设置/移除收藏.

- [ ] Write input-routing regressions for right-click and blank-click close.
- [ ] Add right-click case signal carrying item id.
- [ ] Add Manage popup and visible actions.
- [ ] Add Launch Settings editor for all LaunchProfile fields, with Browse buttons for launch exe/content/monitor exe.
- [ ] Save via `game.launch_profile.update` and refresh selection state.

### Task 7: Chinese feature map and G3 docs

**Files:** Replace `docs/v0.6/Phase1_Feature_Status.md` with Chinese G3 status; update development log; update SYSTEM status text.

- [ ] Write a Chinese status table distinguishing 已可用 / 待实机验收 / 仅入口 / 未实现.
- [ ] List direct EXE, Mod/launcher, PS1 emulator, and RPCS3 as the four acceptance samples.
- [ ] Document final GLB modeling/export contract.
- [ ] Rename future patch convention to `G3-v0.6.x-*.zip`.

### Task 8: Verification and packaging

**Files:** All changed files.

- [ ] Run full Python/Godot structural test suite.
- [ ] Run protocol smoke.
- [ ] Run `python -m compileall -q g3_core g3_launcher`.
- [ ] Run editable install against the renamed package.
- [ ] Verify source contains no runtime import/path references to `g3_core`, `g3_launcher`, or `g3_frontend` except historical docs.
- [ ] Build one root-level cumulative package named `G3-v0.6.1-Games-Vertical-Slice.zip`.
- [ ] Windows authoritative acceptance: launch UI, inspect real 3D case, configure all four sample launch profiles, Preview, launch/return, and verify session timing.
