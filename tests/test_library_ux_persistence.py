from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mouse_wheel_target_moves_one_notch_by_a_useful_distance():
    module = load_module(ROOT / "app/ui/poster_scroll.py", "poster_scroll")
    target = module.accumulate_scroll_target(
        current_value=500.0,
        target_value=500.0,
        angle_delta=120,
        minimum=0.0,
        maximum=2000.0,
    )
    assert target == 368.0


def test_mouse_wheel_target_accumulates_without_restart():
    module = load_module(ROOT / "app/ui/poster_scroll.py", "poster_scroll_accumulate")
    first = module.accumulate_scroll_target(500.0, 500.0, -120, 0.0, 2000.0)
    second = module.accumulate_scroll_target(500.0, first, -120, 0.0, 2000.0)
    assert first == 632.0
    assert second == 764.0


def test_smooth_scroll_converges_without_overshoot():
    module = load_module(ROOT / "app/ui/poster_scroll.py", "poster_scroll_smooth")
    value = 0.0
    for _ in range(20):
        next_value = module.smooth_scroll_value(value, 132.0, 0.016)
        assert value <= next_value <= 132.0
        value = next_value
    assert value > 129.0


def test_settings_schema_contains_runtime_library_state():
    source = (ROOT / "app/config/settings.py").read_text(encoding="utf-8")
    for field in (
        "movie_folder_id",
        "game_folder_id",
        "movie_view_mode",
        '"movie_folder_id": settings.movie_folder_id',
        '"game_folder_id": settings.game_folder_id',
        '"movie_view_mode": settings.movie_view_mode',
    ):
        assert field in source


def test_bootstrap_restores_and_persists_runtime_library_state():
    source = (ROOT / "app/bootstrap.py").read_text(encoding="utf-8")
    assert "window._current_folder_ids" in source
    assert "settings.movie_folder_id" in source
    assert "settings.game_folder_id" in source
    assert "window._movie_view_index" in source
    assert "persist_current_folder" in source
    assert "persist_movie_view_mode" in source
    assert "sidebar_state_changed.connect" in source


def test_movie_wall_exposes_episode_count_and_stronger_focus():
    model_source = (ROOT / "app/ui/movie_models.py").read_text(encoding="utf-8")
    delegate_source = (ROOT / "app/ui/movie_delegate.py").read_text(encoding="utf-8")
    assert "EpisodeCountRole" in model_source
    assert "len(record.episodes)" in model_source
    assert "HOVER_SCALE = 1.035" in delegate_source
    assert "HOVER_LIFT = 4.0" in delegate_source
    assert 'f"{episode_count} 集"' in delegate_source
    assert "_draw_hover_caption" in delegate_source


def load_settings_module():
    import sys
    import types

    theme = types.ModuleType("app.config.theme_registry")
    theme.DEFAULT_THEME_ID = "flat_pro"
    theme.resolve_theme_id = lambda value: value or "flat_pro"
    sys.modules["app.config.theme_registry"] = theme

    path = ROOT / "app/config/settings.py"
    spec = importlib.util.spec_from_file_location("settings_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_settings_round_trip_runtime_library_state(tmp_path):
    module = load_settings_module()
    settings_path = tmp_path / "settings.json"
    store = module.SettingsStore(settings_path)
    original = module.AppSettings(
        data_dir=tmp_path / "data",
        cover_dir=tmp_path / "covers",
        libraries=[],
        movie_filter="subtitle",
        game_filter="recent",
        movie_folder_id="movie-folder-1",
        game_folder_id="game-folder-2",
        movie_view_mode="list",
        sidebar_visible=True,
        sidebar_width=196,
    )

    store.save(original)
    restored = store.load()

    assert restored.movie_filter == "subtitle"
    assert restored.game_filter == "recent"
    assert restored.movie_folder_id == "movie-folder-1"
    assert restored.game_folder_id == "game-folder-2"
    assert restored.movie_view_mode == "list"
    assert restored.sidebar_visible is True
    assert restored.sidebar_width == 196


def test_settings_old_file_gets_safe_runtime_defaults(tmp_path):
    import json

    module = load_settings_module()
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({
            "data_dir": str(tmp_path / "data"),
            "cover_dir": str(tmp_path / "covers"),
            "libraries": [],
            "movie_filter": "subtitle",
        }),
        encoding="utf-8",
    )

    restored = module.SettingsStore(settings_path).load()

    assert restored.movie_filter == "subtitle"
    assert restored.movie_folder_id is None
    assert restored.game_folder_id is None
    assert restored.movie_view_mode == "poster"
