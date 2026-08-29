from pathlib import Path

from app.ui.retro_showcase_state import (
    arc_pose,
    effective_package_face_ratio,
)

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_real_cover_aspect_overrides_platform_face_template():
    # A PS3 profile may describe material/depth, but the real front face must
    # follow the supplied cover so full cover scans do not gain letterboxing.
    assert effective_package_face_ratio(0.715, 0.625) == 0.625
    assert effective_package_face_ratio(0.715, 0.98) == 0.98
    assert effective_package_face_ratio(0.715, None) == 0.715


def test_focus_pose_is_lower_and_less_oversized_than_v4():
    browse = arc_pose(0.0, focus=0.0)
    focused = arc_pose(0.0, focus=1.0)

    assert 1.08 <= focused.scale <= 1.16
    assert focused.center_y > browse.center_y
    assert 0.47 <= focused.center_y <= 0.51


def test_v5_draws_cover_in_ratio_preserving_inner_face_and_adds_focus_backdrop_dim():
    source = read("app/ui/retro_showcase.py")
    assert "effective_package_face_ratio" in source
    assert "def _cover_inner_rect" in source
    assert "FOCUS_BACKDROP_ALPHA" in source
    assert "self._draw_focus_backdrop" in source


def test_v5_keeps_more_layout_but_restores_more_hero_scale():
    source = read("app/ui/retro_showcase.py")
    assert "DETAIL_PANEL_WIDTH_RATIO = 0.42" in source
    assert "target_scale = 1.12 if abs(position) < 0.5 else 0.88" in source


def test_v5_log_remains_packaged_as_history():
    log = read("docs/development-logs/Retro_Prototype_v5.md")
    assert "v0.5.0.4" in log
    assert "ADAPTIVE FRONT FACE" in log
    assert "FOCUS COMPOSITION" in log
    assert "BACKDROP DIM" in log
