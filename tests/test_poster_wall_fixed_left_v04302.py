from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_poster_wall_view_uses_fixed_left_alignment():
    source = read("app/ui/poster_view.py")
    assert 'LAYOUT_ALIGNMENT = "fixed_left"' in source


def test_fixed_left_targets_do_not_shift_when_only_virtual_capacity_changes():
    from app.ui.poster_layout import poster_wall_targets

    heights = [260, 280, 240, 300]
    narrow = poster_wall_targets(1500, heights, card_width=190, min_spacing=10, alignment="fixed_left")
    wide = poster_wall_targets(1700, heights, card_width=190, min_spacing=10, alignment="fixed_left")

    assert narrow.columns != wide.columns
    assert [(t.x, t.y) for t in narrow.targets] == [(t.x, t.y) for t in wide.targets]
    assert narrow.spacing == wide.spacing == 10


def test_release_is_v04302():
    assert 'version = "0.4.3.1.1"' in read("pyproject.toml")
    assert "v0.4.3.1.1" in read("app/ui/main_window.py")
    assert "v0.4.3.1.1" in read("app/ui/app_chrome.py")
