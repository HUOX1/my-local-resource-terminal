from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from collections.abc import Callable, Mapping

from g3_core.settings import TerminalSettings


class GodotDiscoveryError(FileNotFoundError):
    pass


def choose_godot_executable_windows() -> str | None:
    if os.name != "nt":
        return None
    script = r'''
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = 'Select Godot 4.7 executable'
$dialog.Filter = 'Godot executable (Godot*.exe)|Godot*.exe|Executable (*.exe)|*.exe'
$dialog.Multiselect = $false
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
    [Console]::Out.Write($dialog.FileName)
}
'''
    flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-STA", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
        creationflags=flags,
    )
    value = result.stdout.strip()
    return value or None


def _usable_file(value: str | os.PathLike[str] | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if path.is_file():
        return path.resolve()
    return None


def resolve_godot_executable(
    settings: TerminalSettings,
    *,
    environment: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    chooser: Callable[[], str | None] = choose_godot_executable_windows,
) -> Path:
    env = os.environ if environment is None else environment

    saved = _usable_file(settings.godot_executable)
    if saved is not None:
        return saved

    environment_path = _usable_file(env.get("GODOT_EXE"))
    if environment_path is not None:
        settings.godot_executable = str(environment_path)
        return environment_path

    for name in (
        "godot",
        "godot4",
        "Godot_v4.7.2-stable_win64.exe",
        "Godot_v4.7-stable_win64.exe",
    ):
        found = _usable_file(which(name))
        if found is not None:
            settings.godot_executable = str(found)
            return found

    selected = _usable_file(chooser())
    if selected is not None:
        settings.godot_executable = str(selected)
        return selected

    raise GodotDiscoveryError(
        "Godot 4.7 executable was not found. Select it when prompted or set GODOT_EXE."
    )
