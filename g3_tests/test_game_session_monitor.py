from pathlib import Path
import sys

import pytest

from g3_core.models import LaunchProfile
from g3_core.services.game_runtime import build_launch_arguments
from g3_core.services.process_monitor import ProcessMonitor


def test_emulator_content_placeholder_is_substituted(tmp_path):
    content = tmp_path / "game.cue"
    content.write_bytes(b"")
    profile = LaunchProfile(
        profile_type="emulator",
        launch_exe=Path(sys.executable),
        launch_args='--fullscreen "{content}"',
        working_directory=tmp_path,
        content_path=content,
        monitor_exe=Path(sys.executable),
    ).normalized()
    args = build_launch_arguments(profile)
    assert "{content}" not in " ".join(args)
    assert str(content.resolve()) in args


def test_emulator_content_is_appended_when_placeholder_absent(tmp_path):
    content = tmp_path / "game.iso"
    content.write_bytes(b"")
    profile = LaunchProfile(
        profile_type="emulator",
        launch_exe=Path(sys.executable),
        launch_args="--fullscreen",
        working_directory=tmp_path,
        content_path=content,
        monitor_exe=Path(sys.executable),
    ).normalized()
    assert build_launch_arguments(profile)[-1] == str(content.resolve())


def test_process_monitor_waits_for_launcher_target_then_exit(tmp_path):
    target = (tmp_path / "eldenring.exe").resolve()
    snapshots = iter([
        set(),
        {str(tmp_path / "modengine.exe")},
        {str(target)},
        {str(target)},
        set(),
    ])
    last = set()

    def process_paths():
        nonlocal last
        try:
            last = next(snapshots)
        except StopIteration:
            pass
        return last

    monitor = ProcessMonitor(process_paths=process_paths, sleep=lambda _: None, poll_interval_s=0.0)
    assert monitor.wait_until_present(target, timeout_s=1.0)
    monitor.wait_until_absent(target)


def test_process_monitor_times_out_when_target_never_appears(tmp_path):
    target = tmp_path / "missing.exe"
    clock = iter([0.0, 0.2, 0.4, 0.6])
    monitor = ProcessMonitor(
        process_paths=lambda: set(),
        now=lambda: next(clock, 1.0),
        sleep=lambda _: None,
        poll_interval_s=0.0,
    )
    assert monitor.wait_until_present(target, timeout_s=0.5) is False
