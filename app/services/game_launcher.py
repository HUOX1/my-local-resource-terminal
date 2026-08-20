from __future__ import annotations

import ctypes
import os
from pathlib import Path
import shlex
import subprocess
from typing import Callable

from app.models.game import GameMetadata


ElevatedLaunch = Callable[[Path, list[str], str], object]


def _windows_elevated_launch(
    executable: Path,
    arguments: list[str],
    working_directory: str,
) -> object:
    if os.name != "nt":
        raise OSError("管理员权限启动仅支持 Windows")

    parameters = subprocess.list2cmdline(arguments) if arguments else None
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        str(executable),
        parameters,
        working_directory,
        1,
    )
    code = int(result)
    if code <= 32:
        if code == 5:
            raise OSError("管理员授权被取消，或 Windows 拒绝了提权启动")
        raise OSError(f"Windows 提权启动失败（ShellExecute 返回 {code}）")
    return result


class GameLauncher:
    def __init__(
        self,
        popen: Callable[..., object] = subprocess.Popen,
        elevated_launch: ElevatedLaunch = _windows_elevated_launch,
    ) -> None:
        self._popen = popen
        self._elevated_launch = elevated_launch

    def launch(self, game: GameMetadata) -> object:
        executable = Path(game.launch_exe)
        if not executable.is_file():
            raise FileNotFoundError(executable)
        arguments = shlex.split(game.launch_args) if game.launch_args else []
        working_directory = game.working_directory or str(executable.parent)
        try:
            return self._popen(
                [str(executable), *arguments],
                cwd=working_directory,
                shell=False,
            )
        except OSError as exc:
            if getattr(exc, "winerror", None) != 740:
                raise
            return self._elevated_launch(executable, arguments, working_directory)
