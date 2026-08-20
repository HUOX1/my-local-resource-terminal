from __future__ import annotations

from pathlib import Path

import pytest

from app.models.game import GameMetadata
from app.services.game_launcher import GameLauncher


def test_launcher_rejects_missing_executable(tmp_path):
    game = GameMetadata.new("Demo")
    game.launch_exe = str(tmp_path / "missing.exe")
    game.timing_exe = game.launch_exe
    launcher = GameLauncher(popen=lambda *args, **kwargs: None)

    with pytest.raises(FileNotFoundError):
        launcher.launch(game)


def test_launcher_uses_explicit_args_and_working_directory(tmp_path):
    exe = tmp_path / "demo.exe"
    exe.write_bytes(b"")
    work = tmp_path / "work"
    work.mkdir()
    game = GameMetadata.new("Demo")
    game.launch_exe = str(exe)
    game.launch_args = '--profile "My Save" -dx11'
    game.working_directory = str(work)
    game.timing_exe = str(exe)
    calls = []

    def fake_popen(args, **kwargs):
        calls.append((args, kwargs))
        return object()

    GameLauncher(popen=fake_popen).launch(game)

    args, kwargs = calls[0]
    assert args[0] == str(exe)
    assert args[1:] == ["--profile", "My Save", "-dx11"]
    assert kwargs["cwd"] == str(work)
    assert kwargs["shell"] is False


def test_launcher_falls_back_to_windows_elevation_on_winerror_740(tmp_path):
    exe = tmp_path / "admin-game.exe"
    exe.write_bytes(b"")
    work = tmp_path / "work"
    work.mkdir()
    game = GameMetadata.new("Admin Game")
    game.launch_exe = str(exe)
    game.launch_args = '--profile "My Save" -dx11'
    game.working_directory = str(work)
    game.timing_exe = str(exe)
    elevated_calls = []

    def failing_popen(*args, **kwargs):
        error = OSError("elevation required")
        error.winerror = 740
        raise error

    def fake_elevated_launch(executable, arguments, working_directory):
        elevated_calls.append((executable, arguments, working_directory))
        return "elevated"

    result = GameLauncher(
        popen=failing_popen,
        elevated_launch=fake_elevated_launch,
    ).launch(game)

    assert result == "elevated"
    assert elevated_calls == [(exe, ["--profile", "My Save", "-dx11"], str(work))]


def test_launcher_does_not_elevate_for_unrelated_os_errors(tmp_path):
    exe = tmp_path / "broken-game.exe"
    exe.write_bytes(b"")
    game = GameMetadata.new("Broken Game")
    game.launch_exe = str(exe)
    game.timing_exe = str(exe)
    elevated_calls = []

    def failing_popen(*args, **kwargs):
        error = OSError("other failure")
        error.winerror = 2
        raise error

    def fake_elevated_launch(*args):
        elevated_calls.append(args)

    with pytest.raises(OSError, match="other failure"):
        GameLauncher(
            popen=failing_popen,
            elevated_launch=fake_elevated_launch,
        ).launch(game)

    assert elevated_calls == []
