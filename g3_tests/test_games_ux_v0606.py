from pathlib import Path
import json

ROOT = Path(__file__).parents[1]
MAIN = ROOT / "g3_frontend/scripts/main.gd"
CASE = ROOT / "g3_frontend/scripts/game_case_3d.gd"
CAROUSEL = ROOT / "g3_frontend/scripts/game_carousel.gd"
CYAN = ROOT / "g3_frontend/themes/classic_cyan/theme.json"
STATUS = ROOT / "docs/v0.6/Phase1_Feature_Status.md"


def test_browse_case_is_offset_left_and_down_with_caption_following_case():
    carousel = CAROUSEL.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    assert 'const BROWSE_ANCHOR_X: float = -7.45' in carousel
    assert 'const BROWSE_ANCHOR_Y: float = 2.05' in carousel
    assert 'const PREVIEW_ANCHOR_X: float = -7.65' in carousel
    assert 'const PREVIEW_ANCHOR_Y: float = 2.05' in carousel
    assert 'func selected_case_world_position() -> Vector3:' in carousel
    assert 'case_title_label' in main
    assert '_update_case_caption_position()' in main
    assert 'title_label.text = str(game.get("title", "GAMES"))' not in main


def test_game_case_has_default_yaw_and_visible_thickness():
    text = CASE.read_text(encoding="utf-8")
    assert 'const BASE_YAW_DEGREES: float = 10.0' in text
    assert 'game_case.glb' in text
    assert 'game_case_placeholder.glb' in text
    assert '_spine_meshes' in text
    assert 'var target_rot_y: float = deg_to_rad(BASE_YAW_DEGREES + hover_vector.x * 5.0)' in text
    assert 'func set_theme_colors(accent: Color, secondary: Color) -> void:' in text


def test_preview_can_close_on_blank_click_and_caption_fades():
    text = MAIN.read_text(encoding="utf-8")
    assert 'func _unhandled_input(event: InputEvent) -> void:' in text
    assert 'preview.get_global_rect().has_point(mouse_event.position)' in text
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
    assert 'G3 当前功能地图' in main
    assert '已可用：' in main
    assert '待实机验收：' in main
    assert '仅保留入口：' in main
    assert STATUS.is_file()
    status = STATUS.read_text(encoding="utf-8")
    assert "真实 3D GLB 游戏盒管线" in status
    assert "Movies / Comics / Music / Search" in status


def test_fullscreen_ui_does_not_swallow_blank_preview_close_clicks():
    main = MAIN.read_text(encoding="utf-8")
    assert 'ui.mouse_filter = Control.MOUSE_FILTER_IGNORE' in main
