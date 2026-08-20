from pathlib import Path


def read(rel: str) -> str:
    return Path(rel).read_text(encoding="utf-8")


def test_version_bumped_to_v0417() -> None:
    assert 'version = "0.4.3.0.3"' in read("pyproject.toml")
    assert 'v0.4.3.0.3' in read("app/ui/main_window.py")
    assert 'v0.4.3.0.3' in read("app/ui/app_chrome.py")


def test_top_toolbar_is_removed_and_low_frequency_controls_live_in_popup() -> None:
    source = read("app/ui/main_window.py")
    assert 'toolbar = QWidget()' not in source
    assert 'setObjectName("toolbar")' not in source
    assert 'self.library_tools_popup' in source
    assert 'setObjectName("libraryToolsPopup")' in source
    assert 'self.search_edit = QLineEdit()' in source
    assert 'self.filter_combo = QComboBox()' in source
    assert 'self.sort_combo = QComboBox()' in source
    assert 'self.view_button = QPushButton("列表视图")' in source
    assert 'self.rescan_button = QPushButton("重新扫描")' in source
    assert 'self.cover_tools_button = QPushButton("封面工具")' in source


def test_bottom_status_bar_owns_count_search_and_add_actions() -> None:
    source = read("app/ui/main_window.py")
    assert 'self.content_status_icon = QLabel()' in source
    assert 'kind = "cartridge" if self.current_library == "games" else "movie"' in source
    assert 'self.library_tools_button.setIcon(flat_icon("search"))' in source
    assert 'self.add_game_button.setIcon(flat_icon("add"))' in source
    assert 'self.add_game_button.setToolTip("添加游戏")' in source
    assert 'self.add_game_button.setVisible(False)' in source
    assert 'self.add_game_button.setVisible(True)' in source


def test_catalog_count_remains_the_default_bottom_status() -> None:
    source = read("app/ui/main_window.py")
    assert 'self._catalog_status_text' in source
    assert 'self._set_catalog_status(self._folder_status_text(len(movies), "部影片"))' in source
    assert 'self._set_catalog_status(self._folder_status_text(len(games), "个游戏"))' in source
    assert 'self.content_status_label.setText(self._catalog_status_text)' in source


def test_movie_context_menu_uses_archive_wording() -> None:
    source = read("app/ui/main_window.py")
    assert 'menu.addAction("影片档案")' in source
    assert 'menu.addAction("查看详情")' not in source


def test_flat_icons_include_search_and_fc_cartridge() -> None:
    source = read("app/ui/flat_icons.py")
    assert 'elif kind == "search":' in source
    assert 'elif kind == "cartridge":' in source
