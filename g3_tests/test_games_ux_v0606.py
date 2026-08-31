from pathlib import Path
import json

ROOT = Path(__file__).parents[1]
MAIN = ROOT / "g3_frontend/scripts/main.gd"
CASE = ROOT / "g3_frontend/scripts/game_case_3d.gd"
CAROUSEL = ROOT / "g3_frontend/scripts/game_carousel.gd"
CYAN = ROOT / "g3_frontend/themes/classic_cyan/theme.json"
STATUS = ROOT / "docs/v0.6/Phase1_Feature_Status.md"


def test_browse_is_centered_and_preview_moves_main_case_left():
    carousel = CAROUSEL.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    assert 'const BROWSE_ANCHOR_X: float = -0.35' in carousel
    assert 'const BROWSE_ANCHOR_Y: float = 0.60' in carousel
    assert 'const PREVIEW_ANCHOR_X: float = -3.10' in carousel
    assert 'const PREVIEW_ANCHOR_Y: float = 0.82' in carousel
    assert 'const PREVIEW_SELECTED_SCALE: float = 2.18' in carousel
    assert 'func selected_case_world_position() -> Vector3:' in carousel
    assert 'case_title_label' in main
    assert '_update_case_caption_position()' in main
    assert 'title_label.text = str(game.get("title", "GAMES"))' not in main


def test_game_case_uses_front_pose_hover_tilt_and_acrylic_material():
    text = CASE.read_text(encoding="utf-8")
    assert 'const BASE_YAW_DEGREES: float = 0.0' in text
    assert 'const HOVER_YAW_DEGREES: float = 12.0' in text
    assert 'const PLASTIC_COLOR: Color = Color(0.75, 0.81, 0.84, 0.84)' in text
    assert 'material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA' in text
    assert 'material.clearcoat_enabled = true' in text
    assert 'func set_theme_colors(accent: Color, secondary: Color) -> void:' in text


def test_preview_can_close_on_blank_click_and_caption_fades():
    text = MAIN.read_text(encoding="utf-8")
    assert 'func _unhandled_input(event: InputEvent) -> void:' in text
    assert '_close_preview()' in text
    assert 'func _set_case_caption_visible(value: bool, immediate: bool = false) -> void:' in text
    assert '_set_case_caption_visible(false)' in text
    assert '_set_case_caption_visible(true)' in text


def test_cyan_theme_is_real_and_theme_colors_drive_shader():
    assert CYAN.is_file()
    payload = json.loads(CYAN.read_text(encoding="utf-8"))
    assert payload["id"] == "classic_cyan"
    assert payload["colors"]["base_top"].lower().startswith("#0")
    main = MAIN.read_text(encoding="utf-8")
    for shader_key in ("top_color", "bottom_color", "wave_a", "wave_b", "symbol_color"):
        assert f'"{shader_key}"' in main
    assert 'carousel.set_theme_colors(_theme_accent, _theme_secondary)' in main


def test_system_and_docs_expose_phase1_feature_status():
    main = MAIN.read_text(encoding="utf-8")
    assert 'G3 当前状态' in main
    assert '已可用：' in main
    assert '本轮更新：' in main
    assert '当前仍保留入口：' in main
    assert STATUS.is_file()
    status = STATUS.read_text(encoding="utf-8")
    assert "真实 3D GLB 游戏盒管线" in status
    assert "电影 / 漫画 / 音乐 / 搜索" in status


def test_fullscreen_ui_keeps_canvas_ignore_while_preview_consumes_clicks():
    main = MAIN.read_text(encoding="utf-8")
    preview = (ROOT / "g3_frontend/scripts/preview_panel.gd").read_text(encoding="utf-8")
    assert 'ui.mouse_filter = Control.MOUSE_FILTER_IGNORE' in main
    assert 'mouse_filter = Control.MOUSE_FILTER_STOP' in preview
