from pathlib import Path

from app.services.discovery_service import DiscoveryService


def test_discovery_stops_below_identified_movie_folder(tmp_path: Path) -> None:
    movie = tmp_path / "SPSD-62"
    extras = movie / "extras"
    extras.mkdir(parents=True)
    (movie / "SPSD-62.mp4").write_bytes(b"x" * 100)
    (extras / "bonus.mp4").write_bytes(b"x" * 200)

    candidates = DiscoveryService().discover(tmp_path)

    assert [c.video_path.name for c in candidates] == ["SPSD-62.mp4"]


def test_selects_exact_folder_stem_before_larger_video(tmp_path: Path) -> None:
    folder = tmp_path / "ABC-1"
    folder.mkdir()
    (folder / "ABC-1.mkv").write_bytes(b"x" * 10)
    (folder / "other.mp4").write_bytes(b"x" * 100)

    candidate = DiscoveryService().discover(tmp_path)[0]

    assert candidate.video_path.name == "ABC-1.mkv"


def test_discovers_external_subtitles_for_main_video(tmp_path: Path) -> None:
    folder = tmp_path / "ABC-1"
    folder.mkdir()
    (folder / "ABC-1.mkv").write_bytes(b"video")
    (folder / "ABC-1.zh.srt").write_text("", encoding="utf-8")
    (folder / "unrelated.srt").write_text("", encoding="utf-8")

    candidate = DiscoveryService().discover(tmp_path)[0]

    assert [path.name for path in candidate.subtitle_paths] == ["ABC-1.zh.srt"]
