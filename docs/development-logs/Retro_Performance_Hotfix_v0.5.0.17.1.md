# Retro Performance Hotfix · v0.5.0.17.1

## Problem

Retro idle CPU usage was reported at roughly 30% while the application was open and untouched. The ambient timer was running every 33 ms and calling `update()` for the full custom-painted scene. Since v0.5.0.15 the cost of each frame had also increased with ambient symbols plus a second five-band foreground-wave pass drawn after the package showcase.

## Root cause

The main cost was the always-on full-window repaint loop, not the Sound Pack service. `UISoundService` has no continuous timer/thread when idle. The Retro ambient timer did have a continuous 33 ms cadence and forced the entire showcase to repaint even without interaction.

## Changes

- Idle ambient cadence: 33 ms -> 66 ms (about 30 fps -> 15 fps).
- Ambient phase now advances from real elapsed milliseconds, preserving the previous movement speed at the lower repaint cadence.
- Hover easing temporarily switches to 33 ms only while the hover pose is changing, then returns to 66 ms after settling.
- Hidden or minimized Retro scenes skip ambient repaint work and refresh the elapsed clock instead.
- Removed the entire post-showcase `_draw_foreground_waves()` pass. All remaining ambient waves/symbols are painted behind the package showcase.
- Cached deterministic ambient-symbol placement and size seeds once per overlay instead of recomputing them every frame.
- Added an idle-paint-budget GUI smoke check. The Windows smoke now has 10 checks and should report `PASS (10/10 checks passed)`.

## Scope protection

No changes to box geometry, carousel click behavior, Focus scale, cover polygon, Sound Pack mapping/playback, or library services.

## Verification

Container verification covers pure/static tests and compilation. PySide6 is not installed in the container, so native Windows paint-rate and CPU measurements remain authoritative on the user's machine via `tools\\run_retro_smoke.bat` and Task Manager.
