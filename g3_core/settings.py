
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path

DEFAULT_START_SECTIONS = {"games", "movies", "comics", "music", "search", "system"}


@dataclass(slots=True)
class TerminalSettings:
    settings_schema: int = 2
    display_mode: str = "borderless"
    monitor: int = 0
    preview_audio: bool = True
    preview_volume: float = 0.25
    preview_auto_play: bool = True
    theme_music: bool = True
    theme_music_volume: float = 0.35
    restore_last_section: bool = False
    default_start_section: str = "games"
    restore_last_item: bool = True
    current_theme: str = "classic_cyan"
    ffmpeg_path: str = "ffmpeg"
    godot_executable: str = ""

    @classmethod
    def default(cls) -> "TerminalSettings":
        return cls()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "TerminalSettings":
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ValueError(f"Unknown settings key(s): {', '.join(unknown)}")
        settings = cls(**payload)
        settings._validate()
        return settings

    @classmethod
    def load(cls, path: Path) -> "TerminalSettings":
        if not path.exists():
            return cls.default()
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("settings root must be an object")
        payload = dict(payload)
        if "settings_schema" not in payload:
            if payload.get("current_theme") == "classic_violet":
                payload["current_theme"] = "classic_cyan"
            payload["settings_schema"] = 2
        return cls.from_dict(payload)

    def save(self, path: Path) -> None:
        self._validate()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        json.loads(temporary.read_text(encoding="utf-8"))
        temporary.replace(path)

    def _validate(self) -> None:
        if self.display_mode not in {"borderless", "windowed", "fullscreen"}:
            raise ValueError(f"invalid display_mode: {self.display_mode}")
        if self.default_start_section not in DEFAULT_START_SECTIONS:
            raise ValueError(f"invalid default_start_section: {self.default_start_section}")
        if self.monitor < 0:
            raise ValueError("monitor must be >= 0")
        if not 0.0 <= self.preview_volume <= 1.0:
            raise ValueError("preview_volume must be between 0 and 1")
        if not 0.0 <= self.theme_music_volume <= 1.0:
            raise ValueError("theme_music_volume must be between 0 and 1")
