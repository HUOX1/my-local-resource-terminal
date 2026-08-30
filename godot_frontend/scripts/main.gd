extends Node

const AMBIENT_SHADER: Shader = preload("res://shaders/ambient.gdshader")
const BACKEND_CLIENT_SCRIPT: Script = preload("res://scripts/backend_client.gd")
const CAROUSEL_SCRIPT: Script = preload("res://scripts/game_carousel.gd")
const PREVIEW_SCRIPT: Script = preload("res://scripts/preview_panel.gd")
const AUDIO_LOADER: Script = preload("res://scripts/audio_file_loader.gd")

const XMB_SECTIONS: Array[String] = ["GAMES", "MOVIES", "COMICS", "MUSIC", "SEARCH", "SYSTEM"]
const PREVIEW_SETTLE_SECONDS: float = 0.40

var backend
var camera: Camera3D
var carousel
var preview
var xmb_buttons: Array[Button] = []
var section_index: int = 0
var backend_label: Label
var fps_label: Label
var title_label: Label
var hint_label: Label
var placeholder_label: Label
var system_panel: VBoxContainer
var add_game_dialog: FileDialog
var theme_music_player: AudioStreamPlayer
var _ambient_material: ShaderMaterial
var _preview_open: bool = false
var _selected_game: Dictionary = {}
var _pending_preview_id: String = ""
var _pending_games_id: String = ""
var _pending_launch_id: String = ""
var _pending_theme_id: String = ""
var _pending_state_id: String = ""
var _pending_settings_id: String = ""
var _pending_create_id: String = ""
var _preview_generation: int = 0
var _restore_item_id: String = ""
var _restore_section: String = "GAMES"
var _fps_accum: float = 0.0
var _theme_music_base_volume: float = 0.35
var _theme_music_enabled: bool = true
var _current_theme: Dictionary = {}
var _audio_tween: Tween

func _ready() -> void:
    _build_ambient()
    _build_3d_world()
    _build_ui()
    _build_backend()
    _set_section(0, false)
    backend.connect_backend()
    set_process(true)

func _build_ambient() -> void:
    var layer: CanvasLayer = CanvasLayer.new()
    layer.layer = -10
    add_child(layer)
    var background: ColorRect = ColorRect.new()
    background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    background.mouse_filter = Control.MOUSE_FILTER_IGNORE
    _ambient_material = ShaderMaterial.new()
    _ambient_material.shader = AMBIENT_SHADER
    background.material = _ambient_material
    layer.add_child(background)

func _build_3d_world() -> void:
    var world: Node3D = Node3D.new()
    world.name = "CollectionWorld"
    add_child(world)

    camera = Camera3D.new()
    camera.position = Vector3(0.0, 0.0, 7.2)
    camera.current = true
    world.add_child(camera)

    var light: DirectionalLight3D = DirectionalLight3D.new()
    light.rotation_degrees = Vector3(-15.0, -25.0, 0.0)
    light.light_energy = 1.15
    light.light_color = Color(0.82, 0.86, 1.0)
    world.add_child(light)

    var fill: OmniLight3D = OmniLight3D.new()
    fill.position = Vector3(-2.5, 1.0, 3.0)
    fill.omni_range = 8.0
    fill.light_energy = 1.3
    fill.light_color = Color(0.45, 0.18, 0.95)
    world.add_child(fill)

    carousel = CAROUSEL_SCRIPT.new()
    world.add_child(carousel)
    carousel.configure(camera)
    carousel.selection_changed.connect(_on_selection_changed)
    carousel.main_case_clicked.connect(_on_main_case_clicked)
    carousel.main_case_double_clicked.connect(_on_main_case_double_clicked)

