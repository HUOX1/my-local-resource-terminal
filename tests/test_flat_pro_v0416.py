from pathlib import Path


def read(rel: str) -> str:
    return Path(rel).read_text(encoding="utf-8")


def test_version_bumped_to_v0416() -> None:
    assert 'version = "0.4.3.1.1"' in read("pyproject.toml")
    assert 'v0.4.3.1.1' in read("app/ui/main_window.py")
    assert 'v0.4.3.1.1' in read("app/ui/app_chrome.py")


def test_content_header_is_removed_and_toolbar_is_first() -> None:
    source = read("app/ui/main_window.py")
    assert 'self.library_title_label' not in source
    assert 'self.library_count_label' not in source
    assert 'setObjectName("libraryTitle")' not in source
    assert 'setObjectName("libraryCountBadge")' not in source
    assert 'toolbar = QWidget()' not in source
    assert source.index('self.view_stack = QStackedWidget()') < source.index('self.content_status_bar = QWidget()')


def test_counts_live_only_in_bottom_content_status() -> None:
    source = read("app/ui/main_window.py")
    assert 'self._set_catalog_status(self._folder_status_text(len(movies), "部影片"))' in source
    assert 'self._set_catalog_status(self._folder_status_text(len(games), "个游戏"))' in source
    assert 'library_count_label.setText' not in source


def test_flat_pro_toolbar_moves_up_without_header_gap() -> None:
    source = read("app/ui/main_window.py")
    assert 'content_layout.setContentsMargins(22, 10, 18, 14)' in source
    theme = read("app/ui/flat_theme.py")
    assert 'QLabel#libraryTitle' not in theme
    assert 'QLabel#libraryCountBadge' not in theme
