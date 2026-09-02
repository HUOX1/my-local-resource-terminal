from pathlib import Path

ROOT=Path(__file__).parents[1]
C=(ROOT/'g3_frontend/scripts/game_carousel.gd').read_text(encoding='utf-8')
M=(ROOT/'g3_frontend/scripts/main.gd').read_text(encoding='utf-8')

def test_browse_uses_four_asymmetric_slots_with_selected_second():
    assert 'const VISIBLE_SLOT_COUNT: int = 4' in C
    assert 'const SELECTED_SLOT: int = 1' in C
    assert 'const SLOT_SCREEN_X: Array[float] = [0.20, 0.455, 0.71, 0.89]' in C

def test_browse_caption_is_hidden_and_focus_details_own_text():
    assert 'case_title_label.visible = false' in M
    assert 'case_meta_label.visible = false' in M
