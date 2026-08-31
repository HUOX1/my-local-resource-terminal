extends PopupPanel
class_name G3GameManageMenu

signal action_requested(action: String)

const ACTIONS: Array[String] = [
    "launch",
    "preview",
    "edit_metadata",
    "media_assets",
    "launch_settings",
    "remove",
]

var _root: VBoxContainer

func _ready() -> void:
    name = "GameManageMenu"
    size = Vector2i(196, 248)
    _build_ui()
    hide()

func _build_ui() -> void:
    var margin: MarginContainer = MarginContainer.new()
    margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    margin.add_theme_constant_override("margin_left", 10)
    margin.add_theme_constant_override("margin_top", 10)
    margin.add_theme_constant_override("margin_right", 10)
    margin.add_theme_constant_override("margin_bottom", 10)
    add_child(margin)

    _root = VBoxContainer.new()
    _root.add_theme_constant_override("separation", 4)
    margin.add_child(_root)

    _add_action_button("启动", 0)
    _add_action_button("预览", 1)
    _add_separator()
    _add_action_button("编辑资料", 2)
    _add_action_button("媒体素材", 3)
    _add_action_button("启动设置", 4)
    _add_separator()
    _add_action_button("移除收藏", 5)

func _add_action_button(label_text: String, action_id: int) -> void:
    var button: Button = Button.new()
    button.text = label_text
    button.flat = true
    button.focus_mode = Control.FOCUS_NONE
    button.custom_minimum_size = Vector2(176.0, 28.0)
    button.alignment = HORIZONTAL_ALIGNMENT_LEFT
    button.add_theme_font_size_override("font_size", 18)
    button.pressed.connect(_on_action_pressed.bind(action_id))
    _root.add_child(button)

func _add_separator() -> void:
    var separator: HSeparator = HSeparator.new()
    _root.add_child(separator)

func show_at(screen_position: Vector2) -> void:
    position = Vector2i(int(screen_position.x), int(screen_position.y))
    popup()
    grab_focus()

func _on_action_pressed(action_id: int) -> void:
    hide()
    if action_id < 0 or action_id >= ACTIONS.size():
        return
    action_requested.emit(ACTIONS[action_id])
