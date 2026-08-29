from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "retro_smoke_runner.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("retro_smoke_runner_under_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_can_restore_project_root_to_sys_path():
    runner = _load_runner()
    root = str(ROOT)
    original = list(sys.path)
    try:
        sys.path[:] = [entry for entry in sys.path if entry != root]
        assert root not in sys.path
        runner._ensure_project_root_on_sys_path()
        assert sys.path[0] == root
    finally:
        sys.path[:] = original
