from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from app.config.settings import AppSettings
from app.models.movie import (
    MovieEpisodeMetadata,
    MovieEpisodeRecord,
    MovieEpisodeRuntime,
    MovieMetadata,
    MovieRecord,
    MovieRuntime,
)
from app.models.scan import EpisodeCandidate, MatchAmbiguity, MovieCandidate, ScanError, ScanSummary
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
                summary.offline += self.repository.mark_library_episodes_offline(library.id)
                summary.errors.append(ScanError(root, "影片库路径不存在或当前不可用"))
                continue

            seen_episode_uuids: list[str] = []
            for candidate in self.discovery.discover(root):
                matched_records: list[MovieRecord] = []
                try:
                    matched_records, is_new, ambiguity = self._match_or_create_work(candidate)
                    if ambiguity is not None:
                        summary.ambiguities.append(ambiguity)
                        seen_episode_uuids.extend(
                            self._seen_episode_ids(candidate, matched_records)
                        )
                        continue

                    movie, runtimes, scanned_ids = self._reconcile_work(
                        candidate,
                        matched_records,
                        library.id,
                        summary,
                        is_new=is_new,
                    )
                    first_episode = movie.episodes[0]
                    first_runtime = runtimes[first_episode.uuid]
                    first_video = candidate.episodes[0].video_path
                    cover = self.cover_service.resolve(
                        movie.cover_key,
                        first_video,
                        first_runtime.duration,
                    )
                    existing_cover = matched_records[0].runtime.cover_path if matched_records else None
                    cover_path = str(cover.path) if cover.path else existing_cover
                    duplicate_ids = [
                        record.metadata.uuid
                        for record in matched_records[1:]
                    ]
                    self._persist_work(
                        movie,
                        runtimes,
                        cover_path=cover_path,
                        duplicate_movie_uuids=duplicate_ids,
                    )
                    seen_episode_uuids.extend(scanned_ids)
                    if is_new:
                        summary.new += 1
                    else:
                        summary.updated += 1
                except Exception as exc:
                    seen_episode_uuids.extend(
                        self._seen_episode_ids(candidate, matched_records)
                    )
                    summary.errors.append(ScanError(candidate.folder, str(exc)))

            summary.offline += self.repository.mark_library_episodes_offline(
                library.id,
                seen_episode_uuids,
            )
        return summary

    def _match_or_create_work(
        self,
        candidate: MovieCandidate,
    ) -> tuple[list[MovieRecord], bool, MatchAmbiguity | None]:
        path_matches = self._unique_records(
            record
            for episode in candidate.episodes
            for record in self.repository.find_by_episode_video_path(
                str(episode.video_path.resolve())
            )
        )
        if path_matches:
            return self._resolve_records(candidate, path_matches)

        identity_matches: list[MovieRecord] = []
        for episode in candidate.episodes:
            matches = self.repository.find_by_episode_source_name(episode.source_name)
            matches.extend(
                self.repository.find_by_episode_identity(
                    episode.season_number,
                    episode.episode_number,
                )
            )
            identity_matches.extend(
                record
                for record in matches
                if self._record_belongs_to_candidate(record, candidate)
            )
        identity_matches = self._unique_records(identity_matches)
        if identity_matches:
            return self._resolve_records(candidate, identity_matches)

        folder_matches = self._unique_records(
            [
                *self.repository.find_by_cover_key(candidate.cover_key),
                *self.repository.find_by_code(candidate.inferred_code),
            ]
        )
        folder_matches = [
            record
            for record in folder_matches
            if record.runtime.availability_status == "offline"
        ]
        if folder_matches:
            return self._resolve_records(candidate, folder_matches)

        legacy_part_matches: list[MovieRecord] = []
        for episode in candidate.episodes:
            stem = episode.video_path.stem
            legacy_part_matches.extend(self.repository.find_by_cover_key(stem))
            legacy_part_matches.extend(self.repository.find_by_code(stem))
        legacy_part_matches = self._unique_records(legacy_part_matches)
        if legacy_part_matches:
            return self._resolve_records(candidate, legacy_part_matches)

        movie = MovieMetadata.new(candidate.cover_key, candidate.inferred_code)
        return [MovieRecord(movie, MovieRuntime(), [])], True, None

    def _resolve_records(
        self,
        candidate: MovieCandidate,
        records: list[MovieRecord],
    ) -> tuple[list[MovieRecord], bool, MatchAmbiguity | None]:
        records = self._unique_records(records)
        if len(records) == 1:
            return records, False, None
        if self._can_consolidate(records, candidate):
            ordered = sorted(
                records,
                key=lambda record: (
                    record.metadata.cover_key.casefold()
                    != candidate.cover_key.casefold(),
                    record.metadata.added_at,
                    record.metadata.uuid,
                ),
            )
            return ordered, False, None
        ambiguity = MatchAmbiguity(
            candidate,
            sorted(record.metadata.uuid for record in records),
        )
        return records, False, ambiguity

    def _can_consolidate(
        self,
        records: list[MovieRecord],
        candidate: MovieCandidate,
    ) -> bool:
        if len(records) < 2 or len(candidate.episodes) < 2:
            return False
        if not all(self._is_unedited_generated(record.metadata) for record in records):
            return False

        candidate_paths = {
            _normalized_path(episode.video_path) for episode in candidate.episodes
        }
        candidate_stems = {
            episode.video_path.stem.casefold() for episode in candidate.episodes
        }
        for record in records:
            keyed_to_part = (
                record.metadata.cover_key.casefold() in candidate_stems
                or record.metadata.code.casefold() in candidate_stems
            )
            path_tied = any(
                episode.runtime.video_path
                and _normalized_path(episode.runtime.video_path) in candidate_paths
                for episode in record.episodes
            )
            source_tied = any(
                Path(episode.metadata.source_name).stem.casefold() in candidate_stems
                for episode in record.episodes
                if episode.metadata.source_name
            )
            if not (keyed_to_part or path_tied or source_tied):
                return False
        return True

    @staticmethod
    def _is_unedited_generated(movie: MovieMetadata) -> bool:
        return not any(
            (
                movie.title,
                movie.actors,
                movie.series,
                movie.studio,
                movie.release_date,
                movie.tags,
                movie.rating,
                movie.watched,
                movie.play_count,
                movie.total_play_seconds,
                movie.favorite,
                movie.notes,
                movie.folder_id,
                movie.first_watched_at,
                movie.last_watched_at,
                movie.play_history,
            )
        )

    def _reconcile_work(
        self,
        candidate: MovieCandidate,
        records: list[MovieRecord],
        library_id: str,
        summary: ScanSummary,
        *,
        is_new: bool,
    ) -> tuple[MovieMetadata, dict[str, MovieEpisodeRuntime], list[str]]:
        parent = records[0]
        existing = [
            (record, episode)
            for record in records
            for episode in record.episodes
        ]
        used_episode_uuids: set[str] = set()
        episode_metadata: list[MovieEpisodeMetadata] = []
        runtimes: dict[str, MovieEpisodeRuntime] = {}
        scanned_ids: list[str] = []

        for discovered in candidate.episodes:
            matched = self._match_episode(
                discovered,
                existing,
                used_episode_uuids,
            )
            episode_uuid = (
                matched.metadata.uuid
                if matched is not None
                else MovieEpisodeMetadata.new(1).uuid
            )
            used_episode_uuids.add(episode_uuid)
            metadata = MovieEpisodeMetadata(
                uuid=episode_uuid,
                display_order=discovered.display_order,
                episode_number=discovered.episode_number,
                season_number=discovered.season_number,
                source_name=discovered.source_name,
            )
            info = None
            try:
                info = self.media_probe.probe(discovered.video_path)
            except Exception as exc:
                summary.errors.append(ScanError(discovered.video_path, str(exc)))
            runtime = MovieEpisodeRuntime(
                video_path=str(discovered.video_path.resolve()),
                library_id=library_id,
                availability_status="available",
                subtitle_status=compute_subtitle_status(
                    discovered.subtitle_paths,
                    info,
                ),
                duration=info.duration if info else None,
                width=info.width if info else None,
                height=info.height if info else None,
                video_codec=info.video_codec if info else None,
                audio_codec=info.audio_codec if info else None,
                file_size=_safe_size(discovered.video_path),
                last_scanned_at=datetime.now(timezone.utc),
            )
            episode_metadata.append(metadata)
            runtimes[episode_uuid] = runtime
            scanned_ids.append(episode_uuid)

        next_order = len(episode_metadata) + 1
        for _record, episode in existing:
            if episode.metadata.uuid in used_episode_uuids:
                continue
            preserved = MovieEpisodeMetadata(
                uuid=episode.metadata.uuid,
                display_order=next_order,
                episode_number=episode.metadata.episode_number,
                season_number=episode.metadata.season_number,
                source_name=episode.metadata.source_name,
            )
            episode_metadata.append(preserved)
            runtimes[preserved.uuid] = episode.runtime
            next_order += 1

        generated_part_keys = {
            episode.video_path.stem.casefold() for episode in candidate.episodes
        }
        normalize_work_key = (
            is_new
            or len(records) > 1
            or (
                self._is_unedited_generated(parent.metadata)
                and (
                    parent.metadata.cover_key.casefold() in generated_part_keys
                    or parent.metadata.code.casefold() in generated_part_keys
                )
            )
        )
        movie = replace(
            parent.metadata,
            cover_key=(candidate.cover_key if normalize_work_key else parent.metadata.cover_key),
            code=(candidate.inferred_code if normalize_work_key else parent.metadata.code),
            episodes=episode_metadata,
        )
        return movie, runtimes, scanned_ids

    @staticmethod
    def _match_episode(
        discovered: EpisodeCandidate,
        existing: list[tuple[MovieRecord, MovieEpisodeRecord]],
        used_episode_uuids: set[str],
    ) -> MovieEpisodeRecord | None:
        available = [
            (record, episode)
            for record, episode in existing
            if episode.metadata.uuid not in used_episode_uuids
        ]
        target_path = _normalized_path(discovered.video_path)
        matched = _unique_episode(
            episode
            for _record, episode in available
            if episode.runtime.video_path
            and _normalized_path(episode.runtime.video_path) == target_path
        )
        if matched is not None:
            return matched

        matched = _unique_episode(
            episode
            for _record, episode in available
            if episode.metadata.source_name.casefold()
            == discovered.source_name.casefold()
        )
        if matched is not None:
            return matched

        if discovered.episode_number is not None:
            matched = _unique_episode(
                episode
                for _record, episode in available
                if episode.metadata.episode_number == discovered.episode_number
                and episode.metadata.season_number == discovered.season_number
            )
            if matched is not None:
                return matched

        stem = discovered.video_path.stem.casefold()
        return _unique_episode(
            episode
            for record, episode in available
            if record.metadata.cover_key.casefold() == stem
            or record.metadata.code.casefold() == stem
        )

    def _persist_work(
        self,
        movie: MovieMetadata,
        runtimes: dict[str, MovieEpisodeRuntime],
        *,
        cover_path: str | None,
        duplicate_movie_uuids: list[str],
    ) -> None:
        parent_path = self.metadata.path_for(movie.uuid)
        original = parent_path.read_bytes() if parent_path.exists() else None
        self.metadata.save(movie)
        try:
            self.repository.replace_work(
                movie,
                runtimes,
                cover_path=cover_path,
                duplicate_movie_uuids=duplicate_movie_uuids,
            )
        except Exception:
            if original is None:
                self.metadata.delete(movie.uuid)
            else:
                temporary = parent_path.with_name(f"{parent_path.name}.rollback.tmp")
                temporary.write_bytes(original)
                temporary.replace(parent_path)
            raise
        for duplicate_uuid in duplicate_movie_uuids:
            self.metadata.delete(duplicate_uuid)

    @staticmethod
    def _unique_records(records) -> list[MovieRecord]:
        unique: dict[str, MovieRecord] = {}
        for record in records:
            unique.setdefault(record.metadata.uuid, record)
        return list(unique.values())

    @staticmethod
    def _record_belongs_to_candidate(
        record: MovieRecord,
        candidate: MovieCandidate,
    ) -> bool:
        work_key = candidate.cover_key.casefold()
        if (
            record.metadata.cover_key.casefold() == work_key
            or record.metadata.code.casefold() == work_key
        ):
            return True
        candidate_folder = _normalized_path(candidate.folder)
        return any(
            episode.runtime.video_path
            and _normalized_path(Path(episode.runtime.video_path).parent)
            == candidate_folder
            for episode in record.episodes
        )

    @staticmethod
    def _seen_episode_ids(
        candidate: MovieCandidate,
        records: list[MovieRecord],
    ) -> list[str]:
        paths = {_normalized_path(episode.video_path) for episode in candidate.episodes}
        return [
            episode.metadata.uuid
            for record in records
            for episode in record.episodes
            if episode.runtime.video_path
            and _normalized_path(episode.runtime.video_path) in paths
        ]


def _unique_episode(episodes) -> MovieEpisodeRecord | None:
    unique: dict[str, MovieEpisodeRecord] = {}
    for episode in episodes:
        unique.setdefault(episode.metadata.uuid, episode)
    return next(iter(unique.values())) if len(unique) == 1 else None


def _normalized_path(path: Path | str) -> str:
    return str(Path(path).resolve()).casefold()


def _safe_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None
