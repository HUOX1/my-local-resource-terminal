from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from pathlib import Path

from app.models.movie import MovieRecord


def normalize_cover_match_text(value: str) -> str:
    folded = unicodedata.normalize("NFKC", str(value)).casefold()
    return "".join(character for character in folded if character.isalnum())


def movie_cover_keys(records: Iterable[MovieRecord]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()

    def add(raw: str | None) -> None:
        item = str(raw or "").strip()
        key = normalize_cover_match_text(item)
        if item and key and key not in seen:
            values.append(item)
            seen.add(key)

    for record in records:
        add(record.metadata.title)
        add(record.metadata.cover_key)
        add(record.metadata.code)
        for episode in record.episodes:
            if episode.metadata.source_name:
                source = Path(episode.metadata.source_name)
                add(source.name)
                add(source.stem)
            if episode.runtime.video_path:
                video = Path(episode.runtime.video_path)
                add(episode.runtime.video_path)
                add(video.parent.name)
                add(video.name)
                add(video.stem)
    return values
