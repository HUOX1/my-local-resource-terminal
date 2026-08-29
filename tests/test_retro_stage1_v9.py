from pathlib import Path

from app.ui.retro_showcase_state import library_filter_options

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8')


def test_favorite_is_no_longer_a_retro_browsing_concept():
    game = {key for _label, key, _payload in library_filter_options('games')}
    movie = {key for _label, key, _payload in library_filter_options('movies')}
    assert 'favorite' not in game
    assert 'favorite' not in movie
    source = read('app/ui/retro_showcase.py')
    record_menu = source.split('def _show_record_menu', 1)[1].split('def _set_box_style', 1)[0]
    assert '取消收藏' not in record_menu
    assert '收藏' not in record_menu


def test_retro_restores_game_and_movie_archive_edit_entry_points():
    source = read('app/ui/retro_showcase.py')
    assert '编辑游戏档案…' in source
    assert '编辑影片档案…' in source
    assert 'def _edit_current_game' in source
    assert 'def _edit_current_movie' in source
    dialogs = read('app/ui/retro_edit_dialogs.py')
    assert 'class RetroGameArchiveEditDialog' in dialogs
    assert 'class RetroMovieArchiveEditDialog' in dialogs


def test_retro_has_minimum_window_and_about_page():
    bootstrap = read('app/bootstrap.py')
    assert 'window.setMinimumSize(1100, 700)' in bootstrap
    assert 'v0.5.0.8' in bootstrap
    source = read('app/ui/retro_showcase.py')
    assert '"关于"' in source
    assert 'RETRO_VERSION = "0.5.0.8"' in source


def test_system_panel_has_one_settings_entry_and_no_duplicate_search_entry():
    source = read('app/ui/retro_showcase.py')
    body = source.split('def _draw_system_body', 1)[1].split('def _draw_corner_menu', 1)[0]
    assert body.count('打开完整设置…') == 1
    assert '搜索当前媒体库…' not in body
    assert '添加游戏…' not in body


def test_background_has_no_diagonal_base_glow():
    source = read('app/ui/retro_showcase.py')
    block = source.split('def _draw_background', 1)[1].split('def _draw_focus_backdrop', 1)[0]
    assert 'rect.topLeft(), rect.bottomRight()' not in block
    assert 'QLinearGradient(0.0, rect.top(), 0.0, rect.bottom())' in block


def test_cover_art_uses_inset_polygon_face_not_outer_front_rect():
    source = read('app/ui/retro_showcase.py')
    assert 'def _inset_front_face' in source
    assert 'def _draw_cover_on_face' in source
    classic = source.split('def _draw_classic_game_case', 1)[1].split('def _draw_neo_game_case', 1)[0]
    neo = source.split('def _draw_neo_game_case', 1)[1].split('def _draw_case_spine', 1)[0]
    assert '_draw_cover_on_face' in classic
    assert '_draw_cover_on_face' in neo


def test_v9_version_and_log_are_packaged():
    assert 'version = "0.5.0.8"' in read('pyproject.toml')
    log = read('docs/development-logs/Retro_Prototype_v9.md')
    assert 'STAGE 1' in log
    assert 'ARCHIVE EDIT' in log
    assert 'MINIMUM WINDOW' in log
    assert 'ABOUT' in log
