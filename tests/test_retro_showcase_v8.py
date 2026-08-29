from pathlib import Path

from app.ui.retro_showcase_state import arc_pose

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_browse_focus_is_visually_stronger_than_neighbors():
    center = arc_pose(0.0)
    near = arc_pose(1.0)
    far = arc_pose(2.0)

    assert center.opacity == 1.0
    assert near.opacity <= 0.60
    assert far.opacity <= 0.32
    assert center.scale > near.scale > far.scale


def test_focus_composition_pushes_right_neighbor_out_of_text_safe_zone():
    browse = arc_pose(1.0, focus=0.0)
    focused = arc_pose(1.0, focus=1.0)

    assert focused.center_x >= 0.82
    assert focused.center_x > browse.center_x
    assert focused.opacity < browse.opacity * 0.70


def test_short_game_info_drops_runtime_environment_and_last_played():
    source = read("app/ui/retro_showcase.py")
    block = source.split("def _focus_lines", 1)[1].split("def _movie_runtime_text", 1)[0]

    assert '"PC" if m.launch_exe' not in block
    assert "LAST PLAYED" not in block
    assert "profile.label" in block
    assert "PLAY TIME ·" in block


def test_focus_title_uses_bounded_two_line_layout():
    source = read("app/ui/retro_showcase.py")
    block = source.split("def _draw_focus_info", 1)[1].split("def _focus_lines", 1)[0]

    assert "_draw_focus_title" in block
    assert "focus_title_max_lines: int = 2" in source
    assert "focus_title_max_lines=info_layout.title_max_lines" in source
    assert "focus_info_layout" in source


def test_game_cover_is_clipped_to_the_same_slanted_front_face_as_the_case():
    source = read("app/ui/retro_showcase.py")
    game_box = source.split("def _draw_game_box", 1)[1].split("def _draw_classic_game_case", 1)[0]
    classic = source.split("def _draw_classic_game_case", 1)[1].split("def _draw_neo_game_case", 1)[0]
    neo = source.split("def _draw_neo_game_case", 1)[1].split("def _draw_case_spine", 1)[0]

    assert "front_face = QPolygonF" in game_box
    assert "front_face" in classic and "setClipPath" in classic
    assert "front_face" in neo and "setClipPath" in neo


def test_v8_version_and_log_are_packaged():
    assert 'version = "0.5.0.17.1"' in read("pyproject.toml")
    assert "v0.5.0.17" in read("app/bootstrap.py")
    log = read("docs/development-logs/Retro_Prototype_v8.md")
    assert "FOCUS CONTRAST" in log
    assert "FRONT FACE CLIP" in log
    assert "SHORT INFO" in log
