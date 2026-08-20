from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path


def _settings_payload(tmp_path: Path, theme_id: str) -> dict:
    return {
        "data_dir": str(tmp_path / "data"),
        "cover_dir": str(tmp_path / "covers"),
        "libraries": [],
        "player_mode": "system",
        "player_path": None,
        "ffprobe_path": "ffprobe",
        "ffmpeg_path": "ffmpeg",
        "auto_scan": True,
        "ui_theme": theme_id,
    }


def test_theme_registry_is_single_source_of_truth() -> None:
    from app.config.theme_registry import DEFAULT_THEME_ID, THEMES, theme_options

    assert DEFAULT_THEME_ID == "flat_pro"
    assert set(THEMES) == {"flat_pro", "flat_pro_light"}
    options = dict(theme_options())
    assert options["flat_pro"] == "Flat Pro"
    assert options["flat_pro_light"] == "Flat Pro Light"


def test_settings_store_accepts_newly_registered_theme_without_its_own_allowlist(
    tmp_path: Path, monkeypatch
) -> None:
    from app.config.settings import SettingsStore
    from app.config.theme_registry import THEMES

    monkeypatch.setitem(
        THEMES,
        "test_skin",
        replace(THEMES["flat_pro"], display_name="Test Skin"),
    )
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(_settings_payload(tmp_path, "test_skin")), encoding="utf-8")

    assert SettingsStore(path).load().ui_theme == "test_skin"


def test_theme_metrics_are_owned_by_each_theme() -> None:
    from app.config.theme_registry import THEMES

    metrics = THEMES["flat_pro"].metrics
    assert metrics.radius_small == 5
    assert metrics.radius_medium == 7
    assert metrics.radius_large == 9
    assert metrics.space_1 == 4
    assert metrics.space_5 == 24
    assert metrics.control_height == 34
    assert metrics.sidebar_width == 196


def test_theme_asset_resolver_uses_theme_owned_relative_assets(tmp_path: Path, monkeypatch) -> None:
    from app.config.theme_registry import THEMES, ThemeAssets
    from app.ui.theme_assets import resolve_theme_asset_path

    monkeypatch.setitem(
        THEMES,
        "test_skin",
        replace(
            THEMES["flat_pro"],
            display_name="Test Skin",
            assets=ThemeAssets(background="background.png"),
        ),
    )
    skin_dir = tmp_path / "test_skin"
    skin_dir.mkdir()
    expected = skin_dir / "background.png"
    expected.write_bytes(b"PNG")

    assert resolve_theme_asset_path("test_skin", "background", asset_root=tmp_path) == expected
    assert resolve_theme_asset_path("test_skin", "texture", asset_root=tmp_path) is None


def test_settings_dialog_populates_theme_combo_from_registry() -> None:
    source = Path("app/ui/settings_dialog.py").read_text(encoding="utf-8")
    assert "theme_options" in source
    assert "for theme_id, display_name in theme_options()" in source
    assert 'addItem("Flat Dark"' not in source
    assert 'addItem("Flat Light"' not in source


def test_settings_validation_has_no_duplicate_theme_allowlist() -> None:
    source = Path("app/config/settings.py").read_text(encoding="utf-8")
    assert "resolve_theme_id" in source
    assert 'ui_theme not in {"flat_dark", "flat_light"}' not in source


def test_flat_theme_activation_maps_theme_metrics_into_runtime_tokens() -> None:
    source = Path("app/ui/flat_theme.py").read_text(encoding="utf-8")
    for token_name, metric_name in (
        ("RADIUS_SMALL", "radius_small"),
        ("RADIUS_MEDIUM", "radius_medium"),
        ("RADIUS_LARGE", "radius_large"),
        ("SPACE_1", "space_1"),
        ("SPACE_5", "space_5"),
        ("CONTROL_HEIGHT", "control_height"),
        ("SIDEBAR_WIDTH", "sidebar_width"),
    ):
        assert f'"{token_name}": spec.metrics.{metric_name}' in source


def test_flat_theme_keeps_required_qt_runtime_imports() -> None:
    source = Path("app/ui/flat_theme.py").read_text(encoding="utf-8")
    assert "from PySide6.QtGui import QColor, QPalette" in source
    assert "from PySide6.QtWidgets import QApplication" in source


def test_windows_debug_launcher_pauses_after_python_exits() -> None:
    source = Path("run_windows_debug.bat").read_text(encoding="utf-8")
    assert "set \"APP_EXIT=%ERRORLEVEL%\"" in source
    assert "pause" in source
