from datetime import datetime, timezone
from pathlib import Path

from app.config.settings import AppSettings, LibraryConfig
from app.db.database import Database
from app.models.movie import MovieMetadataPatch
from app.repositories.movie_repository import MovieRepository
from app.services.catalog_service import CatalogService
from app.services.cover_service import CoverService
from app.services.discovery_service import DiscoveryService
from app.services.metadata_service import MetadataService
from app.services.scanner import Scanner
from app.services.viewing_service import ViewingService


class NullProbe:
    def probe(self, path: Path):
        return None


def test_archive_lifecycle_survives_video_delete_and_db_rebuild(tmp_path: Path) -> None:
    data = tmp_path / "data"
    movies_root = tmp_path / "movies"
    cover_root = tmp_path / "covers"
    movie_folder = movies_root / "SPSD-62"
    movie_folder.mkdir(parents=True)
    cover_root.mkdir()
    video = movie_folder / "SPSD-62.mp4"
    video.write_bytes(b"fake video")
    cover = cover_root / "SPSD-62.jpg"
    cover.write_bytes(b"cover")

    settings = AppSettings(
        data_dir=data,
        cover_dir=cover_root,
        libraries=[LibraryConfig("main", "主收藏", movies_root)],
    )
    metadata = MetadataService(data / "metadata")
    database = Database(data / "library.db")
    database.initialize()
    repo = MovieRepository(database)
    covers = CoverService(cover_root, data / "cache")
    scanner = Scanner(DiscoveryService(), metadata, repo, NullProbe(), covers)
    catalog = CatalogService(repo, metadata, NullProbe(), covers, settings)
    viewing = ViewingService(repo, metadata)

    scanner.scan(settings)
    movie = catalog.list_movies(search="SPSD-62")[0]
    catalog.update_metadata(
        movie.metadata.uuid,
        MovieMetadataPatch(title="保留档案", favorite=True, tags=["测试"]),
    )
    when = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    viewing.record_launch(movie.metadata.uuid, when)

    video.unlink()
    scanner.scan(settings)
    offline = catalog.list_movies(search="SPSD-62")[0]
    assert offline.runtime.availability_status == "offline"
    assert offline.metadata.favorite is True
    assert offline.metadata.play_count == 1
    assert offline.runtime.cover_path == str(cover)

    database.path.unlink()
    rebuilt_database = Database(database.path)
    rebuilt_database.initialize()
    rebuilt_repo = MovieRepository(rebuilt_database)
    archived, errors = metadata.load_all()
    assert errors == []
    rebuilt_repo.rebuild_from_archives(archived)
    rebuilt_catalog = CatalogService(rebuilt_repo, metadata, NullProbe(), covers, settings)

    rebuilt = rebuilt_catalog.list_movies(search="SPSD-62")[0]
    assert rebuilt.metadata.title == "保留档案"
    assert rebuilt.metadata.favorite is True
    assert rebuilt.metadata.play_count == 1
    assert rebuilt.metadata.play_history[0].played_at == when
    assert rebuilt.runtime.availability_status == "offline"
    assert cover.exists()
