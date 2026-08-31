from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = ROOT / "g3_frontend" / "scripts" / "main.gd"
CAROUSEL = ROOT / "g3_frontend" / "scripts" / "game_carousel.gd"


def test_duplicate_section_title_is_removed():
    text = MAIN.read_text(encoding="utf-8")
    assert "var title_label" not in text
    assert "\n    title_label = Label.new()" not in text


def test_browse_anchor_is_now_near_screen_center():
    text = CAROUSEL.read_text(encoding="utf-8")
    assert "BROWSE_ANCHOR_X" in text
    assert "BROWSE_ANCHOR_X: float = -0.35" in text
    assert "PREVIEW_ANCHOR_X: float = -3.10" in text


def test_case_caption_uses_projected_selected_case_position():
    text = MAIN.read_text(encoding="utf-8")
    assert "selected_case_world_position" in text
    assert "camera.unproject_position" in text
