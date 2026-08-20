from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.config.settings import AppSettings
from app.models.movie import MovieMetadata, MovieRecord
from app.models.scan import MatchAmbiguity, MovieCandidate, ScanError, ScanSummary
from app.repositories.movie_repository import MovieRepository
from app.services.cover_service import CoverService
from app.services.discovery_service import DiscoveryService
from app.services.media_probe import MediaProbe, compute_subtitle_status
from app.services.metadata_service import MetadataService


class Scanner:
    def __init__(
        self,
        discovery: DiscoveryService,
        metadata: MetadataService,
        repository: MovieRepository,
        media_probe: MediaProbe,
        cover_service: CoverService,
    ) -> None:
        self.discovery = discovery
        self.metadata = metadata
        self.repository = repository
        self.media_probe = media_probe
        self.cover_service = cover_service

    def scan(self, settings: AppSettings) -> ScanSummary:
        summary = ScanSummary()
        for library in settings.libraries:
            if not library.enabled:
                continue
            root = Path(library.path)
            if not root.is_dir():
                summary.offline += self.repository.mark_library_offline(library.id)
                summary.errors.append(ScanError(root, "影片库路径不存在或当前不可用"))
                continue
            seen: list[str] = []
            for candidate in self.discovery.discover(root):
                try:
                    matched, is_new, ambiguity = self._match_or_create(candidate)
                    if ambiguity is not None:
                        summary.ambiguities.append(ambiguity)
                        continue
                    assert matched is not None
                    info = self.media_probe.probe(candidate.video_path)
                    cover = self.cover_service.resolve(
                        matched.metadata.cover_key,
                        candidate.video_path,
                        info.duration if info else None,
                    )
                    self.repository.update_runtime(
                        matched.metadata.uuid,
                        video_path=str(candidate.video_path.resolve()),
                        library_id=library.id,
                        availability_status="available",
                        subtitle_status=compute_subtitle_status(candidate.subtitle_paths, info),
                        duration=info.duration if info else None,
                        width=info.width if info else None,
                        height=info.height if info else None,
                        video_codec=info.video_codec if info else None,
                        audio_codec=info.audio_codec if info else None,
                        file_size=_safe_size(candidate.video_path),
                        cover_path=str(cover.path) if cover.path else None,
                        last_scanned_at=datetime.now(timezone.utc),
                    )
                    seen.append(matched.metadata.uuid)
                    if is_new:
                        summary.new += 1
                    else:
                        summary.updated += 1
                except Exception as exc:
                    summary.errors.append(ScanError(candidate.video_path, str(exc)))
            summary.offline += self.repository.mark_library_offline(library.id, seen)
        return summary

    def _match_or_create(
        self, candidate: MovieCandidate
    ) -> tuple[MovieRecord | None, bool, MatchAmbiguity | None]:
        normalized_path = str(candidate.video_path.resolve())
        exact = self.repository.find_by_video_path(normalized_path)
        if len(exact) == 1:
            return exact[0], False, None
        if len(exact) > 1:
            return None, False, MatchAmbiguity(candidate, [r.metadata.uuid for r in exact])

        by_cover = [
            record
            for record in self.repository.find_by_cover_key(candidate.cover_key)
            if record.runtime.availability_status == "offline"
        ]
        if len(by_cover) == 1:
            return by_cover[0], False, None
        if len(by_cover) > 1:
            return None, False, MatchAmbiguity(candidate, [r.metadata.uuid for r in by_cover])

        by_code = [
            record
            for record in self.repository.find_by_code(candidate.inferred_code)
            if record.runtime.availability_status == "offline"
        ]
        if len(by_code) == 1:
            return by_code[0], False, None
        if len(by_code) > 1:
            return None, False, MatchAmbiguity(candidate, [r.metadata.uuid for r in by_code])

        movie = MovieMetadata.new(candidate.cover_key, candidate.inferred_code)
        self.metadata.save(movie)
        self.repository.upsert_metadata(movie)
        record = self.repository.get(movie.uuid)
        if record is None:
            raise RuntimeError("new movie archive was not persisted")
        return record, True, None


def _safe_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None
