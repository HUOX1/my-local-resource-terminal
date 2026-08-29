from __future__ import annotations

from pathlib import Path

from app.ui.retro_showcase_state import (
    RETRO_MAX_VISIBLE_ITEMS,
    hover_pose,
    showcase_click_intent,
)

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_showcase_caps_visible_composition_at_four_items():
    assert RETRO_MAX_VISIBLE_ITEMS == 4
    source = read("app/ui/retro_showcase.py")
    assert "carousel_slots(count, RETRO_MAX_VISIBLE_ITEMS)" in source
    assert "carousel_slots(count, 5)" not in source


def test_click_intent_separates_selection_from_focus():
    assert showcase_click_intent(clicked_sequence=3, current_sequence=1, focused=False) == "select"
    assert showcase_click_intent(clicked_sequence=1, current_sequence=1, focused=False) == "focus"
    assert showcase_click_intent(clicked_sequence=1, current_sequence=1, focused=True) == "stay"


def test_hover_pose_is_restrained_and_directional():
    neutral = hover_pose(0.0, x_bias=1.0, y_bias=-1.0)
    assert neutral.scale_multiplier == 1.0
    assert neutral.lift_px == 0.0
    assert neutral.angle_delta == 0.0

    left = hover_pose(1.0, x_bias=-1.0, y_bias=0.0)
    right = hover_pose(1.0, x_bias=1.0, y_bias=0.0)
    assert 1.02 <= left.scale_multiplier <= 1.05
    assert -9.0 <= left.lift_px <= -3.0
    assert left.angle_delta < 0 < right.angle_delta
    assert abs(left.angle_delta) <= 1.5
    assert 0.0 < left.emphasis_boost <= 0.3


def test_showcase_interaction_tracks_visible_hit_rects_and_retargets_arc():
    source = read("app/ui/retro_showcase.py")
    assert "_record_hit_rects" in source
    assert "def _record_hit_at" in source
    assert "def _animate_arc_to" in source
    assert "_hover_strengths" in source
    assert "QEasingCurve.Type.OutQuart" in source


def test_local_smoke_exercises_four_item_click_hover_and_wrap():
    smoke = read("tests/test_retro_gui_smoke.py")
    runner = read("tools/retro_smoke_runner.py")
    assert "test_showcase_four_item_click_hover_and_wrap" in smoke
    assert '"showcase 4-up / click / hover / wrap"' in runner


def test_stage2_batch2_version_is_05014():
    assert 'version = "0.5.0.17.1"' in read("pyproject.toml")
    assert "v0.5.0.17" in read("app/bootstrap.py")
    assert "v0.5.0.17" in read("app/ui/app_chrome.py")
    assert 'RETRO_VERSION = "0.5.0.17.1"' in read("app/ui/retro_showcase.py")
