from app.ui.poster_layout import poster_height_for_width


def test_poster_height_preserves_original_ratio() -> None:
    assert poster_height_for_width(1200, 1800, 180) == 270
    assert poster_height_for_width(1200, 1700, 180) == 255


def test_poster_height_uses_fallback_for_invalid_dimensions() -> None:
    assert poster_height_for_width(0, 1800, 180, fallback_height=260) == 260
