from __future__ import annotations

import ctypes
import os
import subprocess
from ctypes import wintypes
from pathlib import Path
from typing import Protocol

from app.config.settings import AppSettings


class PlaybackError(RuntimeError):
    pass


class PlaybackHandle(Protocol):
    def is_running(self) -> bool: ...
    def close(self) -> None: ...


class _PopenPlaybackHandle:
    def __init__(self, process) -> None:
        self.process = process

    def is_running(self) -> bool:
        return self.process.poll() is None

    def close(self) -> None:
        # subprocess.Popen owns its process handle lifecycle. Do not terminate the player.
        return None


class _Win32PlaybackHandle:
    WAIT_TIMEOUT = 0x00000102

    def __init__(self, handle: int) -> None:
        self._handle = int(handle)

    def is_running(self) -> bool:
        if not self._handle:
            return False
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        result = kernel32.WaitForSingleObject(wintypes.HANDLE(self._handle), 0)
        return int(result) == self.WAIT_TIMEOUT

    def close(self) -> None:
        if not self._handle:
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle(wintypes.HANDLE(self._handle))
        self._handle = 0


class _SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", wintypes.ULONG),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIconOrMonitor", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


class PlayerService:
    def play(self, video_path: Path, settings: AppSettings) -> PlaybackHandle | None:
        video = Path(video_path)
        if not video.is_file():
            raise PlaybackError(f"video file does not exist: {video}")
        if settings.player_mode == "custom":
            if settings.player_path is None or not Path(settings.player_path).is_file():
                raise PlaybackError("custom player path is invalid")
            try:
                process = subprocess.Popen([str(settings.player_path), str(video)])
            except OSError as exc:
                raise PlaybackError(str(exc)) from exc
            return _PopenPlaybackHandle(process)
        if os.name != "nt":
            raise PlaybackError("system default playback is only available on Windows")
        return self._play_with_windows_shell(video)

    @staticmethod
    def _play_with_windows_shell(video: Path) -> PlaybackHandle | None:
        SEE_MASK_NOCLOSEPROCESS = 0x00000040
        SW_SHOWNORMAL = 1
        info = _SHELLEXECUTEINFOW()
        info.cbSize = ctypes.sizeof(info)
        info.fMask = SEE_MASK_NOCLOSEPROCESS
        info.lpVerb = "open"
        info.lpFile = str(video)
        info.nShow = SW_SHOWNORMAL
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        shell_execute = shell32.ShellExecuteExW
        shell_execute.argtypes = [ctypes.POINTER(_SHELLEXECUTEINFOW)]
        shell_execute.restype = wintypes.BOOL
        if not shell_execute(ctypes.byref(info)):
            error = ctypes.get_last_error()
            raise PlaybackError(f"Windows failed to open video (error {error})")
        if info.hProcess:
            return _Win32PlaybackHandle(int(info.hProcess))
        # Some file associations activate an existing player instance and return no process handle.
        # Playback still succeeds; this launch simply cannot contribute reliable process-time data.
        return None
