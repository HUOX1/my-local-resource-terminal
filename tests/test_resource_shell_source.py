from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_main_window_uses_flat_sidebar_resource_switcher():
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert 'NavigationButton("影片")' in source
    assert 'NavigationButton("游戏")' in source
    assert "filter_combo" in source
    assert "TwoStateSidebarSplitter" in source
    assert "sidebar_toggle_button" not in source
    assert "self.sidebar" in source
    assert 'setObjectName("sidebar")' in source


def test_game_wall_launches_on_double_click_and_tracks_live_session():
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "game_view.doubleClicked.connect" in source
    assert "_launch_game" in source
    assert "game_session_service.request_launch" in source
    assert "game_session_service.poll" in source
    assert "game_session_service.checkpoint" in source
    assert "正在记录" in source


def test_live_game_timer_uses_content_local_status_widget():
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert 'self.active_game_label.setObjectName("contentStatusActiveGame")' in source
    assert 'status_layout.addWidget(self.active_game_label)' in source
    assert "self.statusBar().addPermanentWidget(self.active_game_label)" not in source
    assert "root.addWidget(self.active_game_label)" not in source


def test_switching_library_clears_search_and_game_has_add_button():
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "self.search_edit.clear()" in source
    assert 'self.add_game_button = QPushButton()' in source
    assert 'self.add_game_button.setToolTip("添加游戏")' in source
