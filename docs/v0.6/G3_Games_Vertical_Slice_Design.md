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

When Preview opens, the selected case leaves the far-left browse anchor and glides right into a dedicated focus anchor at roughly 28–30% of viewport width. The Preview begins on the right side, so case and Preview read as one composition. The title under the case fades out while the Preview's title is visible, then fades back when Preview closes.

The selected case uses a product-display pose rather than a flat front view: idle yaw is about 20°. In Preview focus mode, pressing and dragging the selected case rotates it up to ±40° horizontally and ±12° vertically; a small movement threshold preserves normal click/double-click behavior. On release, the case eases back to the standard display pose.

Clicking an empty Games-background region closes Preview. Clicking XMB, Preview content, or a case does not count as an empty-background click.

## 3. Real 3D Case Asset Pipeline

G3 stops using flat-card / faux-3D case presentation as the final design. Games use a real reusable **GLB/glTF 3D case model**.

The case model is a shared mesh resource; individual games change textures/material parameters, not geometry.

### Asset contract

First formal case template: `g3_frontend/assets/models/cases/standard_tall.glb`

Recommended modeling constraints:

- Front-facing rectangular console/DVD-style case.
- Real depth, real spine, real rear face, and a slightly raised front cover plane/lip.
- Pivot/origin at the geometric center of the case.
- Local axes: +Y up, +X right, front face oriented toward +Z.
- Apply transforms before export: scale 1/1/1 and rotation 0/0/0.
- Standard Tall is modeled at real-world proportions: height about 190 mm, width 135 mm, depth 15–18 mm. G3 currently applies a 10x presentation scale at runtime to fit the established carousel coordinate system.
- 500–2,000 triangles is preferred; hard-surface bevels should be modest.
- One UV set. Front-cover UV region must not overlap the spine/back if a single atlas is used.
- Preferred material slots:
  - `盒体`
  - `封面正面`
  - optional `封面书脊` / `封面背面`
  - legacy English names remain accepted for compatibility
- No baked lighting or baked shadows.
- G3 supplies neutral plastic materials at runtime instead of theme-tinting the whole case. Theme color is reserved for a restrained rim light.
- Runtime presentation uses a low-energy three-point product-light rig (warm key, cool fill, theme-aware rim) plus weak neutral ambient fill so bevels, seams, and opening recesses remain readable without washing out cover art.
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


## v0.6.1.9 G1 Layout Correction

The earlier fixed left-anchor percentages in this document are superseded by the Windows acceptance reference taken from the actual G1 animation. Browse now uses four viewport-relative slots at approximately **17% / 44% / 70% / 92%** of the current G3 window. The selected cover is the second slot. Secondary covers are distinguished by depth, scale, brightness, and a restrained toe-in toward the camera; the right-edge cover must remain cover-readable rather than presenting a bright bare spine.

G3 defaults to a normal resizable Windows window, matching G1 desktop behavior. Maximizing the window is supported and keeps the same relative four-slot composition. Preview keeps the large selected-case focus behavior, with its horizontal anchor expressed relative to the viewport rather than a fixed world X.


### v0.6.1.9.1 G1 visual measurement correction

Windows acceptance showed that matching G1 requires matching case *visual extents*, not merely spreading four center points across the window. The current reference centers are approximately **20% / 45.5% / 71% / 89%**, while the left/right near cases are roughly two-thirds of the selected case's apparent width. Preview keeps a large left-side selected case, but non-selected cases remain recognizably case-sized background objects rather than thumbnail dots.
