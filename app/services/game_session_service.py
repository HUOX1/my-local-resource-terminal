from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Callable, Iterable

from app.models.game import GameMetadata, GameSession
from app.repositories.game_repository import GameRepository
from app.services.game_metadata_service import GameMetadataService


WAIT_TIMEOUT_SECONDS = 300
CHECKPOINT_SECONDS = 30


def _normalize_executable(path: str | Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def running_executable_paths() -> set[str]:
    if os.name != "nt":
        return set()
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    enum_processes = psapi.EnumProcesses
    enum_processes.argtypes = [ctypes.POINTER(wintypes.DWORD), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    enum_processes.restype = wintypes.BOOL
    open_process = kernel32.OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE
    query_image = kernel32.QueryFullProcessImageNameW
    query_image.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    query_image.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    size = 4096
    process_ids = (wintypes.DWORD * size)()
    bytes_returned = wintypes.DWORD()
    if not enum_processes(process_ids, ctypes.sizeof(process_ids), ctypes.byref(bytes_returned)):
        return set()
    count = bytes_returned.value // ctypes.sizeof(wintypes.DWORD)
    result: set[str] = set()
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    for pid in process_ids[:count]:
        if not pid:
            continue
        handle = open_process(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            continue
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(buffer))
            if query_image(handle, 0, buffer, ctypes.byref(length)):
                result.add(_normalize_executable(buffer.value))
        finally:
            close_handle(handle)
    return result


class GameSessionService:
    def __init__(
        self,
        repository: GameRepository,
        metadata: GameMetadataService,
        state_path: Path,
        *,
        process_paths: Callable[[], Iterable[str]] = running_executable_paths,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.metadata = metadata
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._process_paths = process_paths
        self._now = now or (lambda: datetime.now(timezone.utc))
        self.waiting_game_uuid: str | None = None
        self._waiting_game: GameMetadata | None = None
        self._waiting_started_at: datetime | None = None
        self.active_session: GameSession | None = None
        self._active_game: GameMetadata | None = None

    @property
    def active_game_uuid(self) -> str | None:
        return self.active_session.game_uuid if self.active_session else None

    @property
    def active_game_title(self) -> str | None:
        return self._active_game.title if self._active_game else None

    @property
    def elapsed_seconds(self) -> int:
        if self.active_session is None:
            return 0
        return max(0, int((self._now() - self.active_session.started_at).total_seconds()))

    def request_launch(self, game: GameMetadata) -> bool:
        if self.active_session is not None or self.waiting_game_uuid is not None:
            return False
        self.waiting_game_uuid = game.uuid
        self._waiting_game = game
        self._waiting_started_at = self._now()
        return True

    def poll(self) -> None:
        now = self._now()
        if self.active_session is not None:
            if not self._is_running(self._active_game.timing_exe if self._active_game else ""):
                self.finish_active(now)
            return
        if self.waiting_game_uuid is None or self._waiting_game is None or self._waiting_started_at is None:
            return
        if (now - self._waiting_started_at).total_seconds() > WAIT_TIMEOUT_SECONDS:
            self._clear_waiting()
            return
        if self._is_running(self._waiting_game.timing_exe):
            game = self._waiting_game
            self.active_session = GameSession.active(game.uuid, now)
            self._active_game = game
            self.repository.upsert_active_session(self.active_session)
            self._write_state()
            self._clear_waiting()

    def checkpoint(self) -> None:
        if self.active_session is None:
            return
        now = self._now()
        self.active_session.duration_seconds = self.elapsed_seconds
        self.active_session.last_checkpoint_at = now
        self.repository.upsert_active_session(self.active_session)
        self._write_state()

    def finish_active(self, ended_at: datetime | None = None, *, status: str = "completed") -> None:
        if self.active_session is None or self._active_game is None:
            return
        ended = ended_at or self._now()
        session = self.active_session
        session.ended_at = ended
        session.duration_seconds = max(0, int((ended - session.started_at).total_seconds()))
        session.last_checkpoint_at = ended
        session.status = status
        game = self._load_current_game(self._active_game.uuid)
        game.sessions = [item for item in game.sessions if item.id != session.id]
        game.sessions.append(session)
        game.recalculate_play_stats()
        self.metadata.save(game)
        self.repository.complete_session(game, session)
        self.active_session = None
        self._active_game = None
        self.state_path.unlink(missing_ok=True)

    def recover(self) -> None:
        if not self.state_path.exists() or self.active_session is not None:
            return
        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        game_uuid = str(payload["game_uuid"])
        game = self._load_current_game(game_uuid)
        started_at = datetime.fromisoformat(str(payload["started_at"]))
        last_checkpoint_at = datetime.fromisoformat(str(payload["last_checkpoint_at"]))
        elapsed_seconds = max(0, int(payload.get("elapsed_seconds", 0)))
        session = GameSession(
            id=str(payload["session_id"]),
            game_uuid=game_uuid,
            started_at=started_at,
            duration_seconds=elapsed_seconds,
            last_checkpoint_at=last_checkpoint_at,
            status="active",
        )
        if self._is_running(game.timing_exe):
            self.active_session = session
            self._active_game = game
            self.repository.upsert_active_session(session)
            return
        session.ended_at = last_checkpoint_at
        session.duration_seconds = max(0, int((last_checkpoint_at - started_at).total_seconds()))
        session.status = "recovered"
        game.sessions = [item for item in game.sessions if item.id != session.id]
        game.sessions.append(session)
        game.recalculate_play_stats()
        self.metadata.save(game)
        self.repository.complete_session(game, session)
        self.state_path.unlink(missing_ok=True)

    def _load_current_game(self, game_uuid: str) -> GameMetadata:
        try:
            return self.metadata.load(game_uuid)
        except FileNotFoundError:
            record = self.repository.get(game_uuid)
            if record is None:
                raise
            return record.metadata

    def _is_running(self, target: str) -> bool:
        if not target:
            return False
        normalized = _normalize_executable(target)
        return normalized in {_normalize_executable(path) for path in self._process_paths()}

    def _write_state(self) -> None:
        if self.active_session is None:
            return
        last_checkpoint = self.active_session.last_checkpoint_at or self._now()
        payload = {
            "game_uuid": self.active_session.game_uuid,
            "session_id": self.active_session.id,
            "started_at": self.active_session.started_at.isoformat(),
            "last_checkpoint_at": last_checkpoint.isoformat(),
            "elapsed_seconds": self.elapsed_seconds,
        }
        temporary = self.state_path.with_name(f".{self.state_path.name}.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        json.loads(temporary.read_text(encoding="utf-8"))
        temporary.replace(self.state_path)

    def _clear_waiting(self) -> None:
        self.waiting_game_uuid = None
        self._waiting_game = None
        self._waiting_started_at = None
