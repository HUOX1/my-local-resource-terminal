from pathlib import Path

from app.config.settings import AppSettings, LibraryConfig
from app.db.database import Database
import pytest

from app.models.movie import (
    MovieEpisodeMetadata,
    MovieEpisodeRuntime,
    MovieMetadata,
    MovieMetadataPatch,
)
from app.repositories.movie_repository import MovieRepository
from app.services.catalog_service import CatalogService, MovieFilter
from app.services.cover_service import CoverResult
from app.services.metadata_service import MetadataService


class NullProbe:
    def probe(self, path: Path):
        return None


class NullCover:
    def resolve(self, cover_key: str, video_path: Path | None, duration: float | None):
        return CoverResult(None, "placeholder")


def build_catalog(tmp_path: Path):
    data = tmp_path / "data"
    metadata = MetadataService(data / "metadata")
    db = Database(data / "library.db")
    db.initialize()
    repo = MovieRepository(db)
    library = tmp_path / "movies"
    library.mkdir()
    settings = AppSettings(data, tmp_path / "covers", [LibraryConfig("main", "主收藏", library)])
    catalog = CatalogService(repo, metadata, NullProbe(), NullCover(), settings)
    return catalog, repo, metadata, settings


def test_search_actor_and_filter_offline(tmp_path: Path) -> None:
    catalog, repo, metadata, _ = build_catalog(tmp_path)
    movie = MovieMetadata.new("SPSD-62", "SPSD-62")
    movie.title = "示例"
    movie.actors = ["卡丽娜"]
    metadata.save(movie)
    repo.upsert_metadata(movie)

    results = catalog.list_movies(
        search="卡丽娜",
        filters=MovieFilter(availability_status="offline"),
    )

    assert [r.metadata.code for r in results] == ["SPSD-62"]


def test_update_metadata_keeps_cover_key_unless_explicitly_changed(tmp_path: Path) -> None:
    catalog, repo, metadata, _ = build_catalog(tmp_path)
    movie = MovieMetadata.new("OLD-COVER", "OLD-1")
    metadata.save(movie)
    repo.upsert_metadata(movie)

    updated = catalog.update_metadata(movie.uuid, MovieMetadataPatch(code="NEW-1", title="新标题"))

    assert updated.metadata.code == "NEW-1"
    assert updated.metadata.cover_key == "OLD-COVER"
    assert metadata.load(movie.uuid).title == "新标题"


def test_delete_archive_leaves_video_and_cover_files(tmp_path: Path) -> None:
    catalog, repo, metadata, _ = build_catalog(tmp_path)
    movie = MovieMetadata.new("ABC-1", "ABC-1")
    video = tmp_path / "movie.mp4"
    cover = tmp_path / "cover.jpg"
    video.write_bytes(b"v")
    cover.write_bytes(b"c")
    metadata.save(movie)
    repo.upsert_metadata(movie)
    repo.update_runtime(movie.uuid, video_path=str(video), library_id="main", availability_status="available", subtitle_status=False, cover_path=str(cover))

    deleted = catalog.delete_archive(movie.uuid)

    assert deleted.video_paths == (str(video),)
    assert deleted.video_path == str(video)
    assert deleted.cover_path == str(cover)
    assert video.exists() and cover.exists()
    assert not metadata.path_for(movie.uuid).exists()
    assert repo.get(movie.uuid) is None


def test_manual_relink_preserves_archive_identity(tmp_path: Path) -> None:
    catalog, repo, metadata, settings = build_catalog(tmp_path)
    movie = MovieMetadata.new("ABC-9", "ABC-9")
    movie.favorite = True
    metadata.save(movie)
    repo.upsert_metadata(movie)
    video = settings.libraries[0].path / "ABC-9" / "ABC-9.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"video")

    relinked = catalog.relink_video(movie.uuid, video)

    assert relinked.metadata.uuid == movie.uuid
    assert relinked.metadata.cover_key == "ABC-9"
    assert relinked.metadata.favorite is True
    assert relinked.runtime.availability_status == "available"
    assert Path(relinked.runtime.video_path) == video.resolve()
    assert relinked.runtime.library_id == "main"


