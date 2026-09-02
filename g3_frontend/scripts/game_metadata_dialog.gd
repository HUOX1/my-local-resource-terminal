extends Window
class_name G3GameMetadataDialog

const TEXT_MENU_LOCALIZER: Script = preload("res://scripts/text_context_menu_localizer.gd")

signal save_requested(item_id: String, metadata: Dictionary)

var _item_id: String = ""
var _title_field: LineEdit
var _platform: LineEdit
var _developer: LineEdit
var _publisher: LineEdit
var _release_year: LineEdit
var _tags: LineEdit
var _description: TextEdit
var _notes: TextEdit

func _ready() -> void:
    title = "编辑资料"
    size = Vector2i(720, 650)
    min_size = Vector2i(620, 560)
    close_requested.connect(hide)
    _build_ui()
    TEXT_MENU_LOCALIZER.localize_tree(self)
    call_deferred("_localize_context_menus")
    hide()

func _build_ui() -> void:
    var margin: MarginContainer = MarginContainer.new()
    margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    margin.add_theme_constant_override("margin_left", 22)
    margin.add_theme_constant_override("margin_top", 20)
    margin.add_theme_constant_override("margin_right", 22)
    margin.add_theme_constant_override("margin_bottom", 20)
    add_child(margin)

    var root: VBoxContainer = VBoxContainer.new()
    root.add_theme_constant_override("separation", 12)
    margin.add_child(root)

    _title_field = LineEdit.new()
    _add_control_row(root, "标题", _title_field)

    _platform = LineEdit.new()
    _platform.placeholder_text = "PC / PS4 / PS1 / PSP / Switch…"
    _add_control_row(root, "平台", _platform)

    _developer = LineEdit.new()
    _add_control_row(root, "开发商", _developer)

    _publisher = LineEdit.new()
    _add_control_row(root, "发行商", _publisher)

    _release_year = LineEdit.new()
    _release_year.placeholder_text = "例如 2017；可留空"
    _add_control_row(root, "发行年份", _release_year)

    _tags = LineEdit.new()
    _tags.placeholder_text = "例如 生存, 平台, 探索"
    _add_control_row(root, "标签", _tags)

    var description_label: Label = Label.new()
    description_label.text = "简介"
    root.add_child(description_label)
    _description = TextEdit.new()
    _description.custom_minimum_size = Vector2(0, 120)
    _description.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
    root.add_child(_description)

    var notes_label: Label = Label.new()
    notes_label.text = "收藏备注"
    root.add_child(notes_label)
    _notes = TextEdit.new()
    _notes.custom_minimum_size = Vector2(0, 86)
    _notes.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
    root.add_child(_notes)

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

func show_metadata(item_id: String, metadata: Dictionary) -> void:
    _item_id = item_id
    _title_field.text = str(metadata.get("title", ""))
    _platform.text = str(metadata.get("platform", ""))
    _developer.text = str(metadata.get("developer", ""))
    _publisher.text = str(metadata.get("publisher", ""))
    var year_value: Variant = metadata.get("release_year")
    _release_year.text = "" if year_value == null or int(year_value) == 0 else str(year_value)
    _tags.text = str(metadata.get("tags", ""))
    _description.text = str(metadata.get("description", ""))
    _notes.text = str(metadata.get("notes", ""))
    popup_centered()

func _add_control_row(root: VBoxContainer, label_text: String, control: Control) -> void:
    var row: HBoxContainer = HBoxContainer.new()
    row.add_theme_constant_override("separation", 12)
    root.add_child(row)
    var label: Label = Label.new()
    label.text = label_text
    label.custom_minimum_size = Vector2(90.0, 0.0)
    row.add_child(label)
    control.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    row.add_child(control)

func _save() -> void:
    save_requested.emit(
        _item_id,
        {
            "title": _title_field.text.strip_edges(),
            "platform": _platform.text.strip_edges(),
            "developer": _developer.text.strip_edges(),
            "publisher": _publisher.text.strip_edges(),
            "release_year": _release_year.text.strip_edges(),
            "tags": _tags.text.strip_edges(),
            "description": _description.text.strip_edges(),
            "notes": _notes.text.strip_edges(),
        }
    )
    hide()

func _localize_context_menus() -> void:
    TEXT_MENU_LOCALIZER.localize_tree(self)