func _build_ui() -> void:
    var layer: CanvasLayer = CanvasLayer.new()
    layer.layer = 10
    add_child(layer)

    var ui: Control = Control.new()
    ui.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    layer.add_child(ui)

    var x: float = 62.0
    for i: int in range(XMB_SECTIONS.size()):
        var button: Button = Button.new()
        button.position = Vector2(x, 46.0)
        button.size = Vector2(144.0, 48.0)
        button.text = XMB_SECTIONS[i]
        button.flat = true
        button.focus_mode = Control.FOCUS_NONE
        button.add_theme_font_size_override("font_size", 17)
        button.pressed.connect(_on_xmb_pressed.bind(i))
        ui.add_child(button)
        xmb_buttons.append(button)
        x += 148.0

    title_label = Label.new()
    title_label.position = Vector2(78.0, 118.0)
    title_label.size = Vector2(720.0, 52.0)
    title_label.add_theme_font_size_override("font_size", 34)
    ui.add_child(title_label)

    backend_label = Label.new()
    backend_label.set_anchors_preset(Control.PRESET_TOP_RIGHT)
    backend_label.position = Vector2(-340.0, 60.0)
    backend_label.size = Vector2(220.0, 28.0)
    backend_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
    backend_label.text = "BACKEND CONNECTING"
    backend_label.add_theme_font_size_override("font_size", 12)
    ui.add_child(backend_label)

    fps_label = Label.new()
    fps_label.set_anchors_preset(Control.PRESET_TOP_RIGHT)
    fps_label.position = Vector2(-110.0, 60.0)
    fps_label.size = Vector2(72.0, 28.0)
    fps_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
    fps_label.add_theme_font_size_override("font_size", 12)
    ui.add_child(fps_label)

    hint_label = Label.new()
    hint_label.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
    hint_label.position = Vector2(78.0, -72.0)
    hint_label.size = Vector2(820.0, 30.0)
    hint_label.text = "WHEEL / ← →  SELECT    CLICK CENTER  PREVIEW    DOUBLE CLICK  LAUNCH"
    hint_label.add_theme_font_size_override("font_size", 12)
    hint_label.add_theme_color_override("font_color", Color(0.56, 0.57, 0.70))
    ui.add_child(hint_label)

    preview = PREVIEW_SCRIPT.new()
    preview.position = Vector2(970.0, 210.0)
    preview.size = Vector2(540.0, 500.0)
    preview.visible = false
    preview.media_audio_activity_changed.connect(_on_preview_audio_activity_changed)
    ui.add_child(preview)

    theme_music_player = AudioStreamPlayer.new()
    add_child(theme_music_player)

    placeholder_label = Label.new()
    placeholder_label.position = Vector2(78.0, 240.0)
    placeholder_label.size = Vector2(980.0, 100.0)
    placeholder_label.add_theme_font_size_override("font_size", 20)
    placeholder_label.add_theme_color_override("font_color", Color(0.58, 0.59, 0.70))
    placeholder_label.visible = false
    ui.add_child(placeholder_label)

    system_panel = VBoxContainer.new()
    system_panel.position = Vector2(78.0, 220.0)
    system_panel.size = Vector2(460.0, 300.0)
    system_panel.add_theme_constant_override("separation", 14)
    system_panel.visible = false
    ui.add_child(system_panel)

    var add_game_button: Button = Button.new()
    add_game_button.text = "ADD GAME…"
    add_game_button.custom_minimum_size = Vector2(320.0, 46.0)
    add_game_button.pressed.connect(_open_add_game_dialog)
    system_panel.add_child(add_game_button)

    var window_button: Button = Button.new()
    window_button.text = "TOGGLE WINDOW / MAXIMIZED"
    window_button.custom_minimum_size = Vector2(320.0, 46.0)
    window_button.pressed.connect(_toggle_window_mode)
    system_panel.add_child(window_button)

    var system_note: Label = Label.new()
    system_note.text = "Phase 1 System shell\nData: LocalResourceTerminal / v0.6\nBackend: 127.0.0.1 only"
    system_note.add_theme_font_size_override("font_size", 13)
    system_note.add_theme_color_override("font_color", Color(0.56, 0.57, 0.70))
    system_panel.add_child(system_note)

    add_game_dialog = FileDialog.new()
    add_game_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    add_game_dialog.access = FileDialog.ACCESS_FILESYSTEM
    add_game_dialog.filters = PackedStringArray(["*.exe ; Windows Executable"])
    add_game_dialog.size = Vector2i(920, 620)
    add_game_dialog.file_selected.connect(_on_game_executable_selected)
    ui.add_child(add_game_dialog)

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

func _unhandled_key_input(event: InputEvent) -> void:
    if not (event is InputEventKey):
        return
    var key: InputEventKey = event as InputEventKey
    if not key.pressed or key.echo:
        return
    if key.keycode == KEY_ESCAPE and _preview_open:
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
            Color(0.96, 0.95, 1.0) if active else Color(0.48, 0.49, 0.61)
        )
        button.add_theme_font_size_override("font_size", 22 if active else 16)

    var section: String = XMB_SECTIONS[section_index]
    title_label.text = section
    carousel.visible = section == "GAMES"
    system_panel.visible = section == "SYSTEM"
    placeholder_label.visible = section != "GAMES" and section != "SYSTEM"
    if placeholder_label.visible:
        placeholder_label.text = section + "  /  PHASE 1 ARCHITECTURE SLOT"
    if section != "GAMES":
        _close_preview()
    else:
        title_label.text = String(_selected_game.get("title", "GAMES"))

    if persist and backend != null and backend.is_connected_to_backend():
        backend.request("state.update", {"last_section": section.to_lower()})

