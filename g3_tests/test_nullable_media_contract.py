
from pathlib import Path
import sys

from g3_core.backend_app import BackendApplication
from g3_core.database import Database
from g3_core.models import CreateGame
from g3_core.paths import TerminalPaths
from g3_core.services.media_assets import PreviewManifest


def _paths(root: Path) -> TerminalPaths:
    return TerminalPaths(
        root=root,
        database=root / "library.db",
        assets=root / "assets",
        cache=root / "cache",
        themes=root / "themes",
        logs=root / "logs",
        settings=root / "settings.json",
    )


def test_game_payload_uses_empty_string_for_missing_cover(tmp_path):
    app = BackendApplication(_paths(tmp_path), builtin_theme_root=tmp_path / "builtin")
    app.initialize()
    game = app.repository.create_game(
        CreateGame(title="RainWorld", executable_path=Path(sys.executable))
    )
    payload = app._game_to_dict(game)
    assert payload["cover"] == ""


def test_preview_payload_uses_empty_strings_for_missing_optional_paths():
    payload = BackendApplication._preview_to_dict(PreviewManifest())
    assert payload["cover"] == ""
    assert payload["background"] == ""
    assert payload["video_ogv"] == ""
    assert payload["preview_audio"] == ""
    assert payload["logo"] == ""


def test_game_case_guards_null_cover_before_string_conversion():
    text = (
        Path(__file__).parents[1]
        / "g3_frontend"
        / "scripts"
        / "game_case_3d.gd"
    ).read_text(encoding="utf-8")
    assert 'var cover_value: Variant = game.get("cover", "")' in text
    assert 'var cover_path: String = "" if cover_value == null else str(cover_value)' in text
