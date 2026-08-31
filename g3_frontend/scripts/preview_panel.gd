extends Control
class_name PreviewPanel

signal media_audio_activity_changed(active: bool)

const AUDIO_LOADER: Script = preload("res://scripts/audio_file_loader.gd")
const TEXT_ANIMATION_OFFSET_X: float = 32.0
const MEDIA_ANIMATION_OFFSET_Y: float = 24.0
const ANIMATION_DURATION: float = 0.28

var _text_group: Control
var _media_group: Control
var _title: Label
var _metadata: Label
var _description: Label
var _details: Label
var _image: TextureRect
var _video: VideoStreamPlayer
var _audio: AudioStreamPlayer
var _status: Label
var _gif_frames: Array[String] = []
var _gif_durations: Array[int] = []
var _gif_index: int = 0
var _gif_elapsed_ms: float = 0.0
var _preview_audio_enabled: bool = true
var _preview_volume: float = 0.25
var _enter_tween: Tween
var _base_text_position: Vector2 = Vector2.ZERO
var _base_media_position: Vector2 = Vector2.ZERO

func _ready() -> void:
    mouse_filter = Control.MOUSE_FILTER_STOP
    _build_ui()
    set_process(true)

func set_audio_preferences(enabled: bool, volume: float) -> void:
    _preview_audio_enabled = enabled
    _preview_volume = clampf(volume, 0.0, 1.0)
    var db: float = linear_to_db(maxf(_preview_volume, 0.0001))
    if _video != null:
        _video.volume_db = db
    if _audio != null:
        _audio.volume_db = db

func _build_ui() -> void:
    _text_group = Control.new()
    _text_group.position = Vector2.ZERO
    _text_group.size = Vector2(620.0, 248.0)
    add_child(_text_group)
    _base_text_position = _text_group.position

    _title = Label.new()
    _title.position = Vector2(0, 0)
    _title.size = Vector2(620, 48)
    _title.add_theme_font_size_override("font_size", 34)
    _text_group.add_child(_title)

    _metadata = Label.new()
    _metadata.position = Vector2(0, 50)
    _metadata.size = Vector2(620, 28)
    _metadata.add_theme_font_size_override("font_size", 14)
    _metadata.add_theme_color_override("font_color", Color(0.62, 0.78, 0.80))
    _text_group.add_child(_metadata)

    _description = Label.new()
    _description.position = Vector2(0, 90)
    _description.size = Vector2(620, 124)
    _description.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    _description.add_theme_font_size_override("font_size", 15)
    _description.add_theme_color_override("font_color", Color(0.78, 0.80, 0.84))
    _text_group.add_child(_description)

    _details = Label.new()
    _details.position = Vector2(0, 220)
    _details.size = Vector2(620, 74)
    _details.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    _details.add_theme_font_size_override("font_size", 12)
    _details.add_theme_color_override("font_color", Color(0.56, 0.66, 0.70))
    _text_group.add_child(_details)

    _media_group = Control.new()
    _media_group.position = Vector2(0, 318)
    _media_group.size = Vector2(620.0, 260.0)
    add_child(_media_group)
    _base_media_position = _media_group.position

    _image = TextureRect.new()
    _image.position = Vector2(0, 0)
    _image.size = Vector2(560, 224)
    _image.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    _image.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
    _media_group.add_child(_image)

    _video = VideoStreamPlayer.new()
    _video.position = Vector2(0, 0)
    _video.size = Vector2(560, 224)
    _video.expand = true
    _video.visible = false
    _video.finished.connect(_on_video_finished)
    _media_group.add_child(_video)

    _audio = AudioStreamPlayer.new()
    add_child(_audio)

    _status = Label.new()
    _status.position = Vector2(0, 236)
    _status.size = Vector2(560, 24)
    _status.add_theme_font_size_override("font_size", 12)
    _status.add_theme_color_override("font_color", Color(0.48, 0.50, 0.64))
    _media_group.add_child(_status)
    set_audio_preferences(_preview_audio_enabled, _preview_volume)

func show_game(game: Dictionary, manifest: Dictionary = {}) -> void:
    visible = true
    _title.text = str(game.get("title", "Untitled"))
    _metadata.text = _format_metadata(game)
    _description.text = str(game.get("description", ""))
    _details.text = _format_details(game)
    _stop_media()
    _set_status("", false)

    var has_visual_media: bool = false
    var video_path: String = str(manifest.get("video_ogv", ""))
    if not video_path.is_empty():
        var stream: VideoStreamTheora = VideoStreamTheora.new()
        stream.file = video_path
        _video.stream = stream
        _video.visible = true
        _video.volume_db = linear_to_db(maxf(_preview_volume, 0.0001)) if _preview_audio_enabled else -80.0
        _video.play()
        media_audio_activity_changed.emit(_preview_audio_enabled)
        has_visual_media = true
    else:
        var gif_variant: Variant = manifest.get("gif_frames", [])
        if gif_variant is Array and not (gif_variant as Array).is_empty():
            _gif_frames.clear()
            for path_value: Variant in gif_variant as Array:
                _gif_frames.append(str(path_value))
            var durations_variant: Variant = manifest.get("gif_durations_ms", [])
            _gif_durations.clear()
            if durations_variant is Array:
                for duration_value: Variant in durations_variant as Array:
                    _gif_durations.append(int(duration_value))
            _gif_index = 0
            _gif_elapsed_ms = 0.0
            _show_gif_frame()
            has_visual_media = true
        else:
            var screenshots_variant: Variant = manifest.get("screenshots", [])
            if screenshots_variant is Array and not (screenshots_variant as Array).is_empty():
                _load_image(str((screenshots_variant as Array)[0]))
                has_visual_media = true
            else:
                var background_path: String = str(manifest.get("background", ""))
                if not background_path.is_empty():
                    _load_image(background_path)
                    has_visual_media = true

    if not has_visual_media:
        _set_status("暂无预览素材", true)

    _play_optional_audio(str(manifest.get("preview_audio", "")))
    _play_enter_animation(has_visual_media)

