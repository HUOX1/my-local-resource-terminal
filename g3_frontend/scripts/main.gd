extends Node

const AMBIENT_SHADER: Shader = preload("res://shaders/ambient.gdshader")
const BACKEND_CLIENT_SCRIPT: Script = preload("res://scripts/backend_client.gd")
const CAROUSEL_SCRIPT: Script = preload("res://scripts/game_carousel.gd")
const PREVIEW_SCRIPT: Script = preload("res://scripts/preview_panel.gd")
const MANAGE_MENU_SCRIPT: Script = preload("res://scripts/manage_menu.gd")
const LAUNCH_PROFILE_DIALOG_SCRIPT: Script = preload("res://scripts/launch_profile_dialog.gd")
const GAME_METADATA_DIALOG_SCRIPT: Script = preload("res://scripts/game_metadata_dialog.gd")
const AUDIO_LOADER: Script = preload("res://scripts/audio_file_loader.gd")

const XMB_SECTIONS: Array[String] = ["GAMES", "MOVIES", "COMICS", "MUSIC", "SEARCH", "SYSTEM"]
const XMB_SECTION_LABELS: Array[String] = ["游戏", "电影", "漫画", "音乐", "搜索", "系统"]
const PREVIEW_SETTLE_SECONDS: float = 0.40

var backend
var collection_world: Node3D
var camera: Camera3D
var key_light: DirectionalLight3D
var fill_light: DirectionalLight3D
var rim_light: DirectionalLight3D
var carousel
var preview
var xmb_buttons: Array[Button] = []
var section_index: int = 0
var backend_label: Label
var fps_label: Label
var case_title_label: Label
var case_meta_label: Label
var runtime_error_label: Label
var hint_label: Label
var placeholder_label: Label
var system_panel: VBoxContainer
var add_game_dialog: FileDialog
var manage_menu
var launch_profile_dialog
var game_metadata_dialog
var theme_music_player: AudioStreamPlayer
var _ambient_material: ShaderMaterial
var _ambient_mesh: MeshInstance3D
var _preview_open: bool = false
var _selected_game: Dictionary = {}
var _pending_preview_id: String = ""
var _pending_games_id: String = ""
var _pending_launch_id: String = ""
var _pending_theme_id: String = ""
var _pending_state_id: String = ""
var _pending_settings_id: String = ""
var _pending_create_id: String = ""
var _pending_profile_get_id: String = ""
var _pending_profile_update_id: String = ""
var _pending_metadata_get_id: String = ""
var _pending_metadata_update_id: String = ""
var _preview_generation: int = 0
var _restore_item_id: String = ""
var _restore_section: String = "GAMES"
var _fps_accum: float = 0.0
var _theme_music_base_volume: float = 0.35
var _theme_music_enabled: bool = true
var _current_theme: Dictionary = {}
var _theme_text: Color = Color(0.93, 1.0, 1.0, 1.0)
var _theme_muted: Color = Color(0.55, 0.70, 0.72, 1.0)
var _theme_accent: Color = Color(0.20, 0.82, 0.76, 1.0)
var _theme_secondary: Color = Color(0.25, 0.55, 0.90, 1.0)
var _audio_tween: Tween
var _caption_tween: Tween

func _ready() -> void:
    _build_3d_world()
    _build_ambient()
    _build_ui()
    _build_backend()
    _set_section(0, false)
    backend.connect_backend()
    set_process(true)

func _build_ambient() -> void:
    _ambient_mesh = MeshInstance3D.new()
    _ambient_mesh.name = "AmbientBackground3D"
    _ambient_mesh.position = Vector3(0.0, 0.0, -6.0)

    var quad: QuadMesh = QuadMesh.new()
    _ambient_mesh.mesh = quad

    _ambient_material = ShaderMaterial.new()
    _ambient_material.shader = AMBIENT_SHADER
    _ambient_mesh.material_override = _ambient_material

    collection_world.add_child(_ambient_mesh)
    _resize_ambient_mesh()
    get_viewport().size_changed.connect(_resize_ambient_mesh)

