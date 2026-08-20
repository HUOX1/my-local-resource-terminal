from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.services.subprocess_utils import hidden_console_kwargs

SUPPORTED_COVER_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


@dataclass(slots=True, frozen=True)
class CoverResult:
    path: Path | None
    source: Literal["library", "generated", "placeholder"]


class CoverService:
    def __init__(self, cover_dir: Path, cache_dir: Path, ffmpeg_path: str = "ffmpeg") -> None:
        self.cover_dir = Path(cover_dir)
        self.cache_dir = Path(cache_dir)
        self.generated_dir = self.cache_dir / "generated_covers"
        self.thumbnail_dir = self.cache_dir / "thumbnails"
        self.ffmpeg_path = ffmpeg_path
        self.cover_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnail_dir.mkdir(parents=True, exist_ok=True)
        self._index: dict[tuple[str, str], Path] | None = None


    def reconfigure(self, cover_dir: Path, cache_dir: Path, ffmpeg_path: str) -> None:
        self.cover_dir = Path(cover_dir)
        self.cache_dir = Path(cache_dir)
        self.generated_dir = self.cache_dir / "generated_covers"
        self.thumbnail_dir = self.cache_dir / "thumbnails"
        self.ffmpeg_path = ffmpeg_path
        self.cover_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnail_dir.mkdir(parents=True, exist_ok=True)
        self.invalidate_index()

    def invalidate_index(self) -> None:
        self._index = None

    def resolve(
        self,
        cover_key: str,
        video_path: Path | None,
        duration: float | None,
    ) -> CoverResult:
        library = self._lookup(cover_key)
        if library:
            return CoverResult(library, "library")
        if video_path and Path(video_path).is_file():
            generated = self._generate_frame(cover_key, Path(video_path), duration)
            if generated:
                return CoverResult(generated, "generated")
        return CoverResult(None, "placeholder")

    def replace(self, cover_key: str, source_image: Path) -> Path:
        source = Path(source_image)
        if not source.is_file():
            raise FileNotFoundError(source)
        extension = source.suffix.casefold()
        if extension not in SUPPORTED_COVER_EXTENSIONS:
            return self._convert_with_qimage(cover_key, source)
        target = self.cover_dir / f"{cover_key}{extension}"
        temporary = target.with_name(f".{target.name}.tmp")
        shutil.copy2(source, temporary)
        temporary.replace(target)
        for stale_ext in SUPPORTED_COVER_EXTENSIONS:
            stale = self.cover_dir / f"{cover_key}{stale_ext}"
            if stale != target:
                stale.unlink(missing_ok=True)
        self.invalidate_index()
        return target

    def thumbnail(self, source: Path, width: int = 240, height: int = 340) -> Path:
        source = Path(source)
        key = hashlib.sha1(f"{source.resolve()}|{source.stat().st_mtime_ns}|{width}|{height}".encode()).hexdigest()
        target = self.thumbnail_dir / f"{key}.jpg"
        if target.exists():
            return target
        try:
            from PySide6.QtCore import Qt
            from PySide6.QtGui import QImage
        except ImportError as exc:
            raise RuntimeError("PySide6 is required to generate thumbnails") from exc
        image = QImage(str(source))
        if image.isNull():
            raise ValueError(f"invalid cover image: {source}")
        scaled = image.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        if not scaled.save(str(target), "JPG", 88):
            raise OSError(f"failed to save thumbnail: {target}")
        return target

    def _lookup(self, cover_key: str) -> Path | None:
        if self._index is None:
            self._index = {}
            try:
                paths = list(self.cover_dir.iterdir())
            except OSError:
                paths = []
            for path in paths:
                if path.is_file() and path.suffix.casefold() in SUPPORTED_COVER_EXTENSIONS:
                    self._index[(path.stem.casefold(), path.suffix.casefold())] = path
        key = cover_key.casefold()
        for extension in SUPPORTED_COVER_EXTENSIONS:
            match = self._index.get((key, extension))
            if match:
                return match
        return None

    def _generate_frame(self, cover_key: str, video_path: Path, duration: float | None) -> Path | None:
        digest = hashlib.sha1(str(video_path.resolve()).encode()).hexdigest()[:16]
        target = self.generated_dir / f"{cover_key}-{digest}.jpg"
        if target.exists():
            return target
        seek = max(1.0, duration * 0.10) if duration else 10.0
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss",
            f"{seek:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(target),
        ]
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                check=False,
                **hidden_console_kwargs(),
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if completed.returncode != 0 or not target.exists():
            target.unlink(missing_ok=True)
            return None
        return target

    def _convert_with_qimage(self, cover_key: str, source: Path) -> Path:
        try:
            from PySide6.QtGui import QImage
        except ImportError as exc:
            raise ValueError(f"unsupported image format without PySide6: {source.suffix}") from exc
        image = QImage(str(source))
        if image.isNull():
            raise ValueError(f"invalid image: {source}")
        target = self.cover_dir / f"{cover_key}.jpg"
        temporary = target.with_name(f".{target.stem}.tmp.jpg")
        if not image.save(str(temporary), "JPG", 92):
            raise OSError(f"failed to convert image: {source}")
        temporary.replace(target)
        for stale_ext in SUPPORTED_COVER_EXTENSIONS:
            stale = self.cover_dir / f"{cover_key}{stale_ext}"
            if stale != target:
                stale.unlink(missing_ok=True)
        self.invalidate_index()
        return target
