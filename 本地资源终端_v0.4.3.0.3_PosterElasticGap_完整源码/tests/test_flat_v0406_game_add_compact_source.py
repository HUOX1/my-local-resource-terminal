from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_game_add_dialog_is_single_page_and_keeps_three_required_fields_together():
    source = read("app/ui/game_edit_dialog.py")
    build_start = source.index("    def _build_ui")
    section_start = source.index("    def _section_card", build_start)
    build_block = source[build_start:section_start]

    assert "QTabWidget" not in build_block
    assert 'form.addRow("游戏名称 *", self.title_edit)' in build_block
    assert 'form.addRow("启动 EXE *", self._path_row(self.launch_edit, self._browse_launch))' in build_block
    assert 'form.addRow("计时 EXE *", self._path_row(self.timing_edit, self._browse_timing))' in build_block


def test_game_add_dialog_hides_archive_only_fields_but_keeps_rating():
    source = read("app/ui/game_edit_dialog.py")
    build_start = source.index("    def _build_ui")
    section_start = source.index("    def _section_card", build_start)
    build_block = source[build_start:section_start]

    for label in ["系列", "开发商", "发行商", "发行日期", "标签", "收藏", "备注"]:
        assert f'"{label}"' not in build_block

    assert 'form.addRow("评分", self.rating_spin)' in build_block


def test_hidden_archive_fields_default_empty_for_new_game_and_are_not_read_from_widgets():
    source = read("app/ui/game_edit_dialog.py")
    accept_start = source.index("    def _accept_validated")
    accept_block = source[accept_start:]

    assert "series=self._hidden_series" in accept_block
    assert "developer=self._hidden_developer" in accept_block
    assert "publisher=self._hidden_publisher" in accept_block
    assert "release_date=self._hidden_release_date" in accept_block
    assert "tags=list(self._hidden_tags)" in accept_block
    assert "favorite=self._hidden_favorite" in accept_block
    assert "notes=self._hidden_notes" in accept_block
    assert "series_edit" not in accept_block
    assert "notes_edit" not in accept_block


def test_version_advances_to_v0406():
    source = read("app/ui/main_window.py")
    assert 'self.setWindowTitle("本地资源终端 · v0.4.3.0.3")' in source

    pyproject = read("pyproject.toml")
    assert 'version = "0.4.3.0.3"' in pyproject
