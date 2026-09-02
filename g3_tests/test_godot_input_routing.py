
from pathlib import Path
import re

SOURCE = Path(__file__).parents[1] / "g3_frontend" / "scripts" / "game_carousel.gd"

def test_carousel_does_not_consume_unrelated_left_clicks():
    text = SOURCE.read_text(encoding="utf-8")
    left_block = re.search(
        r'if mouse_event\.button_index == MOUSE_BUTTON_LEFT:(.*?)(?=\n        if mouse_event\.pressed and mouse_event\.button_index == MOUSE_BUTTON_RIGHT:)',
        text,
        flags=re.S,
    )
    assert left_block is not None
    body = left_block.group(1)
    assert "if _handle_left_click(mouse_event.position):" in body
    assert re.search(
        r'if _handle_left_click\(mouse_event\.position\):\s*\n\s*get_viewport\(\)\.set_input_as_handled\(\)',
        body,
    )

def test_carousel_skips_mouse_input_when_hidden_or_empty():
    text = SOURCE.read_text(encoding="utf-8")
    assert 'if not visible or games.is_empty():' in text

def test_handle_click_reports_whether_case_was_hit():
    text = SOURCE.read_text(encoding="utf-8")
    assert "func _handle_left_click(position_2d: Vector2) -> bool:" in text
    assert "if clicked_index < 0: return false" in text
