from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from app.config.settings import AppSettings
from app.db.database import Database
from app.models.movie import MovieMetadata
from app.repositories.movie_repository import MovieRepository
from app.services.metadata_service import MetadataService
from app.services.player_service import PlayerService
from app.services.viewing_service import ViewingService

ROOT = Path(__file__).resolve().parents[1]


def _build_movie_services(tmp_path: Path):
    metadata = MetadataService(tmp_path / "metadata")
    database = Database(tmp_path / "library.db")
    database.initialize()
    repository = MovieRepository(database)
    movie = MovieMetadata.new("MOVIE", "MOVIE")
    metadata.save(movie)
    repository.upsert_metadata(movie)
    return metadata, repository, movie


def test_movie_metadata_has_permanent_total_play_seconds_and_round_trips(tmp_path: Path) -> None:
    metadata, repository, movie = _build_movie_services(tmp_path)

    assert hasattr(movie, "total_play_seconds")
    movie.total_play_seconds = 3723
    metadata.save(movie)
    repository.upsert_metadata(movie)

    assert metadata.load(movie.uuid).total_play_seconds == 3723
    assert repository.get(movie.uuid).metadata.total_play_seconds == 3723


def test_viewing_service_accumulates_real_tracked_process_time(tmp_path: Path) -> None:
    metadata, repository, movie = _build_movie_services(tmp_path)
    viewing = ViewingService(repository, metadata)
    start = datetime(2026, 8, 19, 0, 0, tzinfo=timezone.utc)

    class FakeHandle:
        def __init__(self) -> None:
            self.running = True
            self.closed = False

        def is_running(self) -> bool:
            return self.running

        def close(self) -> None:
            self.closed = True

    handle = FakeHandle()
    viewing.start_playback(movie.uuid, handle, started_at=start)
    handle.running = False
    viewing.poll_playbacks(now=start + timedelta(seconds=366))

    updated = metadata.load(movie.uuid)
    assert updated.total_play_seconds == 366
    assert handle.closed is True


def test_custom_player_returns_trackable_playback_handle(tmp_path: Path) -> None:
    player_path = tmp_path / "player.exe"
    player_path.write_bytes(b"x")
    video = tmp_path / "movie.mp4"
    video.write_bytes(b"x")
    settings = AppSettings(
        tmp_path / "data",
        tmp_path / "covers",
        [],
        player_mode="custom",
        player_path=player_path,
    )

    class FakeProcess:
        def poll(self):
            return None

    with patch("app.services.player_service.subprocess.Popen", return_value=FakeProcess()):
        handle = PlayerService().play(video, settings)

    assert handle is not None
    assert handle.is_running() is True


def test_main_window_uses_explicit_system_resize_handles_instead_of_status_grip_only() -> None:
    main = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    resize = (ROOT / "app" / "ui" / "window_resize.py")
    assert resize.exists()
    resize_source = resize.read_text(encoding="utf-8")
    assert "startSystemResize" in resize_source
    assert "top_left" in resize_source
    assert "bottom_right" in resize_source
    assert "WindowResizeFrame" in main


def test_movie_archive_removes_watched_favorite_counts_and_uses_natural_larger_cover() -> None:
    source = (ROOT / "app" / "ui" / "movie_archive_page.py").read_text(encoding="utf-8")
    assert "watched_button" not in source
    assert "favorite_button" not in source
    assert "movie.play_count" not in source
    assert "first_watched_at" not in source
    assert "last_watched_at" not in source
    assert "total_play_seconds" in source
    assert "_format_hours" in source
    assert "setFixedSize(220, 320)" not in source
    assert "COVER_WIDTH = 280" in source
    assert "scaledToWidth" in source


def test_game_archive_play_area_uses_decimal_hours_and_not_play_count() -> None:
    source = (ROOT / "app" / "ui" / "game_archive_page.py").read_text(encoding="utf-8")
    assert "game.play_count" not in source
    assert "_format_hours" in source
    assert "total_play_seconds" in source
