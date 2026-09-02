from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAV = (ROOT / 'g3_frontend/scripts/navigation_drawer.gd').read_text(encoding='utf-8')


def test_navigation_has_direct_input_fallback_for_handle_click():
    assert 'func _input(event: InputEvent) -> void:' in NAV
    assert '_handle.get_global_rect().has_point(mouse_event.position)' in NAV
    assert '_show_drawer_now()' in NAV


def test_navigation_show_path_does_not_depend_on_alpha_tween():
    assert 'func _show_drawer_now() -> void:' in NAV
    show_body = NAV.split('func _show_drawer_now() -> void:', 1)[1].split('\nfunc ', 1)[0]
    assert '_panel.visible = true' in show_body
    assert '_panel.modulate.a = 1.0' in show_body
    assert 'tween_property' not in show_body


def test_navigation_uses_explicit_bottom_right_offsets_and_high_z():
    assert 'const NAV_Z_INDEX: int = 400' in NAV
    assert '_panel.offset_right = -74.0' in NAV
    assert '_handle.offset_right = -18.0' in NAV
