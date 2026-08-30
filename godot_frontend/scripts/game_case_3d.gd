extends Node3D
class_name GameCase3D

var item_id: String = ""
var title_text: String = ""
var selected: bool = false
var hovered: bool = false
var target_position: Vector3 = Vector3.ZERO
var target_scale: float = 1.0
var target_alpha: float = 1.0
var hover_vector: Vector2 = Vector2.ZERO

var _body: MeshInstance3D
var _front: MeshInstance3D
var _spine: MeshInstance3D
var _cover_texture: Texture2D
var _base_material: StandardMaterial3D
var _front_material: StandardMaterial3D

func configure(game: Dictionary) -> void:
    item_id = str(game.get("id", ""))
    title_text = str(game.get("title", "Untitled"))
    _build_case()
    var cover_value: Variant = game.get("cover", "")
    var cover_path: String = "" if cover_value == null else str(cover_value)
    if not cover_path.is_empty():
        set_cover_path(cover_path)

func _build_case() -> void:
    if _body != null:
        return

    _body = MeshInstance3D.new()
    var box: BoxMesh = BoxMesh.new()
    box.size = Vector3(1.34, 1.90, 0.18)
    _body.mesh = box
    _base_material = StandardMaterial3D.new()
    _base_material.albedo_color = Color(0.035, 0.038, 0.060, 1.0)
    _base_material.metallic = 0.15
    _base_material.roughness = 0.34
    _body.material_override = _base_material
    add_child(_body)

    _front = MeshInstance3D.new()
    var quad: QuadMesh = QuadMesh.new()
    quad.size = Vector2(1.24, 1.78)
    _front.mesh = quad
    _front.position = Vector3(0.0, 0.0, 0.095)
    _front_material = StandardMaterial3D.new()
    _front_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    _front_material.albedo_color = Color(0.13, 0.08, 0.22, 1.0)
    _front.material_override = _front_material
    add_child(_front)

    _spine = MeshInstance3D.new()
    var spine_quad: QuadMesh = QuadMesh.new()
    spine_quad.size = Vector2(0.14, 1.78)
    _spine.mesh = spine_quad
    _spine.position = Vector3(-0.681, 0.0, 0.0)
    _spine.rotation_degrees = Vector3(0.0, -90.0, 0.0)
    var spine_material: StandardMaterial3D = StandardMaterial3D.new()
    spine_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    spine_material.albedo_color = Color(0.20, 0.08, 0.38, 1.0)
    _spine.material_override = spine_material
    add_child(_spine)

func set_cover_path(path: String) -> void:
    var image: Image = Image.new()
    var error: int = image.load(path)
    if error != OK:
        return
    _cover_texture = ImageTexture.create_from_image(image)
    if _front_material != null:
        _front_material.albedo_texture = _cover_texture
        _front_material.albedo_color = Color.WHITE

func set_selected(value: bool) -> void:
    selected = value

func set_hover(value: bool, normalized_mouse: Vector2 = Vector2.ZERO) -> void:
    hovered = value
    hover_vector = normalized_mouse if value else Vector2.ZERO

func _process(delta: float) -> void:
    var position_follow: float = 1.0 - exp(-delta * 9.0)
    var rotation_follow: float = 1.0 - exp(-delta * 12.0)
    position = position.lerp(target_position, position_follow)

    var selected_boost: float = 1.045 if selected else 1.0
    var hover_boost: float = 1.035 if hovered else 1.0
    var final_scale: float = target_scale * selected_boost * hover_boost
    scale = scale.lerp(Vector3.ONE * final_scale, position_follow)

    var target_rot_x: float = deg_to_rad(-hover_vector.y * 3.2)
    var target_rot_y: float = deg_to_rad(hover_vector.x * 5.5)
    rotation.x = lerp_angle(rotation.x, target_rot_x, rotation_follow)
    rotation.y = lerp_angle(rotation.y, target_rot_y, rotation_follow)

    if _base_material != null:
        var glow: float = 0.12 if selected else 0.0
        if hovered:
            glow += 0.12
        _base_material.emission_enabled = glow > 0.0
        _base_material.emission = Color(0.38, 0.15, 0.72)
        _base_material.emission_energy_multiplier = glow
