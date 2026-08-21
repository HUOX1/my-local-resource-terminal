from __future__ import annotations

from pathlib import Path

from app.models.game import GameRecord
from app.services.game_asset_service import GameAssetService


def usable_archive_media_path(value: str | Path | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_file() and path.suffix.lower() in GameAssetService.ARCHIVE_MEDIA_SUFFIXES:
        return path
    return None


def resolve_game_archive_media(record: GameRecord, screenshot_service) -> Path | None:
    """Resolve Hero media without ever falling back to the poster cover."""

    game = record.metadata
    dedicated = usable_archive_media_path(game.archive_media_path)
    if dedicated is not None:
        return dedicated

    preview = usable_archive_media_path(game.preview_gif_path)
    if preview is not None and preview.suffix.lower() == ".gif":
        return preview

    if screenshot_service is None:
        return None
    result = screenshot_service.list_images(game.screenshot_directory)
    if result.available:
        for item in result.items:
            candidate = usable_archive_media_path(item.path)
            if candidate is not None:
                return candidate
    return None
