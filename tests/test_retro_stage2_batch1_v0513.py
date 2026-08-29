from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOWCASE = ROOT / "app" / "ui" / "retro_showcase.py"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_search_is_scene_capsule_not_input_dialog():
    source = SHOWCASE.read_text(encoding="utf-8")
    assert "QInputDialog" not in source
    assert "QLineEdit" in source
    assert 'setObjectName("retroSearchCapsule")' in source
    assert "def _show_search_bar" in source
    assert "def _hide_search_bar" in source
    assert "def _on_search_text_changed" in source
    scene_menu = source.split("def _show_scene_menu", 1)[1].split("def _show_record_menu", 1)[0]
    assert 'menu.addAction("搜索…").triggered.connect(self._show_search_bar)' in scene_menu


def test_gear_opens_one_settings_drawer_with_about_inline():
    source = SHOWCASE.read_text(encoding="utf-8")
    panel = source.split("def _draw_system_panel", 1)[1].split("def _draw_corner_menu", 1)[0]
    assert 'tabs = ["设置", "关于"]' not in panel
    assert "_system_tab_rects" not in panel
    assert "RETRO UI FONT" in panel
    assert "LOCAL RESOURCE TERMINAL" in panel
    assert 'f"V{RETRO_VERSION}"' in panel
    assert "完整设置" not in panel
    assert "高级设置…" in panel


def test_installed_font_selector_is_scene_child_and_persistent():
    source = SHOWCASE.read_text(encoding="utf-8")
    assert "QFontDatabase" in source
    assert "QComboBox" in source
    assert 'setObjectName("retroFontSelector")' in source
    assert 'QSettings("LocalMovieManager", "LocalMovieManager")' in source
    assert '"retro/ui_font_family"' in source
    assert "def _set_retro_font_family" in source
    assert "def _ui_font" in source


def test_local_smoke_exercises_scene_search_settings_and_font():
    smoke = read("tests/test_retro_gui_smoke.py")
    runner = read("tools/retro_smoke_runner.py")
    assert "test_scene_search_settings_and_font_controls" in smoke
    assert '"scene search / settings / font"' in runner


def test_stage2_batch1_version_is_05013():
    assert 'version = "0.5.0.17.1"' in read("pyproject.toml")
    assert "v0.5.0.17" in read("app/bootstrap.py")
    assert "v0.5.0.17" in read("app/ui/app_chrome.py")
    assert 'RETRO_VERSION = "0.5.0.17.1"' in read("app/ui/retro_showcase.py")