func _resize_ambient_mesh() -> void:
    if _ambient_mesh == null or camera == null:
        return

    var viewport_size: Vector2 = get_viewport().get_visible_rect().size
    if viewport_size.y <= 0.0:
        return

    var distance: float = absf(camera.global_position.z - _ambient_mesh.global_position.z)
    var half_height: float = tan(deg_to_rad(camera.fov * 0.5)) * distance
    var aspect: float = viewport_size.x / viewport_size.y
    var overscan: float = 1.02
    var quad: QuadMesh = _ambient_mesh.mesh as QuadMesh
    quad.size = Vector2(
        half_height * 2.0 * aspect * overscan,
        half_height * 2.0 * overscan
    )

func _build_3d_world() -> void:
    collection_world = Node3D.new()
    collection_world.name = "CollectionWorld"
    add_child(collection_world)

    camera = Camera3D.new()
    camera.position = Vector3(0.0, 0.0, 7.2)
    camera.current = true
    collection_world.add_child(camera)

    var world_environment: WorldEnvironment = WorldEnvironment.new()
    var environment: Environment = Environment.new()
    environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment.ambient_light_color = Color(0.46, 0.52, 0.56, 1.0)
    environment.ambient_light_energy = 0.12
    environment.ambient_light_sky_contribution = 0.0
    environment.ssao_enabled = true
    environment.ssao_radius = 0.18
    environment.ssao_intensity = 1.10
    world_environment.environment = environment
    collection_world.add_child(world_environment)

    key_light = DirectionalLight3D.new()
    key_light.rotation_degrees = Vector3(-24.0, -34.0, 0.0)
    key_light.light_energy = 0.74
    key_light.light_color = Color(1.0, 0.94, 0.88, 1.0)
    collection_world.add_child(key_light)

    fill_light = DirectionalLight3D.new()
    fill_light.rotation_degrees = Vector3(-8.0, 38.0, 0.0)
    fill_light.light_energy = 0.18
    fill_light.light_color = Color(0.74, 0.84, 1.0, 1.0)
    collection_world.add_child(fill_light)

    rim_light = DirectionalLight3D.new()
    rim_light.rotation_degrees = Vector3(12.0, 148.0, 0.0)
    rim_light.light_energy = 0.54
    rim_light.light_color = _theme_accent.lerp(Color.WHITE, 0.55)
    collection_world.add_child(rim_light)

    carousel = CAROUSEL_SCRIPT.new()
    collection_world.add_child(carousel)
    carousel.configure(camera)
    carousel.selection_changed.connect(_on_selection_changed)
    carousel.main_case_clicked.connect(_on_main_case_clicked)
    carousel.main_case_double_clicked.connect(_on_main_case_double_clicked)
    carousel.main_case_right_clicked.connect(_on_main_case_right_clicked)

