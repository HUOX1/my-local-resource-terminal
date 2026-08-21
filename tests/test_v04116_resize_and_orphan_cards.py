from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8')


def test_poster_layout_tracks_native_resize_without_delayed_fill():
    source = read('app/ui/poster_view.py')
    assert 'self._apply_poster_layout(animate=False)' in source
    assert 'self._resize_layout_timer' not in source
    assert 'self._item_height_cache' in source
    assert 'item_heights = self._poster_item_heights()' in source
    assert 'RESIZE_REFIT_DELAY_MS' not in source


def test_poster_scroll_returns_to_direct_per_pixel_behavior():
    source = read('app/ui/poster_view.py')
    assert 'def wheelEvent' in source
    assert '_scroll_target' not in source
    assert '_scroll_position' in source
    assert '_scroll_tick' not in source
    main = read('app/ui/main_window.py')
    assert 'setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)' in main
    assert 'verticalScrollBar().setSingleStep(28)' in main


def test_offline_movie_posters_are_rendered_grayscale():
    source = read('app/ui/movie_delegate.py')
    assert 'def _grayscale_pixmap' in source
    assert 'MovieListModel.AvailabilityRole' in source
    assert 'availability != "available"' in source
    assert '_grayscale_pixmap(pixmap)' in source


def test_uninstalled_game_posters_are_grayscale_and_do_not_start_gif_preview():
    source = read('app/ui/game_delegate.py')
    assert 'def _grayscale_pixmap' in source
    assert 'GameListModel.InstalledRole' in source
    assert 'if not bool(index.data(GameListModel.InstalledRole)):' in source
    assert '_grayscale_pixmap(pixmap)' in source
    start_preview = source.split('def _start_hover_preview', 1)[1].split('def _stop_movie', 1)[0]
    assert 'GameListModel.InstalledRole' in start_preview
    assert 'return' in start_preview


def test_release_is_v04116():
    assert 'version = "0.4.3.1.1"' in read('pyproject.toml')
    assert 'v0.4.3.1.1' in read('app/ui/main_window.py')
    assert 'v0.4.3.1.1' in read('app/ui/app_chrome.py')
