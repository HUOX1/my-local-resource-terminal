extends Node3D
class_name GameCarousel3D

signal selection_changed(index: int, game: Dictionary)
signal main_case_clicked(game: Dictionary)
signal main_case_double_clicked(game: Dictionary)
signal main_case_right_clicked(game: Dictionary, screen_position: Vector2)

const CASE_SCRIPT: Script = preload("res://scripts/game_case_3d.gd")
const VISIBLE_SLOT_COUNT: int = 4
const SELECTED_SLOT: int = 1

# G1 reference composition: four covers span the window, with the selected cover
# in the second slot rather than at geometric center. X is expressed as viewport
# ratios so the composition survives normal window resize/maximize behavior.
const SLOT_SCREEN_X: Array[float] = [0.20, 0.455, 0.71, 0.89]
const SLOT_Y: Array[float] = [0.34, 0.34, 0.27, 0.18]
const SLOT_Z: Array[float] = [-2.35, 0.24, -1.55, -2.75]
const SLOT_SCALE: Array[float] = [2.70, 3.35, 2.85, 2.15]
const SLOT_BRIGHTNESS: Array[float] = [0.48, 1.00, 0.58, 0.34]
const SLOT_YAW_DEGREES: Array[float] = [6.0, 0.0, -5.0, -7.0]
const OFFSCREEN_SCREEN_MARGIN: float = 0.12
const PREVIEW_SCREEN_X: float = 0.26
const PREVIEW_ANCHOR_Y: float = -0.18
const PREVIEW_SELECTED_SCALE: float = 3.42
const PREVIEW_BACKGROUND_Z: float = -5.10
const PREVIEW_BACKGROUND_SCALE: float = 1.28
const PREVIEW_BACKGROUND_MIN_SCALE: float = 1.04
const TRACK_STEP_SECONDS: float = 0.38
const EXIT_SECONDS: float = 0.34
const MAX_QUEUED_STEPS: int = 8
const DRAG_THRESHOLD_PX: float = 7.0
const DRAG_YAW_DEGREES_PER_PX: float = 0.24
const DRAG_PITCH_DEGREES_PER_PX: float = 0.18

var games: Array[Dictionary] = []
var selected_index: int = 0
var preview_mode: bool = false
var camera: Camera3D
var _cases_by_index: Dictionary = {}
var _last_click_msec: int = 0
var _hover_index: int = -1
var _click_generation: int = 0
var _drag_candidate: bool = false
var _dragging: bool = false
var _drag_start_position: Vector2 = Vector2.ZERO
var _accent: Color = Color(0.20, 0.82, 0.76, 1.0)
var _secondary: Color = Color(0.25, 0.55, 0.90, 1.0)
var _transitioning: bool = false
var _queued_steps: int = 0
var _transition_generation: int = 0

func configure(target_camera: Camera3D) -> void:
    camera = target_camera
    set_process(true)
    set_process_input(true)
    get_viewport().size_changed.connect(_on_viewport_size_changed)

func set_games(value: Array[Dictionary]) -> void:
    games = value
    _transition_generation += 1
    _queued_steps = 0
    _transitioning = false
    _clear_cases()
    selected_index = clampi(selected_index, 0, maxi(games.size() - 1, 0))
    _ensure_visible_slots(0)
    _layout_targets()
    _emit_selection()

func set_theme_colors(accent: Color, secondary: Color) -> void:
    _accent = accent
    _secondary = secondary
    for index_value: Variant in _cases_by_index.keys():
        _cases_by_index[index_value].set_theme_colors(_accent, _secondary)

func set_preview_mode(value: bool) -> void:
    if preview_mode and not value:
        _cancel_case_drag()
    preview_mode = value
    _layout_targets()

func jump_to_index(index: int) -> void:
    if games.is_empty():
        return
    _transition_generation += 1
    _queued_steps = 0
    _transitioning = false
    selected_index = wrapi(index, 0, games.size())
    _clear_cases()
    _ensure_visible_slots(0)
    _layout_targets()
    _emit_selection()

func select_index(index: int) -> void:
    if games.is_empty():
        return
    var target: int = wrapi(index, 0, games.size())
    if target == selected_index:
        return
    var forward_distance: int = wrapi(target - selected_index, 0, games.size())
    var backward_distance: int = wrapi(selected_index - target, 0, games.size())
    if forward_distance <= backward_distance:
        _request_track_steps(forward_distance)
    else:
        _request_track_steps(-backward_distance)

