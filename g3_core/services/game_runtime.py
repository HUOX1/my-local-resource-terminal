from __future__ import annotations

import asyncio
import ctypes
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import shlex
import subprocess
from typing import Callable

from g3_core.models import GameRecord, LaunchProfile
from g3_core.repository import LibraryRepository
from g3_core.services.process_monitor import ProcessMonitor, normalize_executable


logger = logging.getLogger("g3.game_runtime")


def build_windows_shell_command(executable: Path, arguments: list[str]) -> list[str]:
    return [
        "cmd.exe",
        "/d",
        "/s",
        "/c",
        "start",
        "",
        "/wait",
        str(executable),
        *arguments,
    ]


def build_launch_arguments(profile: LaunchProfile) -> list[str]:
    arguments = shlex.split(profile.launch_args, posix=False) if profile.launch_args else []
    normalized: list[str] = []
    content = str(profile.content_path) if profile.content_path else ""
    used_content_placeholder = False
    for arg in arguments:
        if len(arg) >= 2 and arg[0] == arg[-1] and arg[0] in {'"', "'"}:
            arg = arg[1:-1]
        if "{content}" in arg:
            used_content_placeholder = True
            arg = arg.replace("{content}", content)
        normalized.append(arg)
    if profile.profile_type == "emulator" and content and not used_content_placeholder:
        normalized.append(content)
    return normalized


def _windows_elevated_launch(
    executable: Path,
    arguments: list[str],
    working_directory: Path,
) -> None:
    if os.name != "nt":
        raise OSError("administrator launch is only available on Windows")
    parameters = subprocess.list2cmdline(arguments) if arguments else None
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        str(executable),
        parameters,
        str(working_directory),
        1,
    )
    code = int(result)
    if code <= 32:
        if code == 5:
            raise OSError("administrator authorization was cancelled or denied")
        raise OSError(f"ShellExecuteW failed with code {code}")


@dataclass(slots=True)
class RunningGame:
    item_id: str
    process: subprocess.Popen | None
    launch_pid: int
    profile: LaunchProfile
    started_at: datetime


@dataclass(slots=True)
class GameExit:
    item_id: str
    exit_code: int
    elapsed_seconds: int
    ended_at: datetime
    session_started_at: datetime


