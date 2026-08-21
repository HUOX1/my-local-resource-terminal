from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil


@dataclass(frozen=True, slots=True)
class DataLayout:
    root: Path
    database_path: Path
    metadata_dir: Path
    movie_metadata_dir: Path
    game_metadata_dir: Path
    game_assets_dir: Path
    game_cover_dir: Path
    game_preview_dir: Path
    game_archive_media_dir: Path
    collections_dir: Path
    collection_folders_path: Path
    state_dir: Path
    active_game_session_path: Path
    cache_dir: Path
    thumbnail_cache_dir: Path
    generated_cover_dir: Path
    movie_cache_dir: Path
    game_cache_dir: Path
    game_screenshot_cache_dir: Path
    logs_dir: Path


@dataclass(frozen=True, slots=True)
class MovieMetadataMigrationError:
    path: Path
    message: str


@dataclass(frozen=True, slots=True)
class MovieMetadataMigrationSummary:
    migrated: int
    errors: tuple[MovieMetadataMigrationError, ...]


def ensure_data_layout(data_dir: Path) -> DataLayout:
    root = Path(data_dir)
    metadata_dir = root / "metadata"
    movie_metadata_dir = metadata_dir / "movies"
    game_metadata_dir = metadata_dir / "games"
    game_assets_dir = root / "game_assets"
    game_cover_dir = game_assets_dir / "covers"
    game_preview_dir = game_assets_dir / "previews"
    game_archive_media_dir = game_assets_dir / "archive"
    collections_dir = root / "collections"
    state_dir = root / "state"
    cache_dir = root / "cache"
    thumbnail_cache_dir = cache_dir / "thumbnails"
    generated_cover_dir = cache_dir / "generated_covers"
    movie_cache_dir = cache_dir / "movies"
    game_cache_dir = cache_dir / "games"
    game_screenshot_cache_dir = game_cache_dir / "screenshots"
    logs_dir = root / "logs"
    for directory in (
        root,
        metadata_dir,
        movie_metadata_dir,
        game_metadata_dir,
        game_assets_dir,
        game_cover_dir,
        game_preview_dir,
        game_archive_media_dir,
        collections_dir,
        state_dir,
        cache_dir,
        thumbnail_cache_dir,
        generated_cover_dir,
        movie_cache_dir,
        game_cache_dir,
        game_screenshot_cache_dir,
        logs_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return DataLayout(
        root=root,
        database_path=root / "library.db",
        metadata_dir=metadata_dir,
        movie_metadata_dir=movie_metadata_dir,
        game_metadata_dir=game_metadata_dir,
        game_assets_dir=game_assets_dir,
        game_cover_dir=game_cover_dir,
        game_preview_dir=game_preview_dir,
        game_archive_media_dir=game_archive_media_dir,
        collections_dir=collections_dir,
        collection_folders_path=collections_dir / "folders.json",
        state_dir=state_dir,
        active_game_session_path=state_dir / "active_game_session.json",
        cache_dir=cache_dir,
        thumbnail_cache_dir=thumbnail_cache_dir,
        generated_cover_dir=generated_cover_dir,
        movie_cache_dir=movie_cache_dir,
        game_cache_dir=game_cache_dir,
        game_screenshot_cache_dir=game_screenshot_cache_dir,
        logs_dir=logs_dir,
    )


class MovieMetadataMigrator:
    """Move v0.2.x root-level movie JSON archives into metadata/movies safely."""

    def migrate(self, layout: DataLayout) -> MovieMetadataMigrationSummary:
        migrated = 0
        errors: list[MovieMetadataMigrationError] = []
        for source in sorted(layout.metadata_dir.glob("*.json")):
            if not source.is_file():
                continue
            target = layout.movie_metadata_dir / source.name
            try:
                payload = json.loads(source.read_text(encoding="utf-8"))
                self._validate_movie_payload(payload)
                if target.exists():
                    target_payload = json.loads(target.read_text(encoding="utf-8"))
                    self._validate_movie_payload(target_payload)
                    if target_payload != payload:
                        raise ValueError(f"destination already exists with different content: {target}")
                    source.unlink()
                    continue
                temporary = target.with_name(f".{target.name}.migrate.tmp")
                shutil.copy2(source, temporary)
                copied_payload = json.loads(temporary.read_text(encoding="utf-8"))
                self._validate_movie_payload(copied_payload)
                if copied_payload != payload:
                    raise ValueError("copied metadata content differs from source")
                temporary.replace(target)
                source.unlink()
                migrated += 1
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                errors.append(MovieMetadataMigrationError(source, str(exc)))
                temporary = target.with_name(f".{target.name}.migrate.tmp")
                temporary.unlink(missing_ok=True)
        return MovieMetadataMigrationSummary(migrated, tuple(errors))

    @staticmethod
    def _validate_movie_payload(payload: object) -> None:
        if not isinstance(payload, dict):
            raise ValueError("metadata root must be an object")
        version = int(payload.get("schema_version", 1))
        if version not in {1, 2}:
            raise ValueError(f"unsupported movie metadata schema_version: {version}")
        if not str(payload.get("uuid", "")).strip():
            raise ValueError("movie metadata is missing uuid")
        if "cover_key" not in payload:
            raise ValueError("movie metadata is missing cover_key")


class DataDirectoryMigrator:
    def migrate(self, old: DataLayout, new_root: Path) -> DataLayout:
        destination = Path(new_root)
        if destination.resolve() == old.root.resolve():
            return old
        if destination.exists():
            existing_db = destination / "library.db"
            if existing_db.exists():
                raise FileExistsError(f"destination already contains library.db: {existing_db}")
        new = ensure_data_layout(destination)
        if old.database_path.exists():
            shutil.copy2(old.database_path, new.database_path)
        self._copy_tree_contents(old.metadata_dir, new.metadata_dir)
        self._copy_tree_contents(old.game_assets_dir, new.game_assets_dir)
        self._copy_tree_contents(old.collections_dir, new.collections_dir)
        if old.active_game_session_path.exists():
            shutil.copy2(old.active_game_session_path, new.active_game_session_path)
        return new

    @staticmethod
    def _copy_tree_contents(source_dir: Path, destination_dir: Path) -> None:
        if not source_dir.exists():
            return
        for source in source_dir.rglob("*"):
            if not source.is_file():
                continue
            relative = source.relative_to(source_dir)
            target = destination_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
