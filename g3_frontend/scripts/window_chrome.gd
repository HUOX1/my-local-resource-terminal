extends Control
class_name G3WindowChrome

const TITLE_BAR_HEIGHT: float = 34.0
const BUTTON_WIDTH: float = 44.0
const RESIZE_MARGIN: float = 6.0
const CORNER_MARGIN: float = 10.0

var _title_bar: Panel
var _title_label: Label
var _minimize_button: Button
var _maximize_button: Button
var _close_button: Button
var _text_color: Color = Color(0.93, 1.0, 1.0, 1.0)
var _muted_color: Color = Color(0.55, 0.70, 0.72, 1.0)
var _accent_color: Color = Color(0.20, 0.82, 0.76, 1.0)
var _base_color: Color = Color(0.025, 0.085, 0.105, 1.0)

func _ready() -> void:
    set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    mouse_filter = Control.MOUSE_FILTER_IGNORE
    z_index = 100
    _build_title_bar()
    _build_resize_handles()
    set_process(true)

func set_theme_colors(text: Color, muted: Color, accent: Color, base: Color) -> void:
    _text_color = text
    _muted_color = muted
    _accent_color = accent
    _base_color = base
    if _title_bar != null:
        _apply_theme()

func _build_title_bar() -> void:
    _title_bar = Panel.new()
    _title_bar.anchor_left = 0.0
    _title_bar.anchor_right = 1.0
    _title_bar.anchor_top = 0.0
    _title_bar.anchor_bottom = 0.0
    _title_bar.offset_left = 0.0
    _title_bar.offset_right = 0.0
    _title_bar.offset_top = 0.0
    _title_bar.offset_bottom = TITLE_BAR_HEIGHT
    _title_bar.mouse_filter = Control.MOUSE_FILTER_STOP
    _title_bar.z_index = 100
    _title_bar.gui_input.connect(_on_title_bar_input)
    add_child(_title_bar)

    _title_label = Label.new()
    _title_label.position = Vector2(12.0, 0.0)
    _title_label.size = Vector2(240.0, TITLE_BAR_HEIGHT)
    _title_label.text = "G3"
    _title_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
    _title_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
    _title_label.add_theme_font_size_override("font_size", 13)
    _title_bar.add_child(_title_label)

    _minimize_button = _make_window_button("—", 2)
    _minimize_button.pressed.connect(_minimize_window)
    _title_bar.add_child(_minimize_button)

    _maximize_button = _make_window_button("□", 1)
    _maximize_button.pressed.connect(_toggle_maximize)
    _title_bar.add_child(_maximize_button)

    _close_button = _make_window_button("×", 0)
    _close_button.pressed.connect(_close_window)
    _title_bar.add_child(_close_button)

    _apply_theme()

func _make_window_button(text_value: String, slot_from_right: int) -> Button:
    var button := Button.new()
    button.anchor_left = 1.0
    button.anchor_right = 1.0
    button.anchor_top = 0.0
    button.anchor_bottom = 0.0
    button.offset_left = -BUTTON_WIDTH * float(slot_from_right + 1)
    button.offset_right = -BUTTON_WIDTH * float(slot_from_right)
    button.offset_top = 0.0
    button.offset_bottom = TITLE_BAR_HEIGHT
    button.text = text_value
    button.flat = true
    button.focus_mode = Control.FOCUS_NONE
    button.mouse_filter = Control.MOUSE_FILTER_STOP
    button.add_theme_font_size_override("font_size", 15)
    return button

func _apply_theme() -> void:
    var bar_style := StyleBoxFlat.new()
    bar_style.bg_color = _base_color.darkened(0.24)
    bar_style.border_color = _accent_color.darkened(0.20)
    bar_style.border_width_bottom = 1
    _title_bar.add_theme_stylebox_override("panel", bar_style)
    _title_label.add_theme_color_override("font_color", _text_color)

    for button: Button in [_minimize_button, _maximize_button, _close_button]:
        button.add_theme_color_override("font_color", _muted_color)
        button.add_theme_color_override("font_hover_color", _text_color)
        button.add_theme_color_override("font_pressed_color", _text_color)
        button.add_theme_stylebox_override("normal", _button_style(Color(0.0, 0.0, 0.0, 0.0)))
        button.add_theme_stylebox_override("hover", _button_style(_accent_color.darkened(0.62)))
        button.add_theme_stylebox_override("pressed", _button_style(_accent_color.darkened(0.48)))

func _button_style(color: Color) -> StyleBoxFlat:
    var style := StyleBoxFlat.new()
    style.bg_color = color
    return style