func _build_ui() -> void:
    var layer: CanvasLayer = CanvasLayer.new()
    layer.layer = 10
    add_child(layer)

    var ui: Control = Control.new()
    ui.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    ui.mouse_filter = Control.MOUSE_FILTER_IGNORE
    layer.add_child(ui)

    var x: float = 62.0
    for i: int in range(XMB_SECTIONS.size()):
        var button: Button = Button.new()
        button.position = Vector2(x, 46.0)
        button.size = Vector2(144.0, 48.0)
        button.text = XMB_SECTION_LABELS[i]
        button.flat = true
        button.focus_mode = Control.FOCUS_NONE
        button.add_theme_font_size_override("font_size", 17)
        button.pressed.connect(_on_xmb_pressed.bind(i))
        ui.add_child(button)
        xmb_buttons.append(button)
        x += 148.0

    case_title_label = Label.new()
    case_title_label.size = Vector2(440.0, 42.0)
    case_title_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    case_title_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
    case_title_label.add_theme_font_size_override("font_size", 28)
    case_title_label.add_theme_color_override("font_color", _theme_text)
    case_title_label.modulate.a = 0.0
    ui.add_child(case_title_label)

    case_meta_label = Label.new()
    case_meta_label.size = Vector2(440.0, 26.0)
    case_meta_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    case_meta_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
    case_meta_label.add_theme_font_size_override("font_size", 12)
    case_meta_label.add_theme_color_override("font_color", _theme_muted)
    case_meta_label.modulate.a = 0.0
    ui.add_child(case_meta_label)

    backend_label = Label.new()
    backend_label.set_anchors_preset(Control.PRESET_TOP_RIGHT)
    backend_label.position = Vector2(-340.0, 60.0)
    backend_label.size = Vector2(220.0, 28.0)
    backend_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
    backend_label.text = "后端连接中"
    backend_label.add_theme_font_size_override("font_size", 12)
    ui.add_child(backend_label)

    fps_label = Label.new()
    fps_label.set_anchors_preset(Control.PRESET_TOP_RIGHT)
    fps_label.position = Vector2(-110.0, 60.0)
    fps_label.size = Vector2(72.0, 28.0)
    fps_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
    fps_label.add_theme_font_size_override("font_size", 12)
    ui.add_child(fps_label)

    runtime_error_label = Label.new()
    runtime_error_label.set_anchors_preset(Control.PRESET_TOP_RIGHT)
    runtime_error_label.position = Vector2(-650.0, 96.0)
    runtime_error_label.size = Vector2(610.0, 58.0)
    runtime_error_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
    runtime_error_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    runtime_error_label.add_theme_font_size_override("font_size", 12)
    runtime_error_label.add_theme_color_override("font_color", Color(1.0, 0.60, 0.52))
    runtime_error_label.visible = false
    runtime_error_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
    ui.add_child(runtime_error_label)

    hint_label = Label.new()
    hint_label.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
    hint_label.position = Vector2(78.0, -72.0)
    hint_label.size = Vector2(820.0, 30.0)
    hint_label.text = "滚轮 / ← → 选择    单击预览    聚焦后拖动盒子旋转    双击启动    右键管理    Ctrl+Q 退出"
    hint_label.add_theme_font_size_override("font_size", 12)
    hint_label.add_theme_color_override("font_color", _theme_muted)
    ui.add_child(hint_label)

    preview = PREVIEW_SCRIPT.new()
    preview.position = Vector2(708.0, 150.0)
    preview.size = Vector2(660.0, 592.0)
    preview.visible = false
    preview.media_audio_activity_changed.connect(_on_preview_audio_activity_changed)
    ui.add_child(preview)

    theme_music_player = AudioStreamPlayer.new()
    add_child(theme_music_player)

    placeholder_label = Label.new()
    placeholder_label.position = Vector2(78.0, 240.0)
    placeholder_label.size = Vector2(980.0, 100.0)
    placeholder_label.add_theme_font_size_override("font_size", 20)
    placeholder_label.add_theme_color_override("font_color", _theme_muted)
    placeholder_label.visible = false
    ui.add_child(placeholder_label)

    system_panel = VBoxContainer.new()
    system_panel.position = Vector2(78.0, 150.0)
    system_panel.size = Vector2(760.0, 560.0)
    system_panel.add_theme_constant_override("separation", 14)
    system_panel.visible = false
    ui.add_child(system_panel)

    var add_game_button: Button = Button.new()
    add_game_button.text = "添加游戏…"
    add_game_button.custom_minimum_size = Vector2(320.0, 46.0)
    add_game_button.pressed.connect(_open_add_game_dialog)
    system_panel.add_child(add_game_button)

    var window_button: Button = Button.new()
    window_button.text = "窗口 / 最大化切换"
    window_button.custom_minimum_size = Vector2(320.0, 46.0)
    window_button.pressed.connect(_toggle_window_mode)
    system_panel.add_child(window_button)

    var exit_button: Button = Button.new()
    exit_button.text = "退出 G3"
    exit_button.custom_minimum_size = Vector2(320.0, 46.0)
    exit_button.pressed.connect(_exit_application)
    system_panel.add_child(exit_button)

    var system_note: Label = Label.new()
    system_note.text = "G3 当前状态\n已可用：启动器 / Python Core / 本地库 / 中文 XMB / 右键管理 / 启动设置 / 编辑资料 / 实体 3D 游戏盒\n本轮更新：浏览态回到大封面居中轮播、聚焦主盒显著放大、亚克力半透明盒体、预览文字/媒体入场动画、右键菜单改为清晰中文面板、预览详情点击不再误返回、System 增加退出 G3 / Ctrl+Q\n性能策略：默认 60 FPS 上限、轻量 MSAA、弱化背景与 SSAO 开销、游戏运行时最小化并暂停渲染\n当前仍保留入口：电影 / 漫画 / 音乐 / 搜索\n数据目录：%LOCALAPPDATA%\\G3  ·  Backend 127.0.0.1"
    system_note.add_theme_font_size_override("font_size", 13)
    system_note.add_theme_color_override("font_color", _theme_muted)
    system_panel.add_child(system_note)

    add_game_dialog = FileDialog.new()
    add_game_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    add_game_dialog.access = FileDialog.ACCESS_FILESYSTEM
    add_game_dialog.filters = PackedStringArray(["*.exe ; Windows Executable"])
    add_game_dialog.size = Vector2i(920, 620)
    add_game_dialog.file_selected.connect(_on_game_executable_selected)
    ui.add_child(add_game_dialog)

    manage_menu = MANAGE_MENU_SCRIPT.new()
    manage_menu.action_requested.connect(_on_manage_action_requested)
    ui.add_child(manage_menu)

    launch_profile_dialog = LAUNCH_PROFILE_DIALOG_SCRIPT.new()
    launch_profile_dialog.save_requested.connect(_on_launch_profile_save_requested)
    add_child(launch_profile_dialog)

    game_metadata_dialog = GAME_METADATA_DIALOG_SCRIPT.new()
    game_metadata_dialog.save_requested.connect(_on_game_metadata_save_requested)
    add_child(game_metadata_dialog)

