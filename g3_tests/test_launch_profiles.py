from pathlib import Path
import sys

import pytest

from g3_core.database import Database
from g3_core.models import CreateGame, LaunchProfile
from g3_core.repository import LibraryRepository


def _repo(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()
    return LibraryRepository(db)


def test_direct_game_gets_direct_launch_profile(tmp_path):
    repo = _repo(tmp_path)
    game = repo.create_game(CreateGame(title="Rain World", executable_path=Path(sys.executable)))
    profile = repo.get_launch_profile(game.id)
    assert profile.profile_type == "direct"
    assert profile.launch_exe == Path(sys.executable).resolve()
    assert profile.monitor_exe == Path(sys.executable).resolve()
    assert profile.wait_timeout_s == 300


def test_launcher_profile_round_trip(tmp_path):
    repo = _repo(tmp_path)
    game = repo.create_game(CreateGame(title="Elden Ring", executable_path=Path(sys.executable)))
    mod_engine = tmp_path / "modengine.exe"
    eldenring = tmp_path / "eldenring.exe"
    mod_engine.write_bytes(b"")
    eldenring.write_bytes(b"")
    profile = LaunchProfile(
        profile_type="launcher",
        launch_exe=mod_engine,
        launch_args="--profile default",
        working_directory=tmp_path,
        content_path=None,
        monitor_exe=eldenring,
        wait_timeout_s=90,
        run_as_admin=False,
    )
    repo.update_launch_profile(game.id, profile)
    loaded = repo.get_launch_profile(game.id)
    assert loaded == profile.normalized()


def test_emulator_profile_keeps_content_path(tmp_path):
    repo = _repo(tmp_path)
    game = repo.create_game(CreateGame(title="Silent Hill", executable_path=Path(sys.executable)))
    emulator = tmp_path / "emu.exe"
    image = tmp_path / "silent-hill.cue"
    emulator.write_bytes(b"")
    image.write_bytes(b"")
    repo.update_launch_profile(
        game.id,
        LaunchProfile(
            profile_type="emulator",
            launch_exe=emulator,
            launch_args='--fullscreen "{content}"',
            working_directory=tmp_path,
            content_path=image,
            monitor_exe=emulator,
            wait_timeout_s=60,
        ),
    )
    loaded = repo.get_launch_profile(game.id)
    assert loaded.profile_type == "emulator"
    assert loaded.content_path == image.resolve()


def test_launch_profile_rejects_invalid_type():
    with pytest.raises(ValueError):
        LaunchProfile(profile_type="magic", launch_exe=Path(sys.executable)).normalized()


def test_launch_profile_rejects_negative_timeout():
    with pytest.raises(ValueError):
        LaunchProfile(profile_type="direct", launch_exe=Path(sys.executable), wait_timeout_s=-1).normalized()


def test_launch_profile_rejects_missing_monitor_executable(tmp_path):
    launch = tmp_path / "launcher.exe"
    launch.write_bytes(b"")
    with pytest.raises(FileNotFoundError):
        LaunchProfile(
            profile_type="launcher",
            launch_exe=launch,
            monitor_exe=tmp_path / "missing-game.exe",
        ).normalized()
