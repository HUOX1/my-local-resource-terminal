from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import shlex
import subprocess

from terminal_core.models import GameRecord
from terminal_core.repository import LibraryRepository


@dataclass(slots=True)
class RunningGame:
    item_id: str
    process: subprocess.Popen
    started_at: datetime


@dataclass(slots=True)
class GameExit:
    item_id: str
    exit_code: int
    elapsed_seconds: int
    ended_at: datetime


class GameRuntime:
    def __init__(self, repository: LibraryRepository) -> None:
        self.repository = repository

    def launch(self, game: GameRecord) -> RunningGame:
        executable = Path(game.executable_path)
        if not executable.is_file():
            raise FileNotFoundError(executable)
        arguments = shlex.split(game.launch_args, posix=False) if game.launch_args else []
        normalized: list[str] = []
        for arg in arguments:
            if len(arg) >= 2 and arg[0] == arg[-1] and arg[0] in {'"', "'"}:
                arg = arg[1:-1]
            normalized.append(arg)
        cwd = game.working_directory or str(executable.parent)
        process = subprocess.Popen([str(executable), *normalized], cwd=cwd, shell=False)
        return RunningGame(
            item_id=game.id,
            process=process,
            started_at=datetime.now(timezone.utc),
        )

    def wait_for_exit_blocking(self, running: RunningGame) -> GameExit:
        exit_code = int(running.process.wait())
        ended_at = datetime.now(timezone.utc)
        elapsed = max(0, int((ended_at - running.started_at).total_seconds()))
        self.repository.update_play_stats(running.item_id, elapsed, ended_at)
        return GameExit(
            item_id=running.item_id,
            exit_code=exit_code,
            elapsed_seconds=elapsed,
            ended_at=ended_at,
        )

    async def wait_for_exit(self, running: RunningGame) -> GameExit:
        return await asyncio.to_thread(self.wait_for_exit_blocking, running)
