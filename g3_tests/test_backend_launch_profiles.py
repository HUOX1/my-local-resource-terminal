from pathlib import Path
import sys

import pytest

from g3_core.backend_app import BackendApplication
from g3_core.paths import TerminalPaths


def _paths(root: Path) -> TerminalPaths:
    return TerminalPaths(
        root=root,
        database=root / "library.db",
        assets=root / "assets",
        cache=root / "cache",
        themes=root / "themes",
        logs=root / "logs",
        settings=root / "settings.json",
    )


@pytest.mark.asyncio
async def test_backend_gets_and_updates_launch_profile(tmp_path):
    app = BackendApplication(_paths(tmp_path / "G3"), builtin_theme_root=tmp_path / "builtin")
    app.initialize()
    game = await app.handle_command(
        "game.create",
        {"title": "Rain World", "executable_path": sys.executable},
    )
    profile = await app.handle_command("game.launch_profile.get", {"id": game["id"]})
    assert profile["profile_type"] == "direct"
    assert profile["launch_exe"] == str(Path(sys.executable).resolve())

    launcher = tmp_path / "modengine.exe"
    monitor = tmp_path / "eldenring.exe"
    launcher.write_bytes(b"")
    monitor.write_bytes(b"")
    updated = await app.handle_command(
        "game.launch_profile.update",
        {
            "id": game["id"],
            "profile_type": "launcher",
            "launch_exe": str(launcher),
            "launch_args": "--mod",
            "working_directory": str(tmp_path),
            "content_path": "",
            "monitor_exe": str(monitor),
            "wait_timeout_s": 120,
            "run_as_admin": False,
        },
    )
    assert updated["profile_type"] == "launcher"
    listed = await app.handle_command("library.games.list", {})
    assert listed[0]["launch_profile"]["monitor_exe"] == str(monitor.resolve())
