from __future__ import annotations

from collections import Counter
from pathlib import Path

from app.models.scan import EpisodeCandidate, MovieCandidate
from app.services.episode_parser import EpisodeIdentity, natural_name_key, parse_episode_identity

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
        videos = [
            path
            for path in children
            if path.is_file() and path.suffix.casefold() in VIDEO_EXTENSIONS
        ]
        if videos:
            ordered = self._order_videos(videos)
            identity_counts = Counter(
                self._identity_key(identity)
                for _, identity in ordered
                if identity.reliable
            )
            episodes: list[EpisodeCandidate] = []
            for display_order, (video, identity) in enumerate(ordered, start=1):
                identity_key = self._identity_key(identity)
                conflicted = identity.reliable and identity_counts[identity_key] > 1
                episodes.append(
                    EpisodeCandidate(
                        video_path=video,
                        source_name=video.name,
                        display_order=display_order,
                        episode_number=None if conflicted else identity.episode_number,
                        season_number=None if conflicted else identity.season_number,
                        subtitle_paths=tuple(self._find_subtitles(children, video)),
                    )
                )
            work_key = folder.name.strip()
            results.append(
                MovieCandidate(
                    folder=folder,
                    cover_key=work_key,
                    inferred_code=work_key,
                    episodes=tuple(episodes),
                )
            )
            return
        for child in sorted((p for p in children if p.is_dir()), key=lambda p: p.name.casefold()):
            self._walk(child, results)

    @staticmethod
    def _order_videos(videos: list[Path]) -> list[tuple[Path, EpisodeIdentity]]:
        identified = [(video, parse_episode_identity(video.stem)) for video in videos]
        keys = [
            DiscoveryService._identity_key(identity)
            for _, identity in identified
            if identity.reliable
        ]
        all_unique_and_identified = (
            len(keys) == len(identified)
            and len(set(keys)) == len(keys)
        )
        if all_unique_and_identified:
            return sorted(
                identified,
                key=lambda item: (
                    item[1].season_number or 0,
                    item[1].episode_number or 0,
                    natural_name_key(item[0].name),
                ),
            )
        return sorted(identified, key=lambda item: natural_name_key(item[0].name))

    @staticmethod
    def _identity_key(identity: EpisodeIdentity) -> tuple[int, int]:
        return identity.season_number or 0, identity.episode_number or 0

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