func _on_title_bar_input(event: InputEvent) -> void:
    if not (event is InputEventMouseButton):
        return
    var mouse_event := event as InputEventMouseButton
    if not mouse_event.pressed or mouse_event.button_index != MOUSE_BUTTON_LEFT:
        return
    if mouse_event.double_click:
        _toggle_maximize()
        return
    var window := get_window()
    if window != null:
        window.start_drag()

func _minimize_window() -> void:
    var window := get_window()
    if window != null:
        window.mode = Window.MODE_MINIMIZED

func _toggle_maximize() -> void:
    var window := get_window()
    if window == null:
        return
    window.borderless = true
    if window.mode == Window.MODE_MAXIMIZED:
        window.mode = Window.MODE_WINDOWED
    else:
        window.mode = Window.MODE_MAXIMIZED
    _refresh_maximize_glyph()

func _close_window() -> void:
    get_tree().quit()

func _process(_delta: float) -> void:
    _refresh_maximize_glyph()

func _refresh_maximize_glyph() -> void:
    if _maximize_button == null:
        return
    var window := get_window()
    if window == null:
        return
    _maximize_button.text = "❐" if window.mode == Window.MODE_MAXIMIZED else "□"

func _build_resize_handles() -> void:
    _add_resize_handle(DisplayServer.WINDOW_EDGE_TOP, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, RESIZE_MARGIN, Control.CURSOR_VSIZE)
    _add_resize_handle(DisplayServer.WINDOW_EDGE_BOTTOM, 0.0, 1.0, 1.0, 1.0, 0.0, -RESIZE_MARGIN, 0.0, 0.0, Control.CURSOR_VSIZE)
    _add_resize_handle(DisplayServer.WINDOW_EDGE_LEFT, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, RESIZE_MARGIN, 0.0, Control.CURSOR_HSIZE)
    _add_resize_handle(DisplayServer.WINDOW_EDGE_RIGHT, 1.0, 0.0, 1.0, 1.0, -RESIZE_MARGIN, 0.0, 0.0, 0.0, Control.CURSOR_HSIZE)
    _add_resize_handle(DisplayServer.WINDOW_EDGE_TOP_LEFT, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, CORNER_MARGIN, CORNER_MARGIN, Control.CURSOR_FDIAGSIZE)
    _add_resize_handle(DisplayServer.WINDOW_EDGE_TOP_RIGHT, 1.0, 0.0, 1.0, 0.0, -CORNER_MARGIN, 0.0, 0.0, CORNER_MARGIN, Control.CURSOR_BDIAGSIZE)
    _add_resize_handle(DisplayServer.WINDOW_EDGE_BOTTOM_LEFT, 0.0, 1.0, 0.0, 1.0, 0.0, -CORNER_MARGIN, CORNER_MARGIN, 0.0, Control.CURSOR_BDIAGSIZE)
    _add_resize_handle(DisplayServer.WINDOW_EDGE_BOTTOM_RIGHT, 1.0, 1.0, 1.0, 1.0, -CORNER_MARGIN, -CORNER_MARGIN, 0.0, 0.0, Control.CURSOR_FDIAGSIZE)

func _add_resize_handle(
    edge: int,
    anchor_left_value: float,
    anchor_top_value: float,
    anchor_right_value: float,
    anchor_bottom_value: float,
    offset_left_value: float,
    offset_top_value: float,
    offset_right_value: float,
    offset_bottom_value: float,
    cursor_shape: int
) -> void:
    var handle := Control.new()
    handle.anchor_left = anchor_left_value
    handle.anchor_top = anchor_top_value
    handle.anchor_right = anchor_right_value
    handle.anchor_bottom = anchor_bottom_value
    handle.offset_left = offset_left_value
    handle.offset_top = offset_top_value
    handle.offset_right = offset_right_value
    handle.offset_bottom = offset_bottom_value
    handle.mouse_filter = Control.MOUSE_FILTER_STOP
    handle.mouse_default_cursor_shape = cursor_shape
    handle.z_index = 110
    handle.gui_input.connect(_on_resize_input.bind(edge))
    add_child(handle)

func _on_resize_input(event: InputEvent, edge: int) -> void:
    if not (event is InputEventMouseButton):
        return
    var mouse_event := event as InputEventMouseButton
    if not mouse_event.pressed or mouse_event.button_index != MOUSE_BUTTON_LEFT:
        return
    var window := get_window()
    if window == null or window.mode != Window.MODE_WINDOWED:
        return
    window.start_resize(edge)
