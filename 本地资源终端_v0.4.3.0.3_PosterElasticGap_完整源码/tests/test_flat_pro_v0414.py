from pathlib import Path


def read(rel: str) -> str:
    return Path(rel).read_text(encoding="utf-8")


def test_version_bumped_to_v0414() -> None:
    assert 'version = "0.4.3.0.3"' in read("pyproject.toml")
    assert 'v0.4.3.0.3' in read("app/ui/main_window.py")
    assert 'v0.4.3.0.3' in read("app/ui/app_chrome.py")


def test_flat_pro_nav_polish_source() -> None:
    source = read("app/ui/navigation_button.py")
    assert 'subtle depressed card with slightly clearer separation from the rail' in source
    assert 'glaze = QColor(FlatTokens.BORDER_STRONG)' in source
    theme_source = read("app/config/theme_registry.py")
    assert 'nav_selected_bg="#12161B"' in theme_source
