from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_poster_wall_double_click_opens_archive_pages_instead_of_launching_or_playing():
    source = read("app/ui/main_window.py")
    assert "self.grid_view.doubleClicked.connect(lambda index: self._open_detail(self.grid_model.movie_at(index.row())))" in source
    assert "self.table_view.doubleClicked.connect(lambda index: self._open_detail(self.table_model.movie_at(index.row())))" in source
    assert "self.game_view.doubleClicked.connect(lambda index: self._open_game_detail(self.game_model.game_at(index.row())))" in source
    assert "self.grid_view.doubleClicked.connect(lambda index: self._play_record" not in source
    assert "self.table_view.doubleClicked.connect(lambda index: self._play_record" not in source
    assert "self.game_view.doubleClicked.connect(lambda index: self._launch_game" not in source


def test_flat_pro_final_polish_keeps_archive_editing_content_like_and_cards_quiet():
    source = read("app/ui/flat_theme.py")
    assert "QLabel#movieArchiveTitle:hover, QLabel#movieArchiveMeta:hover, QLabel#movieArchiveEditableValue:hover" in source
    assert "border-bottom: 1px solid {t.BORDER};" in source
    assert "QLineEdit#movieArchiveInlineEdit:focus" in source
    assert "QLineEdit#movieArchiveTitleEdit:focus" in source
    assert "QTextEdit#movieArchiveNotesEdit:focus" in source
    assert "background: transparent;\n    border: 0;\n    border-bottom: 1px solid {t.ACCENT};" in source
    assert "QFrame#movieArchiveHero, QFrame#movieArchiveCard" in source
    assert "QFrame#gameArchiveCard" in source
    assert source.count("border: 1px solid {t.CHROME_BORDER};") >= 4
    assert "QLabel#movieArchiveSectionTitle" in source
    assert "QLabel#gameArchiveSectionTitle" in source
    assert source.count("font-size: 12px;") >= 4


def test_menus_scrollbars_settings_and_focus_states_are_quieter():
    source = read("app/ui/flat_theme.py")
    menu_selected = source.split("QMenu::item:selected {{", 1)[1].split("}}", 1)[0]
    assert "background: {t.SURFACE_HOVER};" in menu_selected
    assert "color: {t.TEXT_PRIMARY};" in menu_selected
    assert "background: {t.ACCENT};" not in menu_selected
    assert "QScrollBar:vertical" in source
    assert "width: 7px;" in source
    assert "QScrollBar::handle:vertical" in source
    assert "background: {t.BORDER};" in source
    assert "QPushButton:focus" in source
    assert "QLineEdit:focus, QComboBox:focus" in source
    assert "QWidget#settingsNav" in source
    assert "QWidget#settingsPage" in source


def test_movie_archive_removes_persistent_auto_save_instruction_from_content():
    source = read("app/ui/movie_archive_page.py")
    assert 'QLabel("移开焦点自动保存")' not in source
    assert 'self.notes_edit.setToolTip("移开焦点自动保存")' in source


def test_v04112_is_visible_in_project_window_and_chrome():
    assert 'version = "0.4.3.0.3"' in read("pyproject.toml")
    assert "v0.4.3.0.3" in read("app/ui/main_window.py")
    assert "v0.4.3.0.3" in read("app/ui/app_chrome.py")
