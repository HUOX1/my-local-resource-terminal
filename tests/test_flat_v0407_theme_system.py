from __future__ import annotations

import json
from pathlib import Path

from app.config.settings import SettingsStore


def _settings_payload(tmp_path: Path) -> dict:
    return {
        "data_dir": str(tmp_path / "data"),
        "cover_dir": str(tmp_path / "covers"),
        "libraries": [],
        "player_mode": "system",
        "player_path": None,
        "ffprobe_path": "ffprobe",
        "ffmpeg_path": "ffmpeg",
        "auto_scan": True,
    }


def test_old_settings_default_to_flat_pro_theme(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(_settings_payload(tmp_path)), encoding="utf-8")

    loaded = SettingsStore(path).load()

    assert loaded.ui_theme == "flat_pro"


def test_ui_theme_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(_settings_payload(tmp_path)), encoding="utf-8")
    store = SettingsStore(path)
    settings = store.load()

    from dataclasses import replace

    store.save(replace(settings, ui_theme="flat_pro_light"))
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["ui_theme"] == "flat_pro_light"
    assert store.load().ui_theme == "flat_pro_light"


def test_invalid_ui_theme_falls_back_to_flat_pro(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    payload = _settings_payload(tmp_path)
    payload["ui_theme"] = "unknown_skin"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = SettingsStore(path).load()

    assert loaded.ui_theme == "flat_pro"


def test_flat_theme_source_exposes_skin_registry() -> None:
    source = Path("app/ui/flat_theme.py").read_text(encoding="utf-8")
    registry = Path("app/config/theme_registry.py").read_text(encoding="utf-8")
    assert '"flat_pro"' in registry
    assert '"flat_pro_light"' in registry
    assert 'LEGACY_THEME_ALIASES' in registry
    assert "THEMES" in source
    assert "def apply_theme(" in source
    assert "def theme_display_name(" in source


def test_settings_dialog_exposes_appearance_page() -> None:
    source = Path("app/ui/settings_dialog.py").read_text(encoding="utf-8")
    assert '("外观", "主题与界面外观")' in source
    assert "self.ui_theme_combo" in source
    assert "theme_options" in source
    assert "for theme_id, display_name in theme_options()" in source
    assert "ui_theme=self.ui_theme_combo.currentData()" in source


def test_bootstrap_applies_saved_theme_and_restarts_when_theme_changes() -> None:
    source = Path("app/bootstrap.py").read_text(encoding="utf-8")
    assert "apply_theme(app, settings.ui_theme)" in source
    assert "if updated.ui_theme != current.ui_theme:" in source
    assert "_local_movie_manager_restart_requested" in source
