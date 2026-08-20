from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_poster_delegate_contains_no_text_badges() -> None:
    source = (ROOT / "app" / "ui" / "movie_delegate.py").read_text(encoding="utf-8")
    assert "badges" not in source
    assert '"字"' not in source
    assert "TitleRole" not in source


def test_double_click_enters_archive_pages_instead_of_launching_content() -> None:
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "grid_view.doubleClicked.connect(lambda index: self._open_detail" in source
    assert "table_view.doubleClicked.connect(lambda index: self._open_detail" in source
    assert "game_view.doubleClicked.connect(lambda index: self._open_game_detail" in source
    assert "grid_view.doubleClicked.connect(lambda index: self._play_record" not in source
    assert "table_view.doubleClicked.connect(lambda index: self._play_record" not in source
    assert "game_view.doubleClicked.connect(lambda index: self._launch_game" not in source


def test_flat_sidebar_and_top_filter_coexist() -> None:
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "sidebar_toggle_button" not in source
    assert "self.sidebar" in source
    assert "TwoStateSidebarSplitter" in source
    assert 'NavigationButton("影片")' in source
    assert 'NavigationButton("游戏")' in source
    assert "filter_combo" in source


def test_cover_tool_is_renamed_and_preferences_are_wired() -> None:
    dialog_source = (ROOT / "app" / "ui" / "giga_cover_dialog.py").read_text(encoding="utf-8")
    main_source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    bootstrap_source = (ROOT / "app" / "bootstrap.py").read_text(encoding="utf-8")

    assert 'setWindowTitle("封面处理")' in dialog_source
    assert "中间深色 Spine" not in dialog_source
    assert "cover_tool_source_dir" in main_source
    assert "cover_tool_margin_px" in main_source
    assert "cover_tool_state_changed" in main_source
    assert "cover_tool_state_changed.connect" in bootstrap_source


def test_movie_and_game_view_preferences_persist_independently() -> None:
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    bootstrap = (ROOT / "app" / "bootstrap.py").read_text(encoding="utf-8")
    assert "sort_combo" in source
    assert "sort_direction_button" in source
    assert "movie_view_state_changed" in source
    assert "game_view_state_changed" in source
    assert "sort=self.settings.sort_key" in source
    assert "descending=self.settings.sort_desc" in source
    assert "sort=self.settings.game_sort_key" in source
    assert "descending=self.settings.game_sort_desc" in source
    assert "movie_view_state_changed.connect" in bootstrap
    assert "game_view_state_changed.connect" in bootstrap
