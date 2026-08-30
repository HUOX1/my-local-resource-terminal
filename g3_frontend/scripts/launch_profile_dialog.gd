extends Window
class_name G3LaunchProfileDialog

signal save_requested(item_id: String, profile: Dictionary)

var _item_id: String = ""
var _profile_type: OptionButton
var _launch_exe: LineEdit
var _launch_args: LineEdit
var _working_directory: LineEdit
var _content_path: LineEdit
var _monitor_exe: LineEdit
var _wait_timeout: SpinBox
var _run_as_admin: CheckBox
var _launch_dialog: FileDialog
var _content_dialog: FileDialog
var _monitor_dialog: FileDialog

func _ready() -> void:
    title = "G3 · 启动设置"
    size = Vector2i(760, 620)
    min_size = Vector2i(680, 560)
    transient = true
    exclusive = true
    close_requested.connect(hide)

    var margin: MarginContainer = MarginContainer.new()
    margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    margin.add_theme_constant_override("margin_left", 28)
    margin.add_theme_constant_override("margin_top", 24)
    margin.add_theme_constant_override("margin_right", 28)
    margin.add_theme_constant_override("margin_bottom", 24)
    add_child(margin)

    var root: VBoxContainer = VBoxContainer.new()
    root.add_theme_constant_override("separation", 12)
    margin.add_child(root)

    var heading: Label = Label.new()
    heading.text = "启动配置"
    heading.add_theme_font_size_override("font_size", 22)
    root.add_child(heading)

    var note: Label = Label.new()
    note.text = "启动程序负责打开游戏链；监控程序代表真正的游戏会话。模拟器可使用 {content} 占位符。"
    note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    root.add_child(note)

    _profile_type = OptionButton.new()
    _profile_type.add_item("直接启动", 0)
    _profile_type.add_item("启动器 / Mod", 1)
    _profile_type.add_item("模拟器", 2)
    _add_control_row(root, "类型", _profile_type)

    _launch_exe = LineEdit.new()
    _add_path_row(root, "启动程序", _launch_exe, _open_launch_dialog)

    _launch_args = LineEdit.new()
    _launch_args.placeholder_text = "例：--fullscreen \"{content}\""
    _add_control_row(root, "启动参数", _launch_args)

    _working_directory = LineEdit.new()
    _add_control_row(root, "工作目录", _working_directory)

    _content_path = LineEdit.new()
    _add_path_row(root, "游戏内容", _content_path, _open_content_dialog)

    _monitor_exe = LineEdit.new()
    _add_path_row(root, "监控程序", _monitor_exe, _open_monitor_dialog)

    _wait_timeout = SpinBox.new()
    _wait_timeout.min_value = 0.0
    _wait_timeout.max_value = 1800.0
    _wait_timeout.step = 5.0
    _wait_timeout.value = 300.0
    _wait_timeout.suffix = " 秒"
    _add_control_row(root, "等待时间", _wait_timeout)

    _run_as_admin = CheckBox.new()
    _run_as_admin.text = "以管理员权限启动"
    root.add_child(_run_as_admin)

    var buttons: HBoxContainer = HBoxContainer.new()
    buttons.alignment = BoxContainer.ALIGNMENT_END
    root.add_child(buttons)

    var cancel_button: Button = Button.new()
    cancel_button.text = "取消"
    cancel_button.pressed.connect(hide)
    buttons.add_child(cancel_button)

    var save_button: Button = Button.new()
    save_button.text = "保存"
    save_button.pressed.connect(_save)
    buttons.add_child(save_button)

    _launch_dialog = _make_file_dialog(PackedStringArray(["*.exe ; Windows Executable"]))
    _launch_dialog.file_selected.connect(_on_launch_selected)
    add_child(_launch_dialog)

    _content_dialog = _make_file_dialog(PackedStringArray(["* ; Game / ROM / ISO / EBOOT"]))
    _content_dialog.file_selected.connect(_on_content_selected)
    add_child(_content_dialog)

    _monitor_dialog = _make_file_dialog(PackedStringArray(["*.exe ; Windows Executable"]))
    _monitor_dialog.file_selected.connect(_on_monitor_selected)
    add_child(_monitor_dialog)

func show_profile(item_id: String, profile: Dictionary) -> void:
    _item_id = item_id
    var profile_type: String = str(profile.get("profile_type", "direct"))
    var type_index: int = 0
    if profile_type == "launcher":
        type_index = 1
    elif profile_type == "emulator":
        type_index = 2
    _profile_type.select(type_index)
    _launch_exe.text = str(profile.get("launch_exe", ""))
    _launch_args.text = str(profile.get("launch_args", ""))
    _working_directory.text = str(profile.get("working_directory", ""))
    _content_path.text = str(profile.get("content_path", ""))
    _monitor_exe.text = str(profile.get("monitor_exe", ""))
    _wait_timeout.value = float(profile.get("wait_timeout_s", 300))
    _run_as_admin.button_pressed = bool(profile.get("run_as_admin", false))
    popup_centered()

func _add_control_row(root: VBoxContainer, label_text: String, control: Control) -> void:
    var row: HBoxContainer = HBoxContainer.new()
    row.add_theme_constant_override("separation", 12)
    root.add_child(row)
    var label: Label = Label.new()
    label.text = label_text
    label.custom_minimum_size = Vector2(100.0, 0.0)
    row.add_child(label)
    control.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    row.add_child(control)

func _add_path_row(root: VBoxContainer, label_text: String, field: LineEdit, callback: Callable) -> void:
    var row: HBoxContainer = HBoxContainer.new()
    row.add_theme_constant_override("separation", 12)
    root.add_child(row)
    var label: Label = Label.new()
    label.text = label_text
    label.custom_minimum_size = Vector2(100.0, 0.0)
    row.add_child(label)
    field.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    row.add_child(field)
    var browse: Button = Button.new()
    browse.text = "浏览…"
    browse.pressed.connect(callback)
    row.add_child(browse)

func _make_file_dialog(filters: PackedStringArray) -> FileDialog:
    var dialog: FileDialog = FileDialog.new()
    dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
    dialog.access = FileDialog.ACCESS_FILESYSTEM
    dialog.filters = filters
    dialog.size = Vector2i(900, 620)
    return dialog

func _open_launch_dialog() -> void:
    _launch_dialog.popup_centered_ratio(0.82)

func _open_content_dialog() -> void:
    _content_dialog.popup_centered_ratio(0.82)

func _open_monitor_dialog() -> void:
    _monitor_dialog.popup_centered_ratio(0.82)

func _on_launch_selected(path: String) -> void:
    _launch_exe.text = path
    if _working_directory.text.is_empty():
        _working_directory.text = path.get_base_dir()
    if _monitor_exe.text.is_empty():
        _monitor_exe.text = path

func _on_content_selected(path: String) -> void:
    _content_path.text = path

func _on_monitor_selected(path: String) -> void:
    _monitor_exe.text = path

func _save() -> void:
    var profile_type: String = "direct"
    if _profile_type.selected == 1:
        profile_type = "launcher"
    elif _profile_type.selected == 2:
        profile_type = "emulator"
    save_requested.emit(
        _item_id,
        {
            "profile_type": profile_type,
            "launch_exe": _launch_exe.text.strip_edges(),
            "launch_args": _launch_args.text.strip_edges(),
            "working_directory": _working_directory.text.strip_edges(),
            "content_path": _content_path.text.strip_edges(),
            "monitor_exe": _monitor_exe.text.strip_edges(),
            "wait_timeout_s": int(_wait_timeout.value),
            "run_as_admin": _run_as_admin.button_pressed,
        }
    )
    hide()
