from pathlib import Path

ROOT = Path(__file__).parents[1]
CAROUSEL = (ROOT / 'g3_frontend/scripts/game_carousel.gd').read_text(encoding='utf-8')
NAV = (ROOT / 'g3_frontend/scripts/navigation_drawer.gd').read_text(encoding='utf-8')
PYPROJECT = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
CORE_INIT = (ROOT / 'g3_core/__init__.py').read_text(encoding='utf-8')


def test_browse_track_matches_g1_tighter_four_case_composition():
    assert 'const SLOT_SCREEN_X: Array[float] = [0.20, 0.455, 0.71, 0.89]' in CAROUSEL
    assert 'const SLOT_SCALE: Array[float] = [2.70, 3.35, 2.85, 2.15]' in CAROUSEL
    assert 'const SLOT_YAW_DEGREES: Array[float] = [6.0, 0.0, -5.0, -7.0]' in CAROUSEL


def test_preview_keeps_background_cases_readable_and_moves_selected_left():
    assert 'const PREVIEW_SCREEN_X: float = 0.26' in CAROUSEL
    assert 'const PREVIEW_BACKGROUND_SCALE: float = 1.28' in CAROUSEL
    assert 'const PREVIEW_BACKGROUND_MIN_SCALE: float = 1.04' in CAROUSEL
    assert 'maxf(PREVIEW_BACKGROUND_MIN_SCALE' in CAROUSEL


def test_navigation_handle_is_independent_viewport_anchor_not_moved_with_drawer():
    assert 'set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)' in NAV
    assert '_handle.anchor_left = 1.0' in NAV
    assert '_panel.anchor_left = 1.0' in NAV
    assert '_handle.text = "≡"' in NAV
    assert 'const NAV_Z_INDEX: int = 400' in NAV
    assert '_handle.z_index = 2' in NAV
    assert '_panel.z_index = 1' in NAV
    assert '_panel.visible = false' in NAV
    assert '_panel.visible = true' in NAV
    assert '_panel.offset_right = -74.0' in NAV
    assert '_handle.offset_right = -18.0' in NAV


def test_version_bumped_to_v06191():
    assert 'version = "0.6.1.9.2"' in PYPROJECT
    assert '__version__ = "0.6.1.9.2"' in CORE_INIT
