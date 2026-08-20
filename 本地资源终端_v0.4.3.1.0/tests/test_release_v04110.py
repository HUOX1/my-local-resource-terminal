from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v04110_is_visible_in_project_window_and_chrome():
    assert 'version = "0.4.3.0.3"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'v0.4.3.0.3' in (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert 'v0.4.3.0.3' in (ROOT / "app" / "ui" / "app_chrome.py").read_text(encoding="utf-8")


def test_v04110_inline_movie_archive_editing_still_exists_in_runtime():
    page = (ROOT / "app" / "ui" / "movie_archive_page.py").read_text(encoding="utf-8")
    assert "InlineEditableField" in page
    assert "StarRatingEditor" in page
    assert "metadata_patch_requested = Signal(str, object)" in page
    assert "本地媒体" in page
