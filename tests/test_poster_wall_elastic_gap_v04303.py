from app.ui.poster_layout import poster_wall_targets


def test_fixed_left_full_row_uses_elastic_gaps_and_keeps_outer_edges():
    layout = poster_wall_targets(
        1500,
        [260] * 21,
        card_width=190,
        min_spacing=10,
        alignment="fixed_left",
    )

    assert layout.columns == 7
    assert layout.targets[0].x == 10
    assert layout.targets[1].x == 225
    assert layout.targets[6].x + layout.targets[6].width == 1490
    assert layout.spacing == 25


def test_fixed_left_elastic_horizontal_gap_does_not_change_vertical_gap():
    layout = poster_wall_targets(
        1500,
        [260] * 14,
        card_width=190,
        min_spacing=10,
        alignment="fixed_left",
    )

    assert layout.targets[0].y == 10
    assert layout.targets[7].y == 280


def test_fixed_left_sparse_row_keeps_minimum_gap_when_virtual_capacity_changes():
    heights = [260, 280, 240, 300]
    narrow = poster_wall_targets(
        1500,
        heights,
        card_width=190,
        min_spacing=10,
        alignment="fixed_left",
    )
    wide = poster_wall_targets(
        1700,
        heights,
        card_width=190,
        min_spacing=10,
        previous_columns=narrow.columns,
        alignment="fixed_left",
    )

    assert [(t.x, t.y) for t in narrow.targets] == [(t.x, t.y) for t in wide.targets]
    assert narrow.spacing == wide.spacing == 10
