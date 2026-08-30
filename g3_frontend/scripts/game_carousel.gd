extends Node3D
class_name GameCarousel3D

signal selection_changed(index: int, game: Dictionary)
signal main_case_clicked(game: Dictionary)
signal main_case_double_clicked(game: Dictionary)
signal main_case_right_clicked(game: Dictionary, screen_position: Vector2)

const CASE_SCRIPT: Script = preload("res://scripts/game_case_3d.gd")
const BROWSE_ANCHOR_X: float = -7.45
const BROWSE_ANCHOR_Y: float = 2.05
const PREVIEW_ANCHOR_X: float = -7.65
const PREVIEW_ANCHOR_Y: float = 2.05
const CASE_SPACING: float = 1.72
const ACTIVE_RADIUS: int = 4

var games: Array[Dictionary] = []
var selected_index: int = 0
var preview_mode: bool = false
var camera: Camera3D
var _cases_by_index: Dictionary = {}
var _last_click_msec: int = 0
var _hover_index: int = -1
var _click_generation: int = 0
var _accent: Color = Color(0.20, 0.82, 0.76, 1.0)
var _secondary: Color = Color(0.25, 0.55, 0.90, 1.0)

func configure(target_camera: Camera3D) -> void:
    camera = target_camera
    set_process(true)
    set_process_input(true)

func set_games(value: Array[Dictionary]) -> void:
    games = value
    _clear_cases()
    selected_index = clampi(selected_index, 0, maxi(games.size() - 1, 0))
    _rebuild_active_cases()
    _layout_targets()
    _emit_selection()

func set_theme_colors(accent: Color, secondary: Color) -> void:
    _accent = accent
    _secondary = secondary
    for index_value: Variant in _cases_by_index.keys():
        var item = _cases_by_index[index_value]
        item.set_theme_colors(_accent, _secondary)

func set_preview_mode(value: bool) -> void:
    preview_mode = value
    _layout_targets()

func select_index(index: int) -> void:
    if games.is_empty():
        return
    selected_index = wrapi(index, 0, games.size())
    _rebuild_active_cases()
    _layout_targets()
    _emit_selection()

func select_relative(delta_index: int) -> void:
    select_index(selected_index + delta_index)

func selected_game() -> Dictionary:
    if games.is_empty() or selected_index < 0 or selected_index >= games.size():
        return {}
    return games[selected_index]

func selected_case_world_position() -> Vector3:
    if not _cases_by_index.has(selected_index):
        return Vector3(9999.0, 9999.0, 9999.0)
    var item = _cases_by_index[selected_index]
    return item.global_position

func selected_case_screen_position() -> Vector2:
    if camera == null:
        return Vector2(-1000.0, -1000.0)
    var world_position: Vector3 = selected_case_world_position()
    if world_position.x > 9000.0:
        return Vector2(-1000.0, -1000.0)
    return camera.unproject_position(world_position)

func _clear_cases() -> void:
    for child: Node in get_children():
        child.queue_free()
    _cases_by_index.clear()
    _hover_index = -1

func _active_indices() -> Array[int]:
    var result: Array[int] = []
    if games.is_empty():
        return result
    var seen: Dictionary = {}
    for offset: int in range(-ACTIVE_RADIUS, ACTIVE_RADIUS + 1):
        var index: int = wrapi(selected_index + offset, 0, games.size())
        if not seen.has(index):
            seen[index] = true
            result.append(index)
    result.sort()
    return result

func _rebuild_active_cases() -> void:
    if games.is_empty():
        _clear_cases()
        return

    var desired: Array[int] = _active_indices()
    var desired_lookup: Dictionary = {}
    for index: int in desired:
        desired_lookup[index] = true

    for index_value: Variant in _cases_by_index.keys():
        var index: int = int(index_value)
        if not desired_lookup.has(index):
            var old_item = _cases_by_index[index]
            old_item.queue_free()
            _cases_by_index.erase(index)

    for index: int in desired:
        if _cases_by_index.has(index):
            continue
        var item = CASE_SCRIPT.new()
        add_child(item)
        item.configure(games[index])
        item.set_theme_colors(_accent, _secondary)
        _cases_by_index[index] = item

func _relative_index(index: int) -> int:
    var raw: int = index - selected_index
    var count: int = games.size()
    if count <= 1:
        return 0
    if raw > count / 2:
        raw -= count
    elif raw < -count / 2:
        raw += count
    return raw

