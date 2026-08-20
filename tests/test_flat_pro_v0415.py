from pathlib import Path


def read(rel: str) -> str:
    return Path(rel).read_text(encoding="utf-8")


def test_version_bumped_to_v0415() -> None:
    assert 'version = "0.4.3.0.3"' in read("pyproject.toml")
    assert 'v0.4.3.0.3' in read("app/ui/main_window.py")
    assert 'v0.4.3.0.3' in read("app/ui/app_chrome.py")


def test_content_status_is_local_to_content_surface() -> None:
    source = read("app/ui/main_window.py")
    assert 'setObjectName("contentStatusBar")' in source
    assert 'setObjectName("contentStatusText")' in source
    assert 'self.statusBar().setVisible(False)' in source
    assert 'self.statusBar().addPermanentWidget' not in source
    assert 'self.statusBar().showMessage' not in source
    assert 'def _show_status_message' in source


def test_library_count_is_kept_in_the_content_status_bar() -> None:
    source = read("app/ui/main_window.py")
    assert 'setObjectName("contentStatusBar")' in source
    assert 'self._set_catalog_status(self._folder_status_text(len(movies), "部影片"))' in source
    assert 'self._set_catalog_status(self._folder_status_text(len(games), "个游戏"))' in source
    assert 'setObjectName("libraryCountBadge")' not in source


def test_popup_controls_have_flat_pro_specific_roles() -> None:
    source = read("app/ui/main_window.py")
    assert 'self.search_edit.setObjectName("toolbarSearch")' in source
    assert 'self.filter_combo.setObjectName("toolbarCombo")' in source
    assert 'self.sort_combo.setObjectName("toolbarCombo")' in source
    theme = read("app/ui/flat_theme.py")
    assert 'QLineEdit#toolbarSearch' in theme
    assert 'QComboBox#toolbarCombo' in theme
    assert 'QFrame#libraryToolsPopup' in theme
    assert 'QWidget#contentStatusBar' in theme
    assert 'QLabel#libraryCountBadge' not in theme


def test_flat_pro_content_accents_are_less_aggressive() -> None:
    registry = read("app/config/theme_registry.py")
    assert 'accent="#4F7FD8"' in registry
    assert 'accent_hover="#5E8CE4"' in registry
    assert 'accent_pressed="#4069B7"' in registry
    assert 'QWidget#sidebar {{\n    background: {t.SURFACE};\n    border: 0;' in read("app/ui/flat_theme.py")


def test_flat_pro_poster_selection_uses_thin_soft_accent() -> None:
    movie = read("app/ui/movie_delegate.py")
    game = read("app/ui/game_delegate.py")
    for source in (movie, game):
        assert 'FlatTokens.NAV_STYLE == "sunken_card"' in source
        assert 'FlatTokens.ACCENT_SOFT_TEXT' in source
        assert 'selected_width = 1' in source
