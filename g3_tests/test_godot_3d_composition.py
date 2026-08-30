from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = ROOT / "g3_frontend" / "scripts" / "main.gd"
SHADER = ROOT / "g3_frontend" / "shaders" / "ambient.gdshader"


def test_ambient_is_spatial_3d_background_not_opaque_canvas_overlay():
    shader = SHADER.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    assert "shader_type spatial;" in shader
    assert "shader_type canvas_item;" not in shader
    assert "ALBEDO = col;" in shader
    build_ambient = main.split("func _build_ambient() -> void:", 1)[1].split("\nfunc _build_3d_world()", 1)[0]
    assert "CanvasLayer.new()" not in build_ambient
    assert "ColorRect.new()" not in build_ambient
    assert "MeshInstance3D.new()" in build_ambient
    assert "_ambient_mesh.position = Vector3(0.0, 0.0, -6.0)" in build_ambient


def test_ambient_quad_tracks_viewport_aspect():
    main = MAIN.read_text(encoding="utf-8")
    assert "func _resize_ambient_mesh() -> void:" in main
    assert "camera.fov" in main
    assert "get_viewport().get_visible_rect().size" in main
    assert "get_viewport().size_changed.connect(_resize_ambient_mesh)" in main
