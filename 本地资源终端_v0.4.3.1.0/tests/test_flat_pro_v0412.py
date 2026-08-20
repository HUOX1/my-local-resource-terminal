from __future__ import annotations

from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_v0412_version_is_visible_and_declared() -> None:
    assert 'version = "0.4.3.0.3"' in read("pyproject.toml")
    assert "v0.4.3.0.3" in read("app/ui/main_window.py")
    assert "v0.4.3.0.3" in read("app/ui/app_chrome.py")


def test_pressed_card_treatment_remains_available_without_owning_flat_pro() -> None:
    from app.config.theme_registry import THEMES

    assert THEMES["flat_pro"].nav_style == "sunken_card"
    assert THEMES["flat_pro_light"].nav_style == "sunken_card"
    assert THEMES["flat_pro_light"].motion_level == "full"
    source = read("app/ui/navigation_button.py")
    assert 'FlatTokens.NAV_STYLE == "pressed_card"' in source
    assert "_paint_pressed_card" in source


def test_pressed_card_navigation_draws_a_face_highlight_and_drop_edge() -> None:
    source = read("app/ui/navigation_button.py")
    assert 'FlatTokens.NAV_STYLE == "pressed_card"' in source
    assert "_paint_pressed_card" in source
    assert "drawRoundedRect" in source
    assert "NAV_SELECTED_BG" in source
    assert "NAV_INSET_LIGHT" in source
    assert "NAV_INSET_DARK" in source
    assert "card_rect" in source
    assert "shadow_rect" in source


def test_pressed_card_checked_qss_keeps_the_face_for_custom_painting() -> None:
    source = read("app/ui/flat_theme.py")
    assert 'elif t.NAV_STYLE == "pressed_card"' in source
    assert "background: transparent;" in source
    assert "padding-top: 1px;" in source


def test_minimize_glyph_is_shorter_than_old_em_dash() -> None:
    source = read("app/ui/app_chrome.py")
    assert 'self._make_button("-", "最小化")' in source
    assert 'self._make_button("—", "最小化")' not in source
