from pathlib import Path

ROOT = Path(__file__).parents[1]
CAROUSEL = (ROOT / 'g3_frontend/scripts/game_carousel.gd').read_text(encoding='utf-8')
MAIN = (ROOT / 'g3_frontend/scripts/main.gd').read_text(encoding='utf-8')
DRAWER = ROOT / 'g3_frontend/scripts/navigation_drawer.gd'
SETTINGS = (ROOT / 'g3_core/settings.py').read_text(encoding='utf-8')


def test_four_slot_track_is_asymmetric_and_directional():
    assert 'const VISIBLE_SLOT_COUNT: int = 4' in CAROUSEL
    assert 'const SELECTED_SLOT: int = 1' in CAROUSEL
    assert 'const SLOT_SCREEN_X: Array[float]' in CAROUSEL
    assert 'const OFFSCREEN_SCREEN_MARGIN' in CAROUSEL
    assert 'func _offscreen_x(' in CAROUSEL
    assert 'func _shift_track(direction: int) -> void:' in CAROUSEL
    assert '_relative_index' not in CAROUSEL
    assert 'ACTIVE_RADIUS' not in CAROUSEL


def test_browse_has_no_persistent_caption_or_corner_chrome():
    assert 'case_title_label.visible = false' in MAIN
    assert 'backend_label.visible = section == "SYSTEM"' in MAIN
    assert 'fps_label.visible = section == "SYSTEM"' in MAIN
    assert 'hint_label.visible = section == "SYSTEM"' in MAIN
    assert 'xmb_root.visible = false' in MAIN


def test_navigation_drawer_is_icon_only_edge_reveal():
    assert DRAWER.is_file()
    text = DRAWER.read_text(encoding='utf-8')
    assert 'signal section_requested(section_id: String)' in text
    assert 'const CONTENT_SECTIONS' in text
    assert 'const SYSTEM_SECTIONS' in text
    assert 'const NAV_Z_INDEX: int = 400' in text
    assert 'func _show_drawer_now() -> void:' in text
    assert 'button.text = ""' in text
    assert 'func set_active_section(section_id: String) -> void:' in text


def test_default_start_section_is_separate_from_last_section():
    assert 'default_start_section: str = "games"' in SETTINGS
    assert 'DEFAULT_START_SECTIONS' in SETTINGS
    assert '_restore_section' not in MAIN
    assert 'settings.get("default_start_section", "games")' in MAIN
    assert 'backend.request("state.update", {"last_section"' not in MAIN
