from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from PIL import Image, ImageOps


@dataclass(frozen=True, slots=True)
class ScreenshotItem:
    path: Path
    modified_at: float


@dataclass(frozen=True, slots=True)
class ScreenshotListResult:
    available: bool
    items: list[ScreenshotItem]


class ScreenshotService:
    SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def list_images(self, directory: Path | str | None) -> ScreenshotListResult:
        if not directory:
            return ScreenshotListResult(False, [])
        root = Path(directory)
        if not root.is_dir():
            return ScreenshotListResult(False, [])
        items = [
            ScreenshotItem(path, path.stat().st_mtime)
            for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in self.SUPPORTED_SUFFIXES
        ]
        items.sort(key=lambda item: (item.modified_at, item.path.name.casefold()), reverse=True)
        return ScreenshotListResult(True, items)

    def thumbnail_for(self, game_uuid: str, image_path: Path) -> Path:
        source = Path(image_path)
        stat = source.stat()
        key_text = f"{source.resolve()}|{stat.st_mtime_ns}|{stat.st_size}"
        digest = hashlib.sha1(key_text.encode("utf-8")).hexdigest()[:20]
        target_dir = self.cache_dir / game_uuid
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{digest}.jpg"
        if target.exists():
            return target
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((320, 200), Image.Resampling.LANCZOS)
            temporary = target.with_name(f".{target.name}.tmp")
            image.save(temporary, format="JPEG", quality=85)
            temporary.replace(target)
        return target
