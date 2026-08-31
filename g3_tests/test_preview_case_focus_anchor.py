from pathlib import Path
import re

CAROUSEL = Path(__file__).parents[1] / "g3_frontend" / "scripts" / "game_carousel.gd"


def _constant(text: str, name: str) -> float:
    match = re.search(rf"const {name}: float = (-?\d+(?:\.\d+)?)", text)
    assert match is not None, name
    return float(match.group(1))


def test_preview_moves_selected_case_left_to_open_right_detail_space():
    text = CAROUSEL.read_text(encoding="utf-8")
    browse_x = _constant(text, "BROWSE_ANCHOR_X")
    preview_x = _constant(text, "PREVIEW_ANCHOR_X")

    assert -1.0 < browse_x < 1.0
    assert preview_x < browse_x - 2.0
    assert -4.0 < preview_x < -2.0


def test_preview_lifts_selected_case_slightly_higher_than_browse():
    text = CAROUSEL.read_text(encoding="utf-8")
    assert _constant(text, "PREVIEW_ANCHOR_Y") > _constant(text, "BROWSE_ANCHOR_Y")
