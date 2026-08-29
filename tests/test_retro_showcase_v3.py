from pathlib import Path

from app.ui.retro_showcase_state import arc_pose

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_wide_arc_centers_hero_and_keeps_two_visible_steps_each_side():
    left_far = arc_pose(-2.0)
    left = arc_pose(-1.0)
    center = arc_pose(0.0)
    right = arc_pose(1.0)
    right_far = arc_pose(2.0)

    assert 0.47 <= center.center_x <= 0.53
    assert left_far.center_x < left.center_x < center.center_x < right.center_x < right_far.center_x
    assert center.scale > left.scale > left_far.scale > 0.0
    assert center.scale > right.scale > right_far.scale > 0.0
    assert left_far.opacity > 0.2
    assert right_far.opacity > 0.2


def test_focus_moves_hero_left_to_make_room_for_text_without_changing_rail_model():
    browse = arc_pose(0.0, focus=0.0)
    focused = arc_pose(0.0, focus=1.0)
    assert focused.center_x < browse.center_x
    assert focused.scale > browse.scale


def test_v3_wide_arc_history_remains_packaged_after_v4_visual_revision():
    source = read("app/ui/retro_showcase.py")
    log = read("docs/development-logs/Retro_Prototype_v3.md")
    assert "carousel_segment" in source
    assert "carousel_slots" in source
    assert "WIDE ARC" in log
    assert "HANGER" in log


def test_v3_ambient_background_uses_continuous_multilayer_bands_without_phase_wrap():
    source = read("app/ui/retro_showcase.py")
    assert "self._phase +=" in source
    assert "% (math.tau)" not in source
    assert "def _draw_wave_band" in source
    assert "AMBIENT_BAND" in source


def test_v3_version_and_log_are_packaged():
    log = read("docs/development-logs/Retro_Prototype_v3.md")
    assert "WIDE ARC" in log
    assert "HANGER" in log
    assert "CONTINUOUS AMBIENT" in log
