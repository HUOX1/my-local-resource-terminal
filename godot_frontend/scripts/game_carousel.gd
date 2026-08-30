extends Node3D
class_name GameCarousel3D

signal selection_changed(index: int, game: Dictionary)
signal main_case_clicked(game: Dictionary)
signal main_case_double_clicked(game: Dictionary)

const CASE_SCRIPT: Script = preload("res://scripts/game_case_3d.gd")

var games: Array[Dictionary] = []
var cases: Array = []
var selected_index: int = 0
var preview_mode: bool = false
var camera: Camera3D
var _last_click_msec: int = 0
var _hover_index: int = -1
var _click_generation: int = 0

func configure(target_camera: Camera3D) -> void:
    camera = target_camera
    set_process(true)
    set_process_input(true)

func set_games(value: Array[Dictionary]) -> void:
    games = value
    for child: Node in get_children():
        child.queue_free()
    cases.clear()
    selected_index = clampi(selected_index, 0, maxi(games.size() - 1, 0))
    for game: Dictionary in games:
        var item = CASE_SCRIPT.new()
        add_child(item)
        item.configure(game)
        cases.append(item)
    _layout_targets()
    _emit_selection()

func set_preview_mode(value: bool) -> void:
    preview_mode = value
    _layout_targets()

func select_index(index: int) -> void:
    if cases.is_empty():
        return
    selected_index = wrapi(index, 0, cases.size())
    _layout_targets()
    _emit_selection()

func select_relative(delta_index: int) -> void:
    select_index(selected_index + delta_index)

func selected_game() -> Dictionary:
    if games.is_empty() or selected_index < 0 or selected_index >= games.size():
        return {}
    return games[selected_index]

func _layout_targets() -> void:
    if cases.is_empty():
        return
    var center_x: float = -1.55 if preview_mode else 0.0
    for i: int in range(cases.size()):
        var relative: float = float(i - selected_index)
        var distance: float = absf(relative)
        var case = cases[i]
        case.target_position = Vector3(
            center_x + relative * 1.62,
            -distance * 0.05,
            -distance * 0.22
        )
        case.target_scale = maxf(0.72, 1.0 - distance * 0.10)
        case.set_selected(i == selected_index)

func _emit_selection() -> void:
    if games.is_empty():
        return
    selection_changed.emit(selected_index, games[selected_index])

func _input(event: InputEvent) -> void:
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
            _handle_click(mouse_event.position)
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
    if camera == null or cases.is_empty():
        return
    var mouse: Vector2 = get_viewport().get_mouse_position()
    var nearest_index: int = -1
    var nearest_distance: float = 999999.0
    for i: int in range(cases.size()):
        var case = cases[i]
        if camera.is_position_behind(case.global_position):
            continue
        var screen: Vector2 = camera.unproject_position(case.global_position)
        var distance: float = mouse.distance_to(screen)
        if distance < 130.0 and distance < nearest_distance:
            nearest_distance = distance
            nearest_index = i
    if nearest_index != _hover_index:
        if _hover_index >= 0 and _hover_index < cases.size():
            cases[_hover_index].set_hover(false)
        _hover_index = nearest_index
    if _hover_index >= 0:
        var hovered_case = cases[_hover_index]
        var center: Vector2 = camera.unproject_position(hovered_case.global_position)
        var normalized: Vector2 = (mouse - center) / Vector2(130.0, 190.0)
        normalized.x = clampf(normalized.x, -1.0, 1.0)
        normalized.y = clampf(normalized.y, -1.0, 1.0)
        hovered_case.set_hover(true, normalized)

func _handle_click(position_2d: Vector2) -> void:
    if camera == null or cases.is_empty():
        return
    var clicked_index: int = -1
    var best: float = 999999.0
    for i: int in range(cases.size()):
        var case = cases[i]
        var screen: Vector2 = camera.unproject_position(case.global_position)
        var distance: float = position_2d.distance_to(screen)
        if distance < 145.0 and distance < best:
            best = distance
            clicked_index = i
    if clicked_index < 0:
        return
    if clicked_index != selected_index:
        select_index(clicked_index)
        return
    var now_msec: int = Time.get_ticks_msec()
    var is_double: bool = now_msec - _last_click_msec <= 330
    _last_click_msec = now_msec
    _click_generation += 1
    var generation: int = _click_generation
    if is_double:
        main_case_double_clicked.emit(games[selected_index])
        return
    _emit_single_click_after_delay(generation)

func _emit_single_click_after_delay(generation: int) -> void:
    await get_tree().create_timer(0.34).timeout
    if generation != _click_generation:
        return
    if games.is_empty():
        return
    main_case_clicked.emit(games[selected_index])