class GameRuntime:
    def __init__(
        self,
        repository: LibraryRepository,
        *,
        monitor: ProcessMonitor | None = None,
        popen: Callable[..., subprocess.Popen] = subprocess.Popen,
        elevated_launch: Callable[[Path, list[str], Path], None] = _windows_elevated_launch,
    ) -> None:
        self.repository = repository
        self.monitor = monitor or ProcessMonitor()
        self._popen = popen
        self._elevated_launch = elevated_launch

    def launch(self, game: GameRecord) -> RunningGame:
        raw_profile = game.launch_profile
        try:
            profile = raw_profile.normalized()
        except Exception:
            logger.exception(
                "Game launch failed: invalid profile item_id=%s launch_exe=%s monitor_exe=%s cwd=%s args=%r",
                game.id,
                raw_profile.launch_exe,
                raw_profile.monitor_exe,
                raw_profile.working_directory,
                raw_profile.launch_args,
            )
            raise
        executable = profile.launch_exe
        assert executable is not None
        cwd = profile.working_directory or executable.parent
        arguments = build_launch_arguments(profile)
        logger.info(
            "Launch requested: item_id=%s type=%s launch_exe=%s monitor_exe=%s cwd=%s args=%r content=%s admin=%s",
            game.id,
            profile.profile_type,
            executable,
            profile.monitor_exe,
            cwd,
            arguments,
            profile.content_path,
            profile.run_as_admin,
        )

        process: subprocess.Popen | None = None
        launch_pid = 0
        if profile.run_as_admin:
            self._elevated_launch(executable, arguments, cwd)
            logger.info("Elevated launch dispatched: item_id=%s exe=%s", game.id, executable)
        else:
            try:
                process = self._popen([str(executable), *arguments], cwd=str(cwd), shell=False)
            except OSError as direct_error:
                if os.name != "nt":
                    logger.exception("Launch failed: exe=%s cwd=%s args=%r", executable, cwd, arguments)
                    raise
                logger.warning(
                    "Direct launch failed; trying Windows shell fallback: exe=%s cwd=%s args=%r error=%s",
                    executable,
                    cwd,
                    arguments,
                    direct_error,
                    exc_info=True,
                )
                fallback = build_windows_shell_command(executable, arguments)
                process = self._popen(
                    fallback,
                    cwd=str(cwd),
                    shell=False,
                    creationflags=int(getattr(subprocess, "CREATE_NO_WINDOW", 0)),
                )
            launch_pid = int(process.pid)
            logger.info("Launch process started: item_id=%s pid=%s", game.id, launch_pid)

        return RunningGame(
            item_id=game.id,
            process=process,
            launch_pid=launch_pid,
            profile=profile,
            started_at=datetime.now(timezone.utc),
        )

    def wait_for_session_start_blocking(self, running: RunningGame) -> datetime:
        monitor_exe = running.profile.monitor_exe or running.profile.launch_exe
        if monitor_exe is None:
            raise RuntimeError("launch profile has no monitor executable")

        launch_exe = running.profile.launch_exe
        same_process = (
            launch_exe is not None
            and normalize_executable(monitor_exe) == normalize_executable(launch_exe)
        )
        if same_process and running.process is not None and running.process.poll() is None:
            started = datetime.now(timezone.utc)
            logger.info("Gameplay session started from launch process: item_id=%s", running.item_id)
            return started

        if not self.monitor.wait_until_present(monitor_exe, running.profile.wait_timeout_s):
            logger.error(
                "Gameplay process did not appear before timeout: item_id=%s monitor_exe=%s timeout_s=%s",
                running.item_id,
                monitor_exe,
                running.profile.wait_timeout_s,
            )
            raise TimeoutError(f"游戏进程未在 {running.profile.wait_timeout_s} 秒内出现：{monitor_exe}")

        started = datetime.now(timezone.utc)
        logger.info(
            "Gameplay session detected: item_id=%s monitor_exe=%s",
            running.item_id,
            monitor_exe,
        )
        return started

    def wait_for_exit_blocking(
        self,
        running: RunningGame,
        session_started_at: datetime | None = None,
    ) -> GameExit:
        session_started = session_started_at or self.wait_for_session_start_blocking(running)
        monitor_exe = running.profile.monitor_exe or running.profile.launch_exe
        assert monitor_exe is not None
        launch_exe = running.profile.launch_exe
        same_process = (
            launch_exe is not None
            and normalize_executable(monitor_exe) == normalize_executable(launch_exe)
        )

        exit_code = 0
        if same_process and running.process is not None:
            exit_code = int(running.process.wait())
        else:
            self.monitor.wait_until_absent(monitor_exe)
            if running.process is not None and running.process.poll() is not None:
                exit_code = int(running.process.returncode or 0)

        ended_at = datetime.now(timezone.utc)
        elapsed = max(0, int((ended_at - session_started).total_seconds()))
        self.repository.update_play_stats(running.item_id, elapsed, ended_at)
        logger.info(
            "Gameplay session exited: item_id=%s monitor_exe=%s exit_code=%s elapsed_seconds=%s",
            running.item_id,
            monitor_exe,
            exit_code,
            elapsed,
        )
        return GameExit(
            item_id=running.item_id,
            exit_code=exit_code,
            elapsed_seconds=elapsed,
            ended_at=ended_at,
            session_started_at=session_started,
        )

    async def wait_for_session_start(self, running: RunningGame) -> datetime:
        return await asyncio.to_thread(self.wait_for_session_start_blocking, running)

    async def wait_for_exit(
        self,
        running: RunningGame,
        session_started_at: datetime | None = None,
    ) -> GameExit:
        return await asyncio.to_thread(self.wait_for_exit_blocking, running, session_started_at)
