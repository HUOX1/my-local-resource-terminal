from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config.settings import AppSettings
from app.db.database import Database
from app.models.movie import MovieMetadata
from app.repositories.movie_repository import MovieRepository
from app.services.metadata_service import MetadataService
from app.services.player_service import PlaybackError, PlayerService
from app.services.viewing_service import ViewingService


def build_services(tmp_path: Path):
    metadata = MetadataService(tmp_path / "metadata")
    db = Database(tmp_path / "library.db")
    db.initialize()
    repo = MovieRepository(db)
    movie = MovieMetadata.new("SPSD-62", "SPSD-62")
    metadata.save(movie)
    repo.upsert_metadata(movie)
    return metadata, repo, movie


def test_record_launch_updates_json_and_sqlite(tmp_path: Path) -> None:
    metadata, repo, movie = build_services(tmp_path)
    viewing = ViewingService(repo, metadata)
    when = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)

    updated = viewing.record_launch(movie.uuid, when)

    assert updated.watched is True
    assert updated.play_count == 1
    assert updated.first_watched_at == when
    assert updated.last_watched_at == when
    assert updated.play_history[-1].played_at == when
    assert repo.get(movie.uuid).metadata.play_count == 1
    assert metadata.load(movie.uuid).play_count == 1


def test_player_rejects_missing_video(tmp_path: Path) -> None:
    settings = AppSettings(tmp_path / "data", tmp_path / "covers", [])
    with pytest.raises(PlaybackError):
        PlayerService().play(tmp_path / "missing.mp4", settings)


def test_custom_player_uses_argument_list_without_shell(tmp_path: Path) -> None:
    player = tmp_path / "player.exe"
    player.write_bytes(b"x")
    video = tmp_path / "movie.mp4"
    video.write_bytes(b"x")
    settings = AppSettings(
        tmp_path / "data",
        tmp_path / "covers",
        [],
        player_mode="custom",
        player_path=player,
    )

    with patch("app.services.player_service.subprocess.Popen") as popen:
        PlayerService().play(video, settings)

    popen.assert_called_once_with([str(player), str(video)])