func _build_backend() -> void:
    backend = BACKEND_CLIENT_SCRIPT.new()
    add_child(backend)
    backend.connected.connect(_on_backend_connected)
    backend.disconnected.connect(_on_backend_disconnected)
    backend.response_received.connect(_on_backend_response)
    backend.event_received.connect(_on_backend_event)

func _process(delta: float) -> void:
    _fps_accum += delta
    if _fps_accum >= 0.25:
        _fps_accum = 0.0
        fps_label.text = "%d FPS" % Engine.get_frames_per_second()
    _update_case_caption_position()

func _unhandled_input(event: InputEvent) -> void:
    if not _preview_open or section_index != 0:
        return
    if not (event is InputEventMouseButton):
        return
    var mouse_event: InputEventMouseButton = event as InputEventMouseButton
    if not mouse_event.pressed or mouse_event.button_index != MOUSE_BUTTON_LEFT:
        return
    _close_preview()
    get_viewport().set_input_as_handled()

func _unhandled_key_input(event: InputEvent) -> void:
    if not (event is InputEventKey):
        return
    var key: InputEventKey = event as InputEventKey
    if not key.pressed or key.echo:
        return
    if key.ctrl_pressed and key.keycode == KEY_Q:
        _exit_application()
        get_viewport().set_input_as_handled()
    elif key.keycode == KEY_ESCAPE and _preview_open:
        _close_preview()
        get_viewport().set_input_as_handled()
    elif key.keycode == KEY_TAB:
        _set_section((section_index + 1) % XMB_SECTIONS.size())
        get_viewport().set_input_as_handled()

func _on_xmb_pressed(index: int) -> void:
    _set_section(index)

func _set_section(index: int, persist: bool = true) -> void:
    section_index = clampi(index, 0, XMB_SECTIONS.size() - 1)
    for i: int in range(xmb_buttons.size()):
        var active: bool = i == section_index
        var button: Button = xmb_buttons[i]
        button.add_theme_color_override(
            "font_color",
            _theme_text if active else _theme_muted
        )
        button.add_theme_font_size_override("font_size", 22 if active else 16)

    var section: String = XMB_SECTIONS[section_index]
    carousel.visible = section == "GAMES"
    system_panel.visible = section == "SYSTEM"
    placeholder_label.visible = section != "GAMES" and section != "SYSTEM"
    if placeholder_label.visible:
        placeholder_label.text = _section_label(section) + "  /  当前仅保留模块入口"
    if section != "GAMES":
        _close_preview()
        _set_case_caption_visible(false, true)
    else:
        _refresh_case_caption()
        _set_case_caption_visible(not _preview_open, true)

    if persist and backend != null and backend.is_connected_to_backend():
        backend.request("state.update", {"last_section": section.to_lower()})

func _on_backend_connected() -> void:
    backend_label.text = "后端已连接"
    _pending_state_id = backend.request("state.get", {})
    _pending_games_id = backend.request("library.games.list", {})
    _pending_theme_id = backend.request("theme.current", {})
    _pending_settings_id = backend.request("settings.get", {})

