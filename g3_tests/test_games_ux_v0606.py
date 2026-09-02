from pathlib import Path
import json
ROOT=Path(__file__).parents[1]
MAIN=(ROOT/'g3_frontend/scripts/main.gd').read_text(encoding='utf-8')
CAR=(ROOT/'g3_frontend/scripts/game_carousel.gd').read_text(encoding='utf-8')
CYAN=ROOT/'g3_frontend/themes/classic_cyan/theme.json'

def test_games_browse_uses_g1_inspired_four_slot_track():
    assert 'VISIBLE_SLOT_COUNT: int = 4' in CAR
    assert 'SELECTED_SLOT: int = 1' in CAR
    assert 'OFFSCREEN_SCREEN_MARGIN' in CAR and 'func _offscreen_x(' in CAR

def test_clean_ui_and_dark_cyan_theme():
    assert 'xmb_root.visible = false' in MAIN
    payload=json.loads(CYAN.read_text(encoding='utf-8'))
    assert payload['colors']['base_bottom']=='#010A0F'
    assert payload['ambient']['glow_strength']==0.0
