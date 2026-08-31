from pathlib import Path

ROOT = Path(__file__).parents[1]
CASE = ROOT / "g3_frontend/scripts/game_case_3d.gd"
CAROUSEL = ROOT / "g3_frontend/scripts/game_carousel.gd"
MAIN = ROOT / "g3_frontend/scripts/main.gd"


def test_case_uses_product_display_angle_and_acrylic_materials():
    text = CASE.read_text(encoding="utf-8")
    assert "const BASE_YAW_DEGREES: float = 0.0" in text
    assert "const HOVER_YAW_DEGREES: float = 12.0" in text
    assert "const PLASTIC_COLOR: Color" in text
    assert "material.metallic = 0.0" in text
    assert "material.clearcoat_enabled = true" in text


def test_case_exposes_bounded_drag_rotation_with_slow_return():
    text = CASE.read_text(encoding="utf-8")
    assert "const DRAG_YAW_LIMIT_DEGREES: float = 55.0" in text
    assert "const DRAG_PITCH_LIMIT_DEGREES: float = 14.0" in text
    assert "func begin_drag() -> void:" in text
    assert "func set_drag_rotation(yaw_degrees: float, pitch_degrees: float) -> void:" in text
    assert "func end_drag() -> void:" in text
    assert "_drag_yaw_degrees = move_toward" in text
    assert "_drag_pitch_degrees = move_toward" in text


def test_preview_selected_case_supports_drag_without_breaking_click_contract():
    text = CAROUSEL.read_text(encoding="utf-8")
    assert "const DRAG_THRESHOLD_PX: float = 7.0" in text
    assert "func _begin_case_drag(position_2d: Vector2) -> bool:" in text
    assert "func _update_case_drag(position_2d: Vector2) -> void:" in text
    assert "func _finish_case_drag(position_2d: Vector2) -> bool:" in text
    assert "event is InputEventMouseMotion" in text
    assert "if preview_mode and _begin_case_drag(mouse_event.position):" in text
    assert "_handle_left_click(position_2d)" in text


def test_collection_world_uses_three_point_product_lighting_and_ambient_fill():
    text = MAIN.read_text(encoding="utf-8")
    assert "var key_light: DirectionalLight3D" in text
    assert "var fill_light: DirectionalLight3D" in text
    assert "var rim_light: DirectionalLight3D" in text
    assert "WorldEnvironment.new()" in text
    assert "ambient_light_energy = 0.12" in text
    assert "environment.ssao_enabled = true" in text
    assert "ambient_light_sky_contribution = 0.0" in text
    assert "rim_light.light_color = _theme_accent.lerp(Color.WHITE, 0.55)" in text
