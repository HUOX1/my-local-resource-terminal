from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from app.models.movie import MovieEpisodeRecord


@dataclass(slots=True, frozen=True)
class EpisodeAction:
    episode_uuid: str
    label: str
    enabled: bool


def build_episode_actions(episodes: list[MovieEpisodeRecord]) -> list[EpisodeAction]:
    ordered = sorted(
        episodes,
        key=lambda episode: (
            episode.metadata.display_order,
            episode.metadata.source_name.casefold(),
            episode.metadata.uuid,
        ),
    )
    number_counts = Counter(
        (episode.metadata.season_number, episode.metadata.episode_number)
        for episode in ordered
        if episode.metadata.episode_number is not None
    )
    actions: list[EpisodeAction] = []
    for episode in ordered:
        identity = (
            episode.metadata.season_number,
            episode.metadata.episode_number,
        )
        number = (
            episode.metadata.episode_number
            if episode.metadata.episode_number is not None
            and number_counts[identity] == 1
            else episode.metadata.display_order
        )
        actions.append(
            EpisodeAction(
                episode_uuid=episode.metadata.uuid,
                label=f"第 {number} 集",
                enabled=(
                    episode.runtime.availability_status == "available"
                    and bool(episode.runtime.video_path)
                ),
            )
        )
    return actions
