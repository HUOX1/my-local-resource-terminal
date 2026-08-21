from app.models.movie import (
    MovieEpisodeMetadata,
    MovieEpisodeRecord,
    MovieEpisodeRuntime,
)
from app.ui.movie_episode_presenter import build_episode_actions


def _episode(
    uuid: str,
    order: int,
    number: int | None,
    *,
    available: bool = True,
) -> MovieEpisodeRecord:
    return MovieEpisodeRecord(
        MovieEpisodeMetadata(uuid, order, episode_number=number),
        MovieEpisodeRuntime(
            video_path=f"/media/{uuid}.mkv",
            availability_status="available" if available else "offline",
        ),
    )


def test_episode_actions_use_unique_episode_numbers_and_runtime_availability() -> None:
    actions = build_episode_actions(
        [
            _episode("third", 3, 10, available=False),
            _episode("first", 1, 1),
            _episode("second", 2, 2),
        ]
    )

    assert [(item.episode_uuid, item.label, item.enabled) for item in actions] == [
        ("first", "第 1 集", True),
        ("second", "第 2 集", True),
        ("third", "第 10 集", False),
    ]


def test_duplicate_or_missing_episode_numbers_fall_back_to_display_order() -> None:
    actions = build_episode_actions(
        [
            _episode("one-a", 1, 1),
            _episode("one-b", 2, 1),
            _episode("unknown", 3, None),
        ]
    )

    assert [item.label for item in actions] == ["第 1 集", "第 2 集", "第 3 集"]
