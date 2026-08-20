from pathlib import Path

from app.services.media_probe import MediaInfo, compute_subtitle_status, parse_ffprobe_payload


def test_parse_ffprobe_json_extracts_media_info() -> None:
    payload = {
        "format": {"duration": "123.5"},
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080},
            {"codec_type": "audio", "codec_name": "aac"},
            {"codec_type": "subtitle", "codec_name": "subrip"},
        ],
    }

    info = parse_ffprobe_payload(payload)

    assert info.duration == 123.5
    assert info.width == 1920
    assert info.height == 1080
    assert info.video_codec == "h264"
    assert info.audio_codec == "aac"
    assert info.embedded_subtitle_count == 1


def test_external_or_embedded_subtitle_counts_as_available(tmp_path: Path) -> None:
    assert compute_subtitle_status([tmp_path / "x.srt"], None) is True
    info = MediaInfo(None, None, None, None, None, 1)
    assert compute_subtitle_status([], info) is True
    assert compute_subtitle_status([], None) is False


def test_probe_decodes_utf8_json_with_non_ascii_filename(monkeypatch, tmp_path: Path) -> None:
    import subprocess

    from app.services.media_probe import MediaProbe

    payload = (
        '{"streams":[{"codec_type":"video","codec_name":"h264","width":1920,"height":1080},'
        '{"codec_type":"audio","codec_name":"aac"}],'
        '"format":{"duration":"6024.086333","filename":"E:/影片/特撮/TBW-35/TBW-35.re.mp4"}}'
    ).encode("utf-8")

    def fake_run(*args, **kwargs):
        assert kwargs.get("text") is not True
        return subprocess.CompletedProcess(args[0], 0, stdout=payload, stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)

    info = MediaProbe("ffprobe").probe(tmp_path / "TBW-35.re.mp4")

    assert info is not None
    assert info.duration == 6024.086333
    assert info.width == 1920
    assert info.height == 1080
    assert info.video_codec == "h264"
    assert info.audio_codec == "aac"


def test_probe_hides_ffprobe_console_on_windows(monkeypatch, tmp_path: Path) -> None:
    import subprocess
    import sys

    from app.services.media_probe import MediaProbe

    no_window = 0x08000000
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", no_window, raising=False)

    payload = b'{"streams":[],"format":{"duration":"1.0"}}'

    def fake_run(*args, **kwargs):
        assert kwargs.get("creationflags") == no_window
        return subprocess.CompletedProcess(args[0], 0, stdout=payload, stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert MediaProbe("ffprobe").probe(tmp_path / "movie.mp4") is not None
