from app.ui.retro_showcase_state import cycle_index, format_duration, neighbor_indices


def test_cycle_index_wraps_arc_collection():
    assert cycle_index(0, 5, -1) == 4
    assert cycle_index(4, 5, 1) == 0
    assert cycle_index(2, 5, 2) == 4


def test_neighbor_indices_handle_small_collections():
    assert neighbor_indices(0, 0) == (None, None, None)
    assert neighbor_indices(0, 1) == (None, 0, None)
    assert neighbor_indices(0, 3) == (2, 0, 1)


def test_format_duration_prefers_compact_console_readout():
    assert format_duration(0) == "0 min"
    assert format_duration(35 * 60) == "35 min"
    assert format_duration(3600) == "1 h"
    assert format_duration(3 * 3600 + 30 * 60) == "3.5 h"
