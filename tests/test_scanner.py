from pathlib import Path

from app.config.settings import AppSettings, LibraryConfig
from app.db.database import Database
from app.models.movie import MovieEpisodeMetadata, MovieMetadata
from app.services.media_probe import MediaInfo
from app.repositories.movie_repository import MovieRepository
from app.services.discovery_service import DiscoveryService
from app.services.metadata_service import MetadataService
from app.services.scanner import Scanner
from app.services.cover_service import CoverResult


class NullProbe:
    def probe(self, path: Path):
        return None


class NullCover:
    def resolve(self, cover_key: str, video_path: Path | None, duration: float | None):
        return CoverResult(None, "placeholder")


class RecordingCover(NullCover):
    def __init__(self) -> None:
        self.calls: list[tuple[str, Path | None, float | None]] = []

    def resolve(self, cover_key: str, video_path: Path | None, duration: float | None):
        self.calls.append((cover_key, video_path, duration))
        return super().resolve(cover_key, video_path, duration)


class SelectiveProbe:
    def probe(self, path: Path):
        if path.name == "SHOW_02.mkv":
            raise RuntimeError("probe failed")
        return MediaInfo(60.0, 1920, 1080, "h264", "aac", 0)


def build_env(tmp_path: Path):
    movies = tmp_path / "movies"
    movies.mkdir()
    data = tmp_path / "data"
    metadata = MetadataService(data / "metadata")
    db = Database(data / "library.db")
    db.initialize()
    repo = MovieRepository(db)
    settings = AppSettings(
        data_dir=data,
        cover_dir=tmp_path / "covers",
        libraries=[LibraryConfig("main", "主收藏", movies, True)],
    )
    scanner = Scanner(DiscoveryService(), metadata, repo, NullProbe(), NullCover())
    return movies, metadata, repo, settings, scanner


def create_movie(root: Path, code: str) -> Path:
    folder = root / code
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{code}.mp4"
    path.write_bytes(b"fake-video")
    return path


def test_second_scan_marks_movie_offline_but_keeps_archive(tmp_path: Path) -> None:
    movies, metadata, repo, settings, scanner = build_env(tmp_path)
    movie_file = create_movie(movies, "SPSD-62")
    first = scanner.scan(settings)
    record = repo.find_by_code("SPSD-62")[0]
    movie_file.unlink()

    second = scanner.scan(settings)
    record = repo.get(record.metadata.uuid)

    assert first.new == 1
    assert record.runtime.availability_status == "offline"
    assert metadata.load(record.metadata.uuid).code == "SPSD-62"
    assert second.offline == 1


def test_offline_archive_relinks_when_same_cover_key_returns(tmp_path: Path) -> None:
    movies, metadata, repo, settings, scanner = build_env(tmp_path)
    first_path = create_movie(movies, "ABC-1")
    scanner.scan(settings)
    uuid = repo.find_by_code("ABC-1")[0].metadata.uuid
    first_path.unlink()
    scanner.scan(settings)

    returned = create_movie(movies, "ABC-1")
    scanner.scan(settings)
    record = repo.get(uuid)

    assert Path(record.runtime.video_path) == returned
    assert record.runtime.availability_status == "available"
    assert len(repo.find_by_code("ABC-1")) == 1


def test_ambiguous_offline_cover_key_does_not_create_duplicate(tmp_path: Path) -> None:
    movies, metadata, repo, settings, scanner = build_env(tmp_path)
    first = MovieMetadata.new("DUP-1", "OLD-A")
    second = MovieMetadata.new("DUP-1", "OLD-B")
    for movie in (first, second):
        metadata.save(movie)
        repo.upsert_metadata(movie)
    create_movie(movies, "DUP-1")

    summary = scanner.scan(settings)

    assert summary.new == 0
    assert len(summary.ambiguities) == 1
    assert len(repo.list_all()) == 2


def test_three_videos_scan_as_one_work_with_folder_cover_key(tmp_path: Path) -> None:
    movies, metadata, repo, settings, _scanner = build_env(tmp_path)
    folder = movies / "SHOW"
    folder.mkdir()
    for number in (3, 1, 2):
        (folder / f"SHOW_{number:02d}.mkv").write_bytes(str(number).encode())
    covers = RecordingCover()
    scanner = Scanner(DiscoveryService(), metadata, repo, NullProbe(), covers)

    summary = scanner.scan(settings)
    records = repo.list_all()

    assert summary.new == 1
    assert summary.updated == 0
    assert len(records) == 1
    record = records[0]
    assert record.metadata.cover_key == "SHOW"
    assert record.metadata.code == "SHOW"
    assert [episode.metadata.episode_number for episode in record.episodes] == [1, 2, 3]
    assert [Path(episode.runtime.video_path).name for episode in record.episodes] == [
        "SHOW_01.mkv",
        "SHOW_02.mkv",
        "SHOW_03.mkv",
    ]
    assert len(covers.calls) == 1
    assert covers.calls[0][0] == "SHOW"
    assert covers.calls[0][1].name == "SHOW_01.mkv"
    assert len(metadata.load(record.metadata.uuid).episodes) == 3


