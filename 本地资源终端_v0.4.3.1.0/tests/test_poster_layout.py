from app.ui.poster_layout import scaled_poster_size


def test_fit_mode_never_exceeds_target_box() -> None:
    width, height = scaled_poster_size(1000, 1400, 174, 260, "fit")
    assert width <= 174
    assert height <= 260
    assert (width, height) == (174, 244)


def test_fill_mode_covers_target_box() -> None:
    width, height = scaled_poster_size(1000, 1400, 174, 260, "fill")
    assert width >= 174
    assert height >= 260
    assert (width, height) == (186, 260)


def test_invalid_dimensions_return_zero_size() -> None:
    assert scaled_poster_size(0, 1400, 174, 260, "fit") == (0, 0)
