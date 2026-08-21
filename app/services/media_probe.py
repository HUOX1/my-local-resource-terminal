from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from app.services.subprocess_utils import hidden_console_kwargs


@dataclass(slots=True, frozen=True)
class MediaInfo:
    duration: float | None
    width: int | None
    height: int | None
    video_codec: str | None
    audio_codec: str | None
    embedded_subtitle_count: int = 0


class MediaProbe:
    def __init__(self, ffprobe_path: str = "ffprobe") -> None:
        self.ffprobe_path = ffprobe_path

    def probe(self, path: Path) -> MediaInfo | None:
        cmd = [
            self.ffprobe_path,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ]
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                timeout=20,
                check=False,
                **hidden_console_kwargs(),
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if completed.returncode != 0:
            return None
        try:
            stdout = completed.stdout.decode("utf-8-sig", errors="replace")
            return parse_ffprobe_payload(json.loads(stdout))
        except (ValueError, TypeError, json.JSONDecodeError):
            return None


def parse_ffprobe_payload(payload: dict[str, Any]) -> MediaInfo:
    streams = list(payload.get("streams") or [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    subtitles = sum(1 for s in streams if s.get("codec_type") == "subtitle")
    raw_duration = (payload.get("format") or {}).get("duration")
    duration: float | None
    try:
        duration = float(raw_duration) if raw_duration is not None else None
    except (TypeError, ValueError):
        duration = None
    return MediaInfo(
        duration=duration,
        width=_as_int(video.get("width")),
        height=_as_int(video.get("height")),
        video_codec=_as_str(video.get("codec_name")),
        audio_codec=_as_str(audio.get("codec_name")),
        embedded_subtitle_count=subtitles,
    )


def compute_subtitle_status(
    external_subtitles: Sequence[Path], media_info: MediaInfo | None
) -> bool:
    return bool(external_subtitles) or bool(media_info and media_info.embedded_subtitle_count > 0)


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None
