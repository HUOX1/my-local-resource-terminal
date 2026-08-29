from pathlib import Path

from app.ui.retro_showcase_state import arc_pose


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_arc_pose_is_continuous_between_side_and_center_slots():
    left = arc_pose(-1.0)
    halfway = arc_pose(-0.5)
    center = arc_pose(0.0)

    assert left.scale < halfway.scale < center.scale
    assert left.opacity < halfway.opacity < center.opacity
    assert left.angle < halfway.angle < center.angle
    assert left.center_x < halfway.center_x < center.center_x


def test_arc_pose_fades_objects_beyond_visible_neighbor_slots():
    edge = arc_pose(1.0)
    far = arc_pose(1.75)
    assert far.opacity < edge.opacity
    assert far.scale < edge.scale
    assert far.center_x > edge.center_x


def test_retro_v2_uses_continuous_arc_position_and_compact_drawers():
    source = read("app/ui/retro_showcase.py")
    assert 'Property(float, _get_arc_position, _set_arc_position)' in source
    assert 'arc_pose(' in source
    assert '_arc_target' in source
    assert '_arc_progress' not in source
    assert 'DETAIL_PANEL_WIDTH_RATIO = 0.42' in source
    assert 'SYSTEM_PANEL_WIDTH_RATIO = 0.34' in source
    assert 'DETAIL_PANEL_HEIGHT_RATIO = 0.78' in source


def test_retro_v2_removes_parallax_wall_and_restores_movie_cover_tool_access():
    source = read("app/ui/retro_showcase.py")
    assert 'Rear smoked-acrylic wall' not in source
    assert 'def _draw_ambient_waves' in source
    assert '影片封面工具…' in source
    assert 'self.host._open_cover_tools()' in source


def test_retro_v2_log_remains_packaged_as_history():
    log = read("docs/development-logs/Retro_Prototype_v2.md")
    assert "CONTINUOUS ARC" in log
    assert "PS3" in log
    assert "MORE" in log