func _on_backend_disconnected(code: int, reason: String) -> void:
    backend_label.text = "后端离线  %d" % code
    if not reason.is_empty():
        backend_label.tooltip_text = reason

func _on_backend_response(request_id: String, ok: bool, data: Variant, error: Variant) -> void:
    if request_id == _pending_state_id:
        _pending_state_id = ""
        if ok and data is Dictionary:
            var state: Dictionary = data as Dictionary
            _restore_item_id = str(state.get("last_item_id", ""))
            _restore_section = str(state.get("last_section", "games")).to_upper()
            var index: int = XMB_SECTIONS.find(_restore_section)
            if index >= 0:
                _set_section(index, false)
        return

    if request_id == _pending_games_id:
        _pending_games_id = ""
        if ok and data is Array:
            var result: Array[Dictionary] = []
            for value: Variant in data as Array:
                if value is Dictionary:
                    result.append(value as Dictionary)
            carousel.set_games(result)
            if not _restore_item_id.is_empty():
                _restore_selection_by_id(_restore_item_id)
        return

    if request_id == _pending_theme_id:
        _pending_theme_id = ""
        if ok and data is Dictionary:
            _current_theme = data as Dictionary
            _apply_theme(_current_theme)
        return

    if request_id == _pending_settings_id:
        _pending_settings_id = ""
        if ok and data is Dictionary:
            var settings: Dictionary = data as Dictionary
            var preview_enabled: bool = bool(settings.get("preview_audio", true))
            var preview_volume: float = float(settings.get("preview_volume", 0.25))
            preview.set_audio_preferences(preview_enabled, preview_volume)
            _theme_music_enabled = bool(settings.get("theme_music", true))
            _theme_music_base_volume = clampf(float(settings.get("theme_music_volume", 0.35)), 0.0, 1.0)
            if not _current_theme.is_empty():
                _apply_theme_audio(_current_theme)
        return

    if request_id == _pending_preview_id:
        _pending_preview_id = ""
        if ok and data is Dictionary:
            preview.show_game(_selected_game, data as Dictionary)
        else:
            preview.show_game(_selected_game, {})
        return

    if request_id == _pending_profile_get_id:
        _pending_profile_get_id = ""
        if ok and data is Dictionary:
            launch_profile_dialog.show_profile(str(_selected_game.get("id", "")), data as Dictionary)
        else:
            _show_runtime_error("启动设置读取失败", _error_message(error))
        return

    if request_id == _pending_profile_update_id:
        _pending_profile_update_id = ""
        if ok:
            backend_label.text = "启动设置已保存"
            _clear_runtime_error()
            _pending_games_id = backend.request("library.games.list", {})
        else:
            _show_runtime_error("启动设置保存失败", _error_message(error))
        return

    if request_id == _pending_metadata_get_id:
        _pending_metadata_get_id = ""
        if ok and data is Dictionary:
            game_metadata_dialog.show_metadata(str(_selected_game.get("id", "")), data as Dictionary)
        else:
            _show_runtime_error("资料读取失败", _error_message(error))
        return

    if request_id == _pending_metadata_update_id:
        _pending_metadata_update_id = ""
        if ok:
            backend_label.text = "资料已保存"
            _clear_runtime_error()
            _pending_games_id = backend.request("library.games.list", {})
        else:
            _show_runtime_error("资料保存失败", _error_message(error))
        return

    if request_id == _pending_launch_id:
        _pending_launch_id = ""
        if not ok:
            var launch_error: String = _error_message(error)
            backend_label.text = "启动失败"
            backend_label.tooltip_text = launch_error
            _show_runtime_error("启动失败", launch_error)
        return

    if request_id == _pending_create_id:
        _pending_create_id = ""
        if not ok:
            var create_error: String = _error_message(error)
            backend_label.text = "添加游戏失败"
            backend_label.tooltip_text = create_error
            _show_runtime_error("添加游戏失败", create_error)
        return

func _on_backend_event(event_type: String, payload: Dictionary) -> void:
    if event_type == "library.changed":
        _pending_games_id = backend.request("library.games.list", {})
    elif event_type == "game.started":
        _clear_runtime_error()
        backend_label.text = "等待游戏进程"
    elif event_type == "game.session_started":
        backend_label.text = "游戏运行中"
        call_deferred("_enter_gameplay_mode")
    elif event_type == "game.exited":
        _restore_item_id = str(payload.get("item_id", ""))
        call_deferred("_restore_from_gameplay")
        backend_label.text = "后端已连接"
        _pending_games_id = backend.request("library.games.list", {})
    elif event_type == "backend.error":
        var error_code: String = str(payload.get("code", ""))
        if error_code.begins_with("game_"):
            call_deferred("_restore_from_gameplay")
            backend_label.text = "游戏启动失败"
        _show_runtime_error("后端错误", _error_message(payload))

