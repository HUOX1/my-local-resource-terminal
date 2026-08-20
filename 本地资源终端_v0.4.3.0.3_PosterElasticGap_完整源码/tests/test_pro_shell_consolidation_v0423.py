from pathlib import Path

from app.config.theme_registry import THEMES, resolve_theme_id, theme_options


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_theme_registry_consolidates_to_pro_dark_and_pro_light_with_legacy_migration():
    assert set(THEMES) == {"flat_pro", "flat_pro_light"}
    assert theme_options() == [("flat_pro", "Flat Pro"), ("flat_pro_light", "Flat Pro Light")]
    assert THEMES["flat_pro"].motion_level == "full"
    assert THEMES["flat_pro_light"].motion_level == "full"
    assert THEMES["flat_pro"].nav_style == "sunken_card"
    assert THEMES["flat_pro_light"].nav_style == "sunken_card"
    assert resolve_theme_id("flat_dark") == "flat_pro"
    assert resolve_theme_id("flat_light") == "flat_pro_light"
    assert resolve_theme_id("missing-theme") == "flat_pro"


def test_sidebar_is_two_state_and_uses_a_center_toggle_handle_instead_of_free_drag():
    splitter = read("app/ui/sidebar_splitter.py")
    main = read("app/ui/main_window.py")
    theme = read("app/ui/flat_theme.py")

    assert "class TwoStateSidebarSplitter" in splitter
    assert "COMPACT_WIDTH = 72" in splitter
    assert "toggle_sidebar" in splitter
    assert "QVariantAnimation" in splitter
    assert "QEasingCurve.Type.OutCubic" in splitter
    assert "class SidebarToggleHandle" in splitter
    assert 'def paintEvent(' in splitter
    assert 'QPolygonF' in splitter
    assert "mouseMoveEvent" in splitter and "event.accept()" in splitter
    assert "TwoStateSidebarSplitter(Qt.Orientation.Horizontal)" in main
    assert "splitterMoved.connect" not in main
    assert "sidebar_width_changed.connect(self._update_sidebar_motion)" in main
    assert "QPushButton#sidebarToggleHandle" not in theme


def test_movie_and_game_archive_pages_hide_horizontal_scrollbars_and_reflow_when_narrow():
    movie = read("app/ui/movie_archive_page.py")
    game = read("app/ui/game_archive_page.py")

    for source in (movie, game):
        assert "setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)" in source
        assert "def _apply_responsive_layout(" in source
        assert "QBoxLayout.Direction.TopToBottom" in source
        assert "QBoxLayout.Direction.LeftToRight" in source


def test_v0423_version_is_visible_in_project_and_chrome():
    assert 'version = "0.4.3.0.3"' in read("pyproject.toml")
    assert "v0.4.3.0.3" in read("app/ui/main_window.py")
    assert "v0.4.3.0.3" in read("app/ui/app_chrome.py")
