from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8')


def test_poster_cell_width_accounts_for_outer_spacing_so_eighth_slot_fits():
    from app.ui.poster_layout import justified_poster_cell_width

    # Real maximized geometry leaves room for 8 fixed 190px cells once QListView's
    # leading/trailing spacing is accounted for. The old 197px cell forces Qt back
    # to 7 columns; 194px keeps all eight on the row.
    assert justified_poster_cell_width(1646, card_width=190, spacing=10) == 194


def test_main_splitter_seam_stays_invisible_with_centered_toggle_handle():
    theme = read('app/ui/flat_theme.py')
    main = read('app/ui/main_window.py')
    assert 'QSplitter#mainSplitter::handle {{\n    background: transparent;' in theme
    assert 'QSplitter#mainSplitter::handle:hover {{\n    background: transparent;' in theme
    assert 'self.main_splitter.setHandleWidth(TwoStateSidebarSplitter.HANDLE_WIDTH)' in main
    splitter = read('app/ui/sidebar_splitter.py')
    assert 'HANDLE_WIDTH = 36' in splitter
    assert 'def paintEvent(' in splitter
    assert 'QPushButton#sidebarToggleHandle' not in theme
    assert 'TwoStateSidebarSplitter' in main


def test_poster_scroll_experiment_is_reverted_to_stable_direct_pixel_scroll():
    source = read('app/ui/poster_view.py')
    assert 'QPropertyAnimation' not in source
    assert 'def wheelEvent' in source
    assert '_scroll_target' not in source
    assert '_scroll_position' in source
    main = read('app/ui/main_window.py')
    assert 'setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)' in main
    assert 'verticalScrollBar().setSingleStep(28)' in main


def test_release_is_v04115():
    assert 'version = "0.4.3.1.1"' in read('pyproject.toml')
    assert 'v0.4.3.1.1' in read('app/ui/main_window.py')
    assert 'v0.4.3.1.1' in read('app/ui/app_chrome.py')
