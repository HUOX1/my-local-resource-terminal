from __future__ import annotations

from pathlib import Path

from app.models.scan import MovieCandidate

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".m4v", ".ts", ".webm"}
SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".vtt"}


class DiscoveryService:
    def discover(self, root: Path) -> list[MovieCandidate]:
        root = Path(root)
        if not root.is_dir():
            return []
        results: list[MovieCandidate] = []
        self._walk(root, results)
        return results

    def _walk(self, folder: Path, results: list[MovieCandidate]) -> None:
        try:
            children = list(folder.iterdir())
        except OSError:
            return
        videos = sorted(
            [p for p in children if p.is_file() and p.suffix.casefold() in VIDEO_EXTENSIONS],
            key=lambda p: p.name.casefold(),
        )
        if videos:
            # Keep every video in a folder. A folder may represent one work with
            # multiple parts (for example GIGA SPSA-01_01 / _02 / _03). The old
            # behavior selected only one "main" video and silently discarded the
            # others during scanning.
            for video in videos:
                subtitles = self._find_subtitles(children, video)
                results.append(
                    MovieCandidate(
                        folder=folder,
                        video_path=video,
                        cover_key=video.stem,
                        inferred_code=video.stem,
                        subtitle_paths=subtitles,
                    )
                )
            return
        for child in sorted((p for p in children if p.is_dir()), key=lambda p: p.name.casefold()):
            self._walk(child, results)

    @staticmethod
    def _select_main_video(folder: Path, videos: list[Path]) -> Path:
        exact = [p for p in videos if p.stem.casefold() == folder.name.casefold()]
        if exact:
            return sorted(exact, key=lambda p: p.name.casefold())[0]
        return sorted(
            videos,
            key=lambda p: (-_safe_size(p), p.name.casefold()),
        )[0]

    @staticmethod
    def _find_subtitles(children: list[Path], main: Path) -> list[Path]:
        stem = main.stem.casefold()
        subtitles = [
            p
            for p in children
            if p.is_file()
            and p.suffix.casefold() in SUBTITLE_EXTENSIONS
            and (p.stem.casefold() == stem or p.stem.casefold().startswith(stem + "."))
        ]
        return sorted(subtitles, key=lambda p: p.name.casefold())


def _safe_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return -1
