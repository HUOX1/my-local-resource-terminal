from pathlib import Path

from app.ui.retro_showcase_state import (
    AMBIENT_ACTIVE_INTERVAL_MS,
    AMBIENT_IDLE_INTERVAL_MS,
    ambient_phase_step,
    ambient_refresh_interval_ms,
)

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_idle_ambient_refresh_is_15fps_and_hover_only_boosts_during_transition():
    assert AMBIENT_IDLE_INTERVAL_MS == 66
    assert AMBIENT_ACTIVE_INTERVAL_MS == 33
    assert ambient_refresh_interval_ms(None, {}) == 66
    assert ambient_refresh_interval_ms(4, {4: 0.25}) == 33
    assert ambient_refresh_interval_ms(4, {4: 1.0}) == 66
    assert ambient_refresh_interval_ms(None, {4: 0.4}) == 33


def test_ambient_phase_uses_elapsed_time_instead_of_fixed_tick_increment():
    old_one_second = (1000.0 / 33.0) * 0.0105
    assert abs(ambient_phase_step(1000) - old_one_second) < 0.01
    assert abs(ambient_phase_step(66) - 2.0 * ambient_phase_step(33)) < 1e-9


def test_showcase_has_no_post_package_foreground_wave_pass_and_uses_elapsed_clock():
    source = read("app/ui/retro_showcase.py")
    assert 'RETRO_VERSION = "0.5.0.17.1"' in source
    assert "self._ambient_timer.setInterval(AMBIENT_IDLE_INTERVAL_MS)" in source
    assert "self._ambient_clock.restart()" in source
    assert "self._phase += ambient_phase_step(elapsed_ms)" in source
    assert "self._draw_foreground_waves(painter)" not in source
    assert "def _draw_foreground_waves" not in source


def test_hidden_or_minimized_scene_skips_ambient_repaint():
    source = read("app/ui/retro_showcase.py")
    assert "if not self.isVisible() or self.window().isMinimized():" in source
    assert "self._ambient_clock.restart()" in source
    assert "return" in source[source.index("if not self.isVisible() or self.window().isMinimized():"):][:220]


def test_ambient_symbol_seed_geometry_is_cached_once_per_overlay():
    source = read("app/ui/retro_showcase.py")
    assert "self._ambient_symbol_bases = self._build_ambient_symbol_bases()" in source
    assert "def _build_ambient_symbol_bases" in source
    specs = source[source.index("    def _ambient_symbol_specs"):source.index("    def _draw_ambient_symbols")]
    assert "math.sin(seed * 12.9898)" not in specs
    assert "math.sin(seed * 7.313 + 1.17)" not in specs
    assert "math.sin(seed * 4.17 + 0.9)" not in specs
