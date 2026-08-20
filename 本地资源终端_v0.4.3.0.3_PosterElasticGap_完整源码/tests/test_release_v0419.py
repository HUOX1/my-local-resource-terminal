from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v0419_is_visible_in_project_window_and_chrome():
    assert 'version = "0.4.3.0.3"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'v0.4.3.0.3' in (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert 'v0.4.3.0.3' in (ROOT / "app" / "ui" / "app_chrome.py").read_text(encoding="utf-8")


def test_v0419_folders_and_movie_archive_page_still_exist_in_runtime():
    main = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    page = (ROOT / "app" / "ui" / "movie_archive_page.py").read_text(encoding="utf-8")
    assert "collection_folders" in main
    assert "new_folder_button" in main
    assert "MovieArchivePage" in main
    assert 'setObjectName("movieArchivePage")' in page
