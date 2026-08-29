# Retro Local GUI Smoke Fix 01

Baseline: v0.5.0.7 local GUI smoke tooling only.

## Symptom

Launching `tools\\run_retro_smoke.bat` reached `tests/test_retro_gui_smoke.py` but failed immediately with `ModuleNotFoundError: No module named 'app'`.

## Root cause

When Python executes `tools/retro_smoke_runner.py` directly, the script directory (`tools/`) is placed on `sys.path`; changing the current working directory to the repository root does not update Python's module search path. Therefore the smoke module could not import the repository package `app`.

## Fix

`retro_smoke_runner.py` now explicitly inserts the repository root at `sys.path[0]` before dynamically loading the smoke scenario.

No application source files are changed and the application version is unchanged.

## Regression coverage

Added `tests/test_retro_smoke_runner_import_path.py`. The test first reproduced the missing helper/path behavior, then passed after the runner added the repository root explicitly.
