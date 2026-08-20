from pathlib import Path

from app.config.settings import AppSettings, LibraryConfig
from app.db.database import Database
from app.models.movie import MovieMetadata, MovieMetadataPatch
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
