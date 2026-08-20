from __future__ import annotations

from pathlib import Path
import shutil

from PIL import Image


class GameAssetService:
    COVER_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    ARCHIVE_MEDIA_SUFFIXES = COVER_SUFFIXES | {".gif"}

    def __init__(self, cover_dir: Path, preview_dir: Path, archive_media_dir: Path | None = None) -> None:
        self.cover_dir = Path(cover_dir)
        self.preview_dir = Path(preview_dir)
        self.archive_media_dir = Path(archive_media_dir) if archive_media_dir is not None else self.preview_dir.parent / "archive"
        self.cover_dir.mkdir(parents=True, exist_ok=True)
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        self.archive_media_dir.mkdir(parents=True, exist_ok=True)

    def import_cover(self, game_uuid: str, source: Path | None) -> Path | None:
        if source is None:
            return None
        source = Path(source)
        suffix = source.suffix.lower()
        if suffix not in self.COVER_SUFFIXES:
            raise ValueError(f"unsupported game cover type: {source.suffix}")
        self._verify_image(source)
        target = self.cover_dir / f"{game_uuid}{suffix}"
        self._replace_owned_asset(game_uuid, self.cover_dir, target, source)
        return target

    def import_preview(self, game_uuid: str, source: Path | None) -> Path | None:
        if source is None:
            return None
        source = Path(source)
        if source.suffix.lower() != ".gif":
            raise ValueError("game preview must be a GIF file")
        self._verify_image(source)
        target = self.preview_dir / f"{game_uuid}.gif"
        self._replace_owned_asset(game_uuid, self.preview_dir, target, source)
        return target

    def import_archive_media(self, game_uuid: str, source: Path | None) -> Path | None:
        if source is None:
            return None
        source = Path(source)
        suffix = source.suffix.lower()
        if suffix not in self.ARCHIVE_MEDIA_SUFFIXES:
            raise ValueError(f"unsupported archive media type: {source.suffix}")
        self._verify_image(source)
        target = self.archive_media_dir / f"{game_uuid}{suffix}"
        self._replace_owned_asset(game_uuid, self.archive_media_dir, target, source)
        return target

    def remove_game_assets(self, game_uuid: str) -> None:
        for directory in (self.cover_dir, self.preview_dir, self.archive_media_dir):
            for path in directory.glob(f"{game_uuid}.*"):
                if path.is_file():
                    path.unlink(missing_ok=True)

    def remove_cover(self, game_uuid: str) -> None:
        self._remove_owned_assets(game_uuid, self.cover_dir)

    def remove_preview(self, game_uuid: str) -> None:
        self._remove_owned_assets(game_uuid, self.preview_dir)

    def remove_archive_media(self, game_uuid: str) -> None:
        self._remove_owned_assets(game_uuid, self.archive_media_dir)

    @staticmethod
    def _verify_image(source: Path) -> None:
        if not source.is_file():
            raise FileNotFoundError(source)
        with Image.open(source) as image:
            image.verify()

    @staticmethod
    def _replace_owned_asset(game_uuid: str, directory: Path, target: Path, source: Path) -> None:
        for existing in directory.glob(f"{game_uuid}.*"):
            if existing != target and existing.is_file():
                existing.unlink(missing_ok=True)
        temporary = target.with_name(f".{target.name}.tmp")
        shutil.copy2(source, temporary)
        temporary.replace(target)

    @staticmethod
    def _remove_owned_assets(game_uuid: str, directory: Path) -> None:
        for path in directory.glob(f"{game_uuid}.*"):
            if path.is_file():
                path.unlink(missing_ok=True)
