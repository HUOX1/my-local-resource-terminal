from pathlib import Path

from app.ui.retro_showcase_state import (
    library_filter_options,
    library_sort_options,
    persistent_filter_key,
)

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_retro_exposes_core_filter_and_sort_choices_without_flat_ui():
    game_filters = {key for _label, key, _payload in library_filter_options("games")}
    movie_filters = {key for _label, key, _payload in library_filter_options("movies")}
    game_sorts = {key for _label, key in library_sort_options("games")}
    movie_sorts = {key for _label, key in library_sort_options("movies")}

    assert {"all", "installed", "uninstalled", "recent"} <= game_filters
    assert {"all", "watched", "unwatched", "available", "offline", "subtitle", "no_subtitle"} <= movie_filters
    assert {"title", "last_played_at", "total_play_seconds", "play_count"} <= game_sorts
    assert {"title", "last_watched_at", "rating", "play_count"} <= movie_sorts


def test_dynamic_filters_remain_session_only_for_settings_persistence():
    assert persistent_filter_key("games", "favorite") == "all"
    assert persistent_filter_key("movies", "subtitle") == "subtitle"
    assert persistent_filter_key("games", "tag:Action") == "all"
    assert persistent_filter_key("movies", "library:abc") == "all"


def test_retro_scene_menu_recovers_library_management_entry_points():
    source = read("app/ui/retro_showcase.py")
    for token in (
        'menu.addAction("添加游戏…")',
        'menu.addAction("搜索…")',
        'menu.addMenu("筛选")',
        'menu.addMenu("排序")',
        'menu.addMenu("分类")',
        'def _show_search_bar',
        'def _set_filter',
        'def _set_sort',
        'def _set_folder',
    ):
        assert token in source


def test_retro_record_menu_recovers_move_to_folder():
    source = read("app/ui/retro_showcase.py")
    assert 'move_menu = menu.addMenu("移动到分类")' in source
    assert 'def _move_current_to_folder' in source
    assert '.set_folder([record.metadata.uuid], folder_id)' in source


def test_retro_queries_services_with_its_own_view_state():
    source = read("app/ui/retro_showcase.py")
    assert 'self._search_text[self.domain]' in source
    assert 'folder_id=self._folder_ids["games"]' in source
    assert 'sort=self._sort_keys["games"]' in source
    assert 'folder_id=self._folder_ids["movies"]' in source
    assert 'sort=self._sort_keys["movies"]' in source


def test_retro_state_persistence_is_connected_without_flat_controls():
    source = read("app/bootstrap.py")
    assert "retro.view_state_changed.connect(persist_retro_view_state)" in source
    assert "retro.folder_state_changed.connect(persist_retro_folder_state)" in source


def test_v6_version_and_log_are_packaged():
    assert 'version = "0.5.0.17.1"' in read("pyproject.toml")
    assert "v0.5.0.17" in read("app/bootstrap.py")
    log = read("docs/development-logs/Retro_Prototype_v6.md")
    assert "FUNCTION RECOVERY" in log
    assert "ADD GAME" in log
    assert "SEARCH / FILTER / SORT / FOLDER" in log
