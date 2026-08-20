from datetime import datetime, timezone
from pathlib import Path

from app.models.movie import MovieMetadata, PlayEvent
from app.services.metadata_service import MetadataService


def test_metadata_survives_without_video_path(tmp_path: Path) -> None:
    service = MetadataService(tmp_path / "metadata")
    movie = MovieMetadata.new(cover_key="SPSD-62", code="SPSD-62")
    movie.title = "示例影片"
    service.save(movie)

    loaded = service.load(movie.uuid)

    assert loaded.uuid == movie.uuid
    assert loaded.cover_key == "SPSD-62"
    assert loaded.title == "示例影片"
    assert not hasattr(loaded, "video_path")


def test_play_history_round_trip(tmp_path: Path) -> None:
    service = MetadataService(tmp_path / "metadata")
    when = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    movie = MovieMetadata.new("SPSD-62", "SPSD-62")
    movie.play_count = 1
    movie.watched = True
    movie.first_watched_at = when
    movie.last_watched_at = when
    movie.play_history.append(PlayEvent(when))

    service.save(movie)
    loaded = service.load(movie.uuid)

    assert loaded.play_count == 1
    assert loaded.first_watched_at == when
    assert loaded.play_history == [PlayEvent(when)]


def test_load_all_skips_corrupt_json(tmp_path: Path) -> None:
    service = MetadataService(tmp_path)
    good = MovieMetadata.new("GOOD-1", "GOOD-1")
    service.save(good)
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")

    movies, errors = service.load_all()

    assert [m.uuid for m in movies] == [good.uuid]
    assert len(errors) == 1


def test_added_at_is_persisted_and_legacy_metadata_is_migrated(tmp_path: Path) -> None:
    import json
    import os
    from datetime import datetime, timezone

    service = MetadataService(tmp_path / "metadata")
    movie = service.create("ABC-1", "ABC-1")
    loaded = service.load(movie.uuid)
    assert loaded.added_at == movie.added_at

    legacy_path = service.path_for("legacy")
    legacy_path.write_text(
        json.dumps({
            "schema_version": 1,
            "uuid": "legacy",
            "cover_key": "LEGACY-1",
            "code": "LEGACY-1",
        }),
        encoding="utf-8",
    )
    legacy_time = datetime(2025, 1, 2, 3, 4, tzinfo=timezone.utc).timestamp()
    os.utime(legacy_path, (legacy_time, legacy_time))

    migrated = service.load("legacy")
    assert migrated.added_at == datetime.fromtimestamp(legacy_time, tz=timezone.utc)
    payload = json.loads(legacy_path.read_text(encoding="utf-8"))
    assert payload["added_at"] == migrated.added_at.isoformat()


def test_movie_folder_id_round_trip_and_legacy_default(tmp_path: Path) -> None:
    import json

    service = MetadataService(tmp_path / "metadata")
    movie = MovieMetadata.new("ABC-2", "ABC-2")
    movie.folder_id = "folder-movies-1"
    service.save(movie)

    restored = service.load(movie.uuid)
    assert restored.folder_id == "folder-movies-1"

    payload = json.loads(service.path_for(movie.uuid).read_text(encoding="utf-8"))
    payload.pop("folder_id")
    service.path_for(movie.uuid).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    assert service.load(movie.uuid).folder_id is None
