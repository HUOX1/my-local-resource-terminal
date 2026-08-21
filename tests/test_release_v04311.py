from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_version_is_v04311_everywhere_visible() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    main_window = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    chrome = (ROOT / "app" / "ui" / "app_chrome.py").read_text(encoding="utf-8")

    assert 'version = "0.4.3.1.1"' in project
    assert 'self.setWindowTitle("本地资源终端 · v0.4.3.1.1")' in main_window
    assert 'QLabel("v0.4.3.1.1")' in chrome
