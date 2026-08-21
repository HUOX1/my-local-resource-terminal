from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'app' / 'ui' / 'main_window.py').read_text(encoding='utf-8')


def _section(start: str, end: str) -> str:
    return SOURCE.split(start, 1)[1].split(end, 1)[0]


def test_single_movie_context_menu_no_longer_exposes_favorite_or_watched_actions():
    section = _section('    def _show_movie_context_menu', '    def _ensure_context_row_selected')
    assert 'fav_action' not in section
    assert 'watched_action' not in section
    assert 'MovieMetadataPatch(favorite=' not in section
    assert 'MovieMetadataPatch(watched=' not in section


def test_movie_batch_menu_no_longer_exposes_favorite_or_watched_actions():
    section = _section('    def _populate_batch_menu', '    def _batch_tags')
    assert 'MovieMetadataPatch(favorite=' not in section
    assert 'MovieMetadataPatch(watched=' not in section
    assert '标记已观看' not in section
    assert '标记未观看' not in section