func _format_metadata(game: Dictionary) -> String:
    var parts: PackedStringArray = PackedStringArray()
    var platform: String = str(game.get("platform", "")).strip_edges()
    if not platform.is_empty():
        parts.append(platform)
    var release_year_value: Variant = game.get("release_year")
    if release_year_value != null and int(release_year_value) > 0:
        parts.append(str(release_year_value))
    var developer: String = str(game.get("developer", "")).strip_edges()
    if not developer.is_empty():
        parts.append("开发：" + developer)
    var publisher: String = str(game.get("publisher", "")).strip_edges()
    if not publisher.is_empty():
        parts.append("发行：" + publisher)
    return "  ·  ".join(parts)

func _format_details(game: Dictionary) -> String:
    var lines: PackedStringArray = PackedStringArray()
    var tags: String = str(game.get("tags", "")).strip_edges()
    if not tags.is_empty():
        lines.append("标签：" + tags)
    var notes: String = str(game.get("notes", "")).strip_edges()
    if not notes.is_empty():
        lines.append("备注：" + notes)
    return "\n".join(lines)

func hide_preview() -> void:
    _stop_media()
    visible = false

func _process(delta: float) -> void:
    if _gif_frames.is_empty():
        return
    _gif_elapsed_ms += delta * 1000.0
    var duration_ms: int = 100
    if _gif_index < _gif_durations.size():
        duration_ms = maxi(20, _gif_durations[_gif_index])
    if _gif_elapsed_ms >= float(duration_ms):
        _gif_elapsed_ms = 0.0
        _gif_index = (_gif_index + 1) % _gif_frames.size()
        _show_gif_frame()

func _show_gif_frame() -> void:
    if _gif_frames.is_empty():
        return
    _load_image(_gif_frames[_gif_index])

func _load_image(path: String) -> void:
    var image: Image = Image.new()
    var load_error: int = image.load(path)
    if load_error != OK:
        return
    _image.texture = ImageTexture.create_from_image(image)
    _image.visible = true

func _set_status(text: String, visible_value: bool) -> void:
    _status.text = text
    _status.visible = visible_value

func _play_optional_audio(path: String) -> void:
    if not _preview_audio_enabled or path.is_empty():
        media_audio_activity_changed.emit(false)
        return
    var stream: AudioStream = AUDIO_LOADER.load_audio(path, true)
    if stream == null:
        media_audio_activity_changed.emit(false)
        return
    _audio.stream = stream
    _audio.volume_db = linear_to_db(maxf(_preview_volume, 0.0001))
    _audio.play()
    media_audio_activity_changed.emit(true)

func _stop_media() -> void:
    _gif_frames.clear()
    _gif_durations.clear()
    _gif_index = 0
    _gif_elapsed_ms = 0.0
    _video.stop()
    _video.visible = false
    _video.stream = null
    _audio.stop()
    _audio.stream = null
    _image.texture = null
    _image.visible = true
    _set_status("", false)
    media_audio_activity_changed.emit(false)

func _play_enter_animation(has_visual_media: bool) -> void:
    if _enter_tween != null and _enter_tween.is_valid():
        _enter_tween.kill()

    _text_group.position = _base_text_position + Vector2(TEXT_ANIMATION_OFFSET_X, 0.0)
    _text_group.modulate.a = 0.0
    _media_group.position = _base_media_position + Vector2(0.0, MEDIA_ANIMATION_OFFSET_Y)
    _media_group.modulate.a = 0.0 if has_visual_media or _status.visible else 1.0

    _enter_tween = create_tween()
    _enter_tween.set_parallel(true)
    _enter_tween.tween_property(_text_group, "position", _base_text_position, ANIMATION_DURATION)
    _enter_tween.tween_property(_text_group, "modulate:a", 1.0, ANIMATION_DURATION)
    _enter_tween.tween_property(_media_group, "position", _base_media_position, ANIMATION_DURATION)
    _enter_tween.tween_property(_media_group, "modulate:a", 1.0, ANIMATION_DURATION)

func _on_video_finished() -> void:
    media_audio_activity_changed.emit(false)
