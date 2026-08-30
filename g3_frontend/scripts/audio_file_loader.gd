extends RefCounted
class_name AudioFileLoader

static func load_audio(path: String, loop: bool = false) -> AudioStream:
    if path.is_empty():
        return null
    var extension: String = path.get_extension().to_lower()
    if extension == "mp3":
        var mp3: AudioStreamMP3 = AudioStreamMP3.load_from_file(path)
        if mp3 != null:
            mp3.loop = loop
        return mp3
    if extension == "ogg" or extension == "oga":
        var ogg: AudioStreamOggVorbis = AudioStreamOggVorbis.load_from_file(path)
        if ogg != null:
            ogg.loop = loop
        return ogg
    if extension == "wav":
        var wav: AudioStreamWAV = AudioStreamWAV.load_from_file(path)
        if wav != null and loop:
            wav.loop_mode = AudioStreamWAV.LOOP_FORWARD
        return wav
    return null