func select_relative(delta_index: int) -> void:
    _request_track_steps(delta_index)

func _request_track_steps(delta_index: int) -> void:
    if games.is_empty() or delta_index == 0:
        return
    _queued_steps = clampi(_queued_steps + delta_index, -MAX_QUEUED_STEPS, MAX_QUEUED_STEPS)
    if not _transitioning:
        _consume_queued_steps()

func _consume_queued_steps() -> void:
    if _transitioning:
        return
    _transitioning = true
    var generation: int = _transition_generation
    while _queued_steps != 0 and not games.is_empty() and generation == _transition_generation:
        var direction: int = 1 if _queued_steps > 0 else -1
        _queued_steps -= direction
        selected_index = wrapi(selected_index + direction, 0, games.size())
        _shift_track(direction)
        _emit_selection()
        await get_tree().create_timer(TRACK_STEP_SECONDS).timeout
    if generation == _transition_generation:
        _transitioning = false

func selected_game() -> Dictionary:
    if games.is_empty() or selected_index < 0 or selected_index >= games.size():
        return {}
    return games[selected_index]

func selected_case_world_position() -> Vector3:
    if not _cases_by_index.has(selected_index):
        return Vector3(9999.0, 9999.0, 9999.0)
    return _cases_by_index[selected_index].global_position

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

func _slot_indices() -> Array[int]:
    var result: Array[int] = []
    if games.is_empty():
        return result
    var offsets: Array[int] = [-1, 0, 1, 2]
    var seen: Dictionary = {}
    for offset: int in offsets:
        var index: int = wrapi(selected_index + offset, 0, games.size())
        if not seen.has(index):
            seen[index] = true
            result.append(index)
    return result

func _slot_for_index(index: int) -> int:
    var slots: Array[int] = _slot_indices()
    return slots.find(index)

func _world_x_for_screen_ratio(screen_ratio: float, z_value: float) -> float:
    if camera == null:
        return 0.0
    var viewport_size: Vector2 = get_viewport().get_visible_rect().size
    if viewport_size.y <= 0.0:
        return 0.0
    var distance: float = absf(camera.global_position.z - z_value)
    var half_height: float = tan(deg_to_rad(camera.fov * 0.5)) * distance
    var half_width: float = half_height * (viewport_size.x / viewport_size.y)
    return camera.global_position.x + (screen_ratio - 0.5) * 2.0 * half_width

func _offscreen_x(z_value: float, right_side: bool) -> float:
    var screen_ratio: float = 1.0 + OFFSCREEN_SCREEN_MARGIN if right_side else -OFFSCREEN_SCREEN_MARGIN
    return _world_x_for_screen_ratio(screen_ratio, z_value)

func _spawn_case(index: int, spawn_x: float, slot: int) -> void:
    if _cases_by_index.has(index):
        return
    var item = CASE_SCRIPT.new()
    add_child(item)
    item.configure(games[index])
    item.set_theme_colors(_accent, _secondary)
    item.set_browse_style(SLOT_BRIGHTNESS[slot], SLOT_YAW_DEGREES[slot])
    item.rotation_degrees.y = SLOT_YAW_DEGREES[slot]
    item.position = Vector3(spawn_x, SLOT_Y[slot], SLOT_Z[slot])
    item.scale = Vector3.ONE * SLOT_SCALE[slot]
    _cases_by_index[index] = item

func _ensure_visible_slots(direction: int) -> void:
    var desired: Array[int] = _slot_indices()
    for index: int in desired:
        if _cases_by_index.has(index):
            continue
        var slot: int = _slot_for_index(index)
        var spawn_x: float = _world_x_for_screen_ratio(SLOT_SCREEN_X[slot], SLOT_Z[slot])
        if direction > 0:
            spawn_x = _offscreen_x(SLOT_Z[slot], true)
        elif direction < 0:
            spawn_x = _offscreen_x(SLOT_Z[slot], false)
        _spawn_case(index, spawn_x, slot)

func _shift_track(direction: int) -> void:
    var desired: Array[int] = _slot_indices()
    var leaving: Array[int] = []
    for index_value: Variant in _cases_by_index.keys():
        var index: int = int(index_value)
        if not desired.has(index):
            leaving.append(index)

    for index: int in leaving:
        var old_item = _cases_by_index[index]
        _cases_by_index.erase(index)
        old_item.set_hover(false)
        old_item.target_position.x = _offscreen_x(old_item.target_position.z, direction < 0)
        _dispose_after_exit(old_item)

    _ensure_visible_slots(direction)
    _layout_targets()

