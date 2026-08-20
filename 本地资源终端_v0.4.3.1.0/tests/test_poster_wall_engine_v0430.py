from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_poster_wall_targets_own_fixed_width_row_geometry():
    from app.ui.poster_layout import poster_wall_targets

    layout = poster_wall_targets(
        1500,
        [260, 300, 250, 280, 270, 240, 290, 310],
        card_width=190,
        min_spacing=10,
        alignment="centered",
    )

    assert layout.columns == 7
    assert layout.spacing == 21
    assert layout.targets[0].x == 21
    assert layout.targets[1].x == 232
    assert layout.targets[0].y == 21
    assert layout.targets[7].x == 21
    assert layout.targets[7].y == 342
    assert layout.targets[7].width == 190
    assert layout.targets[7].height == 310
    assert layout.content_height == 673


def test_poster_wall_targets_use_growth_hysteresis_but_shrink_before_overlap():
    from app.ui.poster_layout import poster_wall_targets

    near_growth = poster_wall_targets(
        1615,
        [260] * 8,
        card_width=190,
        min_spacing=10,
        previous_columns=7,
        hysteresis=24,
    )
    growth_crossed = poster_wall_targets(
        1634,
        [260] * 8,
        card_width=190,
        min_spacing=10,
        previous_columns=7,
        hysteresis=24,
    )
    shrink_crossed = poster_wall_targets(
        1609,
        [260] * 8,
        card_width=190,
        min_spacing=10,
        previous_columns=8,
        hysteresis=24,
    )

    assert near_growth.columns == 7
    assert growth_crossed.columns == 8
    assert shrink_crossed.columns == 7


def test_poster_wall_targets_support_fixed_left_without_freezing_that_visual_choice():
    from app.ui.poster_layout import poster_wall_targets

    layout = poster_wall_targets(
        1500,
        [260, 260],
        card_width=190,
        min_spacing=10,
        alignment="fixed_left",
    )

    assert layout.columns == 7
    assert layout.spacing == 10
    assert layout.targets[0].x == 10
    assert layout.targets[1].x == 210


def test_poster_wall_view_applies_explicit_targets_instead_of_qt_wrapping():
    source = read("app/ui/poster_view.py")
    main = read("app/ui/main_window.py")

    assert "poster_wall_targets" in source
    assert "self.setPositionForIndex(" in source
    assert "self.resizeContents(" in source
    assert "setWrapping(False)" in main
    assert "QListView.ResizeMode.Fixed" in main
    assert "QListView.Movement.Free" in main
    assert "setDragEnabled(False)" in main
    assert "adaptive_poster_wall_metrics" not in source
    assert "self.setSpacing(metrics.spacing)" not in source


def test_release_is_v0430():
    assert 'version = "0.4.3.0.3"' in read("pyproject.toml")
    assert "v0.4.3.0.3" in read("app/ui/main_window.py")
    assert "v0.4.3.0.3" in read("app/ui/app_chrome.py")
