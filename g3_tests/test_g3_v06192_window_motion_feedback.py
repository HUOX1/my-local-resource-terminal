from pathlib import Path

ROOT = Path(__file__).parents[1]
CAROUSEL = (ROOT / 'g3_frontend/scripts/game_carousel.gd').read_text(encoding='utf-8')
NAV = (ROOT / 'g3_frontend/scripts/navigation_drawer.gd').read_text(encoding='utf-8')
MAIN = (ROOT / 'g3_frontend/scripts/main.gd').read_text(encoding='utf-8')
PROJECT = (ROOT / 'g3_frontend/project.godot').read_text(encoding='utf-8')
WINDOW_CHROME_PATH = ROOT / 'g3_frontend/scripts/window_chrome.gd'
PYPROJECT = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
CORE_INIT = (ROOT / 'g3_core/__init__.py').read_text(encoding='utf-8')


def test_navigation_click_is_idempotent_reveal_after_hover():
    assert '_handle.mouse_entered.connect(_show_drawer_now)' in NAV
    assert 'func _input(event: InputEvent) -> void:' in NAV
    assert '_handle.get_global_rect().has_point(mouse_event.position)' in NAV


def test_edge_slot_does_not_collapse_and_exit_does_not_shrink():
    assert 'const SLOT_SCALE: Array[float] = [2.70, 3.35, 2.85, 2.15]' in CAROUSEL
    assert 'old_item.target_scale = 0.62' not in CAROUSEL
    assert 'old_item.target_scale =' not in CAROUSEL


def test_custom_theme_window_chrome_replaces_native_titlebar_and_keeps_resize():
    assert 'window/size/borderless=true' in PROJECT
    assert WINDOW_CHROME_PATH.is_file()
    chrome = WINDOW_CHROME_PATH.read_text(encoding='utf-8')
    assert 'class_name G3WindowChrome' in chrome
    assert 'window.start_drag()' in chrome
    assert 'window.start_resize(edge)' in chrome
    assert 'DisplayServer.WINDOW_EDGE_BOTTOM_RIGHT' in chrome
    assert 'WINDOW_CHROME_SCRIPT' in MAIN
    assert 'window_chrome = WINDOW_CHROME_SCRIPT.new()' in MAIN
    assert 'window.borderless = true' in MAIN


def test_runtime_operation_feedback_auto_fades_after_hold_time():
    assert 'const RUNTIME_MESSAGE_HOLD_SECONDS: float = 4.0' in MAIN
    assert 'const RUNTIME_MESSAGE_FADE_SECONDS: float = 0.35' in MAIN
    assert 'func _dismiss_runtime_message_after_delay(generation: int) -> void:' in MAIN
    assert 'await get_tree().create_timer(RUNTIME_MESSAGE_HOLD_SECONDS).timeout' in MAIN
    assert 'tween_property(runtime_error_label, "modulate:a", 0.0, RUNTIME_MESSAGE_FADE_SECONDS)' in MAIN


def test_version_bumped_to_v06192():
    assert 'version = "0.6.1.9.2"' in PYPROJECT
    assert '__version__ = "0.6.1.9.2"' in CORE_INIT


def test_build_ui_does_not_reference_apply_theme_local_top_color():
    build_ui = MAIN.split('func _build_ui() -> void:', 1)[1].split('\nfunc ', 1)[0]
    assert 'top_color' not in build_ui
    assert 'window_chrome.set_theme_colors(_theme_text, _theme_muted, _theme_accent, top_color)' in MAIN.split('func _apply_theme(theme: Dictionary) -> void:', 1)[1]
