from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / "g3_frontend/scripts/main.gd").read_text(encoding="utf-8")
MENU = (ROOT / "g3_frontend/scripts/manage_menu.gd").read_text(encoding="utf-8")
PREVIEW = (ROOT / "g3_frontend/scripts/preview_panel.gd").read_text(encoding="utf-8")
CASE = (ROOT / "g3_frontend/scripts/game_case_3d.gd").read_text(encoding="utf-8")
PROJECT = (ROOT / "g3_frontend/project.godot").read_text(encoding="utf-8")


def test_xmb_and_system_are_localized_and_exitable():
    for label in ("游戏", "电影", "漫画", "音乐", "搜索", "系统"):
        assert label in MAIN
    assert 'exit_button.text = "退出 G3"' in MAIN
    assert 'key.ctrl_pressed and key.keycode == KEY_Q' in MAIN
    assert 'func _exit_application() -> void:' in MAIN


def test_manage_menu_is_custom_chinese_popup_panel():
    assert "extends PopupPanel" in MENU
    for label in ("启动", "预览", "编辑资料", "媒体素材", "启动设置", "移除收藏"):
        assert label in MENU
    assert 'button.add_theme_font_size_override("font_size", 18)' in MENU


def test_preview_panel_animates_text_and_media_and_hides_status_when_media_exists():
    assert 'mouse_filter = Control.MOUSE_FILTER_STOP' in PREVIEW
    assert 'const TEXT_ANIMATION_OFFSET_X: float = 32.0' in PREVIEW
    assert 'const MEDIA_ANIMATION_OFFSET_Y: float = 24.0' in PREVIEW
    assert '_set_status("暂无预览素材", true)' in PREVIEW
    assert '_play_enter_animation(has_visual_media)' in PREVIEW


def test_case_and_project_include_acrylic_and_perf_defaults():
    assert 'TRANSPARENCY_ALPHA' in CASE
    assert 'clearcoat = 0.85' in CASE
    assert 'run/max_fps=60' in PROJECT
    assert 'anti_aliasing/quality/msaa_3d=1' in PROJECT
