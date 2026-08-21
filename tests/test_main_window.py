import pytest

pytest.importorskip("PySide6")

from pathlib import Path

from app.config.settings import AppSettings
from app.ui.main_window import MainWindow


class FakeCatalog:
    def list_movies(self, *args, **kwargs):
        return []

    def common_tags(self, limit=30):
        return []


class FakeGameCatalog:
    def list_games(self, *args, **kwargs):
        return []

    def common_tags(self, limit=30):
        return []


class FakeScanner:
    pass


def test_main_window_uses_top_resource_switch_filter_and_three_views(qtbot, tmp_path: Path):
    settings = AppSettings(tmp_path / "data", tmp_path / "covers", [])
    window = MainWindow(
        FakeCatalog(),
        FakeScanner(),
        settings,
        None,
        None,
        None,
        game_catalog=FakeGameCatalog(),
    )
    qtbot.addWidget(window)

    assert hasattr(window, "sidebar")
    assert window.sidebar.objectName() == "sidebar"
    assert window.movie_library_button.text() == "影片"
    assert window.game_library_button.text() == "游戏"
    assert window.filter_combo.count() > 0
    assert window.view_stack.count() == 3
    assert window.cover_tools_button.text() == "封面工具"
    assert window.grid_delegate.POSTER_WIDTH == 180

    window.switch_library("games")
    assert window.current_library == "games"
    assert window.add_game_button.isVisible() is True
    assert window.cover_tools_button.isVisible() is False
