from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_ambient_symbols_and_background_wave_layers_exist():
    source = read("app/ui/retro_showcase.py")
    assert "def _draw_foreground_waves" not in source
    assert "def _ambient_symbol_specs" in source
    assert "def _draw_ambient_symbols" in source
    assert 'self._draw_ambient_symbols(painter, rect)' in source
    assert 'self._draw_foreground_waves(painter)' not in source
    assert 'symbols = ("△", "○", "□", "×")' in source


def test_background_version_and_log_are_packaged():
    assert 'version = "0.5.0.17.1"' in read("pyproject.toml")
    assert "v0.5.0.17" in read("app/bootstrap.py")
    assert 'QLabel("v0.5.0.17.1")' in read("app/ui/app_chrome.py")
    log = read("docs/development-logs/Retro_Stage2_Batch3_Hotfix_v0.5.0.15.1.md")
    assert "Ambient redistribution" in log
    assert "Foreground waves around the hero box" in log
    assert "Brighter palette" in log
