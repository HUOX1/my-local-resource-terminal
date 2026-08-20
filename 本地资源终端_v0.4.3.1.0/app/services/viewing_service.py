from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.models.movie import MovieMetadata, PlayEvent
from app.repositories.movie_repository import MovieRepository
from app.services.metadata_service import MetadataService
from app.utils.time import utc_now


class PlaybackHandle(Protocol):
    def is_running(self) -> bool: ...
    def close(self) -> None: ...


@dataclass(slots=True)
class _ActivePlayback:
    movie_uuid: str
    started_at: datetime
    handle: PlaybackHandle


class ViewingService:
    def __init__(self, repository: MovieRepository, metadata_service: MetadataService) -> None:
        self.repository = repository
        self.metadata_service = metadata_service
        self._active_playbacks: list[_ActivePlayback] = []

    @property
    def active_playback_count(self) -> int:
        return len(self._active_playbacks)

    def record_launch(self, movie_uuid: str, played_at: datetime | None = None) -> MovieMetadata:
        when = played_at or utc_now()
        movie = self.metadata_service.load(movie_uuid)
        movie.watched = True
        movie.play_count += 1
        if movie.first_watched_at is None:
            movie.first_watched_at = when
        movie.last_watched_at = when
        movie.play_history.append(PlayEvent(when))
        self.metadata_service.save(movie)
        self.repository.upsert_metadata(movie)
        self.repository.record_play_event(movie.uuid, when)
        return movie

    def add_playback_duration(self, movie_uuid: str, duration_seconds: int) -> MovieMetadata:
        movie = self.metadata_service.load(movie_uuid)
        movie.total_play_seconds += max(0, int(duration_seconds))
        self.metadata_service.save(movie)
        self.repository.upsert_metadata(movie)
        return movie

    def start_playback(
        self,
        movie_uuid: str,
        handle: PlaybackHandle | None,
        *,
        started_at: datetime | None = None,
    ) -> MovieMetadata:
        when = started_at or utc_now()
        movie = self.record_launch(movie_uuid, when)
        if handle is not None:
            self._active_playbacks.append(_ActivePlayback(movie_uuid, when, handle))
        return movie

    def poll_playbacks(self, *, now: datetime | None = None) -> list[str]:
        when = now or utc_now()
        finished: list[str] = []
        remaining: list[_ActivePlayback] = []
        for session in self._active_playbacks:
            try:
                running = session.handle.is_running()
            except Exception:
                running = False
            if running:
                remaining.append(session)
                continue
            self._finish_session(session, when)
            finished.append(session.movie_uuid)
        self._active_playbacks = remaining
        return finished

    def finish_all_playbacks(self, *, now: datetime | None = None) -> list[str]:
        when = now or utc_now()
        sessions = self._active_playbacks
        self._active_playbacks = []
        finished: list[str] = []
        for session in sessions:
            self._finish_session(session, when)
            finished.append(session.movie_uuid)
        return finished

    def _finish_session(self, session: _ActivePlayback, ended_at: datetime) -> None:
        duration = max(0, int((ended_at - session.started_at).total_seconds()))
        try:
            self.add_playback_duration(session.movie_uuid, duration)
        finally:
            try:
                session.handle.close()
            except Exception:
                pass
