from __future__ import annotations

from pathlib import Path


def test_flat_pro_is_registered_as_a_selectable_skin() -> None:
    from app.config.theme_registry import THEMES, theme_options

    assert "flat_pro" in THEMES
    assert ("flat_pro", "Flat Pro") in theme_options()


def test_skin_metrics_cover_titlebar_and_navigation_height() -> None:
    from app.config.theme_registry import THEMES

    metrics = THEMES["flat_pro"].metrics
    assert metrics.titlebar_height >= 34
    assert metrics.nav_height >= 40


def test_flat_pro_owns_chrome_and_inset_navigation_tokens() -> None:
    from app.config.theme_registry import THEMES

    theme = THEMES["flat_pro"]
    assert theme.chrome_surface.startswith("#")
    assert theme.chrome_border.startswith("#")
    assert theme.nav_selected_bg.startswith("#")
    assert theme.nav_inset_dark.startswith("#")
    assert theme.nav_inset_light.startswith("#")


def test_window_edge_zone_handles_rectangular_frameless_resize() -> None:
    from app.ui.window_hit_test import edge_zone

    assert edge_zone(1000, 700, 2, 2, 7) == "top_left"
    assert edge_zone(1000, 700, 998, 2, 7) == "top_right"
    assert edge_zone(1000, 700, 2, 698, 7) == "bottom_left"
    assert edge_zone(1000, 700, 998, 698, 7) == "bottom_right"
    assert edge_zone(1000, 700, 500, 2, 7) == "top"
    assert edge_zone(1000, 700, 500, 350, 7) is None


def test_main_window_uses_own_titlebar_and_native_edge_hit_test() -> None:
    source = Path("app/ui/main_window.py").read_text(encoding="utf-8")
    assert "FramelessWindowHint" in source
    assert "AppTitleBar" in source
    assert "self.title_bar = AppTitleBar" in source
    assert "def nativeEvent" in source
    assert "WM_NCHITTEST" in source
    assert "edge_zone" in source


def test_titlebar_delegates_drag_to_the_window_system() -> None:
    source = Path("app/ui/app_chrome.py").read_text(encoding="utf-8")
    assert "class AppTitleBar" in source
    assert "startSystemMove" in source
    assert "showMinimized" in source
    assert "showMaximized" in source
    assert "showNormal" in source
    assert "host_window.close" in source


def test_flat_pro_navigation_checked_state_has_inset_bevel() -> None:
    source = Path("app/ui/flat_theme.py").read_text(encoding="utf-8")
    assert "NAV_SELECTED_BG" in source
    assert "NAV_INSET_DARK" in source
    assert "NAV_INSET_LIGHT" in source
    assert "border-top-color" in source
    assert "border-left-color" in source
    assert "border-right-color" in source
    assert "border-bottom-color" in source


def test_v0410_version_is_visible_and_declared() -> None:
    main_source = Path("app/ui/main_window.py").read_text(encoding="utf-8")
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "v0.4.3.1.1" in main_source
    assert 'version = "0.4.3.1.1"' in pyproject


def test_flat_pro_inset_navigation_does_not_restyle_existing_flat_skins() -> None:
    from app.config.theme_registry import THEMES

    assert THEMES["flat_pro"].nav_style == "sunken_card"
    assert THEMES["flat_pro_light"].nav_style == "sunken_card"
    assert THEMES["flat_pro_light"].motion_level == "full"
