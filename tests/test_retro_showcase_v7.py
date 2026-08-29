from pathlib import Path

from app.ui.retro_showcase_state import (
    anchored_equal_gap_centers,
    carousel_segment,
    carousel_slots,
)

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _edge_gaps(centers, widths):
    return [
        (centers[i + 1] - widths[i + 1] / 2.0) - (centers[i] + widths[i] / 2.0)
        for i in range(len(centers) - 1)
    ]


def test_five_box_layout_uses_equal_visual_edge_gaps_around_selected_item():
    widths = [150.0, 205.0, 390.0, 225.0, 142.0]
    centers = anchored_equal_gap_centers(
        widths,
        anchor_index=2,
        viewport_width=1320.0,
        desired_gap=24.0,
        padding=18.0,
        anchor_x=0.50,
    )

    gaps = _edge_gaps(centers, widths)
    assert len(centers) == 5
    assert max(gaps) - min(gaps) < 1e-6
    assert abs(centers[2] - 660.0) < 1e-6
    assert centers[0] < centers[1] < centers[2] < centers[3] < centers[4]


def test_small_carousel_segment_exits_one_side_and_enters_the_other_without_wrapped_jump():
    slots = carousel_slots(4)
    assert slots == (-1, 0, 1, 2)

    start_base, end_base, progress = carousel_segment(0.35, direction=1)
    assert (start_base, end_base) == (0, 1)
    assert 0.34 < progress < 0.36

    start_seq = tuple(start_base + slot for slot in slots)
    end_seq = tuple(end_base + slot for slot in slots)
    # Forward motion shares the middle three sequence instances.  The old
    # left-most instance can leave the viewport while a new right-most copy
    # enters, instead of one box teleporting across the window.
    assert start_seq == (-1, 0, 1, 2)
    assert end_seq == (0, 1, 2, 3)
    assert set(start_seq) & set(end_seq) == {0, 1, 2}
    assert set(start_seq) - set(end_seq) == {-1}
    assert set(end_seq) - set(start_seq) == {3}


def test_reverse_carousel_segment_is_symmetric_and_continuous():
    start_base, end_base, progress = carousel_segment(-0.35, direction=-1)
    assert (start_base, end_base) == (0, -1)
    assert 0.34 < progress < 0.36


def test_background_removes_extra_radial_glow_and_stage_layers():
    source = read("app/ui/retro_showcase.py")
    block = source.split("def _draw_background", 1)[1].split("def _draw_focus_backdrop", 1)[0]
    assert "glow = QRadialGradient" not in block
    assert "stage = QRadialGradient" not in block
    assert "self._draw_ambient_waves" in block


def test_v7_log_is_packaged():
    log = read("docs/development-logs/Retro_Prototype_v7.md")
    assert "v0.5.0.6" in log
    assert "CLEAN AMBIENT" in log
    assert "EDGE GAP RAIL" in log
    assert "SEAMLESS WRAP" in log
