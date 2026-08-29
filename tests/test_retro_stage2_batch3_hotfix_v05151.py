from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_ambient_hotfix_biases_upper_and_lower_lanes_and_brighter_palette():
    source = read("app/ui/retro_showcase.py")
    assert 'RETRO_VERSION = "0.5.0.17.1"' in source
    assert '(0.18, 0.070, 0.074, 0.16, 18, QColor(42, 150, 165))' in source
    assert '(0.84, 0.074, 0.082, 0.54, 18, QColor(44, 148, 160))' in source
    assert 'def _draw_foreground_waves' not in source
    assert '(10, 0.06, 0.28, 0.036, 0.018, (36.0, 88.0), 7, QColor(108, 217, 223, 20))' in source
    assert '(8, 0.82, 0.95, 0.088, 0.020, (38.0, 84.0), 9, QColor(118, 223, 228, 18))' in source


def test_hotfix_versions_and_log_present():
    assert 'version = "0.5.0.17.1"' in read("pyproject.toml")
    assert "v0.5.0.17" in read("app/bootstrap.py")
    assert 'QLabel("v0.5.0.17.1")' in read("app/ui/app_chrome.py")
    log = read("docs/development-logs/Retro_Stage2_Batch3_Hotfix_v0.5.0.15.1.md")
    assert "Ambient redistribution" in log
    assert "Brighter palette" in log
