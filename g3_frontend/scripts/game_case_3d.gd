extends Node3D
class_name GameCase3D

const FINAL_MODEL_PATH: String = "res://assets/models/game_case.glb"
const PLACEHOLDER_MODEL_PATH: String = "res://assets/models/game_case_placeholder.glb"
const BASE_YAW_DEGREES: float = 10.0

var item_id: String = ""
var title_text: String = ""
var selected: bool = false
var hovered: bool = false
var target_position: Vector3 = Vector3.ZERO
var target_scale: float = 1.0
var hover_vector: Vector2 = Vector2.ZERO

var _model_root: Node3D
var _plastic_meshes: Array[MeshInstance3D] = []
var _spine_meshes: Array[MeshInstance3D] = []
var _cover_mesh: MeshInstance3D
var _cover_texture: Texture2D
var _has_cover: bool = false
var _accent: Color = Color(0.20, 0.82, 0.76, 1.0)
var _secondary: Color = Color(0.25, 0.55, 0.90, 1.0)

func configure(game: Dictionary) -> void:
    item_id = str(game.get("id", ""))
    title_text = str(game.get("title", "Untitled"))
    _load_case_model()
    var cover_value: Variant = game.get("cover", "")
    var cover_path: String = "" if cover_value == null else str(cover_value)
    if not cover_path.is_empty():
        set_cover_path(cover_path)

func _load_case_model() -> void:
    if _model_root != null:
        return

    var model_path: String = PLACEHOLDER_MODEL_PATH
    if ResourceLoader.exists(FINAL_MODEL_PATH):
        model_path = FINAL_MODEL_PATH

    var resource: Resource = load(model_path)
    if not (resource is PackedScene):
        push_error("G3 game case model is not a PackedScene: %s" % model_path)
        return

    var instance: Node = (resource as PackedScene).instantiate()
    if not (instance is Node3D):
        push_error("G3 game case root must be Node3D: %s" % model_path)
        instance.queue_free()
        return

    _model_root = instance as Node3D
    add_child(_model_root)
    _collect_meshes(_model_root)
    _apply_case_materials()
    rotation.y = deg_to_rad(BASE_YAW_DEGREES)

func _collect_meshes(node: Node) -> void:
    if node is MeshInstance3D:
        var mesh_node: MeshInstance3D = node as MeshInstance3D
        var key: String = str(mesh_node.name).to_lower()
        if key.contains("cover_front"):
            _cover_mesh = mesh_node
        elif key.contains("spine"):
            _spine_meshes.append(mesh_node)
        else:
            _plastic_meshes.append(mesh_node)
    for child: Node in node.get_children():
        _collect_meshes(child)

func _apply_case_materials() -> void:
    for mesh_node: MeshInstance3D in _plastic_meshes:
        var material: StandardMaterial3D = StandardMaterial3D.new()
        material.albedo_color = _accent.darkened(0.72)
        material.metallic = 0.18
        material.roughness = 0.30
        mesh_node.material_override = material

    for mesh_node: MeshInstance3D in _spine_meshes:
        var material: StandardMaterial3D = StandardMaterial3D.new()
        material.albedo_color = _secondary.darkened(0.46)
        material.metallic = 0.10
        material.roughness = 0.36
        mesh_node.material_override = material

    if _cover_mesh != null:
        var cover_material: StandardMaterial3D = StandardMaterial3D.new()
        cover_material.albedo_color = _accent.darkened(0.50)
        cover_material.roughness = 0.42
        _cover_mesh.material_override = cover_material

func set_cover_path(path: String) -> void:
    if _cover_mesh == null:
        return
    var image: Image = Image.new()
    var error: int = image.load(path)
    if error != OK:
        push_warning("G3 cover image failed to load: %s" % path)
        return
    _cover_texture = ImageTexture.create_from_image(image)
    _has_cover = true
    var material: StandardMaterial3D = _cover_mesh.material_override as StandardMaterial3D
    if material == null:
        material = StandardMaterial3D.new()
        _cover_mesh.material_override = material
    material.albedo_texture = _cover_texture
    material.albedo_color = Color.WHITE
    material.roughness = 0.40

func set_theme_colors(accent: Color, secondary: Color) -> void:
    _accent = accent
    _secondary = secondary
    for mesh_node: MeshInstance3D in _plastic_meshes:
        var material: StandardMaterial3D = mesh_node.material_override as StandardMaterial3D
        if material != null:
            material.albedo_color = _accent.darkened(0.72)
            material.emission = _accent
    for mesh_node: MeshInstance3D in _spine_meshes:
        var material: StandardMaterial3D = mesh_node.material_override as StandardMaterial3D
        if material != null:
            material.albedo_color = _secondary.darkened(0.46)
    if _cover_mesh != null and not _has_cover:
        var cover_material: StandardMaterial3D = _cover_mesh.material_override as StandardMaterial3D
        if cover_material != null:
            cover_material.albedo_color = _accent.darkened(0.50)

func set_selected(value: bool) -> void:
    selected = value

func set_hover(value: bool, normalized_mouse: Vector2 = Vector2.ZERO) -> void:
    hovered = value
    hover_vector = normalized_mouse if value else Vector2.ZERO

func _process(delta: float) -> void:
    var position_follow: float = 1.0 - exp(-delta * 9.0)
    var rotation_follow: float = 1.0 - exp(-delta * 12.0)
    position = position.lerp(target_position, position_follow)

    var selected_boost: float = 1.055 if selected else 1.0
    var hover_boost: float = 1.035 if hovered else 1.0
    var final_scale: float = target_scale * selected_boost * hover_boost
    scale = scale.lerp(Vector3.ONE * final_scale, position_follow)

    var target_rot_x: float = deg_to_rad(-hover_vector.y * 3.0)
    var target_rot_y: float = deg_to_rad(BASE_YAW_DEGREES + hover_vector.x * 5.0)
    rotation.x = lerp_angle(rotation.x, target_rot_x, rotation_follow)
    rotation.y = lerp_angle(rotation.y, target_rot_y, rotation_follow)

    var glow: float = 0.12 if selected else 0.0
    if hovered:
        glow += 0.10
    for mesh_node: MeshInstance3D in _plastic_meshes:
        var material: StandardMaterial3D = mesh_node.material_override as StandardMaterial3D
        if material != null:
            material.emission_enabled = glow > 0.0
            material.emission = _accent
            material.emission_energy_multiplier = glow
