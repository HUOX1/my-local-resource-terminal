from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_poster_walls_scroll_per_pixel_with_small_explicit_step():
    source = read("app/ui/main_window.py")
    assert "setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)" in source
    assert "verticalScrollBar().setSingleStep(28)" in source


def test_v04111_is_visible_in_project_window_and_chrome():
    assert 'version = "0.4.3.0.3"' in read("pyproject.toml")
    assert "v0.4.3.0.3" in read("app/ui/main_window.py")
    assert "v0.4.3.0.3" in read("app/ui/app_chrome.py")
