from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_sidebar_motion_progress_is_continuous_across_drag_range():
    from app.ui.sidebar_motion import sidebar_motion_progress

    assert sidebar_motion_progress(72, minimum=72, expanded=196) == 0.0
    assert sidebar_motion_progress(196, minimum=72, expanded=196) == 1.0
    middle = sidebar_motion_progress(134, minimum=72, expanded=196)
    assert 0.49 < middle < 0.51


def test_navigation_button_can_fade_text_while_icon_moves_without_resizing_sidebar():
    source = read("app/ui/navigation_button.py")
    assert "def set_sidebar_motion_progress(" in source
    assert "self._sidebar_motion_progress" in source
    assert "QStyleOptionButton" in source
    assert "option.text = \"\"" in source
    assert "option.icon = QIcon()" in source
    assert "painter.setOpacity(text_progress)" in source
    assert "icon_x =" in source


def test_identity_room_uses_continuous_sidebar_progress_instead_of_binary_visibility():
    source = read("app/ui/identity_shell.py")
    assert "def set_motion_progress(" in source
    assert "QGraphicsOpacityEffect" in source
    assert "self.text_container.setVisible(progress > 0.0)" in source
    assert "effect.setOpacity(text_progress)" in source


def test_main_window_drives_sidebar_motion_directly_from_splitter_width_for_flat_pro():
    source = read("app/ui/main_window.py")
    assert "def _update_sidebar_motion(" in source
    assert "sidebar_motion_progress(" in source
    assert "self.movie_library_button.set_sidebar_motion_progress(progress)" in source
    assert "self.game_library_button.set_sidebar_motion_progress(progress)" in source
    assert "self.settings_button.set_sidebar_motion_progress(progress)" in source
    assert "self.identity_room.set_motion_progress(progress)" in source
    assert "self.main_splitter.sidebar_width_changed.connect(self._update_sidebar_motion)" in source
    assert "splitterMoved.connect" not in source


def test_release_is_v0422():
    assert 'version = "0.4.3.0.3"' in read("pyproject.toml")
    assert "v0.4.3.0.3" in read("app/ui/main_window.py")
    assert "v0.4.3.0.3" in read("app/ui/app_chrome.py")


def test_motion_navigation_buttons_do_not_keep_text_based_minimum_width():
    source = read("app/ui/navigation_button.py")
    assert "def minimumSizeHint(" in source
    assert "hint.setWidth(0)" in source
