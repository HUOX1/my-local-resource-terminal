
from pathlib import Path
import json

from g3_core.paths import TerminalPaths
from g3_core.settings import TerminalSettings


def test_terminal_paths_are_isolated_from_legacy(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    paths = TerminalPaths.from_environment()
    assert paths.root == tmp_path / "G3"
    assert paths.database == paths.root / "library.db"
    assert paths.settings == paths.root / "settings.json"


def test_terminal_paths_ensure_creates_runtime_directories(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    paths = TerminalPaths.from_environment()
    paths.ensure()
    assert paths.assets.is_dir()
    assert paths.cache.is_dir()
    assert paths.themes.is_dir()
    assert paths.logs.is_dir()


def test_settings_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    settings = TerminalSettings.default()
    settings.preview_volume = 0.25
    settings.restore_last_item = True
    settings.save(path)
    assert TerminalSettings.load(path) == settings


def test_settings_reject_unknown_key(tmp_path):
    path = tmp_path / "settings.json"
    payload = TerminalSettings.default().to_dict()
    payload["legacy_sidebar_width"] = 196
    path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        TerminalSettings.load(path)
    except ValueError as exc:
        assert "legacy_sidebar_width" in str(exc)
    else:
        raise AssertionError("unknown settings key was accepted")


def test_default_start_section_defaults_to_games_and_validates(tmp_path):
    settings = TerminalSettings.default()
    assert settings.default_start_section == "games"
    settings.default_start_section = "system"
    path = tmp_path / "settings.json"
    settings.save(path)
    assert TerminalSettings.load(path).default_start_section == "system"

    settings.default_start_section = "invalid"
    try:
        settings.save(path)
    except ValueError as exc:
        assert "default_start_section" in str(exc)
    else:
        raise AssertionError("invalid default start section accepted")
