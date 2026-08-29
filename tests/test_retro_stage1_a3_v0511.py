from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "app" / "ui" / "retro_showcase_state.py"


def load_state():
    spec = importlib.util.spec_from_file_location("retro_showcase_state_a3", STATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_retro_minimum_window_contract_is_1100_by_700():
    state = load_state()
    assert state.RETRO_MIN_WINDOW_WIDTH == 1100
    assert state.RETRO_MIN_WINDOW_HEIGHT == 700

    source = (ROOT / "app" / "ui" / "retro_showcase.py").read_text(encoding="utf-8")
    assert "host_window.setMinimumSize(RETRO_MIN_WINDOW_WIDTH, RETRO_MIN_WINDOW_HEIGHT)" in source


def test_focus_info_layout_expands_text_space_at_minimum_window():
    state = load_state()
    compact = state.focus_info_layout(1100, 700, hero_right=555.0)
    assert compact.left >= 555.0 + 20.0
    assert compact.right <= 1100 * 0.791
    assert compact.width >= 280.0
    assert compact.title_max_lines == 3
    assert compact.title_min_point_size == 12

    wide = state.focus_info_layout(1320, 840, hero_right=650.0)
    assert wide.right <= 1320 * 0.806
    assert wide.width > compact.width
    assert wide.title_max_lines == 2
    assert wide.title_min_point_size == 15


def test_local_smoke_has_minimum_window_and_long_title_check():
    smoke = (ROOT / "tests" / "test_retro_gui_smoke.py").read_text(encoding="utf-8")
    runner = (ROOT / "tools" / "retro_smoke_runner.py").read_text(encoding="utf-8")
    assert "test_minimum_window_and_long_focus_title_layout" in smoke
    assert '"minimum window / long focus title"' in runner
