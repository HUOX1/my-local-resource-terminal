from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


LAUNCH_PROFILE_TYPES = {"direct", "launcher", "emulator"}


@dataclass(slots=True)
class LaunchProfile:
    profile_type: str = "direct"
    launch_exe: Path | None = None
    launch_args: str = ""
    working_directory: Path | None = None
    content_path: Path | None = None
    monitor_exe: Path | None = None
    wait_timeout_s: int = 300
    run_as_admin: bool = False

    def normalized(self) -> "LaunchProfile":
        profile_type = str(self.profile_type).strip().lower()
        if profile_type not in LAUNCH_PROFILE_TYPES:
            raise ValueError(f"invalid launch profile type: {profile_type}")
        if self.launch_exe is None:
            raise ValueError("launch_exe is required")
        launch_exe = Path(self.launch_exe).expanduser().resolve()
        if not launch_exe.is_file():
            raise FileNotFoundError(launch_exe)
        wait_timeout_s = int(self.wait_timeout_s)
        if wait_timeout_s < 0:
            raise ValueError("wait_timeout_s must be >= 0")
        working_directory = (
            Path(self.working_directory).expanduser().resolve()
            if self.working_directory
            else launch_exe.parent
        )
        if not working_directory.is_dir():
            raise NotADirectoryError(working_directory)
        content_path = (
            Path(self.content_path).expanduser().resolve()
            if self.content_path
            else None
        )
        if content_path is not None and not content_path.exists():
            raise FileNotFoundError(content_path)
        monitor_exe = (
            Path(self.monitor_exe).expanduser().resolve()
            if self.monitor_exe
            else launch_exe
        )
        if monitor_exe is not None and not monitor_exe.is_file():
            raise FileNotFoundError(monitor_exe)
        return LaunchProfile(
            profile_type=profile_type,
            launch_exe=launch_exe,
            launch_args=str(self.launch_args).strip(),
            working_directory=working_directory,
            content_path=content_path,
            monitor_exe=monitor_exe,
            wait_timeout_s=wait_timeout_s,
            run_as_admin=bool(self.run_as_admin),
        )


@dataclass(slots=True)
class CreateGame:
    title: str
    executable_path: Path
    launch_args: str = ""
    working_directory: str = ""
    platform: str = ""

    def launch_profile(self) -> LaunchProfile:
        executable = Path(self.executable_path).expanduser().resolve()
        return LaunchProfile(
            profile_type="direct",
            launch_exe=executable,
            launch_args=self.launch_args,
            working_directory=Path(self.working_directory) if self.working_directory else executable.parent,
            monitor_exe=executable,
            wait_timeout_s=300,
            run_as_admin=False,
        ).normalized()


@dataclass(slots=True)
class GameRecord:
    id: str
    title: str
    sort_title: str
    description: str
    launch_profile: LaunchProfile
    platform: str
    playtime_seconds: int
    last_played_at: datetime | None
    installed_state: str

    @property
    def executable_path(self) -> Path:
        return self.launch_profile.launch_exe or Path()

    @executable_path.setter
    def executable_path(self, value: Path) -> None:
        self.launch_profile.launch_exe = Path(value)

    @property
    def launch_args(self) -> str:
        return self.launch_profile.launch_args

    @launch_args.setter
    def launch_args(self, value: str) -> None:
        self.launch_profile.launch_args = str(value)

    @property
    def working_directory(self) -> str:
        return str(self.launch_profile.working_directory or "")

    @working_directory.setter
    def working_directory(self, value: str) -> None:
        self.launch_profile.working_directory = Path(value) if value else None


@dataclass(slots=True)
class MediaAsset:
    id: str
    owner_id: str
    kind: str
    path: Path
    cache_path: Path | None
    priority: int
    source: str
