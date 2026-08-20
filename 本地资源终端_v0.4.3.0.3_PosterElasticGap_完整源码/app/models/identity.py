from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LocalIdentity:
    username: str
    avatar_filename: str | None = None
    frame_filename: str | None = None
