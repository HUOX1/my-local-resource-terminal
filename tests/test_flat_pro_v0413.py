from __future__ import annotations

from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_v0413_version_is_visible_and_declared() -> None:
    assert 'version = "0.4.3.1.1"' in read("pyproject.toml")
    assert "v0.4.3.1.1" in read("app/ui/main_window.py")
    assert "v0.4.3.1.1" in read("app/ui/app_chrome.py")


def test_flat_pro_uses_low_contrast_sunken_card_navigation() -> None:
    from app.config.theme_registry import THEMES

    spec = THEMES["flat_pro"]
    assert spec.nav_style == "sunken_card"
    assert spec.nav_selected_bg == "#12161B"
    assert spec.surface == "#171A1F"
    assert THEMES["flat_pro_light"].nav_style == "sunken_card"
    assert THEMES["flat_pro_light"].motion_level == "full"


def test_sunken_card_has_no_external_drop_shadow() -> None:
    source = read("app/ui/navigation_button.py")
    assert 'FlatTokens.NAV_STYLE == "sunken_card"' in source
    assert "_paint_sunken_card" in source
    section = source.split("def _paint_sunken_card", 1)[1].split("def _paint_pressed_card", 1)[0]
    assert "NAV_SELECTED_BG" in section
    assert "NAV_INSET_DARK" in section
    assert "NAV_INSET_LIGHT" in section
    assert "shadow_rect" not in section
    assert ".translated(" not in section


def test_sunken_card_checked_qss_keeps_subtle_pressed_offset() -> None:
    source = read("app/ui/flat_theme.py")
    assert 'elif t.NAV_STYLE == "sunken_card"' in source
    branch = source.split('elif t.NAV_STYLE == "sunken_card"', 1)[1].split("elif t.NAV_STYLE", 1)[0]
    assert "background: transparent;" in branch
    assert "padding-top: 1px;" in branch
    assert "padding-left: 14px;" in branch


def test_sunken_card_can_accent_only_the_selected_navigation_icon() -> None:
    nav_source = read("app/ui/navigation_button.py")
    main_source = read("app/ui/main_window.py")
    assert "def set_nav_icon" in nav_source
    assert "self.toggled.connect(self._refresh_nav_icon)" in nav_source
    assert 'FlatTokens.NAV_STYLE == "sunken_card" and self.isChecked()' in nav_source
    assert "color=FlatTokens.ACCENT" in nav_source
    assert "button.set_nav_icon(icon_name)" in main_source