func _on_selection_changed(_index: int, game: Dictionary) -> void:
    _selected_game = game
    _refresh_case_caption()
    if section_index == 0 and not _preview_open:
        _set_case_caption_visible(true)
    var item_id: String = str(game.get("id", ""))
    if not item_id.is_empty() and backend != null and backend.is_connected_to_backend():
        backend.request("state.update", {"last_item_id": item_id})
    if _preview_open:
        _schedule_preview(game)

func _on_main_case_clicked(game: Dictionary) -> void:
    _selected_game = game
    if not _preview_open:
        _preview_open = true
        carousel.set_preview_mode(true)
        preview.visible = true
        _set_case_caption_visible(false)
    _schedule_preview(game)

func _on_main_case_double_clicked(game: Dictionary) -> void:
    _launch_game(game)

func _on_main_case_right_clicked(game: Dictionary, screen_position: Vector2) -> void:
    _selected_game = game
    manage_menu.show_at(screen_position)

func _on_manage_action_requested(action: String) -> void:
    if _selected_game.is_empty():
        return
    match action:
        "launch":
            _launch_game(_selected_game)
        "preview":
            _on_main_case_clicked(_selected_game)
        "launch_settings":
            var item_id: String = str(_selected_game.get("id", ""))
            if not item_id.is_empty():
                _pending_profile_get_id = backend.request("game.launch_profile.get", {"id": item_id})
        "edit_metadata":
            var metadata_item_id: String = str(_selected_game.get("id", ""))
            if not metadata_item_id.is_empty():
                _pending_metadata_get_id = backend.request("game.metadata.get", {"id": metadata_item_id})
        "media_assets":
            _show_runtime_error("媒体素材", "入口已建立，素材管理器将在下一批补齐。")
        "remove":
            _show_runtime_error("移除收藏", "入口已建立，安全移除流程将在下一批补齐。")

func _launch_game(game: Dictionary) -> void:
    _preview_generation += 1
    var item_id: String = str(game.get("id", ""))
    if item_id.is_empty():
        return
    _pending_launch_id = backend.request("game.launch", {"id": item_id})

func _on_launch_profile_save_requested(item_id: String, profile: Dictionary) -> void:
    if item_id.is_empty():
        return
    var payload: Dictionary = profile.duplicate(true)
    payload["id"] = item_id
    _pending_profile_update_id = backend.request("game.launch_profile.update", payload)

func _on_game_metadata_save_requested(item_id: String, metadata: Dictionary) -> void:
    if item_id.is_empty():
        return
    _restore_item_id = item_id
    var payload: Dictionary = metadata.duplicate(true)
    payload["id"] = item_id
    _pending_metadata_update_id = backend.request("game.metadata.update", payload)

func _schedule_preview(game: Dictionary) -> void:
    _preview_generation += 1
    var generation: int = _preview_generation
    await get_tree().create_timer(PREVIEW_SETTLE_SECONDS).timeout
    if generation != _preview_generation or not _preview_open:
        return
    if str(game.get("id", "")) != str(_selected_game.get("id", "")):
        return
    _request_preview(game)

func _request_preview(game: Dictionary) -> void:
    var item_id: String = str(game.get("id", ""))
    if item_id.is_empty():
        preview.show_game(game, {})
        return
    _pending_preview_id = backend.request("game.preview", {"id": item_id})

func _close_preview() -> void:
    _preview_generation += 1
    _preview_open = false
    carousel.set_preview_mode(false)
    preview.hide_preview()
    if section_index == 0 and not _selected_game.is_empty():
        _set_case_caption_visible(true)

func _restore_selection_by_id(item_id: String) -> void:
    for i: int in range(carousel.games.size()):
        if str(carousel.games[i].get("id", "")) == item_id:
            carousel.select_index(i)
            return

