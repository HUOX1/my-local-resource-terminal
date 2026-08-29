from pathlib import Path

from app.ui.retro_showcase_state import library_filter_options, persistent_filter_key

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_favorite_is_removed_from_retro_navigation_only():
    game_filters = {key for _label, key, _payload in library_filter_options("games")}
    movie_filters = {key for _label, key, _payload in library_filter_options("movies")}
    assert "favorite" not in game_filters
    assert "favorite" not in movie_filters
    assert persistent_filter_key("games", "favorite") == "all"
    assert persistent_filter_key("movies", "favorite") == "all"

    source = read("app/ui/retro_showcase.py")
    record_menu = source.split("def _show_record_menu", 1)[1].split("def _set_box_style", 1)[0]
    assert "收藏" not in record_menu
    assert "_toggle_game_favorite" not in source
    assert "_toggle_movie_favorite" not in source


def test_system_drawer_is_reduced_to_settings_and_about():
    source = read("app/ui/retro_showcase.py")
    panel = source.split("def _draw_system_panel", 1)[1].split("def _draw_corner_menu", 1)[0]
    assert 'tabs = ["设置", "关于"]' not in panel
    assert "RETRO UI FONT" in panel
    assert "LOCAL RESOURCE TERMINAL" in panel
    assert "高级设置…" in panel
    assert "添加游戏…" not in panel
    assert "搜索当前媒体库…" not in panel
    assert "立即扫描影片资源" not in panel
    assert "游戏盒体 ·" not in panel
    assert "角落菜单 ·" not in panel


def test_about_page_is_in_scene_and_reports_current_version():
    source = read("app/ui/retro_showcase.py")
    panel = source.split("def _draw_system_body", 1)[1].split("def _draw_corner_menu", 1)[0]
    assert "LOCAL RESOURCE TERMINAL" in panel
    assert 'RETRO_VERSION = "0.5.0.17.1"' in source
    assert 'f"V{RETRO_VERSION}"' in panel
    assert "QMessageBox.about" not in source


def test_stage1_a1_version_is_0509():
    assert 'version = "0.5.0.17.1"' in read("pyproject.toml")
    assert "v0.5.0.17" in read("app/bootstrap.py")
    assert "v0.5.0.17" in read("app/ui/app_chrome.py")


def test_gear_opens_settings_drawer_directly():
    source = read("app/ui/retro_showcase.py")
    block = source.split("def _activate_corner_action", 1)[1].split("def _handle_detail_click", 1)[0]
    assert 'if key == "settings":' in block
    assert 'self._set_system_open(not self.system_open)' in block
    assert 'self.system_tab = "设置"' not in block

