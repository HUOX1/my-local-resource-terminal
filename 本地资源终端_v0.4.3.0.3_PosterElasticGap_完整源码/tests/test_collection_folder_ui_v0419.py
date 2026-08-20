from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_flat_icons_has_search_add_magnifier_plus():
    source = (ROOT / "app" / "ui" / "flat_icons.py").read_text(encoding="utf-8")
    assert 'elif kind == "search_add"' in source
    assert "painter.drawEllipse" in source
    assert "size / 2" in source


def test_main_window_puts_one_level_folder_controls_inside_magnifier_popup():
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert 'QLabel("分类文件夹")' in source
    assert "self.folder_combo = QComboBox()" in source
    assert 'flat_icon("search_add")' in source
    assert 'setToolTip("新建分类文件夹")' in source
    assert "def _create_collection_folder" in source
    assert "def _rename_collection_folder" in source
    assert "def _delete_collection_folder" in source


def test_main_window_filters_current_library_by_selected_folder_and_shows_status_name():
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "folder_id=self._current_folder_id()" in source
    assert "def _folder_status_text" in source
    assert "self._current_folder_ids" in source


def test_context_menus_can_move_movie_and_game_records_to_folder():
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert 'addMenu("移动到文件夹")' in source
    assert "def _populate_move_to_folder_menu" in source
    assert "def _move_records_to_folder" in source