func _apply_theme(theme: Dictionary) -> void:
    var colors_value: Variant = theme.get("colors", {})
    var colors: Dictionary = {}
    if colors_value is Dictionary:
        colors = colors_value as Dictionary
    _theme_text = _theme_color(colors, "text", Color(0.93, 1.0, 1.0, 1.0))
    _theme_muted = _theme_color(colors, "muted_text", Color(0.55, 0.70, 0.72, 1.0))
    _theme_accent = _theme_color(colors, "accent", Color(0.20, 0.82, 0.76, 1.0))
    _theme_secondary = _theme_color(colors, "accent_secondary", Color(0.25, 0.55, 0.90, 1.0))
    var top_color: Color = _theme_color(colors, "base_top", Color(0.05, 0.28, 0.32, 1.0))
    var bottom_color: Color = _theme_color(colors, "base_bottom", Color(0.01, 0.10, 0.14, 1.0))
    var wave_a: Color = _theme_color(colors, "wave_a", _theme_accent)
    var wave_b: Color = _theme_color(colors, "wave_b", _theme_secondary)
    var symbol: Color = _theme_color(colors, "symbol", _theme_text)

    _ambient_material.set_shader_parameter("top_color", _color_vec3(top_color))
    _ambient_material.set_shader_parameter("bottom_color", _color_vec3(bottom_color))
    _ambient_material.set_shader_parameter("wave_a", _color_vec3(wave_a))
    _ambient_material.set_shader_parameter("wave_b", _color_vec3(wave_b))
    _ambient_material.set_shader_parameter("symbol_color", _color_vec3(symbol))
    if rim_light != null:
        rim_light.light_color = _theme_accent.lerp(Color.WHITE, 0.55)
    carousel.set_theme_colors(_theme_accent, _theme_secondary)
    case_title_label.add_theme_color_override("font_color", _theme_text)
    case_meta_label.add_theme_color_override("font_color", _theme_muted)
    hint_label.add_theme_color_override("font_color", _theme_muted)

    var ambient_value: Variant = theme.get("ambient", {})
    if ambient_value is Dictionary:
        var ambient: Dictionary = ambient_value as Dictionary
        _ambient_material.set_shader_parameter(
            "wave_amount",
            clampf(float(ambient.get("wave_strength", 0.82)), 0.0, 1.0)
        )
        _ambient_material.set_shader_parameter(
            "symbol_amount",
            clampf(float(ambient.get("symbol_opacity", 0.24)) * 1.75, 0.0, 1.0)
        )
    _set_section(section_index, false)
    _apply_theme_audio(theme)

func _theme_color(colors: Dictionary, key: String, fallback: Color) -> Color:
    var value: String = str(colors.get(key, ""))
    if value.is_empty():
        return fallback
    return Color.from_string(value, fallback)

func _color_vec3(value: Color) -> Vector3:
    return Vector3(value.r, value.g, value.b)

func _refresh_case_caption() -> void:
    if case_title_label == null or case_meta_label == null:
        return
    if _selected_game.is_empty():
        case_title_label.text = ""
        case_meta_label.text = ""
        _set_case_caption_visible(false, true)
        return
    case_title_label.text = str(_selected_game.get("title", "Untitled"))
    case_meta_label.text = _format_game_meta(_selected_game)

func _format_game_meta(game: Dictionary) -> String:
    var platform: String = str(game.get("platform", "")).strip_edges()
    if platform.is_empty():
        platform = "PC"
    var playtime_seconds: int = int(game.get("playtime_seconds", 0))
    var played_hours: float = float(playtime_seconds) / 3600.0
    return "%s  ·  %.1f 小时" % [platform.to_upper(), played_hours]

func _update_case_caption_position() -> void:
    if case_title_label == null or carousel == null or camera == null or section_index != 0:
        return
    var selected_case_world_position: Vector3 = carousel.selected_case_world_position()
    if selected_case_world_position.x > 9000.0:
        return
    var caption_world_position: Vector3 = selected_case_world_position + Vector3(0.0, -1.16, 0.0)
    var anchor: Vector2 = camera.unproject_position(caption_world_position)
    case_title_label.position = Vector2(anchor.x - case_title_label.size.x * 0.5, anchor.y)
    case_meta_label.position = Vector2(anchor.x - case_meta_label.size.x * 0.5, anchor.y + 38.0)

