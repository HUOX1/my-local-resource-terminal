from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def function_block(source: str, name: str, next_name: str) -> str:
    start = source.index(f"    def {name}(")
    end = source.index(f"    def {next_name}(", start)
    return source[start:end]


def test_native_resize_applies_layout_immediately_without_reflow_animation():
    source = read("app/ui/poster_view.py")
    resize_block = function_block(source, "resizeEvent", "eventFilter")

    assert "self._apply_poster_layout(animate=False)" in resize_block
    assert "_resize_layout_timer" not in resize_block


def test_poster_height_measurements_are_cached_between_resize_events():
    source = read("app/ui/poster_view.py")

    assert "self._item_height_cache" in source
    assert "def _invalidate_item_height_cache" in source
    assert "def _poster_item_heights" in source
    assert "item_heights = self._poster_item_heights()" in source


def test_model_changes_invalidate_height_cache_before_scheduling_layout():
    source = read("app/ui/poster_view.py")
    schedule_block = function_block(source, "_schedule_poster_layout", "setModel")

    assert "self._invalidate_item_height_cache()" in schedule_block


def test_non_animated_layout_clears_any_inflight_reflow_offset():
    source = read("app/ui/poster_view.py")
    apply_block = function_block(source, "_apply_poster_layout", "_start_reflow_motion")

    assert "def _apply_poster_layout(self, *, animate: bool = True)" in source
    assert "if not animate:" in apply_block
    assert "self._reflow_offsets.clear()" in apply_block
    assert "self._reflow_progress = 1.0" in apply_block


def test_release_is_v04301():
    assert 'version = "0.4.3.1.1"' in read("pyproject.toml")
    assert "v0.4.3.1.1" in read("app/ui/main_window.py")
    assert "v0.4.3.1.1" in read("app/ui/app_chrome.py")
