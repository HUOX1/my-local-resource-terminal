from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from app.config.settings import AppSettings
from app.models.movie import (
    MovieEpisodeMetadata,
    MovieEpisodeRecord,
    MovieEpisodeRuntime,
    MovieMetadata,
    MovieMetadataPatch,
    MovieRecord,
    legacy_episode_uuid,
)
from app.repositories.movie_repository import MovieRepository
from app.services.cover_service import CoverService
from app.services.discovery_service import VIDEO_EXTENSIONS
from app.services.media_probe import MediaProbe, compute_subtitle_status
from app.services.metadata_service import MetadataService


@dataclass(slots=True, frozen=True)
class MovieFilter:
    library_id: str | None = None
    favorite: bool | None = None
    watched: bool | None = None
    subtitle_status: bool | None = None
    availability_status: str | None = None
    tag: str | None = None
    folder_id: str | None = None


@dataclass(slots=True, frozen=True)
class DeletedArchive:
    video_paths: tuple[str, ...]
    cover_path: str | None

    @property
    def video_path(self) -> str | None:
        return self.video_paths[0] if len(self.video_paths) == 1 else None


class CatalogService:
    def __init__(
        self,
        repository: MovieRepository,
        metadata_service: MetadataService,
        media_probe: MediaProbe,
        cover_service: CoverService,
        settings: AppSettings,
    ) -> None:
        self.repository = repository
        self.metadata_service = metadata_service
        self.media_probe = media_probe
        self.cover_service = cover_service
        self.settings = settings

    def list_movies(
        self,
        search: str = "",
        filters: MovieFilter | None = None,
        sort: str = "code",
        descending: bool = False,
    ) -> list[MovieRecord]:
        filters = filters or MovieFilter()
        return self.repository.search(
            search,
            library_id=filters.library_id,
            favorite=filters.favorite,
            watched=filters.watched,
            subtitle_status=filters.subtitle_status,
            availability_status=filters.availability_status,
            tag=filters.tag,
            folder_id=filters.folder_id,
            sort=sort,
            descending=descending,
        )

    def get(self, uuid: str) -> MovieRecord | None:
        return self.repository.get(uuid)

    def update_metadata(self, uuid: str, patch: MovieMetadataPatch) -> MovieRecord:
        movie = self.metadata_service.load(uuid)
        changes = {
            field: value
            for field in (
                "cover_key",
                "code",
                "title",
                "actors",
                "series",
                "studio",
                "release_date",
                "tags",
                "rating",
                "watched",
                "favorite",
                "notes",
            )
            if (value := getattr(patch, field)) is not None
        }
        updated = replace(movie, **changes)
        self.metadata_service.save(updated)
        self.repository.upsert_metadata(updated)
        record = self.repository.get(uuid)
        if record is None:
            raise RuntimeError("movie disappeared after metadata update")
        return record

    def batch_update_metadata(
        self,
        uuids: list[str],
        patch: MovieMetadataPatch,
    ) -> list[MovieRecord]:
        movie_ids = list(dict.fromkeys(str(item) for item in uuids if str(item)))
        originals = {movie_uuid: self.metadata_service.load(movie_uuid) for movie_uuid in movie_ids}
        try:
            return [self.update_metadata(movie_uuid, patch) for movie_uuid in movie_ids]
        except Exception as exc:
            rollback_errors: list[str] = []
            for original in originals.values():
                try:
                    self.metadata_service.save(original)
                    self.repository.upsert_metadata(original)
                except Exception as rollback_exc:
                    rollback_errors.append(f"{original.uuid}: {rollback_exc}")
            if rollback_errors:
                raise RuntimeError(
                    f"batch update failed: {exc}; rollback also failed: {'; '.join(rollback_errors)}"
                ) from exc
            raise

    def batch_update_tags(
        self,
        uuids: list[str],
        tags: list[str],
        *,
        remove: bool = False,
    ) -> list[MovieRecord]:
        movie_ids = list(dict.fromkeys(str(item) for item in uuids if str(item)))
        normalized: list[str] = []
        seen: set[str] = set()
        for value in tags:
            item = str(value).strip()
            folded = item.casefold()
            if item and folded not in seen:
                normalized.append(item)
                seen.add(folded)
        originals = {movie_uuid: self.metadata_service.load(movie_uuid) for movie_uuid in movie_ids}
        try:
            results: list[MovieRecord] = []
            remove_keys = {item.casefold() for item in normalized}
            for movie_uuid in movie_ids:
                movie = originals[movie_uuid]
                if remove:
                    updated_tags = [item for item in movie.tags if item.casefold() not in remove_keys]
                else:
                    updated_tags = list(movie.tags)
                    existing = {item.casefold() for item in updated_tags}
                    for item in normalized:
                        if item.casefold() not in existing:
                            updated_tags.append(item)
                            existing.add(item.casefold())
                results.append(
                    self.update_metadata(movie_uuid, MovieMetadataPatch(tags=updated_tags))
                )
            return results
        except Exception as exc:
            rollback_errors: list[str] = []
            for original in originals.values():
                try:
                    self.metadata_service.save(original)
                    self.repository.upsert_metadata(original)
                except Exception as rollback_exc:
                    rollback_errors.append(f"{original.uuid}: {rollback_exc}")
            if rollback_errors:
                raise RuntimeError(
                    f"batch tag update failed: {exc}; rollback also failed: {'; '.join(rollback_errors)}"
                ) from exc
            raise

    def set_folder(self, uuids: list[str], folder_id: str | None) -> list[MovieRecord]:
        movie_ids = list(dict.fromkeys(str(item) for item in uuids if str(item)))
        normalized_folder = str(folder_id).strip() if folder_id else None
        originals = {movie_uuid: self.metadata_service.load(movie_uuid) for movie_uuid in movie_ids}
        try:
            results: list[MovieRecord] = []
            for movie_uuid in movie_ids:
                movie = originals[movie_uuid]
                movie.folder_id = normalized_folder
                self.metadata_service.save(movie)
                self.repository.upsert_metadata(movie)
                record = self.repository.get(movie_uuid)
                if record is None:
                    raise RuntimeError("movie disappeared after folder update")
                results.append(record)
            return results
        except Exception as exc:
            rollback_errors: list[str] = []
            for original in originals.values():
                try:
                    self.metadata_service.save(original)
                    self.repository.upsert_metadata(original)
                except Exception as rollback_exc:
                    rollback_errors.append(f"{original.uuid}: {rollback_exc}")
            if rollback_errors:
                raise RuntimeError(
                    f"folder update failed: {exc}; rollback also failed: {'; '.join(rollback_errors)}"
                ) from exc
            raise

    def folder_member_uuids(self, folder_id: str) -> list[str]:
        return self.repository.list_uuids_by_folder(folder_id)

    def relink_video(self, uuid: str, path: Path) -> MovieRecord:
        record = self.repository.get(uuid)
        if record is None:
            raise KeyError(uuid)
        if len(record.episodes) > 1:
            raise ValueError("多集作品需要先选择要重新关联的剧集")
        if not record.episodes:
            video = self._validate_video(path)
            archived = self.metadata_service.load(uuid)
            episode = MovieEpisodeMetadata(
                uuid=legacy_episode_uuid(uuid),
                display_order=1,
                source_name=video.name,
            )
            archived = replace(archived, episodes=[episode])
            self.metadata_service.save(archived)
            self.repository.upsert_metadata(archived)
            return self.relink_episode(uuid, episode.uuid, video)
        return self.relink_episode(uuid, record.episodes[0].metadata.uuid, path)

    def relink_episode(self, uuid: str, episode_uuid: str, path: Path) -> MovieRecord:
        video = self._validate_video(path)
        record = self.repository.get(uuid)
        if record is None:
            raise KeyError(uuid)
        selected = record.episode(episode_uuid)
        if selected is None:
            raise KeyError(episode_uuid)
        info = self.media_probe.probe(video)
        external = self._external_subtitles(video)
        cover = self.cover_service.resolve(record.metadata.cover_key, video, info.duration if info else None)
        episode_metadata = MovieEpisodeMetadata(
            uuid=selected.metadata.uuid,
            display_order=selected.metadata.display_order,
            episode_number=selected.metadata.episode_number,
            season_number=selected.metadata.season_number,
            source_name=video.name,
        )
        archived = self.metadata_service.load(uuid)
        archived_episodes = [
            episode_metadata if episode.uuid == episode_uuid else episode
            for episode in record.metadata.episodes
        ]
        updated_archive = replace(archived, episodes=archived_episodes)
        self.metadata_service.save(updated_archive)
        self.repository.upsert_metadata(updated_archive)
        self.repository.upsert_episode_runtime(
            uuid,
            episode_metadata,
            MovieEpisodeRuntime(
            video_path=str(video.resolve()),
            library_id=self._library_for(video),
            availability_status="available",
            subtitle_status=compute_subtitle_status(external, info),
            duration=info.duration if info else None,
            width=info.width if info else None,
            height=info.height if info else None,
            video_codec=info.video_codec if info else None,
            audio_codec=info.audio_codec if info else None,
            file_size=video.stat().st_size,
            ),
        )
        self.repository.update_cover_path(
            uuid,
            str(cover.path) if cover.path else record.runtime.cover_path,
        )
        result = self.repository.get(uuid)
        if result is None:
            raise RuntimeError("movie disappeared after relink")
        return result

    def episode_for_playback(
        self,
        movie_uuid: str,
        episode_uuid: str | None = None,
    ) -> MovieEpisodeRecord:
        record = self.repository.get(movie_uuid)
        if record is None:
            raise KeyError(movie_uuid)
        if episode_uuid is None:
            selected = record.single_episode()
            if selected is None:
                if record.episodes:
                    raise ValueError("请先选择要播放的剧集")
                raise ValueError("这部作品当前没有可播放的视频")
        else:
            selected = record.episode(episode_uuid)
            if selected is None:
                raise KeyError(episode_uuid)
        if (
            selected.runtime.availability_status != "available"
            or not selected.runtime.video_path
        ):
            raise ValueError("所选剧集当前不可用")
        return selected

    def refresh_cover(self, uuid: str) -> MovieRecord:
        record = self.repository.get(uuid)
        if record is None:
            raise KeyError(uuid)
        selected = next(
            (
                episode
                for episode in record.episodes
                if episode.runtime.availability_status == "available"
                and episode.runtime.video_path
            ),
            None,
        )
        video = Path(selected.runtime.video_path) if selected else None
        duration = selected.runtime.duration if selected else None
        result = self.cover_service.resolve(record.metadata.cover_key, video, duration)
        self.repository.update_cover_path(
            uuid,
            str(result.path) if result.path else record.runtime.cover_path,
        )
        refreshed = self.repository.get(uuid)
        if refreshed is None:
            raise RuntimeError("movie disappeared after cover refresh")
        return refreshed

    def common_tags(self, limit: int = 30) -> list[str]:
        return self.repository.list_tags(limit)

    def delete_archive(self, uuid: str) -> DeletedArchive:
        record = self.repository.get(uuid)
        if record is None:
            raise KeyError(uuid)
        paths = DeletedArchive(
            tuple(
                dict.fromkeys(
                    episode.runtime.video_path
                    for episode in record.episodes
                    if episode.runtime.video_path
                )
            ),
            record.runtime.cover_path,
        )
        self.metadata_service.delete(uuid)
        self.repository.delete_archive(uuid)
        return paths

    @staticmethod
    def _validate_video(path: Path) -> Path:
        video = Path(path)
        if not video.is_file() or video.suffix.casefold() not in VIDEO_EXTENSIONS:
            raise ValueError("unsupported or missing video file")
        return video

    @staticmethod
    def _external_subtitles(video: Path) -> list[Path]:
        return [
            item
            for item in video.parent.iterdir()
            if item.is_file()
            and item.suffix.casefold() in {".srt", ".ass", ".ssa", ".vtt"}
            and (
                item.stem.casefold() == video.stem.casefold()
                or item.stem.casefold().startswith(video.stem.casefold() + ".")
            )
        ]

    def _library_for(self, video: Path) -> str | None:
        resolved = video.resolve()
        for library in self.settings.libraries:
            try:
                resolved.relative_to(Path(library.path).resolve())
                return library.id
            except ValueError:
                continue
        return None