def test_rescan_preserves_episode_ids_and_marks_only_missing_child_offline(tmp_path: Path) -> None:
    movies, metadata, repo, settings, scanner = build_env(tmp_path)
    folder = movies / "SERIES"
    folder.mkdir()
    first = folder / "SERIES_01.mkv"
    second = folder / "SERIES_02.mkv"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    scanner.scan(settings)
    original = repo.list_all()[0]
    original_ids = [episode.metadata.uuid for episode in original.episodes]

    first.rename(folder / "RENAMED_E01.mkv")
    second.unlink()
    summary = scanner.scan(settings)
    rescanned = repo.get(original.metadata.uuid)

    assert summary.new == 0
    assert summary.updated == 1
    assert summary.offline == 1
    assert len(repo.list_all()) == 1
    assert rescanned is not None
    assert [episode.metadata.uuid for episode in rescanned.episodes] == original_ids
    assert rescanned.episodes[0].metadata.source_name == "RENAMED_E01.mkv"
    assert rescanned.episodes[0].runtime.availability_status == "available"
    assert rescanned.episodes[1].runtime.availability_status == "offline"


def test_probe_failure_keeps_episode_available_and_scans_siblings(tmp_path: Path) -> None:
    movies, metadata, repo, settings, _scanner = build_env(tmp_path)
    folder = movies / "SHOW"
    folder.mkdir()
    (folder / "SHOW_01.mkv").write_bytes(b"one")
    (folder / "SHOW_02.mkv").write_bytes(b"two")
    scanner = Scanner(DiscoveryService(), metadata, repo, SelectiveProbe(), NullCover())

    summary = scanner.scan(settings)
    record = repo.list_all()[0]

    assert len(summary.errors) == 1
    assert summary.errors[0].path.name == "SHOW_02.mkv"
    assert [episode.runtime.availability_status for episode in record.episodes] == [
        "available",
        "available",
    ]
    assert record.episodes[0].runtime.duration == 60.0
    assert record.episodes[1].runtime.duration is None


def _seed_split_archive(
    metadata: MetadataService,
    repo: MovieRepository,
    video: Path,
    *,
    edited_title: str = "",
) -> MovieMetadata:
    movie = MovieMetadata.new(video.stem, video.stem)
    movie.title = edited_title
    movie.episodes = [
        MovieEpisodeMetadata.new(1, source_name=video.name)
    ]
    metadata.save(movie)
    repo.upsert_metadata(movie)
    repo.update_runtime(
        movie.uuid,
        video_path=str(video.resolve()),
        library_id="main",
        availability_status="available",
        subtitle_status=False,
    )
    return movie


def test_unedited_split_archives_are_consolidated_into_one_work(tmp_path: Path) -> None:
    movies, metadata, repo, settings, scanner = build_env(tmp_path)
    folder = movies / "SHOW"
    folder.mkdir()
    videos = [folder / f"SHOW_{number:02d}.mkv" for number in (1, 2, 3)]
    for video in videos:
        video.write_bytes(video.name.encode())
    old_movies = [_seed_split_archive(metadata, repo, video) for video in videos]

    summary = scanner.scan(settings)
    records = repo.list_all()

    assert summary.new == 0
    assert summary.updated == 1
    assert summary.ambiguities == []
    assert len(records) == 1
    assert records[0].metadata.uuid == old_movies[0].uuid
    assert records[0].metadata.cover_key == "SHOW"
    assert records[0].metadata.code == "SHOW"
    assert len(records[0].episodes) == 3
    assert sorted(path.stem for path in metadata.metadata_dir.glob("*.json")) == [
        old_movies[0].uuid
    ]


def test_edited_split_archive_blocks_automatic_consolidation(tmp_path: Path) -> None:
    movies, metadata, repo, settings, scanner = build_env(tmp_path)
    folder = movies / "SHOW"
    folder.mkdir()
    videos = [folder / f"SHOW_{number:02d}.mkv" for number in (1, 2)]
    for video in videos:
        video.write_bytes(video.name.encode())
    _seed_split_archive(metadata, repo, videos[0], edited_title="手工标题")
    _seed_split_archive(metadata, repo, videos[1])

    summary = scanner.scan(settings)

    assert summary.new == 0
    assert summary.updated == 0
    assert len(summary.ambiguities) == 1
    assert len(repo.list_all()) == 2
    assert len(list(metadata.metadata_dir.glob("*.json"))) == 2


def test_consolidation_repository_failure_restores_parent_json(
    tmp_path: Path, monkeypatch
) -> None:
    movies, metadata, repo, settings, scanner = build_env(tmp_path)
    folder = movies / "SHOW"
    folder.mkdir()
    videos = [folder / f"SHOW_{number:02d}.mkv" for number in (1, 2)]
    for video in videos:
        video.write_bytes(video.name.encode())
    seeded = [_seed_split_archive(metadata, repo, video) for video in videos]
    original_payload = metadata.path_for(seeded[0].uuid).read_bytes()

    def fail_replace(*args, **kwargs):
        raise RuntimeError("database write failed")

    monkeypatch.setattr(repo, "replace_work", fail_replace)
    summary = scanner.scan(settings)

    assert len(summary.errors) == 1
    assert metadata.path_for(seeded[0].uuid).read_bytes() == original_payload
    assert all(metadata.path_for(movie.uuid).exists() for movie in seeded)
    assert len(repo.list_all()) == 2
