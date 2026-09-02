extends Control
class_name G3NavigationDrawer

signal section_requested(section_id: String)

const CONTENT_SECTIONS: Array[Dictionary] = [
    {"id":"GAMES", "icon":"▣", "tip":"游戏"}, {"id":"MOVIES", "icon":"▶", "tip":"电影"},
    {"id":"COMICS", "icon":"▤", "tip":"漫画"}, {"id":"MUSIC", "icon":"♫", "tip":"音乐"},
]
const SYSTEM_SECTIONS: Array[Dictionary] = [
    {"id":"SEARCH", "icon":"⌕", "tip":"搜索"}, {"id":"SYSTEM", "icon":"⚙", "tip":"系统"},
]
const HANDLE_SIZE: float = 48.0
const DRAWER_WIDTH: float = 368.0
const NAV_Z_INDEX: int = 400
const HOVER_SCALE: float = 1.10
const HIDE_DELAY_SECONDS: float = 0.45

var _panel: PanelContainer
var _row: HBoxContainer
var _handle: Button
var _buttons: Dictionary = {}
var _shown: bool = false
var _hide_generation: int = 0

func _ready() -> void:
    set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    mouse_filter = Control.MOUSE_FILTER_IGNORE
    z_index = NAV_Z_INDEX
    _build()
    set_process_input(true)

func _build() -> void:
    _panel = PanelContainer.new()
    _panel.anchor_left = 1.0
    _panel.anchor_right = 1.0
    _panel.anchor_top = 1.0
    _panel.anchor_bottom = 1.0
    _panel.offset_left = -442.0
    _panel.offset_right = -74.0
    _panel.offset_top = -80.0
    _panel.offset_bottom = -16.0
    _panel.mouse_filter = Control.MOUSE_FILTER_STOP
    _panel.z_index = 1
    _panel.visible = false
    _panel.modulate.a = 1.0
    _panel.add_theme_stylebox_override("panel", _drawer_style())
    add_child(_panel)

    _row = HBoxContainer.new()
    _row.add_theme_constant_override("separation", 8)
    _panel.add_child(_row)

    for entry: Dictionary in CONTENT_SECTIONS:
        _add_button(entry)
    var separator := VSeparator.new()
    separator.custom_minimum_size = Vector2(4.0, 48.0)
    _row.add_child(separator)
    for entry: Dictionary in SYSTEM_SECTIONS:
        _add_button(entry)

    _handle = Button.new()
    _handle.anchor_left = 1.0
    _handle.anchor_right = 1.0
    _handle.anchor_top = 1.0
    _handle.anchor_bottom = 1.0
    _handle.offset_left = -66.0
    _handle.offset_right = -18.0
    _handle.offset_top = -72.0
    _handle.offset_bottom = -24.0
    _handle.text = "≡"
    _handle.tooltip_text = "导航"
    _handle.flat = false
    _handle.focus_mode = Control.FOCUS_NONE
    _handle.mouse_filter = Control.MOUSE_FILTER_STOP
    _handle.z_index = 2
    _handle.modulate.a = 0.88
    _handle.add_theme_font_size_override("font_size", 24)
    _handle.add_theme_stylebox_override("normal", _handle_style(Color(0.035, 0.12, 0.15, 0.94), Color(0.28, 0.66, 0.70, 0.72)))
    _handle.add_theme_stylebox_override("hover", _handle_style(Color(0.055, 0.18, 0.21, 1.0), Color(0.46, 0.90, 0.91, 0.94)))
    _handle.add_theme_stylebox_override("pressed", _handle_style(Color(0.025, 0.10, 0.13, 1.0), Color(0.46, 0.90, 0.91, 1.0)))
    add_child(_handle)

    _handle.mouse_entered.connect(_show_drawer_now)
    _handle.mouse_exited.connect(_schedule_hide)
    _panel.mouse_entered.connect(_cancel_hide)
    _panel.mouse_exited.connect(_schedule_hide)

func _drawer_style() -> StyleBoxFlat:
    var style := StyleBoxFlat.new()
    style.bg_color = Color(0.025, 0.085, 0.105, 0.98)
    style.border_color = Color(0.30, 0.72, 0.75, 0.68)
    style.set_border_width_all(1)
    style.set_corner_radius_all(8)
    style.content_margin_left = 8.0
    style.content_margin_right = 8.0
    style.content_margin_top = 8.0
    style.content_margin_bottom = 8.0
    return style

func _handle_style(background: Color, border: Color) -> StyleBoxFlat:
    var style := StyleBoxFlat.new()
    style.bg_color = background
    style.border_color = border
    style.set_border_width_all(1)
    style.set_corner_radius_all(9)
    return style

func _add_button(entry: Dictionary) -> void:
    var button := Button.new()
    button.text = ""
    button.tooltip_text = str(entry["tip"])
    button.custom_minimum_size = Vector2(48, 48)
    button.focus_mode = Control.FOCUS_NONE
    button.mouse_filter = Control.MOUSE_FILTER_STOP
    button.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
    button.add_theme_font_size_override("font_size", 24)
    var icon_label := Label.new()
    icon_label.text = str(entry["icon"])
    icon_label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    icon_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    icon_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
    icon_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
    icon_label.add_theme_color_override("font_color", Color(0.88, 0.97, 0.98, 1.0))
    button.add_child(icon_label)
    var section_id: String = str(entry["id"])
    button.pressed.connect(_on_section_pressed.bind(section_id))
    button.mouse_entered.connect(func(): _animate_button(button, true))
    button.mouse_exited.connect(func(): _animate_button(button, false))
    _buttons[section_id] = button
    _row.add_child(button)

func _on_section_pressed(section_id: String) -> void:
    section_requested.emit(section_id)
    _hide_drawer_now()

func set_active_section(section_id: String) -> void:
    for key: Variant in _buttons.keys():
        var button: Button = _buttons[key]
        button.modulate.a = 1.0 if str(key) == section_id else 0.62

func _input(event: InputEvent) -> void:
    # Direct fallback: this runs before GUI dispatch, so the navigation handle
    # remains usable even if another Control accidentally interferes with the
    # normal Button.pressed path on a particular Windows/Godot setup.
    if _handle == null or not (event is InputEventMouseButton):
        return
    var mouse_event := event as InputEventMouseButton
    if not mouse_event.pressed or mouse_event.button_index != MOUSE_BUTTON_LEFT:
        return
    if _handle.get_global_rect().has_point(mouse_event.position):
        _show_drawer_now()
        get_viewport().set_input_as_handled()

func _show_drawer_now() -> void:
    _cancel_hide()
    _shown = true
    _handle.modulate.a = 1.0
    _panel.visible = true
    _panel.modulate.a = 1.0
    _panel.move_to_front()
    _handle.move_to_front()

func _schedule_hide() -> void:
    _hide_generation += 1
    var generation: int = _hide_generation
    await get_tree().create_timer(HIDE_DELAY_SECONDS).timeout
    if generation != _hide_generation or _panel == null or _handle == null:
        return
    var mouse: Vector2 = get_viewport().get_mouse_position()
    if _panel.get_global_rect().has_point(mouse) or _handle.get_global_rect().has_point(mouse):
        return
    _hide_drawer_now()

func _cancel_hide() -> void:
    _hide_generation += 1

func _hide_drawer_now() -> void:
    _cancel_hide()
    _shown = false
    _handle.modulate.a = 0.88
    _panel.visible = false

func _animate_button(button: Button, active: bool) -> void:
    var target_scale := Vector2.ONE * (HOVER_SCALE if active else 1.0)
    var tween := create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
    tween.tween_property(button, "scale", target_scale, 0.16)
