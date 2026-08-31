extends Node3D
class_name GameCase3D

const STANDARD_TALL_MODEL_PATH: String = "res://assets/models/cases/standard_tall.glb"
const LEGACY_FINAL_MODEL_PATH: String = "res://assets/models/game_case.glb"
const PLACEHOLDER_MODEL_PATH: String = "res://assets/models/game_case_placeholder.glb"
const STANDARD_TALL_DISPLAY_SCALE: float = 10.0
const BASE_YAW_DEGREES: float = 0.0
const HOVER_YAW_DEGREES: float = 12.0
const HOVER_PITCH_DEGREES: float = 4.0
const COVER_PRINT_BRIGHTNESS: float = 0.90
const DRAG_YAW_LIMIT_DEGREES: float = 55.0
const DRAG_PITCH_LIMIT_DEGREES: float = 14.0
const DRAG_RETURN_DEGREES_PER_SECOND: float = 52.0
const PLASTIC_COLOR: Color = Color(0.75, 0.81, 0.84, 0.84)
const SPINE_COLOR: Color = Color(0.57, 0.66, 0.70, 0.76)
const EMPTY_COVER_COLOR: Color = Color(0.18, 0.21, 0.22, 1.0)

var item_id: String = ""
var title_text: String = ""
var selected: bool = false
var hovered: bool = false
var target_position: Vector3 = Vector3.ZERO
var target_scale: float = 1.0
var hover_vector: Vector2 = Vector2.ZERO
var _dragging: bool = false
var _drag_yaw_degrees: float = 0.0
var _drag_pitch_degrees: float = 0.0

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
    if FileAccess.file_exists(STANDARD_TALL_MODEL_PATH):
        model_path = STANDARD_TALL_MODEL_PATH
    elif FileAccess.file_exists(LEGACY_FINAL_MODEL_PATH):
        model_path = LEGACY_FINAL_MODEL_PATH

    var filesystem_path: String = ProjectSettings.globalize_path(model_path)
    var document: GLTFDocument = GLTFDocument.new()
    var state: GLTFState = GLTFState.new()
    var load_error: int = document.append_from_file(filesystem_path, state)
    if load_error != OK:
        push_error("G3 game case GLB import failed (%d): %s" % [load_error, model_path])
        return

    var instance: Node = document.generate_scene(state)
    if not (instance is Node3D):
        push_error("G3 game case GLB root must be Node3D: %s" % model_path)
        if instance != null:
            instance.free()
        return

    _model_root = instance as Node3D
    add_child(_model_root)
    if model_path == STANDARD_TALL_MODEL_PATH:
        _model_root.scale = Vector3.ONE * STANDARD_TALL_DISPLAY_SCALE
    _collect_meshes(_model_root)
    _apply_case_materials()
    rotation.y = deg_to_rad(BASE_YAW_DEGREES)

func _collect_meshes(node: Node) -> void:
    if node is MeshInstance3D:
        var mesh_node: MeshInstance3D = node as MeshInstance3D
        var key: String = str(mesh_node.name).to_lower()
        if key == "封面正面" or key.contains("cover_front"):
            _cover_mesh = mesh_node
        elif key == "封面书脊" or key.contains("spine"):
            _spine_meshes.append(mesh_node)
        else:
            _plastic_meshes.append(mesh_node)
    for child: Node in node.get_children():
        _collect_meshes(child)

func _apply_case_materials() -> void:
    for mesh_node: MeshInstance3D in _plastic_meshes:
        mesh_node.material_override = _make_acrylic_material(PLASTIC_COLOR, 0.18)

    for mesh_node: MeshInstance3D in _spine_meshes:
        mesh_node.material_override = _make_acrylic_material(SPINE_COLOR, 0.22)

    if _cover_mesh != null:
        var cover_material: StandardMaterial3D = StandardMaterial3D.new()
        cover_material.albedo_color = EMPTY_COVER_COLOR
        cover_material.metallic = 0.0
        cover_material.roughness = 0.46
        cover_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
        cover_material.transparency = BaseMaterial3D.TRANSPARENCY_DISABLED
        _cover_mesh.material_override = cover_material

func _make_acrylic_material(color: Color, roughness_value: float) -> StandardMaterial3D:
    var material: StandardMaterial3D = StandardMaterial3D.new()
    material.albedo_color = color
    material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    material.metallic = 0.0
    material.roughness = roughness_value
    material.specular_mode = BaseMaterial3D.SPECULAR_SCHLICK_GGX
    material.clearcoat_enabled = true
    material.clearcoat = 0.85
    material.clearcoat_roughness = 0.18
    material.cull_mode = BaseMaterial3D.CULL_BACK
    return material

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
    material.albedo_color = Color(COVER_PRINT_BRIGHTNESS, COVER_PRINT_BRIGHTNESS, COVER_PRINT_BRIGHTNESS, 1.0)
    material.metallic = 0.0
    material.roughness = 0.52
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    material.transparency = BaseMaterial3D.TRANSPARENCY_DISABLED

func set_theme_colors(accent: Color, secondary: Color) -> void:
    _accent = accent
    _secondary = secondary

func set_selected(value: bool) -> void:
    selected = value

func set_hover(value: bool, normalized_mouse: Vector2 = Vector2.ZERO) -> void:
    hovered = value
    hover_vector = normalized_mouse if value else Vector2.ZERO

func begin_drag() -> void:
    _dragging = true
    set_hover(false)

func set_drag_rotation(yaw_degrees: float, pitch_degrees: float) -> void:
    _drag_yaw_degrees = clampf(yaw_degrees, -DRAG_YAW_LIMIT_DEGREES, DRAG_YAW_LIMIT_DEGREES)
    _drag_pitch_degrees = clampf(pitch_degrees, -DRAG_PITCH_LIMIT_DEGREES, DRAG_PITCH_LIMIT_DEGREES)

func end_drag() -> void:
    _dragging = false

func _process(delta: float) -> void:
    var position_follow: float = 1.0 - exp(-delta * 9.0)
    var rotation_follow: float = 1.0 - exp(-delta * 12.0)
    position = position.lerp(target_position, position_follow)

    var selected_boost: float = 1.055 if selected else 1.0
    var hover_boost: float = 1.025 if hovered else 1.0
    var final_scale: float = target_scale * selected_boost * hover_boost
    scale = scale.lerp(Vector3.ONE * final_scale, position_follow)

    if not _dragging:
        var return_step: float = DRAG_RETURN_DEGREES_PER_SECOND * delta
        _drag_yaw_degrees = move_toward(_drag_yaw_degrees, 0.0, return_step)
        _drag_pitch_degrees = move_toward(_drag_pitch_degrees, 0.0, return_step)

    var target_rot_x: float = deg_to_rad(_drag_pitch_degrees - hover_vector.y * HOVER_PITCH_DEGREES)
    var target_rot_y: float = deg_to_rad(BASE_YAW_DEGREES + _drag_yaw_degrees + hover_vector.x * HOVER_YAW_DEGREES)
    rotation.x = lerp_angle(rotation.x, target_rot_x, rotation_follow)
    rotation.y = lerp_angle(rotation.y, target_rot_y, rotation_follow)
