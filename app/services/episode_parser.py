from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class EpisodeIdentity:
    season_number: int | None
    episode_number: int | None
    reliable: bool


_SEASON_EPISODE = re.compile(
    r"(?:^|[\s_.-])s(?P<season>\d{1,3})[\s_.-]*e(?P<episode>\d{1,4})(?!\d)",
    re.IGNORECASE,
)
_EXPLICIT_EPISODE = re.compile(
    r"(?:^|[\s_.-])ep?(?P<episode>\d{1,4})$",
    re.IGNORECASE,
)
_DELIMITED_TRAILING_NUMBER = re.compile(r"[\s_.-](?P<episode>\d{1,4})$")
_PURE_NUMBER = re.compile(r"^(?P<episode>\d{1,4})$")
_NATURAL_PART = re.compile(r"(\d+)")


def parse_episode_identity(stem: str) -> EpisodeIdentity:
    value = str(stem).strip()
    match = _SEASON_EPISODE.search(value)
    if match is not None:
        return EpisodeIdentity(
            season_number=int(match.group("season")),
            episode_number=int(match.group("episode")),
            reliable=True,
        )

    match = _EXPLICIT_EPISODE.search(value)
    if match is not None:
        return EpisodeIdentity(None, int(match.group("episode")), True)

    match = _DELIMITED_TRAILING_NUMBER.search(value)
    if match is not None:
        return EpisodeIdentity(None, int(match.group("episode")), True)

    match = _PURE_NUMBER.fullmatch(value)
    if match is not None:
        return EpisodeIdentity(None, int(match.group("episode")), True)

    return EpisodeIdentity(None, None, False)


def natural_name_key(name: str) -> tuple[tuple[int, object], ...]:
    parts = _NATURAL_PART.split(str(name).casefold())
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in parts
        if part
    )
