# v0.3.4 Single Instance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent multiple writable terminal instances and activate the existing window when the app is launched again.

**Architecture:** Add a small Qt local-IPC gate that runs immediately after QApplication creation and before settings/services. Primary process owns a QLocalServer; secondary sends `activate` and exits without building the application data layer.

**Tech Stack:** Python 3.11+, PySide6 Widgets + QtNetwork, pytest.

## Global Constraints

- No lock files.
- Do not change movie/game persistence or session formats.
- Secondary instance must not call `build_services()`.
- Existing window should be restored/raised without an informational dialog.
- No new dependency outside existing PySide6.

---

### Task 1: Single-instance IPC gate

**Files:**
- Create: `app/single_instance.py`
- Test: `tests/test_single_instance_source.py`

**Interfaces:**
- Produces: `SingleInstanceGate(server_name: str)`, `acquire() -> bool`, `set_activation_handler(callable) -> None`, `notify_primary() -> bool`.

- [ ] Write source-level failing tests for Qt local IPC, activate message, and no lock-file implementation.
- [ ] Run the focused test and confirm failure because the module does not exist.
- [ ] Implement the minimal gate with QLocalServer/QLocalSocket and pending activation support.
- [ ] Re-run focused tests.

### Task 2: Bootstrap early exit and window activation

**Files:**
- Modify: `app/bootstrap.py`
- Modify: `app/main.py`
- Test: `tests/test_single_instance_source.py`

**Interfaces:**
- Consumes: `SingleInstanceGate` from Task 1.
- Produces: application attribute `_local_movie_manager_secondary_instance` and retained `_local_movie_manager_single_instance_gate`.

- [ ] Write failing tests proving the gate is acquired before `build_services()` and secondary execution exits cleanly.
- [ ] Run focused tests and confirm expected failure.
- [ ] Wire the gate into bootstrap and register an activation callback that calls `showNormal`, `raise_`, and `activateWindow`.
- [ ] Update `main()` so a secondary instance returns 0 without entering the event loop.
- [ ] Re-run focused tests.

### Task 3: Version, regression, packaging

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Create: `升级说明_v0.3.4.txt`

- [ ] Set version to 0.3.4 and document single-instance behavior.
- [ ] Run full `python -m pytest -q`.
- [ ] Run `python -m pytest -q tests/test_python_compatibility.py`.
- [ ] Run `python -m compileall -q app tests`.
- [ ] Overlay changed files on a clean v0.3.3.1 full package and run its regression suite.
- [ ] Build patch and full ZIPs; verify both with `unzip -t` and scan for cache/pyc files.
