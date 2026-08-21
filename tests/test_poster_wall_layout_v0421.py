from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_adaptive_layout_keeps_fixed_card_width_and_distributes_spacing():
    from app.ui.poster_layout import adaptive_poster_wall_metrics

    metrics = adaptive_poster_wall_metrics(
        1500,
        card_width=190,
        min_spacing=10,
    )
    assert metrics.columns == 7
    assert metrics.spacing == 21
    assert metrics.card_width == 190


def test_adaptive_layout_adds_column_only_when_full_card_fits():
    from app.ui.poster_layout import adaptive_poster_wall_metrics

    before = adaptive_poster_wall_metrics(
        1609,
        card_width=190,
        min_spacing=10,
    )
    after = adaptive_poster_wall_metrics(
        1610,
        card_width=190,
        min_spacing=10,
    )
    assert before.columns == 7
    assert after.columns == 8
    assert before.card_width == after.card_width == 190


def test_poster_view_updates_explicit_targets_during_resize_instead_of_qt_wrapping():
    source = read("app/ui/poster_view.py")
    assert "poster_wall_targets" in source
    assert "self._apply_poster_layout(animate=False)" in source
    assert "self._resize_layout_timer" not in source
    assert "self.setPositionForIndex(" in source
    assert "self.resizeContents(" in source
    assert "delegate.set_cell_width(delegate.CARD_WIDTH)" in source
    assert "adaptive_poster_wall_metrics" not in source
    assert "self.setSpacing(metrics.spacing)" not in source


def test_reflow_capture_uses_current_painted_position_when_interrupted():
    source = read("app/ui/poster_view.py")
    assert "include_motion=True" in source
    assert "rect.translate(round(offset.x()), round(offset.y()))" in source
    assert "REFLOW_DURATION_MS = 220" in source
    assert "_ease_out_quint" in source


def test_release_is_v0421():
    assert 'version = "0.4.3.1.1"' in read("pyproject.toml")
    assert "v0.4.3.1.1" in read("app/ui/main_window.py")
    assert "v0.4.3.1.1" in read("app/ui/app_chrome.py")