func _set_case_caption_visible(value: bool, immediate: bool = false) -> void:
    if case_title_label == null or case_meta_label == null:
        return
    if _caption_tween != null and _caption_tween.is_valid():
        _caption_tween.kill()
    var target_alpha: float = 1.0 if value else 0.0
    if immediate:
        case_title_label.modulate.a = target_alpha
        case_meta_label.modulate.a = target_alpha
        return
    _caption_tween = create_tween()
    _caption_tween.set_parallel(true)
    _caption_tween.tween_property(case_title_label, "modulate:a", target_alpha, 0.24)
    _caption_tween.tween_property(case_meta_label, "modulate:a", target_alpha, 0.24)

func _error_message(error: Variant) -> String:
    if error is Dictionary:
        var payload: Dictionary = error as Dictionary
        return str(payload.get("message", payload))
    return str(error)

func _show_runtime_error(prefix: String, message: String) -> void:
    runtime_error_label.text = "%s · %s" % [prefix, message]
    runtime_error_label.visible = true
    push_error(runtime_error_label.text)

func _clear_runtime_error() -> void:
    runtime_error_label.visible = false
    runtime_error_label.text = ""

func _apply_theme_audio(theme: Dictionary) -> void:
    if theme_music_player == null:
        return
    var audio_value: Variant = theme.get("audio", {})
    if not (audio_value is Dictionary):
        theme_music_player.stop()
        theme_music_player.stream = null
        return
    var audio: Dictionary = audio_value as Dictionary
    var music_rel: String = str(audio.get("music", ""))
    var theme_dir: String = str(theme.get("directory", ""))
    if not _theme_music_enabled or music_rel.is_empty() or theme_dir.is_empty():
        theme_music_player.stop()
        theme_music_player.stream = null
        return
    var music_path: String = theme_dir.path_join(music_rel)
    var stream: AudioStream = AUDIO_LOADER.load_audio(music_path, bool(audio.get("loop", true)))
    if stream == null:
        theme_music_player.stop()
        theme_music_player.stream = null
        return
    theme_music_player.stream = stream
    theme_music_player.volume_db = linear_to_db(maxf(_theme_music_base_volume, 0.0001))
    theme_music_player.play()

func _open_add_game_dialog() -> void:
    add_game_dialog.popup_centered_ratio(0.82)

func _on_game_executable_selected(path: String) -> void:
    if not backend.is_connected_to_backend():
        backend_label.text = "后端离线"
        return
    var file_name: String = path.get_file().get_basename()
    _pending_create_id = backend.request(
        "game.create",
        {
            "title": file_name,
            "executable_path": path,
            "working_directory": path.get_base_dir(),
        }
    )

func _toggle_window_mode() -> void:
    if get_window().mode == Window.MODE_MAXIMIZED:
        get_window().mode = Window.MODE_WINDOWED
        get_window().borderless = false
    else:
        get_window().borderless = true
        get_window().mode = Window.MODE_MAXIMIZED

func _section_label(section: String) -> String:
    var index: int = XMB_SECTIONS.find(section)
    if index >= 0 and index < XMB_SECTION_LABELS.size():
        return XMB_SECTION_LABELS[index]
    return section

func _enter_gameplay_mode() -> void:
    var window: Window = get_window()
    if window == null:
        return
    if window.mode != Window.MODE_MINIMIZED:
        window.mode = Window.MODE_MINIMIZED
    RenderingServer.render_loop_enabled = false

func _restore_from_gameplay() -> void:
    RenderingServer.render_loop_enabled = true
    var window: Window = get_window()
    if window == null:
        return
    window.borderless = true
    if window.mode != Window.MODE_MAXIMIZED:
        window.mode = Window.MODE_MAXIMIZED
    window.grab_focus()

func _exit_application() -> void:
    get_tree().quit()

func _on_preview_audio_activity_changed(active: bool) -> void:
    if theme_music_player == null or not theme_music_player.playing:
        return
    if _audio_tween != null and _audio_tween.is_valid():
        _audio_tween.kill()
    var target_linear: float = _theme_music_base_volume * (0.30 if active else 1.0)
    var target_db: float = linear_to_db(maxf(target_linear, 0.0001))
    _audio_tween = create_tween()
    _audio_tween.tween_property(theme_music_player, "volume_db", target_db, 0.28)
