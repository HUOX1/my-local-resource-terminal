extends RefCounted
class_name G3TextContextMenuLocalizer

const LABELS: Dictionary = {
    "Emoji & Symbols": "表情与符号",
    "Cut": "剪切",
    "Copy": "复制",
    "Paste": "粘贴",
    "Select All": "全选",
    "Clear": "清空",
    "Undo": "撤销",
    "Redo": "重做",
    "Text Writing Direction": "文字方向",
    "Display Control Characters": "显示控制字符",
    "Insert Control Character": "插入控制字符",
    "Auto": "自动",
    "Left-to-Right": "从左到右",
    "Right-to-Left": "从右到左",
    "Inherited": "继承",
}

static func localize_tree(root: Node) -> void:
    if root == null:
        return
    _localize_node(root)
    for child: Node in root.get_children():
        localize_tree(child)

static func _localize_node(node: Node) -> void:
    if node is LineEdit:
        _localize_popup((node as LineEdit).get_menu())
    elif node is TextEdit:
        _localize_popup((node as TextEdit).get_menu())
    elif node is PopupMenu:
        _localize_popup(node as PopupMenu)

static func _localize_popup(menu: PopupMenu) -> void:
    if menu == null:
        return
    for index: int in range(menu.item_count):
        var current: String = menu.get_item_text(index)
        if LABELS.has(current):
            menu.set_item_text(index, str(LABELS[current]))
    for child: Node in menu.get_children():
        if child is PopupMenu:
            _localize_popup(child as PopupMenu)
