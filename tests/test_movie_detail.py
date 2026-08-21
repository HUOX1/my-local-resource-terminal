import pytest

pytest.importorskip("PySide6")

from app.models.movie import MovieMetadata, MovieRecord, MovieRuntime
from app.ui.movie_detail import MovieDetailDialog


def test_offline_movie_disables_play_but_keeps_editing(qtbot):
    record = MovieRecord(MovieMetadata.new("A", "A"), MovieRuntime(availability_status="offline"))
    dialog = MovieDetailDialog(record, None, None, None, None, None)
    qtbot.addWidget(dialog)
    assert dialog.play_button.isEnabled() is False
    assert dialog.relink_button.isEnabled() is True
    assert dialog.title_edit.isEnabled() is True
