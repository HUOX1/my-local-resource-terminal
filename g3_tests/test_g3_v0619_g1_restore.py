from pathlib import Path

ROOT = Path(__file__).parents[1]
CAROUSEL = (ROOT / 'g3_frontend/scripts/game_carousel.gd').read_text(encoding='utf-8')
CASE = (ROOT / 'g3_frontend/scripts/game_case_3d.gd').read_text(encoding='utf-8')
NAV = (ROOT / 'g3_frontend/scripts/navigation_drawer.gd').read_text(encoding='utf-8')
MAIN = (ROOT / 'g3_frontend/scripts/main.gd').read_text(encoding='utf-8')
PROJECT = (ROOT / 'g3_frontend/project.godot').read_text(encoding='utf-8')
PYPROJECT = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')


def test_g1_track_uses_screen_space_slots_and_true_offscreen_entry():
    assert 'const SLOT_SCREEN_X: Array[float]' in CAROUSEL
    assert 'const OFFSCREEN_SCREEN_MARGIN: float' in CAROUSEL
    assert 'func _world_x_for_screen_ratio(' in CAROUSEL
    assert 'func _offscreen_x(' in CAROUSEL
    assert 'get_viewport().size_changed.connect(_on_viewport_size_changed)' in CAROUSEL


def test_g1_track_has_slot_visual_hierarchy_not_scale_only():
    assert 'const SLOT_BRIGHTNESS: Array[float]' in CAROUSEL
    assert 'const SLOT_YAW_DEGREES: Array[float]' in CAROUSEL
    assert 'item.set_browse_style(SLOT_BRIGHTNESS[slot], SLOT_YAW_DEGREES[slot])' in CAROUSEL
    assert 'func set_browse_style(brightness: float, yaw_degrees: float) -> void:' in CASE
    assert 'var _browse_brightness: float = 1.0' in CASE
    assert 'var _slot_yaw_degrees: float = 0.0' in CASE


def test_track_serializes_scroll_transitions_to_prevent_ghost_accumulation():
    assert 'var _transitioning: bool = false' in CAROUSEL
    assert 'var _queued_steps: int = 0' in CAROUSEL
    assert 'func _request_track_steps(delta_index: int) -> void:' in CAROUSEL
    assert 'func _consume_queued_steps() -> void:' in CAROUSEL
    assert 'await get_tree().create_timer(TRACK_STEP_SECONDS).timeout' in CAROUSEL


def test_navigation_has_persistent_g1_style_handle_and_click_fallback():
    assert 'const HANDLE_SIZE: float = 48.0' in NAV
    assert 'var _handle: Button' in NAV
    assert '_handle.mouse_entered.connect(_show_drawer_now)' in NAV
    assert 'func _input(event: InputEvent) -> void:' in NAV
    assert 'func _toggle_drawer() -> void:' not in NAV
    assert '_panel.get_global_rect().has_point(mouse)' in NAV
    assert '_handle.get_global_rect().has_point(mouse_event.position)' in NAV


def test_default_window_is_normal_resizable_window_and_gameplay_restore_preserves_mode():
    assert 'window/size/mode=0' in PROJECT
    assert 'window/size/borderless=true' in PROJECT
    assert 'window/size/resizable=true' in PROJECT
    assert 'var _window_mode_before_gameplay: int = Window.MODE_WINDOWED' in MAIN
    assert 'var _window_borderless_before_gameplay: bool = true' in MAIN
    assert 'window.mode = _window_mode_before_gameplay' in MAIN
    assert 'window.borderless = _window_borderless_before_gameplay' in MAIN


def test_version_is_v0619_or_newer_patch():
    assert 'version = "0.6.1.9.2"' in PYPROJECT
    assert '__version__ = "0.6.1.9.2"' in (ROOT / 'g3_core/__init__.py').read_text(encoding='utf-8')
