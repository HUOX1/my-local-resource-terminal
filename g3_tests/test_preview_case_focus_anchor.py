from pathlib import Path
import re
ROOT=Path(__file__).parents[1]
C=(ROOT/'g3_frontend/scripts/game_carousel.gd').read_text(encoding='utf-8')

def _c(name):
 m=re.search(rf'const {name}: float = (-?\d+(?:\.\d+)?)', C); assert m; return float(m.group(1))

def test_focus_moves_left_and_down_from_browse_selected_slot():
    assert 0.25 <= _c('PREVIEW_SCREEN_X') <= 0.35
    assert _c('PREVIEW_ANCHOR_Y') < 0.0

def test_focus_size_stays_near_browse_impact_instead_of_exploding():
    assert 3.2 <= _c('PREVIEW_SELECTED_SCALE') <= 3.7
