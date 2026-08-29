# Retro Stage 2 Batch 2 · v0.5.0.14

## Scope

This batch advances the existing QPainter showcase interaction without changing renderer architecture or package-face clipping.

- Settled showcase composition is capped at four records.
- The primary package is larger and the four-up rail is intentionally asymmetric: one neighbor left, two right.
- Clicking a non-primary visible package only moves that package into the primary slot.
- Clicking the already-settled primary package enters short-info focus.
- Double-clicking the primary package keeps launch/play behavior.
- Visible packages now respond to pointer hover with restrained lift, scale, directional roll, and edge emphasis.
- Wheel and click navigation share the same unwrapped carousel target and `OutQuart` easing.
- Seamless wrap remains based on unwrapped sequence instances; no modulo teleport was reintroduced.

## Safety boundary

This batch does **not** change:

- game-cover/front-face clipping or the known top-right cover mismatch;
- search, settings, font controls, archive edit dialogs;
- background wave geometry;
- minimum-window behavior;
- MORE panel contents;
- Qt Quick / Qt Quick 3D architecture.

## Local GUI smoke

`tools/run_retro_smoke.bat` now includes `showcase 4-up / click / hover / wrap` in addition to the six existing checks. The new check creates six fake records and exercises:

1. a settled four-item viewport;
2. hover response without changing selection;
3. first click moving a non-primary package to primary without focus;
4. second click entering focus;
5. double-click launch path;
6. wrap from the final logical record to index zero while the live arc coordinate remains continuous.

The authoritative GUI result remains the user's native Windows + PySide6 runtime.
