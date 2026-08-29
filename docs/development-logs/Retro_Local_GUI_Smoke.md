# Retro Local GUI Smoke

**Baseline:** v0.5.0.7  
**Purpose:** Add a Windows-local runtime safety check without changing product code or version.

## Why this exists

The failed v0.5.0.8 update demonstrated that source compilation and source-level regression tests are not enough for PySide6 GUI work. A runtime exception inside the Retro paint chain can make later layers disappear and can become much worse during repeated resize/repaint events.

This local smoke runner executes against the same Windows/PySide6 environment used to run the application.

## Entry point

Double-click:

`tools/run_retro_smoke.bat`

The launcher prefers `.venv\Scripts\python.exe`, then `py -3`, then `python`.
It clears `QT_QPA_PLATFORM` so Windows uses the native Qt platform plugin rather than the CI `offscreen` plugin.

## Checks

1. Browse-state showcase rendering.
2. Focus-state short information and MORE hit target.
3. Details/MORE panel rendering.
4. System panel plus bottom-right and top-right chrome drawing.
5. Repeated native widget resize/repaint at several viewport sizes.
6. `QWidget.grab()` to force a real paint and save a screenshot.
7. Python exceptions routed through Qt callbacks are captured and fail the run.

## Output

- `artifacts/retro-smoke-local/latest.log`
- timestamped PNG screenshots under `artifacts/retro-smoke-local/<timestamp>/`

A failing run returns a non-zero exit code and prints `[FAIL]` in the console.
