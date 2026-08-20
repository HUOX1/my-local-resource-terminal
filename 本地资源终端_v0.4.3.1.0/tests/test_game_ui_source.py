from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_game_delegate_uses_delayed_single_gif_preview():
    source = (ROOT / "app" / "ui" / "game_delegate.py").read_text(encoding="utf-8")
    assert "QMovie" in source
    assert "setInterval(250)" in source
    assert "_stop_movie" in source
    assert "PreviewGifRole" in source


def test_game_edit_dialog_is_manual_exe_only():
    source = (ROOT / "app" / "ui" / "game_edit_dialog.py").read_text(encoding="utf-8")
    assert "启动 EXE" in source
    assert "计时 EXE" in source
    assert "QFileDialog.getOpenFileName" in source
    assert "rglob" not in source
    assert "glob(\"*.exe\")" not in source


def test_game_detail_has_media_browser_and_sessions():
    source = (ROOT / "app" / "ui" / "game_detail.py").read_text(encoding="utf-8")
    assert "截图" in source
    assert "media_preview_label" in source
    assert "QMovie" in source
    assert "QListView.Flow.LeftToRight" in source
    assert "setWrapping(False)" in source
    assert "itemClicked" in source
    assert "_show_media" in source
    assert "游玩记录" in source
    assert "duration_seconds" in source


def test_game_detail_uses_qlistview_enums_for_inherited_view_configuration() -> None:
    source = Path("app/ui/game_detail.py").read_text(encoding="utf-8")
    assert "QListView.ViewMode.IconMode" in source
    assert "QListView.Flow.LeftToRight" in source


def test_game_edit_dialog_exposes_clear_cover_and_preview_flags():
    source = (ROOT / "app" / "ui" / "game_edit_dialog.py").read_text(encoding="utf-8")
    assert "remove_cover" in source
    assert "remove_preview" in source
    assert 'QPushButton("清除")' in source
    assert "_clear_cover" in source
    assert "_clear_preview" in source


def test_game_archive_dialog_uses_tabs_and_unifies_editable_archive_fields():
    source = (ROOT / "app" / "ui" / "game_detail.py").read_text(encoding="utf-8")
    assert "QTabWidget" in source
    assert 'addTab(' in source
    assert '"资料"' in source
    assert '"游玩"' in source
    assert '"媒体"' in source
    assert '"作品介绍"' in source
    assert '"我的记录"' in source
    assert '"保存"' in source
    assert "description_edit" in source
    assert "notes_edit" in source
    assert "launch_edit" in source
    assert "timing_edit" in source
    assert "cover_edit" in source
    assert "preview_edit" in source


def test_game_archive_dialog_does_not_repeat_large_cover_panel():
    source = (ROOT / "app" / "ui" / "game_detail.py").read_text(encoding="utf-8")
    assert "cover_label" not in source
    assert "_show_cover" not in source
    assert "setMinimumSize(280, 380)" not in source


def test_game_context_menu_uses_single_game_archive_entry():
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    start = source.index("    def _show_game_context_menu")
    end = source.index("    def _toggle_game_favorite", start)
    block = source[start:end]
    assert 'menu.addAction("游戏档案")' in block
    assert 'menu.addAction("查看详情")' not in block
    assert 'menu.addAction("编辑游戏")' not in block
    assert "_edit_game(record)" not in block


def test_game_archive_direct_edit_updates_description_and_personal_notes():
    page = (ROOT / "app" / "ui" / "game_archive_page.py").read_text(encoding="utf-8")
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "GameMetadataPatch(description=value)" in page
    assert "GameMetadataPatch(notes=value)" in page
    assert "def _update_game_archive_metadata" in source
    assert "self.game_archive_page.set_record(updated)" in source


def test_game_archive_can_crop_import_cover_with_existing_manual_cropper():
    page = (ROOT / "app" / "ui" / "game_archive_page.py").read_text(encoding="utf-8")
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert 'QPushButton("裁剪导入")' in page
    assert "cover_crop_requested = Signal(str)" in page
    assert "ManualCoverCropDialog" in source
    assert "GigaCoverCropper" in source
    assert "def _crop_game_archive_cover" in source


def test_game_media_preview_does_not_feed_pixmap_size_back_into_dialog_layout():
    source = (ROOT / "app" / "ui" / "game_detail.py").read_text(encoding="utf-8")
    assert "QSizePolicy" in source
    assert "self.media_preview_label.setSizePolicy(" in source
    assert "QSizePolicy.Policy.Ignored" in source
