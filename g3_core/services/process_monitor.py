from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import time
from typing import Callable, Iterable


def normalize_executable(path: str | Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def running_executable_paths() -> set[str]:
    """Return full executable paths for visible Windows processes.

    On non-Windows systems this returns an empty set; tests inject a process-path
    provider so the launch/session state machine can be verified portably.
    """
    if os.name != "nt":
        return set()

    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    enum_processes = psapi.EnumProcesses
    enum_processes.argtypes = [
        ctypes.POINTER(wintypes.DWORD),
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    enum_processes.restype = wintypes.BOOL

    open_process = kernel32.OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE

    query_image = kernel32.QueryFullProcessImageNameW
    query_image.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    query_image.restype = wintypes.BOOL

    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    size = 4096
    process_ids = (wintypes.DWORD * size)()
    bytes_returned = wintypes.DWORD()
    if not enum_processes(
        process_ids,
        ctypes.sizeof(process_ids),
        ctypes.byref(bytes_returned),
    ):
        return set()

    count = bytes_returned.value // ctypes.sizeof(wintypes.DWORD)
    result: set[str] = set()
    process_query_limited_information = 0x1000
    for pid in process_ids[:count]:
        if not pid:
            continue
        handle = open_process(process_query_limited_information, False, pid)
        if not handle:
            continue
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(buffer))
            if query_image(handle, 0, buffer, ctypes.byref(length)):
                result.add(normalize_executable(buffer.value))
        finally:
            close_handle(handle)
    return result


class ProcessMonitor:
    def __init__(
        self,
        *,
        process_paths: Callable[[], Iterable[str | Path]] = running_executable_paths,
        now: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        poll_interval_s: float = 0.25,
    ) -> None:
        self._process_paths = process_paths
        self._now = now
        self._sleep = sleep
        self.poll_interval_s = max(0.0, float(poll_interval_s))

    def snapshot(self) -> set[str]:
        return {normalize_executable(path) for path in self._process_paths()}

    def is_running(self, target: str | Path) -> bool:
        return normalize_executable(target) in self.snapshot()

    def wait_until_present(self, target: str | Path, timeout_s: float) -> bool:
        normalized = normalize_executable(target)
        started = self._now()
        timeout = max(0.0, float(timeout_s))
        while True:
            if normalized in self.snapshot():
                return True
            if self._now() - started >= timeout:
                return False
            self._sleep(self.poll_interval_s)

    def wait_until_absent(self, target: str | Path) -> None:
        normalized = normalize_executable(target)
        while normalized in self.snapshot():
            self._sleep(self.poll_interval_s)
