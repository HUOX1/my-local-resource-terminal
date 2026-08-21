import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QPushButton

from app.models.movie import (
    MovieEpisodeMetadata,
    MovieEpisodeRecord,
    MovieEpisodeRuntime,
    MovieMetadata,
    MovieRecord,
    MovieRuntime,
)
from app.ui.movie_archive_page import MovieArchivePage
from app.ui.movie_episode_dialog import MovieEpisodeDialog


def _record(count: int) -> MovieRecord:
    episodes = [
        MovieEpisodeRecord(
            MovieEpisodeMetadata(
                uuid=f"episode-{index}",
                display_order=index,
                episode_number=index,
                source_name=f"SHOW_{index:02d}.mkv",
            ),
            MovieEpisodeRuntime(
                video_path=f"/media/SHOW_{index:02d}.mkv",
                availability_status=("offline" if index == count else "available"),
            ),
        )
        for index in range(1, count + 1)
    ]
    runtime = MovieRuntime(
        video_path=episodes[0].runtime.video_path if count == 1 else None,
        availability_status="available",
    )
    metadata = MovieMetadata(
        uuid="work",
        cover_key="SHOW",
        code="SHOW",
        episodes=[episode.metadata for episode in episodes],
    )
    return MovieRecord(metadata, runtime, episodes)


def test_single_episode_keeps_existing_archive_controls(qtbot) -> None:
    page = MovieArchivePage()
    qtbot.addWidget(page)

    page.set_record(_record(1))

    assert page.episode_card.isHidden()
    assert page.play_button.isHidden() is False
    assert page.media_card.isHidden() is False


def test_multi_episode_shows_compact_buttons_and_emits_selected_child(qtbot) -> None:
    page = MovieArchivePage()
    qtbot.addWidget(page)
    page.set_record(_record(3))
    buttons = [
        button
        for button in page.findChildren(QPushButton)
        if button.objectName() == "movieEpisodeButton"
    ]

    assert page.episode_card.isHidden() is False
    assert page.play_button.isHidden()
    assert page.media_card.isHidden()
    assert [button.text() for button in buttons] == ["第 1 集", "第 2 集", "第 3 集"]
    assert buttons[-1].isEnabled() is False
    assert page.episode_details_button.text() == ""
    assert page.episode_details_button.toolTip() == "剧集详情"

    with qtbot.waitSignal(page.episode_play_requested) as signal:
        qtbot.mouseClick(buttons[0], Qt.MouseButton.LeftButton)
    assert signal.args == ["work", "episode-1"]


def test_episode_details_dialog_lists_every_episode_card(qtbot) -> None:
    dialog = MovieEpisodeDialog(_record(3))
    qtbot.addWidget(dialog)

    cards = [
        card
        for card in dialog.findChildren(QFrame)
        if card.objectName() == "movieEpisodeDetailCard"
    ]

    assert len(cards) == 3
