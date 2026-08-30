from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import logging
from pathlib import Path
import subprocess
from typing import Callable

from PIL import Image, ImageSequence

from terminal_core.repository import LibraryRepository


logger = logging.getLogger("local_resource_terminal.media_assets")


@dataclass(slots=True)
class PreviewManifest:
    cover: Path | None = None
    background: Path | None = None
    screenshots: list[Path] = field(default_factory=list)
    gif_frames: list[Path] = field(default_factory=list)
    gif_durations_ms: list[int] = field(default_factory=list)
    video_ogv: Path | None = None
    preview_audio: Path | None = None
    logo: Path | None = None


class MediaAssetService:
    def __init__(
        self,
        repository: LibraryRepository,
        cache_root: Path,
        *,
        ffmpeg_path: str = "ffmpeg",
        runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    ) -> None:
        self.repository = repository
        self.cache_root = Path(cache_root)
        self.ffmpeg_path = ffmpeg_path
        self._runner = runner
        self.cache_root.mkdir(parents=True, exist_ok=True)

    def resolve_preview(self, item_id: str) -> PreviewManifest:
        game = self.repository.get_game(item_id)
        if game is None:
            raise KeyError(item_id)
        discovered = self._discover(game.executable_path.parent)
        indexed = self.repository.list_media_assets(item_id)
        by_kind: dict[str, list[tuple[int, int, Path]]] = {}
        source_rank = {"manual": 0, "auto": 1, "generated": 2}
        for asset in indexed:
            by_kind.setdefault(asset.kind, []).append(
                (source_rank[asset.source], asset.priority, asset.path)
            )
        for kind, paths in discovered.items():
            for index, path in enumerate(paths):
                by_kind.setdefault(kind, []).append((1, index, path))

        def best(kind: str) -> Path | None:
            options = by_kind.get(kind, [])
            if not options:
                return None
            return min(options, key=lambda item: (item[0], item[1], str(item[2])))[2]

        manifest = PreviewManifest(
            cover=best("cover"),
            background=best("background"),
            screenshots=[
                path
                for _, _, path in sorted(
                    by_kind.get("screenshot", []),
                    key=lambda item: (item[0], item[1], str(item[2])),
                )
            ],
            preview_audio=best("preview_audio"),
            logo=best("logo"),
        )
        gif_path = best("preview_gif")
        if gif_path is not None:
            manifest.gif_frames, manifest.gif_durations_ms = self._expand_gif(gif_path)
        video_path = best("preview_video")
        if video_path is not None:
            manifest.video_ogv = self._ensure_ogv(video_path)
        return manifest

    def _discover(self, directory: Path) -> dict[str, list[Path]]:
        result: dict[str, list[Path]] = {}
        if not directory.is_dir():
            return result
        for path in sorted(directory.iterdir()):
            if not path.is_file():
                continue
            stem = path.stem.casefold()
            suffix = path.suffix.casefold()
            if stem == "preview":
                if suffix == ".gif":
                    result.setdefault("preview_gif", []).append(path.resolve())
                elif suffix in {".ogv", ".mp4", ".mkv", ".mov", ".webm", ".avi"}:
                    result.setdefault("preview_video", []).append(path.resolve())
                elif suffix in {".mp3", ".ogg", ".wav", ".flac"}:
                    result.setdefault("preview_audio", []).append(path.resolve())
            elif stem == "background" and suffix in {".png", ".jpg", ".jpeg", ".webp"}:
                result.setdefault("background", []).append(path.resolve())
            elif stem == "logo" and suffix in {".png", ".jpg", ".jpeg", ".webp"}:
                result.setdefault("logo", []).append(path.resolve())
            elif stem == "cover" and suffix in {".png", ".jpg", ".jpeg", ".webp"}:
                result.setdefault("cover", []).append(path.resolve())
        screenshots = directory / "screenshots"
        if screenshots.is_dir():
            for path in sorted(screenshots.iterdir()):
                if path.is_file() and path.suffix.casefold() in {".png", ".jpg", ".jpeg", ".webp"}:
                    result.setdefault("screenshot", []).append(path.resolve())
        return result

    def _cache_key(self, source: Path) -> str:
        stat = source.stat()
        value = f"{source.resolve()}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")
        return hashlib.sha256(value).hexdigest()[:24]

    def _expand_gif(self, source: Path) -> tuple[list[Path], list[int]]:
        key = self._cache_key(source)
        target_dir = self.cache_root / "gif" / key
        manifest_path = target_dir / "manifest.json"
        if manifest_path.is_file():
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            frames = [target_dir / name for name in payload["frames"]]
            if all(path.is_file() for path in frames):
                return frames, [int(v) for v in payload["durations_ms"]]
        target_dir.mkdir(parents=True, exist_ok=True)
        frames: list[Path] = []
        durations: list[int] = []
        with Image.open(source) as image:
            for index, frame in enumerate(ImageSequence.Iterator(image)):
                output = target_dir / f"{index:04d}.png"
                frame.convert("RGBA").save(output, format="PNG")
                frames.append(output)
                durations.append(max(20, int(frame.info.get("duration", 100))))
        manifest_path.write_text(
            json.dumps(
                {"frames": [path.name for path in frames], "durations_ms": durations},
                indent=2,
            ),
            encoding="utf-8",
        )
        return frames, durations

    def _ensure_ogv(self, source: Path) -> Path | None:
        if source.suffix.casefold() == ".ogv":
            return source.resolve()
        key = self._cache_key(source)
        output = self.cache_root / "video" / f"{key}.ogv"
        if output.is_file() and output.stat().st_size > 0:
            return output
        output.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self.ffmpeg_path,
            "-y",
            "-i",
            str(source),
            "-vf",
            "scale='min(1920,iw)':-2,fps=30",
            "-c:v",
            "libtheora",
            "-q:v",
            "7",
            "-c:a",
            "libvorbis",
            "-q:a",
            "4",
            str(output),
        ]
        try:
            result = self._runner(
                command,
                capture_output=True,
                text=True,
                check=False,
                creationflags=0,
            )
        except OSError as exc:
            logger.warning("preview transcode unavailable for %s: %s", source, exc)
            return None
        if int(result.returncode) != 0 or not output.is_file():
            logger.warning("preview transcode failed for %s: %s", source, getattr(result, "stderr", ""))
            output.unlink(missing_ok=True)
            return None
        return output
