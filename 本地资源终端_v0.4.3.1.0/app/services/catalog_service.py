from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config.settings import AppSettings
from app.models.movie import MovieMetadata, MovieMetadataPatch, MovieRecord
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
    video_path: str | None
    cover_path: str | None


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
        payload = {
            "uuid": movie.uuid,
            "cover_key": patch.cover_key if patch.cover_key is not None else movie.cover_key,
            "code": patch.code if patch.code is not None else movie.code,
            "title": patch.title if patch.title is not None else movie.title,
            "actors": patch.actors if patch.actors is not None else movie.actors,
            "series": patch.series if patch.series is not None else movie.series,
            "studio": patch.studio if patch.studio is not None else movie.studio,
            "release_date": patch.release_date if patch.release_date is not None else movie.release_date,
            "tags": patch.tags if patch.tags is not None else movie.tags,
            "rating": patch.rating if patch.rating is not None else movie.rating,
            "watched": patch.watched if patch.watched is not None else movie.watched,
            "play_count": movie.play_count,
            "total_play_seconds": movie.total_play_seconds,
            "favorite": patch.favorite if patch.favorite is not None else movie.favorite,
            "notes": patch.notes if patch.notes is not None else movie.notes,
            "folder_id": movie.folder_id,
            "first_watched_at": movie.first_watched_at,
            "last_watched_at": movie.last_watched_at,
            "added_at": movie.added_at,
            "play_history": movie.play_history,
        }
        updated = MovieMetadata(**payload)
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
        video = Path(path)
        if not video.is_file() or video.suffix.casefold() not in VIDEO_EXTENSIONS:
            raise ValueError("unsupported or missing video file")
        record = self.repository.get(uuid)
        if record is None:
            raise KeyError(uuid)
        info = self.media_probe.probe(video)
        external = [
            item
            for item in video.parent.iterdir()
            if item.is_file()
            and item.suffix.casefold() in {".srt", ".ass", ".ssa", ".vtt"}
            and (item.stem.casefold() == video.stem.casefold() or item.stem.casefold().startswith(video.stem.casefold() + "."))
        ]
        cover = self.cover_service.resolve(record.metadata.cover_key, video, info.duration if info else None)
        self.repository.update_runtime(
            uuid,
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
            cover_path=str(cover.path) if cover.path else None,
        )
        result = self.repository.get(uuid)
        if result is None:
            raise RuntimeError("movie disappeared after relink")
        return result


    def refresh_cover(self, uuid: str) -> MovieRecord:
        record = self.repository.get(uuid)
        if record is None:
            raise KeyError(uuid)
        video = Path(record.runtime.video_path) if record.runtime.video_path and record.runtime.availability_status == "available" else None
        result = self.cover_service.resolve(record.metadata.cover_key, video, record.runtime.duration)
        self.repository.update_runtime(
            uuid,
            video_path=record.runtime.video_path,
            library_id=record.runtime.library_id,
            availability_status=record.runtime.availability_status,
            subtitle_status=record.runtime.subtitle_status,
            duration=record.runtime.duration,
            width=record.runtime.width,
            height=record.runtime.height,
            video_codec=record.runtime.video_codec,
            audio_codec=record.runtime.audio_codec,
            file_size=record.runtime.file_size,
            cover_path=str(result.path) if result.path else None,
            last_scanned_at=record.runtime.last_scanned_at,
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
        paths = DeletedArchive(record.runtime.video_path, record.runtime.cover_path)
        self.metadata_service.delete(uuid)
        self.repository.delete_archive(uuid)
        return paths

    def _library_for(self, video: Path) -> str | None:
        resolved = video.resolve()
        for library in self.settings.libraries:
            try:
                resolved.relative_to(Path(library.path).resolve())
                return library.id
            except ValueError:
                continue
        return None
