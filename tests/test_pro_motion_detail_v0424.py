from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_sidebar_toggle_is_a_custom_painted_trapezoid_that_switches_sides():
    source = read("app/ui/sidebar_splitter.py")
    theme = read("app/ui/flat_theme.py")

    assert "def paintEvent(" in source
    assert "QPolygonF" in source
    assert "_trapezoid_points" in source
    assert "if self._expanded" in source
    assert '"‹" if self._expanded else "›"' in source
    assert "QPushButton" not in source
    assert "QPushButton#sidebarToggleHandle" not in theme


def test_archive_responsive_reflow_is_debounced_and_animated_instead_of_instant():
    motion = read("app/ui/motion.py")
    assert "def animate_responsive_reflow(" in motion
    assert "QGraphicsOpacityEffect" in motion
    assert "QParallelAnimationGroup" in motion

    for rel in ("app/ui/movie_archive_page.py", "app/ui/game_archive_page.py"):
        source = read(rel)
        assert "self._responsive_timer = QTimer(self)" in source
        assert "self._responsive_timer.setSingleShot(True)" in source
        assert "self._pending_responsive_narrow" in source
        assert "def _commit_responsive_layout(" in source
        assert "animate_responsive_reflow(" in source


def test_motion_detail_animates_identity_tools_menus_and_inline_editing():
    motion = read("app/ui/motion.py")
    main = read("app/ui/main_window.py")
    movie = read("app/ui/movie_archive_page.py")

    assert "def show_popup_with_motion(" in motion
    assert "def exec_menu_with_motion(" in motion
    assert "def pulse_opacity(" in motion
    assert "transition_stack_page(self.root_stack, self.main_shell" in main
    assert "show_popup_with_motion(self.library_tools_popup" in main
    assert main.count("exec_menu_with_motion(menu,") >= 2
    assert "transition_stack_page(" in movie
    assert "pulse_opacity(" in movie


def test_game_archive_hero_crossfades_media_switches():
    source = read("app/ui/game_archive_page.py")
    assert "QVariantAnimation" in source
    assert "self._previous_pixmap" in source
    assert "self._media_mix" in source
    assert "def _start_media_crossfade(" in source
    assert "painter.setOpacity(" in source
    assert "self.hero.set_media(path, animated=True)" in source


def test_release_is_v0424():
    assert 'version = "0.4.3.0.3"' in read("pyproject.toml")
    assert "v0.4.3.0.3" in read("app/ui/main_window.py")
    assert "v0.4.3.0.3" in read("app/ui/app_chrome.py")
