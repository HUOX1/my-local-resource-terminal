from pathlib import Path

from app.services.cover_service import CoverService


def test_cover_format_priority_is_stable(tmp_path: Path) -> None:
    covers = tmp_path / "covers"
    covers.mkdir()
    (covers / "SPSD-62.png").write_bytes(b"png")
    (covers / "spsd-62.jpg").write_bytes(b"jpg")
    service = CoverService(covers, tmp_path / "cache", ffmpeg_path="ffmpeg")

    result = service.resolve("SPSD-62", None, None)

    assert result.path is not None
    assert result.path.name.lower() == "spsd-62.jpg"
    assert result.source == "library"


def test_offline_movie_still_resolves_cover_by_cover_key(tmp_path: Path) -> None:
    covers = tmp_path / "covers"
    covers.mkdir()
    (covers / "ABC-1.jpg").write_bytes(b"jpg")
    service = CoverService(covers, tmp_path / "cache", "ffmpeg")

    result = service.resolve("ABC-1", None, None)

    assert result.source == "library"


def test_replace_uses_cover_key_and_removes_old_format(tmp_path: Path) -> None:
    covers = tmp_path / "covers"
    covers.mkdir()
    (covers / "ABC-1.png").write_bytes(b"old")
    source = tmp_path / "new.jpg"
    source.write_bytes(b"new")
    service = CoverService(covers, tmp_path / "cache", "ffmpeg")

    target = service.replace("ABC-1", source)

    assert target.name == "ABC-1.jpg"
    assert target.read_bytes() == b"new"
    assert not (covers / "ABC-1.png").exists()


def test_generated_cover_hides_ffmpeg_console_on_windows(monkeypatch, tmp_path: Path) -> None:
    import subprocess
    import sys

    covers = tmp_path / "covers"
    covers.mkdir()
    video = tmp_path / "movie.mp4"
    video.write_bytes(b"video")
    service = CoverService(covers, tmp_path / "cache", "ffmpeg")

    no_window = 0x08000000
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", no_window, raising=False)

    def fake_run(cmd, **kwargs):
        assert kwargs.get("creationflags") == no_window
        Path(cmd[-1]).write_bytes(b"jpg")
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = service.resolve("ABC-1", video, 100.0)

    assert result.source == "generated"
