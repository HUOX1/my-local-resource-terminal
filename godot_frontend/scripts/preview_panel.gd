extends Control
class_name PreviewPanel

signal media_audio_activity_changed(active: bool)

const AUDIO_LOADER: Script = preload("res://scripts/audio_file_loader.gd")

var _title: Label
var _description: Label
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

func _ready() -> void:
    mouse_filter = Control.MOUSE_FILTER_IGNORE
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
    _title = Label.new()
    _title.position = Vector2(0, 0)
    _title.size = Vector2(520, 48)
    _title.add_theme_font_size_override("font_size", 32)
    add_child(_title)

    _description = Label.new()
    _description.position = Vector2(0, 54)
    _description.size = Vector2(520, 78)
    _description.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    _description.add_theme_font_size_override("font_size", 14)
    _description.add_theme_color_override("font_color", Color(0.72, 0.72, 0.82))
    add_child(_description)

    _image = TextureRect.new()
    _image.position = Vector2(0, 150)
    _image.size = Vector2(520, 292)
    _image.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    _image.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
    add_child(_image)

    _video = VideoStreamPlayer.new()
    _video.position = Vector2(0, 150)
    _video.size = Vector2(520, 292)
    _video.expand = true
    _video.visible = false
    _video.finished.connect(_on_video_finished)
    add_child(_video)

    _audio = AudioStreamPlayer.new()
    add_child(_audio)

    _status = Label.new()
    _status.position = Vector2(0, 454)
    _status.size = Vector2(520, 26)
    _status.add_theme_font_size_override("font_size", 12)
    _status.add_theme_color_override("font_color", Color(0.48, 0.50, 0.64))
    add_child(_status)
    set_audio_preferences(_preview_audio_enabled, _preview_volume)

func show_game(game: Dictionary, manifest: Dictionary = {}) -> void:
    visible = true
    _title.text = str(game.get("title", "Untitled"))
    _description.text = str(game.get("description", ""))
    _stop_media()
    _status.text = ""

    var video_path: String = str(manifest.get("video_ogv", ""))
    if not video_path.is_empty():
        var stream: VideoStreamTheora = VideoStreamTheora.new()
        stream.file = video_path
        _video.stream = stream
        _video.visible = true
        _video.volume_db = linear_to_db(maxf(_preview_volume, 0.0001)) if _preview_audio_enabled else -80.0
        _video.play()
        media_audio_activity_changed.emit(_preview_audio_enabled)
        _status.text = "VIDEO PREVIEW"
        return

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
        _status.text = "ANIMATED PREVIEW"
    else:
        var screenshots_variant: Variant = manifest.get("screenshots", [])
        if screenshots_variant is Array and not (screenshots_variant as Array).is_empty():
            _load_image(str((screenshots_variant as Array)[0]))
            _status.text = "SCREENSHOT"
        else:
            var background_path: String = str(manifest.get("background", ""))
            if not background_path.is_empty():
                _load_image(background_path)
                _status.text = "BACKGROUND"
            else:
                _status.text = "NO PREVIEW MEDIA"

    _play_optional_audio(str(manifest.get("preview_audio", "")))

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
    _audio.stop()
    _audio.stream = null
    _image.texture = null
    _image.visible = true
    media_audio_activity_changed.emit(false)

func _on_video_finished() -> void:
    media_audio_activity_changed.emit(false)
