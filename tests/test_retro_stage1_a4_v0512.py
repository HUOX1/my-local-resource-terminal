from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOWCASE = ROOT / "app" / "ui" / "retro_showcase.py"


def _background_method_source() -> str:
    source = SHOWCASE.read_text(encoding="utf-8")
    start = source.index("    def _draw_background")
    end = source.index("    def _draw_focus_backdrop", start)
    return source[start:end]


def test_background_base_gradient_is_vertical_not_diagonal():
    method = _background_method_source()
    assert "QLinearGradient(0.0, rect.top(), 0.0, rect.bottom())" in method
    assert "QLinearGradient(rect.topLeft(), rect.bottomRight())" not in method


def test_background_cleanup_does_not_reintroduce_glow_or_stage_layers():
    method = _background_method_source()
    assert "QRadialGradient" not in method
    assert "glow = QRadialGradient" not in method
    assert "stage = QRadialGradient" not in method
    assert "self._draw_ambient_waves(painter, rect)" in method


def test_local_smoke_has_clean_background_check():
    smoke = (ROOT / "tests" / "test_retro_gui_smoke.py").read_text(encoding="utf-8")
    runner = (ROOT / "tools" / "retro_smoke_runner.py").read_text(encoding="utf-8")
    assert "test_background_base_is_horizontally_uniform_without_waves" in smoke
    assert '"clean background base"' in runner