def test_update_metadata_preserves_added_at(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    catalog, repo, metadata, _ = build_catalog(tmp_path)
    added = datetime(2024, 5, 6, 7, 8, tzinfo=timezone.utc)
    movie = MovieMetadata.new("ABC-7", "ABC-7", added_at=added)
    metadata.save(movie)
    repo.upsert_metadata(movie)

    updated = catalog.update_metadata(movie.uuid, MovieMetadataPatch(title="新标题"))

    assert updated.metadata.added_at == added
    assert metadata.load(movie.uuid).added_at == added


def _add_movie_for_batch(repo, metadata, code: str, *, tags=None, studio="", series=""):
    movie = MovieMetadata.new(code, code)
    movie.tags = list(tags or [])
    movie.studio = studio
    movie.series = series
    metadata.save(movie)
    repo.upsert_metadata(movie)
    return movie


def test_batch_update_metadata_overwrites_shared_fields(tmp_path: Path) -> None:
    catalog, repo, metadata, _ = build_catalog(tmp_path)
    first = _add_movie_for_batch(repo, metadata, "A-1", studio="旧厂商", series="旧系列")
    second = _add_movie_for_batch(repo, metadata, "A-2", studio="另一个", series="另一个系列")

    results = catalog.batch_update_metadata(
        [first.uuid, second.uuid],
        MovieMetadataPatch(studio="GIGA", series="新系列", favorite=True, watched=True),
    )

    assert [item.metadata.uuid for item in results] == [first.uuid, second.uuid]
    for movie_uuid in (first.uuid, second.uuid):
        archived = metadata.load(movie_uuid)
        indexed = repo.get(movie_uuid)
        assert archived.studio == "GIGA"
        assert archived.series == "新系列"
        assert archived.favorite is True
        assert archived.watched is True
        assert indexed is not None
        assert indexed.metadata.studio == "GIGA"
        assert indexed.metadata.series == "新系列"


def test_batch_update_tags_adds_and_removes_case_insensitively(tmp_path: Path) -> None:
    catalog, repo, metadata, _ = build_catalog(tmp_path)
    first = _add_movie_for_batch(repo, metadata, "B-1", tags=["战队", "GIGA"])
    second = _add_movie_for_batch(repo, metadata, "B-2", tags=["女英雄"])

    catalog.batch_update_tags([first.uuid, second.uuid], ["giga", "精神控制"])

    assert metadata.load(first.uuid).tags == ["战队", "GIGA", "精神控制"]
    assert metadata.load(second.uuid).tags == ["女英雄", "giga", "精神控制"]

    catalog.batch_update_tags([first.uuid, second.uuid], ["GIGA", "女英雄"], remove=True)

    assert metadata.load(first.uuid).tags == ["战队", "精神控制"]
    assert metadata.load(second.uuid).tags == ["精神控制"]


def test_batch_update_rolls_back_all_movies_when_one_update_fails(tmp_path: Path, monkeypatch) -> None:
    catalog, repo, metadata, _ = build_catalog(tmp_path)
    first = _add_movie_for_batch(repo, metadata, "C-1", studio="旧一")
    second = _add_movie_for_batch(repo, metadata, "C-2", studio="旧二")
    original_upsert = repo.upsert_metadata

    def failing_upsert(movie):
        if movie.uuid == second.uuid and movie.studio == "新厂商":
            raise RuntimeError("simulated database failure")
        return original_upsert(movie)

    monkeypatch.setattr(repo, "upsert_metadata", failing_upsert)

    try:
        catalog.batch_update_metadata(
            [first.uuid, second.uuid],
            MovieMetadataPatch(studio="新厂商"),
        )
    except RuntimeError as exc:
        assert "simulated database failure" in str(exc)
    else:
        raise AssertionError("batch update should fail")

    assert metadata.load(first.uuid).studio == "旧一"
    assert metadata.load(second.uuid).studio == "旧二"
    assert repo.get(first.uuid).metadata.studio == "旧一"
    assert repo.get(second.uuid).metadata.studio == "旧二"


def test_movie_folder_assignment_filter_and_clear_round_trip(tmp_path: Path) -> None:
    catalog, repo, metadata, _ = build_catalog(tmp_path)
    first = _add_movie_for_batch(repo, metadata, "F-1")
    second = _add_movie_for_batch(repo, metadata, "F-2")

    catalog.set_folder([first.uuid], "folder-movies-1")

    filtered = catalog.list_movies(filters=MovieFilter(folder_id="folder-movies-1"))
    assert [item.metadata.uuid for item in filtered] == [first.uuid]
    assert metadata.load(first.uuid).folder_id == "folder-movies-1"
    assert metadata.load(second.uuid).folder_id is None

    catalog.set_folder([first.uuid], None)
    assert metadata.load(first.uuid).folder_id is None
    assert catalog.list_movies(filters=MovieFilter(folder_id="folder-movies-1")) == []


def test_movie_folder_members_can_be_listed_for_delete_cleanup(tmp_path: Path) -> None:
    catalog, repo, metadata, _ = build_catalog(tmp_path)
    first = _add_movie_for_batch(repo, metadata, "FC-1")
    second = _add_movie_for_batch(repo, metadata, "FC-2")
    catalog.set_folder([first.uuid, second.uuid], "folder-delete")

    assert set(catalog.folder_member_uuids("folder-delete")) == {first.uuid, second.uuid}


def _add_episode_work(repo, metadata, *, second_available: bool = True):
    movie = MovieMetadata(
        uuid="episode-work",
        cover_key="SERIES",
        code="SERIES",
        episodes=[
            MovieEpisodeMetadata("episode-1", 1, episode_number=1, source_name="01.mkv"),
            MovieEpisodeMetadata("episode-2", 2, episode_number=2, source_name="02.mkv"),
        ],
    )
    metadata.save(movie)
    repo.replace_work(
        movie,
        {
            "episode-1": MovieEpisodeRuntime(
                video_path="/old/01.mkv",
                library_id="main",
                availability_status="available",
            ),
            "episode-2": MovieEpisodeRuntime(
                video_path="/old/02.mkv",
                library_id="main",
                availability_status="available" if second_available else "offline",
            ),
        },
        cover_path="/covers/SERIES.jpg",
    )
    return movie


def test_update_metadata_preserves_episode_manifest(tmp_path: Path) -> None:
    catalog, repo, metadata, _ = build_catalog(tmp_path)
    movie = _add_episode_work(repo, metadata)

    updated = catalog.update_metadata(movie.uuid, MovieMetadataPatch(title="新标题"))

    assert [episode.uuid for episode in updated.metadata.episodes] == ["episode-1", "episode-2"]
    assert [episode.uuid for episode in metadata.load(movie.uuid).episodes] == [
        "episode-1",
        "episode-2",
    ]
    assert [episode.runtime.video_path for episode in updated.episodes] == [
        "/old/01.mkv",
        "/old/02.mkv",
    ]


def test_episode_for_playback_requires_explicit_child_for_multi_work(tmp_path: Path) -> None:
    catalog, repo, metadata, _ = build_catalog(tmp_path)
    movie = _add_episode_work(repo, metadata, second_available=False)

    with pytest.raises(ValueError, match="选择"):
        catalog.episode_for_playback(movie.uuid)
    with pytest.raises(ValueError, match="不可用"):
        catalog.episode_for_playback(movie.uuid, "episode-2")
    with pytest.raises(KeyError):
        catalog.episode_for_playback(movie.uuid, "missing")

    selected = catalog.episode_for_playback(movie.uuid, "episode-1")
    assert selected.metadata.uuid == "episode-1"
    assert selected.runtime.video_path == "/old/01.mkv"


def test_relink_episode_updates_only_selected_child(tmp_path: Path) -> None:
    catalog, repo, metadata, settings = build_catalog(tmp_path)
    movie = _add_episode_work(repo, metadata, second_available=False)
    replacement = settings.libraries[0].path / "SERIES" / "replacement_02.mkv"
    replacement.parent.mkdir(parents=True)
    replacement.write_bytes(b"replacement")

    with pytest.raises(ValueError, match="剧集"):
        catalog.relink_video(movie.uuid, replacement)

    updated = catalog.relink_episode(movie.uuid, "episode-2", replacement)

    assert updated.episodes[0].runtime.video_path == "/old/01.mkv"
    assert Path(updated.episodes[1].runtime.video_path) == replacement.resolve()
    assert updated.episodes[1].runtime.availability_status == "available"
    assert metadata.load(movie.uuid).episodes[1].source_name == "replacement_02.mkv"


def test_delete_multi_episode_archive_reports_every_video_path(tmp_path: Path) -> None:
    catalog, repo, metadata, _ = build_catalog(tmp_path)
    movie = _add_episode_work(repo, metadata)

    deleted = catalog.delete_archive(movie.uuid)

    assert deleted.video_paths == ("/old/01.mkv", "/old/02.mkv")
    assert deleted.cover_path == "/covers/SERIES.jpg"


def test_refresh_cover_uses_first_available_episode_without_rewriting_runtimes(
    tmp_path: Path,
) -> None:
    class RecordingCover:
        def __init__(self):
            self.calls = []

        def resolve(self, cover_key, video_path, duration):
            self.calls.append((cover_key, video_path, duration))
            return CoverResult(tmp_path / "resolved.jpg", "library")

    catalog, repo, metadata, _ = build_catalog(tmp_path)
    movie = _add_episode_work(repo, metadata)
    first = tmp_path / "SERIES" / "01.mkv"
    second = tmp_path / "SERIES" / "02.mkv"
    first.parent.mkdir()
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    repo.upsert_episode_runtime(
        movie.uuid,
        movie.episodes[0],
        MovieEpisodeRuntime(video_path=str(first), availability_status="offline", duration=10),
    )
    repo.upsert_episode_runtime(
        movie.uuid,
        movie.episodes[1],
        MovieEpisodeRuntime(video_path=str(second), availability_status="available", duration=20),
    )
    covers = RecordingCover()
    catalog.cover_service = covers

    refreshed = catalog.refresh_cover(movie.uuid)

    assert covers.calls == [("SERIES", second, 20)]
    assert refreshed.runtime.cover_path == str(tmp_path / "resolved.jpg")
    assert refreshed.episodes[0].runtime.video_path == str(first)
    assert refreshed.episodes[1].runtime.video_path == str(second)
