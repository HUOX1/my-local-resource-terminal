from __future__ import annotations

import json

from app.config.settings import AppSettings, SettingsStore


def test_old_settings_default_to_movies_and_independent_game_view_state(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    store.path.write_text(
        '{"data_dir":"D:/data","cover_dir":"D:/covers","libraries":[]}',
        encoding="utf-8",
    )

    settings = store.load()

    assert settings.startup_library == "movies"
    assert settings.game_sort_key == "last_played_at"
    assert settings.game_sort_desc is True
    assert settings.movie_filter == "all"
    assert settings.game_filter == "all"


def test_resource_view_settings_round_trip_without_search_text(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    settings = AppSettings(
        data_dir=tmp_path / "data",
        cover_dir=tmp_path / "covers",
        libraries=[],
        startup_library="games",
        sort_key="rating",
        sort_desc=True,
        game_sort_key="total_play_seconds",
        game_sort_desc=True,
        movie_filter="favorite",
        game_filter="installed",
    )

    store.save(settings)
    loaded = store.load()
    payload = json.loads(store.path.read_text(encoding="utf-8"))

    assert loaded.startup_library == "games"
    assert loaded.game_sort_key == "total_play_seconds"
    assert loaded.game_filter == "installed"
    assert "search" not in payload
    assert "search_text" not in payload


def test_invalid_resource_settings_fall_back_to_safe_values(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    store.path.write_text(
        '{"data_dir":"D:/data","cover_dir":"D:/covers","libraries":[],"startup_library":"music","game_sort_key":"nonsense","movie_filter":"x","game_filter":"x"}',
        encoding="utf-8",
    )

    loaded = store.load()

    assert loaded.startup_library == "movies"
    assert loaded.game_sort_key == "last_played_at"
    assert loaded.movie_filter == "all"
    assert loaded.game_filter == "all"
