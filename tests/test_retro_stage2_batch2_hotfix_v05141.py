from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "app" / "ui" / "retro_showcase_state.py"


def load_state():
    spec = importlib.util.spec_from_file_location("retro_showcase_state_v05141", STATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_focus_hero_uses_independent_target_scale_instead_of_compounding_browse_scale():
    state = load_state()
    browse = state.arc_pose(0.0, focus=0.0)
    focused = state.arc_pose(0.0, focus=1.0)

    assert browse.scale == 1.10
    assert focused.scale == 1.12
    assert focused.scale < browse.scale * 1.12


def test_hotfix_version_is_exposed_consistently():
    assert 'version = "0.5.0.17.1"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'RETRO_VERSION = "0.5.0.17.1"' in (ROOT / "app" / "ui" / "retro_showcase.py").read_text(encoding="utf-8")
    assert "v0.5.0.17" in (ROOT / "app" / "ui" / "app_chrome.py").read_text(encoding="utf-8")
    assert "v0.5.0.17" in (ROOT / "app" / "bootstrap.py").read_text(encoding="utf-8")
