from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_pro_dark_and_light_share_the_same_full_motion_profile():
    from app.config.theme_registry import THEMES

    theme = read("app/ui/flat_theme.py")
    assert THEMES["flat_pro"].motion_level == "full"
    assert THEMES["flat_pro_light"].motion_level == "full"
    assert THEMES["flat_pro"].nav_style == "sunken_card"
    assert THEMES["flat_pro_light"].nav_style == "sunken_card"
    assert 'MOTION_LEVEL = "full"' in theme
    assert '"MOTION_LEVEL": spec.motion_level' in theme


def test_poster_wall_uses_one_continuous_motion_timer_for_inertia_hover_and_reflow():
    source = read("app/ui/poster_view.py")
    assert 'MOTION_TICK_MS = 16' in source
    assert 'self._motion_timer = QTimer(self)' in source
    assert 'self._motion_timer.timeout.connect(self._motion_tick)' in source
    assert 'def wheelEvent' in source
    assert 'self._scroll_velocity' in source
    assert 'self._motion_timer.start()' in source
    assert 'QPropertyAnimation' not in source
    assert 'def hover_progress' in source
    assert 'def motion_offset' in source
    assert 'self._capture_visible_rects()' in source
    assert 'self._start_reflow_motion(' in source


def test_movie_and_game_delegates_consume_hover_and_reflow_motion_without_resizing_cards():
    for rel in ("app/ui/movie_delegate.py", "app/ui/game_delegate.py"):
        source = read(rel)
        assert 'hover_progress = getattr(' in source
        assert 'motion_offset = getattr(' in source
        assert 'translated(' in source
        assert 'HOVER_SCALE' in source
        assert 'HOVER_LIFT' in source
        size_hint = source.split('def sizeHint', 1)[1].split('def paint', 1)[0]
        assert 'hover_progress' not in size_hint
        assert 'motion_offset' not in size_hint


def test_archive_page_switches_use_shared_flat_pro_transition_helper():
    motion = read("app/ui/motion.py")
    main = read("app/ui/main_window.py")
    assert 'def transition_stack_page(' in motion
    assert 'QGraphicsOpacityEffect' in motion
    assert 'QParallelAnimationGroup' in motion
    assert 'transition_stack_page(self.content_page_stack, self.movie_archive_page' in main
    assert 'transition_stack_page(self.content_page_stack, self.game_archive_page' in main
    assert 'transition_stack_page(self.content_page_stack, self.library_page' in main


def test_movie_context_menus_no_longer_offer_favorite_or_watched_actions():
    source = read("app/ui/main_window.py")
    single = source.split('def _show_movie_context_menu', 1)[1].split('def _ensure_context_row_selected', 1)[0]
    batch = source.split('def _populate_batch_menu', 1)[1].split('def _batch_tags', 1)[0]
    for forbidden in ('取消收藏', '收藏', '标记未观看', '标记已观看'):
        assert forbidden not in single
        assert forbidden not in batch


def test_release_is_v0420():
    assert 'version = "0.4.3.1.1"' in read("pyproject.toml")
    assert 'v0.4.3.1.1' in read("app/ui/main_window.py")
    assert 'v0.4.3.1.1' in read("app/ui/app_chrome.py")


def test_hover_motion_timer_can_sleep_while_pointer_is_stationary():
    source = read("app/ui/poster_view.py")
    assert 'hover_animating = False' in source
    assert 'hover_animating = True' in source
    stop_block = source.split('if (', 1)[-1] if False else source
    assert 'and not hover_animating' in source


def test_archive_transition_cleans_up_interrupted_previous_effect():
    source = read("app/ui/motion.py")
    assert '_flat_pro_transition_cleanup' in source
    assert 'previous_cleanup = getattr(' in source
    assert 'previous_cleanup()' in source
