from __future__ import annotations

from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_v0411_version_is_visible_and_declared() -> None:
    assert 'version = "0.4.3.0.3"' in read("pyproject.toml")
    assert "v0.4.3.0.3" in read("app/ui/main_window.py")
    assert "v0.4.3.0.3" in read("app/ui/app_chrome.py")


def test_sidebar_system_room_stays_with_navigation_and_debug_version_is_removed() -> None:
    source = read("app/ui/main_window.py")
    system_pos = source.index('self.system_section_label = QLabel("系统")')
    stretch_pos = source.index("sidebar_layout.addStretch(1)")
    assert system_pos < stretch_pos
    assert 'QLabel("本地资源终端 · v0.4.3.0.3")' not in source


def test_primary_library_navigation_uses_inset_capable_component() -> None:
    source = read("app/ui/main_window.py")
    assert "from app.ui.navigation_button import NavigationButton" in source
    assert 'self.movie_library_button = NavigationButton("影片")' in source
    assert 'self.game_library_button = NavigationButton("游戏")' in source


def test_inset_navigation_component_draws_inner_shadow_only_for_inset_skin() -> None:
    source = read("app/ui/navigation_button.py")
    assert 'FlatTokens.NAV_STYLE == "inset"' in source
    assert "self.isChecked()" in source
    assert "QPainter" in source
    assert "NAV_INSET_DARK" in source
    assert "NAV_INSET_LIGHT" in source
    assert "drawLine" in source


def test_flat_pro_pressed_states_have_physical_feedback() -> None:
    source = read("app/ui/flat_theme.py")
    assert "button_pressed_style" in source
    assert "padding-top: 1px" in source
    assert "border-top-color" in source
    assert "border-bottom-color" in source
    assert "QPushButton#titleBarButton:pressed" in source
