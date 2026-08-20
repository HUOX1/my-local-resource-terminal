from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_poster_layout_exposes_full_width_cell_helper():
    from app.ui.poster_layout import justified_poster_cell_width

    # Seven fixed 190px cards fit, but the remaining width should be distributed
    # into their cells instead of leaving a conspicuous empty slot on the right.
    width = justified_poster_cell_width(1500, card_width=190, spacing=10)
    assert width == 202


def test_poster_wall_keeps_hidden_scrollbars_and_immediate_resize_fixed_cards():
    source = read("app/ui/poster_view.py")
    assert "class PosterWallListView(QListView)" in source
    assert "QTimer" in source
    assert "self._apply_poster_layout(animate=False)" in source
    assert "self._resize_layout_timer" not in source
    assert "poster_wall_targets" in source
    assert "delegate.set_cell_width(delegate.CARD_WIDTH)" in source
    assert "self.setPositionForIndex(" in source
    assert "def wheelEvent" in source
    assert "ScrollBarAlwaysOff" in source

    main = read("app/ui/main_window.py")
    assert "self.grid_view = PosterWallListView()" in main
    assert "self.game_view = PosterWallListView()" in main
    assert "set_poster_delegate(self.grid_delegate)" in main
    assert "set_poster_delegate(self.game_delegate)" in main


def test_sidebar_is_two_state_with_icon_only_minimum():
    source = read("app/ui/main_window.py")
    splitter = read("app/ui/sidebar_splitter.py")
    assert "TwoStateSidebarSplitter(Qt.Orientation.Horizontal)" in source
    assert "self.sidebar.setMinimumWidth(72)" in source
    assert "self.sidebar.setMaximumWidth(FlatTokens.SIDEBAR_WIDTH)" in source
    assert "sidebar_width_changed.connect(self._update_sidebar_motion)" in source
    assert "COMPACT_WIDTH = 72" in splitter
    assert "toggle_sidebar" in splitter
    assert "mouseMoveEvent" in splitter

    identity = read("app/ui/identity_shell.py")
    assert "def set_motion_progress(" in identity


def test_game_archive_is_directly_editable_without_legacy_edit_button():
    source = read("app/ui/game_archive_page.py")
    assert "metadata_patch_requested = Signal(str, object)" in source
    assert "cover_change_requested = Signal(str)" in source
    assert "preview_change_requested = Signal(str)" in source
    assert "launch_exe_browse_requested = Signal(str)" in source
    assert "screenshot_dir_browse_requested = Signal(str)" in source
    assert "InlineEditableField" in source
    assert "StarRatingEditor" in source
    assert "编辑档案" not in source

    main = read("app/ui/main_window.py")
    assert "game_archive_page.metadata_patch_requested.connect(self._update_game_archive_metadata)" in main
    assert "game_archive_page.cover_change_requested.connect(self._change_game_archive_cover)" in main
    assert "game_archive_page.preview_change_requested.connect(self._change_game_archive_preview)" in main
    assert "game_archive_page.edit_requested.connect" not in main
    assert "def _edit_game_archive(" not in main


def test_release_is_v04114():
    assert 'version = "0.4.3.0.3"' in read("pyproject.toml")
    assert "v0.4.3.0.3" in read("app/ui/main_window.py")
    assert "v0.4.3.0.3" in read("app/ui/app_chrome.py")
