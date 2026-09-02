from pathlib import Path
ROOT=Path(__file__).parents[1]
C=(ROOT/'g3_frontend/scripts/game_carousel.gd').read_text(encoding='utf-8')
CASE=(ROOT/'g3_frontend/scripts/game_case_3d.gd').read_text(encoding='utf-8')

def test_v0618_supersedes_symmetric_v0617_browse():
    assert 'VISIBLE_SLOT_COUNT: int = 4' in C
    assert 'SLOT_SCALE: Array[float] = [2.70, 3.35, 2.85, 2.15]' in C
    assert 'func _shift_track(direction: int) -> void:' in C

def test_focus_background_remains_noninteractive_and_opaque_case_fix_stays():
    assert 'if preview_mode: return _hit_test_selected_case(position_2d)' in C
    assert 'TRANSPARENCY_ALPHA' not in CASE