func _dispose_after_exit(item: Node) -> void:
    await get_tree().create_timer(EXIT_SECONDS).timeout
    if is_instance_valid(item):
        item.queue_free()

func _layout_targets() -> void:
    if _cases_by_index.is_empty():
        return
    for index_value: Variant in _cases_by_index.keys():
        var i: int = int(index_value)
        var item = _cases_by_index[i]
        var slot: int = _slot_for_index(i)
        if slot < 0:
            continue
        if preview_mode:
            item.set_focus_background(i != selected_index)
            if i == selected_index:
                item.set_browse_style(1.0, 0.0)
                var preview_z: float = 0.35
                item.target_position = Vector3(
                    _world_x_for_screen_ratio(PREVIEW_SCREEN_X, preview_z),
                    PREVIEW_ANCHOR_Y,
                    preview_z
                )
                item.target_scale = PREVIEW_SELECTED_SCALE
            else:
                item.set_browse_style(SLOT_BRIGHTNESS[slot], SLOT_YAW_DEGREES[slot])
                var bg_z: float = PREVIEW_BACKGROUND_Z - float(slot) * 0.28
                var bg_ratio: float = 0.06 if slot == 0 else 0.82 + float(slot - 2) * 0.10
                item.target_position = Vector3(
                    _world_x_for_screen_ratio(bg_ratio, bg_z),
                    -0.18,
                    bg_z
                )
                item.target_scale = maxf(PREVIEW_BACKGROUND_MIN_SCALE, PREVIEW_BACKGROUND_SCALE - float(abs(slot - SELECTED_SLOT)) * 0.12)
        else:
            item.set_focus_background(false)
            item.set_browse_style(SLOT_BRIGHTNESS[slot], SLOT_YAW_DEGREES[slot])
            item.target_position = Vector3(
                _world_x_for_screen_ratio(SLOT_SCREEN_X[slot], SLOT_Z[slot]),
                SLOT_Y[slot],
                SLOT_Z[slot]
            )
            item.target_scale = SLOT_SCALE[slot]
        item.set_selected(i == selected_index)

func _on_viewport_size_changed() -> void:
    _layout_targets()

func _emit_selection() -> void:
    if not games.is_empty():
        selection_changed.emit(selected_index, games[selected_index])

func _input(event: InputEvent) -> void:
    if not visible or games.is_empty():
        return
    if event is InputEventMouseMotion:
        if _drag_candidate:
            _update_case_drag((event as InputEventMouseMotion).position)
            get_viewport().set_input_as_handled()
        return
    if event is InputEventMouseButton:
        var mouse_event: InputEventMouseButton = event as InputEventMouseButton
        if mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_WHEEL_UP:
            select_relative(-1); get_viewport().set_input_as_handled(); return
        if mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
            select_relative(1); get_viewport().set_input_as_handled(); return
        if mouse_event.button_index == MOUSE_BUTTON_LEFT:
            if mouse_event.pressed:
                if preview_mode and _begin_case_drag(mouse_event.position):
                    get_viewport().set_input_as_handled(); return
                if _handle_left_click(mouse_event.position):
                    get_viewport().set_input_as_handled()
                return
            if _drag_candidate and _finish_case_drag(mouse_event.position):
                get_viewport().set_input_as_handled(); return
        if mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_RIGHT:
            if _handle_right_click(mouse_event.position):
                get_viewport().set_input_as_handled()
            return
    if event is InputEventKey:
        var key_event: InputEventKey = event as InputEventKey
        if key_event.pressed and not key_event.echo:
            if key_event.keycode == KEY_LEFT: select_relative(-1)
            elif key_event.keycode == KEY_RIGHT: select_relative(1)

func _begin_case_drag(position_2d: Vector2) -> bool:
    if _hit_test(position_2d) != selected_index or not _cases_by_index.has(selected_index):
        return false
    _drag_candidate = true
    _dragging = false
    _drag_start_position = position_2d
    _cases_by_index[selected_index].set_hover(false)
    return true

func _update_case_drag(position_2d: Vector2) -> void:
    if not _drag_candidate or not _cases_by_index.has(selected_index): return
    var drag_delta: Vector2 = position_2d - _drag_start_position
    if not _dragging:
        if drag_delta.length() < DRAG_THRESHOLD_PX: return
        _dragging = true
        _cases_by_index[selected_index].begin_drag()
    _cases_by_index[selected_index].set_drag_rotation(drag_delta.x * DRAG_YAW_DEGREES_PER_PX, -drag_delta.y * DRAG_PITCH_DEGREES_PER_PX)

