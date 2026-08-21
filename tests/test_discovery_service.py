from pathlib import Path

from app.services.discovery_service import DiscoveryService


def test_discovery_stops_below_identified_movie_folder(tmp_path: Path) -> None:
    movie = tmp_path / "SPSD-62"
    extras = movie / "extras"
    extras.mkdir(parents=True)
    (movie / "SPSD-62.mp4").write_bytes(b"x" * 100)
    (extras / "bonus.mp4").write_bytes(b"x" * 200)

    candidates = DiscoveryService().discover(tmp_path)

    assert len(candidates) == 1
    assert [episode.video_path.name for episode in candidates[0].episodes] == ["SPSD-62.mp4"]


def test_groups_every_video_in_folder_as_one_work(tmp_path: Path) -> None:
    folder = tmp_path / "ABC-1"
    folder.mkdir()
    (folder / "ABC-1_10.mkv").write_bytes(b"x" * 10)
    (folder / "ABC-1_2.mp4").write_bytes(b"x" * 100)
    (folder / "ABC-1_1.mp4").write_bytes(b"x" * 30)

    candidates = DiscoveryService().discover(tmp_path)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.folder == folder
    assert candidate.cover_key == "ABC-1"
    assert candidate.inferred_code == "ABC-1"
    assert [episode.video_path.name for episode in candidate.episodes] == [
        "ABC-1_1.mp4",
        "ABC-1_2.mp4",
        "ABC-1_10.mkv",
    ]
    assert [episode.display_order for episode in candidate.episodes] == [1, 2, 3]
    assert [episode.episode_number for episode in candidate.episodes] == [1, 2, 10]


def test_discovers_external_subtitles_for_main_video(tmp_path: Path) -> None:
    folder = tmp_path / "ABC-1"
    folder.mkdir()
    (folder / "ABC-1.mkv").write_bytes(b"video")
    (folder / "ABC-1.zh.srt").write_text("", encoding="utf-8")
    (folder / "unrelated.srt").write_text("", encoding="utf-8")

    candidate = DiscoveryService().discover(tmp_path)[0]

    assert [path.name for path in candidate.episodes[0].subtitle_paths] == ["ABC-1.zh.srt"]


def test_duplicate_episode_numbers_fall_back_to_natural_order(tmp_path: Path) -> None:
    folder = tmp_path / "Series"
    folder.mkdir()
    (folder / "Part_01.mkv").write_bytes(b"one")
    (folder / "Special_01.mkv").write_bytes(b"special")
    (folder / "Part_2.mkv").write_bytes(b"two")

    candidate = DiscoveryService().discover(tmp_path)[0]

    assert [episode.video_path.name for episode in candidate.episodes] == [
        "Part_01.mkv",
        "Part_2.mkv",
        "Special_01.mkv",
    ]
    assert [episode.display_order for episode in candidate.episodes] == [1, 2, 3]
    assert [episode.episode_number for episode in candidate.episodes] == [None, 2, None]