func _layout_targets() -> void:
    if _cases_by_index.is_empty():
        return
    var anchor_x: float = PREVIEW_ANCHOR_X if preview_mode else BROWSE_ANCHOR_X
    var anchor_y: float = PREVIEW_ANCHOR_Y if preview_mode else BROWSE_ANCHOR_Y
    for index_value: Variant in _cases_by_index.keys():
        var i: int = int(index_value)
        var relative: float = float(_relative_index(i))
        var distance: float = absf(relative)
        var item = _cases_by_index[i]
        item.target_position = Vector3(
            anchor_x + relative * CASE_SPACING,
            anchor_y - distance * 0.04,
            -distance * 0.18
        )
        item.target_scale = maxf(0.74, 1.0 - distance * 0.09)
        item.set_selected(i == selected_index)

func _emit_selection() -> void:
    if games.is_empty():
        return
    selection_changed.emit(selected_index, games[selected_index])

func _input(event: InputEvent) -> void:
    if not visible or games.is_empty():
        return

    if event is InputEventMouseButton:
        var mouse_event: InputEventMouseButton = event as InputEventMouseButton
        if mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_WHEEL_UP:
            select_relative(-1)
            get_viewport().set_input_as_handled()
            return
        if mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
            select_relative(1)
            get_viewport().set_input_as_handled()
            return
        if mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_LEFT:
            if _handle_left_click(mouse_event.position):
                get_viewport().set_input_as_handled()
            return
        if mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_RIGHT:
            if _handle_right_click(mouse_event.position):
                get_viewport().set_input_as_handled()
            return

    if event is InputEventKey:
        var key_event: InputEventKey = event as InputEventKey
        if key_event.pressed and not key_event.echo:
            if key_event.keycode == KEY_LEFT:
                select_relative(-1)
            elif key_event.keycode == KEY_RIGHT:
                select_relative(1)

func _process(_delta: float) -> void:
    if camera == null or _cases_by_index.is_empty():
        return
    var mouse: Vector2 = get_viewport().get_mouse_position()
    var nearest_index: int = -1
    var nearest_distance: float = 999999.0
    for index_value: Variant in _cases_by_index.keys():
        var i: int = int(index_value)
        var item = _cases_by_index[i]
        if camera.is_position_behind(item.global_position):
            continue
        var screen: Vector2 = camera.unproject_position(item.global_position)
        var distance: float = mouse.distance_to(screen)
        if distance < 130.0 and distance < nearest_distance:
            nearest_distance = distance
            nearest_index = i

    if nearest_index != _hover_index:
        if _hover_index >= 0 and _cases_by_index.has(_hover_index):
            _cases_by_index[_hover_index].set_hover(false)
        _hover_index = nearest_index

    if _hover_index >= 0 and _cases_by_index.has(_hover_index):
        var hovered_case = _cases_by_index[_hover_index]
        var center: Vector2 = camera.unproject_position(hovered_case.global_position)
        var normalized: Vector2 = (mouse - center) / Vector2(130.0, 170.0)
        normalized.x = clampf(normalized.x, -1.0, 1.0)
        normalized.y = clampf(normalized.y, -1.0, 1.0)
        hovered_case.set_hover(true, normalized)

func _hit_test(position_2d: Vector2) -> int:
    if camera == null or _cases_by_index.is_empty():
        return -1
    var clicked_index: int = -1
    var best: float = 999999.0
    for index_value: Variant in _cases_by_index.keys():
        var i: int = int(index_value)
        var item = _cases_by_index[i]
        var screen: Vector2 = camera.unproject_position(item.global_position)
        var distance: float = position_2d.distance_to(screen)
        if distance < 145.0 and distance < best:
            best = distance
            clicked_index = i
    return clicked_index

func _handle_left_click(position_2d: Vector2) -> bool:
    var clicked_index: int = _hit_test(position_2d)
    if clicked_index < 0:
        return false
    if clicked_index != selected_index:
        select_index(clicked_index)
        return true

    var now_msec: int = Time.get_ticks_msec()
    var is_double: bool = now_msec - _last_click_msec <= 330
    _last_click_msec = now_msec
    _click_generation += 1
    var generation: int = _click_generation

    if is_double:
        main_case_double_clicked.emit(games[selected_index])
        return true

    _emit_single_click_after_delay(generation)
    return true

func _handle_right_click(position_2d: Vector2) -> bool:
    var clicked_index: int = _hit_test(position_2d)
    if clicked_index < 0:
        return false
    if clicked_index != selected_index:
        select_index(clicked_index)
    main_case_right_clicked.emit(games[selected_index], position_2d)
    return true

func _emit_single_click_after_delay(generation: int) -> void:
    await get_tree().create_timer(0.34).timeout
    if generation != _click_generation:
        return
    if games.is_empty():
        return
    main_case_clicked.emit(games[selected_index])