func _finish_case_drag(position_2d: Vector2) -> bool:
    if not _drag_candidate: return false
    var was_dragging: bool = _dragging
    _drag_candidate = false; _dragging = false
    if _cases_by_index.has(selected_index): _cases_by_index[selected_index].end_drag()
    if not was_dragging: _handle_left_click(position_2d)
    return true

func _cancel_case_drag() -> void:
    if _cases_by_index.has(selected_index): _cases_by_index[selected_index].end_drag()
    _drag_candidate = false; _dragging = false

func _process(_delta: float) -> void:
    if camera == null or _cases_by_index.is_empty() or _drag_candidate: return
    var mouse: Vector2 = get_viewport().get_mouse_position()
    var nearest_index: int = -1
    var nearest_distance: float = 999999.0
    var candidate_indices: Array = [selected_index] if preview_mode else _cases_by_index.keys()
    for index_value: Variant in candidate_indices:
        var i: int = int(index_value)
        if not _cases_by_index.has(i): continue
        var item = _cases_by_index[i]
        if camera.is_position_behind(item.global_position) or not _point_hits_case(mouse, item): continue
        var distance: float = mouse.distance_to(camera.unproject_position(item.global_position))
        if distance < nearest_distance:
            nearest_distance = distance; nearest_index = i
    if nearest_index != _hover_index:
        if _hover_index >= 0 and _cases_by_index.has(_hover_index): _cases_by_index[_hover_index].set_hover(false)
        _hover_index = nearest_index
    if _hover_index >= 0 and _cases_by_index.has(_hover_index):
        var hovered_case = _cases_by_index[_hover_index]
        var center: Vector2 = camera.unproject_position(hovered_case.global_position)
        var display_scale: float = maxf(hovered_case.scale.x, hovered_case.target_scale)
        var normalized: Vector2 = (mouse - center) / Vector2(68.0 * display_scale, 92.0 * display_scale)
        hovered_case.set_hover(true, Vector2(clampf(normalized.x, -1.0, 1.0), clampf(normalized.y, -1.0, 1.0)))

func _point_hits_case(position_2d: Vector2, item) -> bool:
    if camera == null or item == null: return false
    var screen: Vector2 = camera.unproject_position(item.global_position)
    var display_scale: float = maxf(item.scale.x, item.target_scale)
    var half_extents: Vector2 = Vector2(64.0 * display_scale + 8.0, 88.0 * display_scale + 8.0)
    return Rect2(screen - half_extents, half_extents * 2.0).has_point(position_2d)

func _hit_test(position_2d: Vector2) -> int:
    if camera == null or _cases_by_index.is_empty(): return -1
    if preview_mode: return _hit_test_selected_case(position_2d)
    var clicked_index: int = -1
    var best: float = 999999.0
    for index_value: Variant in _cases_by_index.keys():
        var i: int = int(index_value)
        var item = _cases_by_index[i]
        if not _point_hits_case(position_2d, item): continue
        var distance: float = position_2d.distance_to(camera.unproject_position(item.global_position))
        if distance < best: best = distance; clicked_index = i
    return clicked_index

func _hit_test_selected_case(position_2d: Vector2) -> int:
    if not _cases_by_index.has(selected_index): return -1
    return selected_index if _point_hits_case(position_2d, _cases_by_index[selected_index]) else -1

func _handle_left_click(position_2d: Vector2) -> bool:
    var clicked_index: int = _hit_test(position_2d)
    if clicked_index < 0: return false
    if clicked_index != selected_index:
        select_index(clicked_index); return true
    var now_msec: int = Time.get_ticks_msec()
    var is_double: bool = now_msec - _last_click_msec <= 330
    _last_click_msec = now_msec
    _click_generation += 1
    var generation: int = _click_generation
    if is_double:
        main_case_double_clicked.emit(games[selected_index]); return true
    _emit_single_click_after_delay(generation)
    return true

func _handle_right_click(position_2d: Vector2) -> bool:
    var clicked_index: int = _hit_test(position_2d)
    if clicked_index < 0: return false
    if clicked_index != selected_index:
        select_index(clicked_index)
    main_case_right_clicked.emit(games[clicked_index], position_2d)
    return true

func _emit_single_click_after_delay(generation: int) -> void:
    await get_tree().create_timer(0.34).timeout
    if generation == _click_generation and not games.is_empty():
        main_case_clicked.emit(games[selected_index])
