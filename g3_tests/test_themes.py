
import json
from pathlib import Path

import pytest

from g3_core.services.themes import ThemeService, ThemeError


def test_theme_manifest_requires_core_sections(tmp_path):
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "theme.json").write_text(json.dumps({"id":"bad","name":"Bad"}), encoding="utf-8")
    service = ThemeService(builtin_root=tmp_path, user_root=tmp_path / "users")
    with pytest.raises(ThemeError):
        service._load_manifest(bad / "theme.json")


def test_empty_music_is_valid(tmp_path):
    theme_dir = tmp_path / "classic"
    theme_dir.mkdir()
    payload = {
        "id":"classic",
        "name":"Classic",
        "colors":{"base":"#100020","accent":"#8a5cff"},
        "ambient":{"wave_speed":0.5,"wave_strength":0.8,"symbol_amount":36,"symbol_opacity":0.25},
        "audio":{"music":""},
        "icons":{"set":""},
        "transitions":{"speed":1.0}
    }
    (theme_dir / "theme.json").write_text(json.dumps(payload), encoding="utf-8")
    service = ThemeService(builtin_root=tmp_path, user_root=tmp_path / "users")
    manifest = service.load("classic")
    assert manifest.id == "classic"
    assert manifest.audio["music"] == ""


def test_theme_resource_path_cannot_escape_theme_directory(tmp_path):
    theme_dir = tmp_path / "classic"
    theme_dir.mkdir()
    service = ThemeService(builtin_root=tmp_path, user_root=tmp_path / "users")
    with pytest.raises(ThemeError):
        service.resolve_resource(theme_dir, "../outside.mp3")
