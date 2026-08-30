# G3 Games Vertical Slice — Design Addendum

## 1. Product Name

The v0.6 second-generation terminal is now provisionally named **G3**.

All new runtime/code/data naming must use G3:

- `g3_core` → `g3_core`
- `g3_launcher` → `g3_launcher`
- `g3_frontend` → `g3_frontend`
- `%LOCALAPPDATA%\LocalResourceTerminal\v0.6` → `%LOCALAPPDATA%\G3`
- Runtime log: `%LOCALAPPDATA%\G3\logs\g3.log`
- Patch/archive names: `G3-v0.6.x-*.zip`

No compatibility import/migration from the old v0.5 application is required. Current v0.6 test data may be discarded when the G3 data-root rename lands.

## 2. Games Browse Composition

The top XMB is the only module title. The second repeated `GAMES` label below the navigation is removed.

The selected game is presented as one visual unit:

```text
TOP XMB

      [selected 3D case]
          Game Title
       Platform · Time

                       large open region reserved for Preview
```

At 1600×900 reference resolution, the selected-case visual center should be approximately **x=22–26% / y=42–48%** of the viewport. It must never sit at the geometric center of the whole screen. Neighboring cases extend horizontally from this anchor.

When Preview opens, the case unit shifts only slightly left if needed. The title under the case fades out while the Preview's right-side title is visible, then fades back when Preview closes.

Clicking an empty Games-background region closes Preview. Clicking XMB, Preview content, or a case does not count as an empty-background click.

## 3. Real 3D Case Asset Pipeline

G3 stops using flat-card / faux-3D case presentation as the final design. Games use a real reusable **GLB/glTF 3D case model**.

The case model is a shared mesh resource; individual games change textures/material parameters, not geometry.

### Asset contract

Target file: `g3_frontend/assets/models/game_case.glb`

Recommended modeling constraints:

- Front-facing rectangular console/DVD-style case.
- Real depth, real spine, real rear face, and a slightly raised front cover plane/lip.
- Pivot/origin at the geometric center of the case.
- Local axes: +Y up, +X right, front face oriented toward +Z.
- Apply transforms before export: scale 1/1/1 and rotation 0/0/0.
- Approximate physical proportions: height 190 mm, width 135 mm, depth 15–18 mm. Exact unit scale is less important than consistent proportions.
- 500–2,000 triangles is preferred; hard-surface bevels should be modest.
- One UV set. Front-cover UV region must not overlap the spine/back if a single atlas is used.
- Preferred material slots:
  - `case_plastic`
  - `cover_front`
  - optional `case_spine`
- No baked lighting or baked shadows.
- Export as binary `.glb` from Blender using glTF 2.0.

G3 must keep only a small carousel working set alive (target 7–11 instances around the selection). Hundreds of library entries must not imply hundreds of rendered GLB instances.

Until the user-supplied final GLB exists, development may use a temporary low-poly **true 3D placeholder mesh** generated solely for pipeline testing. It must not revert to a 2D card implementation.

## 4. Games Interaction / Discoverability

Primary interactions:

- Single-click selected case: open Preview.
- Double-click selected case: Launch.
- Mouse wheel / left-right keys: move selection.
- Right-click selected case: open a small Manage menu.

Manage menu:

```text
启动
预览
编辑资料
媒体素材
启动设置
移除收藏
```

The visible UI must provide discoverable entries for capabilities already present in the backend. Hidden backend-only functionality does not count as usable product functionality.

## 5. Launch Profiles

A game is no longer modeled as one executable. G3 uses a **Launch Profile** with separate launch and runtime-monitor concepts.

Core fields:

```text
profile_type        direct | launcher | emulator
launch_exe          executable G3 starts
launch_args         command-line arguments
working_directory   process working directory
content_path        ROM/ISO/EBOOT/game content path when applicable
monitor_exe         executable whose presence means the game is actually running
wait_timeout_s      maximum time to wait for monitor_exe to appear
run_as_admin        Windows elevation request
```

The important rule inherited conceptually from the v0.5 prototype is:

> `launch_exe` starts the chain; `monitor_exe` represents the actual gameplay session.

Representative samples:

- Rain World: direct EXE → monitor same EXE.
- Elden Ring + Mod Engine: launch Mod Engine → monitor `eldenring.exe`.
- PS1 emulation: launch emulator with content argument → monitor emulator process.
- RPCS3 / PS3: launch RPCS3 with game/EBOOT argument → monitor RPCS3 process.

G3 must support all three without per-game hardcoded Python logic.

## 6. Theme / Language

`Classic Cyan` stays as the current default G3 theme.

The feature/status map and SYSTEM-facing development status are Chinese. Internal protocol names may remain English.

## 7. Current Scope

This pass focuses on making GAMES a complete vertical slice before expanding Movies/Comics/Music/Search. Other modules may remain slots while Games gains real 3D cases, visible Preview/Manage entry points, launch profiles, launch/return monitoring, and Chinese status documentation.
