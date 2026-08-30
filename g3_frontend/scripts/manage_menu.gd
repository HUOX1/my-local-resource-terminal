extends PopupMenu
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

func _ready() -> void:
    name = "GameManageMenu"
    add_item("启动", 0)
    add_item("预览", 1)
    add_separator()
    add_item("编辑资料", 2)
    add_item("媒体素材", 3)
    add_item("启动设置", 4)
    add_separator()
    add_item("移除收藏", 5)
    id_pressed.connect(_on_id_pressed)

func show_at(screen_position: Vector2) -> void:
    position = Vector2i(int(screen_position.x), int(screen_position.y))
    popup()

func _on_id_pressed(id: int) -> void:
    if id < 0 or id >= ACTIONS.size():
        return
    action_requested.emit(ACTIONS[id])