func _on_backend_connected() -> void:
    backend_label.text = "BACKEND CONNECTED"
    _pending_state_id = backend.request("state.get", {})
    _pending_games_id = backend.request("library.games.list", {})
    _pending_theme_id = backend.request("theme.current", {})
    _pending_settings_id = backend.request("settings.get", {})

func _on_backend_disconnected(code: int, reason: String) -> void:
    backend_label.text = "BACKEND OFFLINE  %d" % code
    if not reason.is_empty():
        backend_label.tooltip_text = reason

func _on_backend_response(request_id: String, ok: bool, data: Variant, error: Variant) -> void:
    if request_id == _pending_state_id:
        _pending_state_id = ""
        if ok and data is Dictionary:
            var state: Dictionary = data as Dictionary
            _restore_item_id = String(state.get("last_item_id", ""))
            _restore_section = String(state.get("last_section", "games")).to_upper()
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

    if request_id == _pending_launch_id:
        _pending_launch_id = ""
        if not ok:
            backend_label.text = "LAUNCH FAILED"
            backend_label.tooltip_text = String(error)
        return

    if request_id == _pending_create_id:
        _pending_create_id = ""
        if not ok:
            backend_label.text = "ADD GAME FAILED"
            backend_label.tooltip_text = String(error)
        return

func _on_backend_event(event_type: String, payload: Dictionary) -> void:
    if event_type == "library.changed":
        _pending_games_id = backend.request("library.games.list", {})
    elif event_type == "game.started":
        backend_label.text = "GAME RUNNING"
        RenderingServer.render_loop_enabled = false
        get_window().hide()
    elif event_type == "game.exited":
        _restore_item_id = String(payload.get("item_id", ""))
        RenderingServer.render_loop_enabled = true
        get_window().show()
        get_window().borderless = true
        get_window().mode = Window.MODE_MAXIMIZED
        get_window().grab_focus()
        backend_label.text = "BACKEND CONNECTED"
        _pending_games_id = backend.request("library.games.list", {})

func _on_selection_changed(_index: int, game: Dictionary) -> void:
    _selected_game = game
    if section_index == 0:
        title_label.text = String(game.get("title", "GAMES"))
    var item_id: String = String(game.get("id", ""))
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
    _schedule_preview(game)

func _on_main_case_double_clicked(game: Dictionary) -> void:
    _preview_generation += 1
    var item_id: String = String(game.get("id", ""))
    if item_id.is_empty():
        return
    _pending_launch_id = backend.request("game.launch", {"id": item_id})

func _schedule_preview(game: Dictionary) -> void:
    _preview_generation += 1
    var generation: int = _preview_generation
    await get_tree().create_timer(PREVIEW_SETTLE_SECONDS).timeout
    if generation != _preview_generation or not _preview_open:
        return
    if String(game.get("id", "")) != String(_selected_game.get("id", "")):
        return
    _request_preview(game)

func _request_preview(game: Dictionary) -> void:
    var item_id: String = String(game.get("id", ""))
    if item_id.is_empty():
        preview.show_game(game, {})
        return
    _pending_preview_id = backend.request("game.preview", {"id": item_id})

func _close_preview() -> void:
    _preview_generation += 1
    _preview_open = false
    carousel.set_preview_mode(false)
    preview.hide_preview()

func _restore_selection_by_id(item_id: String) -> void:
    for i: int in range(carousel.games.size()):
        if String(carousel.games[i].get("id", "")) == item_id:
            carousel.select_index(i)
            return

func _apply_theme(theme: Dictionary) -> void:
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
    _apply_theme_audio(theme)

func _apply_theme_audio(theme: Dictionary) -> void:
    if theme_music_player == null:
        return
    var audio_value: Variant = theme.get("audio", {})
    if not (audio_value is Dictionary):
        theme_music_player.stop()
        theme_music_player.stream = null
        return
    var audio: Dictionary = audio_value as Dictionary
    var music_rel: String = String(audio.get("music", ""))
    var theme_dir: String = String(theme.get("directory", ""))
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
        backend_label.text = "BACKEND OFFLINE"
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

func _on_preview_audio_activity_changed(active: bool) -> void:
    if theme_music_player == null or not theme_music_player.playing:
        return
    if _audio_tween != null and _audio_tween.is_valid():
        _audio_tween.kill()
    var target_linear: float = _theme_music_base_volume * (0.30 if active else 1.0)
    var target_db: float = linear_to_db(maxf(target_linear, 0.0001))
    _audio_tween = create_tween()
    _audio_tween.tween_property(theme_music_player, "volume_db", target_db, 0.28)
