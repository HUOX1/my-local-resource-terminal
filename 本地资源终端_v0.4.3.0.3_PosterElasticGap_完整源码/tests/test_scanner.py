from pathlib import Path

from app.config.settings import AppSettings, LibraryConfig
from app.db.database import Database
from app.models.movie import MovieMetadata
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
