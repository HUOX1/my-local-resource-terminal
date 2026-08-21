from datetime import datetime, timezone
from pathlib import Path

import json

from app.models.movie import MovieEpisodeMetadata, MovieMetadata, PlayEvent
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
    assert payload["schema_version"] == 2
    assert payload["episodes"] == [
        {
            "uuid": "e3b45b99-bcfb-5601-8168-a1f50ae86289",
            "display_order": 1,
            "episode_number": None,
            "season_number": None,
            "source_name": "",
        }
    ]


def test_movie_folder_id_round_trip_and_legacy_default(tmp_path: Path) -> None:
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


def test_schema_v1_migration_preserves_edited_metadata_and_play_history(tmp_path: Path) -> None:
    service = MetadataService(tmp_path / "metadata")
    path = service.path_for("legacy-edited")
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "uuid": "legacy-edited",
                "cover_key": "SHOW",
                "code": "SHOW",
                "title": "手工标题",
                "actors": ["演员 A"],
                "series": "系列",
                "studio": "厂商",
                "release_date": "2026-08-21",
                "tags": ["标签"],
                "rating": 4,
                "watched": True,
                "play_count": 2,
                "total_play_seconds": 123,
                "favorite": True,
                "notes": "保留备注",
                "folder_id": "folder-1",
                "first_watched_at": "2026-08-20T10:00:00+00:00",
                "last_watched_at": "2026-08-21T10:00:00+00:00",
                "added_at": "2026-08-19T10:00:00+00:00",
                "play_history": [
                    {"played_at": "2026-08-20T10:00:00+00:00"},
                    {"played_at": "2026-08-21T10:00:00+00:00"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    movie = service.load("legacy-edited")

    assert movie.title == "手工标题"
    assert movie.actors == ["演员 A"]
    assert movie.rating == 4
    assert movie.favorite is True
    assert movie.notes == "保留备注"
    assert movie.folder_id == "folder-1"
    assert movie.play_count == 2
    assert movie.total_play_seconds == 123
    assert len(movie.play_history) == 2
    assert len(movie.episodes) == 1
    assert movie.episodes[0].uuid == "8126dd25-543b-5d4a-b127-86b71b3df6a8"


def test_schema_v2_round_trip_preserves_ordered_episode_metadata(tmp_path: Path) -> None:
    service = MetadataService(tmp_path / "metadata")
    movie = MovieMetadata(
        uuid="work-episodes",
        cover_key="SHOW",
        code="SHOW",
        episodes=[
            MovieEpisodeMetadata(
                uuid="episode-2",
                display_order=2,
                episode_number=2,
                source_name="SHOW_02.mkv",
            ),
            MovieEpisodeMetadata(
                uuid="episode-1",
                display_order=1,
                episode_number=1,
                season_number=1,
                source_name="SHOW_S01E01.mkv",
            ),
        ],
    )

    service.save(movie)
    restored = service.load(movie.uuid)
    payload = json.loads(service.path_for(movie.uuid).read_text(encoding="utf-8"))

    assert payload["schema_version"] == 2
    assert [episode.uuid for episode in restored.episodes] == ["episode-1", "episode-2"]
    assert restored.episodes[0].season_number == 1
    assert restored.episodes[1].source_name == "SHOW_02.mkv"
