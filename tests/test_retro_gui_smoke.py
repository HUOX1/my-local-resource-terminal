from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace

# The launcher/environment chooses the Qt platform. CI sets offscreen; local Windows uses the native windows plugin.
os.environ.setdefault("PYTHONFAULTHANDLER", "1")

from PySide6.QtCore import QEvent, QObject, QPoint, QRectF, Qt
from PySide6.QtGui import QFont, QFontMetrics, QImage, QPainter
from PySide6.QtWidgets import QApplication, QMainWindow, QScrollArea, QWidget
from PySide6.QtTest import QSignalSpy, QTest

from app.models.game import GameMetadata
from app.models.movie import MovieMetadata
from app.ui.retro_edit_dialogs import RetroGameArchiveEditDialog, RetroMovieArchiveEditDialog
from app.ui.retro_showcase import RetroShowcaseOverlay
from app.services.sound_pack_store import SOUND_EVENTS
from app.ui.retro_showcase_state import (
    RETRO_MIN_WINDOW_HEIGHT,
    RETRO_MIN_WINDOW_WIDTH,
    focus_info_layout,
)


ARTIFACT_DIR = Path(os.environ.get("RETRO_SMOKE_ARTIFACT_DIR", "artifacts/retro-smoke"))


class QtExceptionTrap:
    """Collect Python exceptions routed through sys.excepthook by Qt callbacks."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self._previous = None

    def __enter__(self) -> "QtExceptionTrap":
        self._previous = sys.excepthook

        def hook(exc_type, exc_value, exc_tb) -> None:
            self.errors.append("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))

        sys.excepthook = hook
        return self

    def __exit__(self, exc_type, exc_value, exc_tb) -> bool:
        if self._previous is not None:
            sys.excepthook = self._previous
        return False


class FakeGameCatalog:
    def __init__(self, records) -> None:
        self._records = list(records)
        self.last_search = ""

    def list_games(self, search="", *_args, **_kwargs):
        self.last_search = str(search)
        if not self.last_search:
            return list(self._records)
        needle = self.last_search.casefold()
        return [record for record in self._records if needle in record.metadata.title.casefold()]

    def common_tags(self, _limit: int = 20):
        return []


class FakeMovieCatalog:
    def list_movies(self, *_args, **_kwargs):
        return []

    def common_tags(self, _limit: int = 20):
        return []


class FakeHost(QMainWindow):
    def __init__(self, records) -> None:
        super().__init__()
        self.setCentralWidget(QWidget(self))
        self.settings = SimpleNamespace(
            game_filter="all",
            movie_filter="all",
            game_sort_key="last_played_at",
            sort_key="last_watched_at",
            game_sort_desc=True,
            sort_desc=True,
            game_folder_id=None,
            movie_folder_id=None,
            libraries=[],
            data_dir=ARTIFACT_DIR / "data",
            ffmpeg_path="ffmpeg",
        )
        self.game_catalog = FakeGameCatalog(records)
        self.catalog = FakeMovieCatalog()
        self.collection_folders = None
        self.title_bar = None
        self.launch_count = 0
        self.play_count = 0

    def _launch_game(self, _record) -> None:
        self.launch_count += 1

    def _play_record(self, _record) -> None:
        self.play_count += 1


def make_game_record(title: str = "God of War"):
    metadata = SimpleNamespace(
        uuid="smoke-game",
        title=title,
        cover_path=None,
        tags=["PS2"],
        total_play_seconds=660,
        developer="Santa Monica Studio",
        publisher="Sony Computer Entertainment",
        release_date="2005-03-22",
        description="Smoke test record used to exercise the Retro drawing pipeline.",
        notes="",
        play_count=3,
        first_played_at=None,
        last_played_at=None,
        launch_exe=None,
        timing_exe=None,
        screenshot_directory=None,
    )
    return SimpleNamespace(metadata=metadata, installed=False)


def get_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def make_overlay() -> tuple[QApplication, FakeHost, RetroShowcaseOverlay]:
    app = get_app()
    record = make_game_record()
    host = FakeHost([record])
    host.resize(1320, 840)
    host.show()
    app.processEvents()

    overlay = RetroShowcaseOverlay(host, host.centralWidget())
    overlay.show()
    overlay.raise_()
    app.processEvents()
    assert overlay.current_record() is not None
    return app, host, overlay


def _save_image(image: QImage, name: str) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    assert image.save(str(ARTIFACT_DIR / f"{name}.png"))


def render_scene(overlay: RetroShowcaseOverlay, name: str) -> QImage:
    """Render the same scene stages as paintEvent into a QImage.

    Calling the Python drawing methods directly makes runtime TypeError/value
    errors propagate to pytest instead of being swallowed by the Qt event loop.
    """
    image = QImage(max(1, overlay.width()), max(1, overlay.height()), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        overlay._draw_background(painter)
        if overlay.focused and not overlay.details_open and not overlay.system_open:
            overlay._draw_focus_backdrop(painter)

        showcase_opacity = 1.0 - 0.42 * overlay._panel_progress if overlay._panel_mode == "system" else 1.0
        painter.save()
        painter.setOpacity(showcase_opacity)
        overlay._draw_showcase(painter)
        painter.restore()


        if overlay.focused and not overlay.details_open and not overlay.system_open:
            overlay._draw_focus_info(painter)
        if overlay._panel_mode == "details" and overlay._panel_progress > 0.001:
            overlay._draw_detail_panel(painter)
        if overlay._panel_mode == "system" and overlay._panel_progress > 0.001:
            overlay._draw_system_panel(painter)
        overlay._draw_corner_menu(painter)
        overlay._draw_window_controls(painter)
    finally:
        painter.end()
    _save_image(image, name)
    return image


def test_scene_draw_pipeline_exercises_focus_details_and_chrome():
    app, host, overlay = make_overlay()
    try:
        # Browse state: proves the core package rendering path itself runs.
        render_scene(overlay, "01-browse")
        assert not overlay._main_rect.isNull()

        # Focus state: the regression in v0.5.0.8 made this disappear after the
        # showcase draw failed, so require the MORE hit target to be populated.
        overlay.focused = True
        overlay._focus_progress = 1.0
        overlay.details_open = False
        overlay.system_open = False
        overlay._panel_mode = None
        overlay._panel_progress = 0.0
        render_scene(overlay, "02-focus")
        assert not overlay._more_rect.isNull()

        # MORE/details panel must survive the same frame after package drawing.
        overlay.details_open = True
        overlay._panel_mode = "details"
        overlay._panel_progress = 1.0
        render_scene(overlay, "03-details")
        assert not overlay._detail_panel_rect.isNull()
        assert "概览" in overlay._detail_tab_rects

        # System panel and both hidden chrome families are drawn after the
        # showcase, making them useful canaries for a broken paint chain.
        overlay.details_open = False
        overlay.system_open = True
        overlay._panel_mode = "system"
        overlay._panel_progress = 1.0
        overlay._menu_opacity = 1.0
        overlay._window_controls_visible = True
        render_scene(overlay, "04-system-chrome")
        assert not overlay._system_panel_rect.isNull()
        assert set(overlay._menu_button_rects) == {"movies", "games", "settings"}
        assert set(overlay._window_control_rects) == {"min", "max", "close"}
    finally:
        host.close()
        app.processEvents()


def test_real_widget_resize_and_repaint_does_not_route_python_exceptions():
    app, host, overlay = make_overlay()
    try:
        overlay.focused = True
        overlay._focus_progress = 1.0
        overlay._menu_opacity = 1.0
        overlay._window_controls_visible = True

        # Include the intended minimum-like size plus larger/common viewports.
        sizes = [
            (1320, 840),
            (1180, 720),
            (1100, 700),
            (1440, 900),
            (1600, 900),
            (1280, 760),
        ]
        with QtExceptionTrap() as trap:
            for width, height in sizes:
                host.resize(width, height)
                app.processEvents()
                parent = host.centralWidget()
                assert overlay.geometry() == QRectF(0, 0, parent.width(), parent.height()).toRect()
                overlay.repaint()
                app.processEvents()

            # QWidget::grab forces another actual paint event and leaves a CI
            # screenshot that can be inspected when a future regression occurs.
            pixmap = overlay.grab()
            assert not pixmap.isNull()
            ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
            assert pixmap.save(str(ARTIFACT_DIR / "05-real-widget.png"))

        assert not trap.errors, "Qt callback exception(s):\n" + "\n".join(trap.errors)
    finally:
        host.close()
        app.processEvents()


def test_archive_edit_dialogs_build_scroll_and_metadata_patches():
    app = get_app()

    game = GameMetadata.new("Smoke Game")
    game.series = "Smoke Series"
    game.developer = "Smoke Dev"
    game.publisher = "Smoke Pub"
    game.tags = ["PS2", "Action"]
    game.description = "Game description"
    game.notes = "Game notes"
    game.launch_exe = r"C:\\Games\\Smoke\\smoke.exe"
    game.timing_exe = game.launch_exe
    game.working_directory = r"C:\\Games\\Smoke"
    game.screenshot_directory = r"C:\\Games\\Smoke\\screens"

    game_dialog = RetroGameArchiveEditDialog(game)
    try:
        game_dialog.show()
        app.processEvents()
        screen = app.primaryScreen()
        if screen is not None:
            assert game_dialog.height() <= screen.availableGeometry().height()
        scroll = game_dialog.findChild(QScrollArea, "archiveEditScroll")
        assert scroll is not None
        assert scroll.widgetResizable()
        game_dialog.title_edit.setText("Smoke Game Updated")
        game_dialog.tags_edit.setText("PS2，Action、Retro")
        game_dialog._accept()
        assert game_dialog.result_patch.title == "Smoke Game Updated"
        assert game_dialog.result_patch.tags == ["PS2", "Action", "Retro"]
    finally:
        game_dialog.close()
        app.processEvents()

    movie = MovieMetadata.new("SMOKE-COVER", code="SM-001")
    movie.title = "Smoke Movie"
    movie.actors = ["Actor A"]
    movie.tags = ["Drama"]
    movie.notes = "Movie notes"

    movie_dialog = RetroMovieArchiveEditDialog(movie)
    try:
        movie_dialog.show()
        app.processEvents()
        screen = app.primaryScreen()
        if screen is not None:
            assert movie_dialog.height() <= screen.availableGeometry().height()
        scroll = movie_dialog.findChild(QScrollArea, "archiveEditScroll")
        assert scroll is not None
        assert scroll.widgetResizable()
        movie_dialog.title_edit.setText("Smoke Movie Updated")
        movie_dialog.actors_edit.setText("Actor A，Actor B")
        movie_dialog._accept()
        assert movie_dialog.result_patch.title == "Smoke Movie Updated"
        assert movie_dialog.result_patch.actors == ["Actor A", "Actor B"]
    finally:
        movie_dialog.close()
        app.processEvents()


def test_minimum_window_and_long_focus_title_layout():
    app = get_app()
    long_title = "The Legend of Heroes Trails Through Daybreak II Ultimate Collection"
    record = make_game_record(long_title)
    host = FakeHost([record])
    host.setMinimumSize(RETRO_MIN_WINDOW_WIDTH, RETRO_MIN_WINDOW_HEIGHT)
    host.resize(900, 540)
    host.show()
    app.processEvents()
    try:
        assert host.width() >= RETRO_MIN_WINDOW_WIDTH
        assert host.height() >= RETRO_MIN_WINDOW_HEIGHT

        overlay = RetroShowcaseOverlay(host, host.centralWidget())
        overlay.show()
        overlay.raise_()
        overlay.focused = True
        overlay._focus_progress = 1.0
        app.processEvents()
        render_scene(overlay, "06-minimum-long-title")

        layout = focus_info_layout(
            overlay.width(),
            overlay.height(),
            hero_right=overlay._main_rect.right(),
        )
        assert layout.title_max_lines == 3
        assert layout.title_min_point_size == 12
        assert layout.width >= 280.0
        assert layout.left > overlay._main_rect.right()
        assert not overlay._more_rect.isNull()

        # Prove the exact regression title can fit inside the compact title box
        # at the configured minimum point size instead of being hard-clipped.
        font = QFont("Bahnschrift", layout.title_min_point_size)
        font.setWeight(QFont.Weight.DemiBold)
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 104)
        metrics = QFontMetrics(font)
        bounds = metrics.boundingRect(
            0,
            0,
            max(1, int(layout.width)),
            max(1, int(layout.title_height * 3)),
            int(Qt.TextFlag.TextWordWrap),
            long_title.upper(),
        )
        assert bounds.height() <= metrics.lineSpacing() * layout.title_max_lines + 2
    finally:
        host.close()
        app.processEvents()


def test_background_base_is_horizontally_uniform_without_waves():
    """Catch the diagonal base-gradient regression behind the dirty ambient band."""
    app, host, overlay = make_overlay()
    original_draw_waves = RetroShowcaseOverlay._draw_ambient_waves
    original_draw_symbols = RetroShowcaseOverlay._draw_ambient_symbols
    try:
        RetroShowcaseOverlay._draw_ambient_waves = lambda self, painter, rect: None
        RetroShowcaseOverlay._draw_ambient_symbols = lambda self, painter, rect: None
        image = QImage(
            max(1, overlay.width()),
            max(1, overlay.height()),
            QImage.Format.Format_ARGB32_Premultiplied,
        )
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        try:
            overlay._draw_background(painter)
        finally:
            painter.end()

        y = max(1, image.height() // 2)
        xs = (
            max(1, image.width() // 8),
            max(1, image.width() // 2),
            max(1, image.width() * 7 // 8),
        )
        colors = [image.pixelColor(x, y).rgba() for x in xs]
        assert colors[0] == colors[1] == colors[2], (
            "background base changes horizontally at one y; "
            "a diagonal gradient/glow has been reintroduced"
        )
        _save_image(image, "07-clean-background-base")
    finally:
        RetroShowcaseOverlay._draw_ambient_waves = original_draw_waves
        RetroShowcaseOverlay._draw_ambient_symbols = original_draw_symbols
        host.close()
        app.processEvents()



def test_ambient_symbols_render_behind_showcase_without_breaking_scene():
    app, host, overlay = make_overlay()
    try:
        overlay._phase = 3.25
        specs_a = overlay._ambient_symbol_specs(QRectF(overlay.rect()))
        overlay._phase = 4.10
        specs_b = overlay._ambient_symbol_specs(QRectF(overlay.rect()))
        assert len(specs_a) >= 24
        assert len(specs_a) == len(specs_b)
        assert any(abs(a[1].x() - b[1].x()) > 0.5 for a, b in zip(specs_a, specs_b))

        image = render_scene(overlay, "08-ambient-background-only")
        assert not image.isNull()
        assert not hasattr(overlay, "_draw_foreground_waves")
    finally:
        host.close()
        app.processEvents()


class _PaintCounter(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.paints = 0

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.Paint:
            self.paints += 1
        return False


def test_idle_ambient_refresh_budget_stays_near_15fps():
    app, host, overlay = make_overlay()
    counter = _PaintCounter()
    overlay.installEventFilter(counter)
    try:
        # Native Windows can deliver delayed expose/paint and pointer events for
        # a short period after show(). Move to a blank corner and let that settle
        # before measuring the app-owned ambient timer. Raw QEvent.Paint counts
        # are kept only as diagnostics because the compositor may request paints
        # independently of the animation timer.
        QTest.mouseMove(overlay, QPoint(8, 8))
        overlay._set_hover_sequence(None)
        overlay._hover_strengths.clear()
        overlay._ambient_timer.stop()
        overlay._ambient_timer.setInterval(66)
        overlay._ambient_timer.start()
        QTest.qWait(300)
        app.processEvents()
        assert overlay._ambient_timer.interval() == 66

        counter.paints = 0
        overlay._ambient_timer.stop()
        ambient_spy = QSignalSpy(overlay._ambient_timer.timeout)
        overlay._ambient_timer.start()
        QTest.qWait(1000)
        app.processEvents()

        ambient_timeouts = ambient_spy.count()
        print(f"[PERF] idle ambient timeouts={ambient_timeouts}, paint_events={counter.paints}")
        assert overlay._ambient_timer.interval() == 66
        # 66ms is about 15.2Hz. Allow normal Windows timer scheduling jitter,
        # but reject the former ~30Hz app-owned animation loop.
        assert 10 <= ambient_timeouts <= 20, (ambient_timeouts, counter.paints)
    finally:
        overlay.removeEventFilter(counter)
        host.close()
        app.processEvents()


def test_scene_search_settings_and_font_controls():
    app, host, overlay = make_overlay()
    try:
        # Search stays inside the Retro scene and updates the active catalog query.
        overlay._show_search_bar()
        app.processEvents()
        assert overlay._search_edit.isVisible()
        assert overlay._search_edit.objectName() == "retroSearchCapsule"
        assert overlay._search_edit.geometry().center().x() == overlay.rect().center().x()
        overlay._search_edit.setText("God")
        overlay._apply_search_query()
        app.processEvents()
        assert host.game_catalog.last_search == "God"
        assert overlay.current_record() is not None

        # Escape closes only the capsule; the query remains active until cleared.
        from PySide6.QtGui import QKeyEvent
        escape = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(overlay._search_edit, escape)
        app.processEvents()
        assert not overlay._search_edit.isVisible()
        assert overlay._search_text["games"] == "God"
        overlay._clear_search()
        assert overlay._search_text["games"] == ""

        # Gear opens one scene drawer directly: font + About are inline.
        overlay._activate_corner_action("settings")
        overlay._panel_anim.stop()
        overlay._panel_progress = 1.0
        render_scene(overlay, "08-scene-settings")
        app.processEvents()
        assert overlay.system_open
        assert overlay._font_selector.isVisible()
        assert overlay._font_selector.objectName() == "retroFontSelector"
        assert "advanced_settings" in overlay._system_action_rects
        assert not hasattr(overlay, "_system_tab_rects")

        families = [overlay._font_selector.itemText(i) for i in range(overlay._font_selector.count())]
        alternative = next((family for family in families if family != overlay._ui_font_family), None)
        if alternative:
            original = overlay._ui_font_family
            overlay._set_retro_font_family(alternative, persist=False)
            assert overlay._ui_font_family == alternative
            assert overlay._ui_font(11).family() == alternative
            overlay._set_retro_font_family(original, persist=False)
    finally:
        host.close()
        app.processEvents()


def test_scene_sound_settings_and_semantic_events_are_safe():
    app, host, overlay = make_overlay()
    try:
        # Local smoke must never replace the user's persisted sound preferences.
        overlay._persist_sound_preferences = lambda: None
        pack = overlay._sound_store.create_pack("Smoke Sound Pack")
        overlay._sound_pack_id = pack.id
        overlay._sound_enabled = False
        overlay._sound_volume = 0.70
        overlay._configure_sound_service()

        overlay._set_system_open(True)
        overlay._panel_anim.stop()
        overlay._panel_progress = 1.0
        render_scene(overlay, "10-sound-settings")
        assert "sound_manage" in overlay._system_action_rects
        assert overlay._current_sound_pack().name == "Smoke Sound Pack"

        overlay._system_page = "sound"
        render_scene(overlay, "11-sound-mapping")
        assert "sound_pack_create" in overlay._system_action_rects
        assert "sound_pack_duplicate" in overlay._system_action_rects
        assert "sound_pack_rename" in overlay._system_action_rects
        assert "sound_pack_delete" in overlay._system_action_rects
        for event in SOUND_EVENTS:
            assert f"sound_preview:{event}" in overlay._system_action_rects
            assert f"sound_import:{event}" in overlay._system_action_rects
            assert f"sound_clear:{event}" in overlay._system_action_rects
            overlay._play_ui_sound(event)

        overlay._system_page = "settings"
        overlay._set_system_open(False)
        overlay._panel_anim.stop()
        overlay._panel_progress = 0.0
        overlay._start_arc(1)
        overlay._arc_anim.stop()
        overlay._play_ui_sound("focus")
        overlay._play_ui_sound("back")
    finally:
        host.close()
        app.processEvents()


def test_showcase_four_item_click_hover_and_wrap():
    app = get_app()
    records = [make_game_record(f"Smoke Game {index}") for index in range(6)]
    host = FakeHost(records)
    host.resize(1320, 840)
    host.show()
    app.processEvents()
    overlay = RetroShowcaseOverlay(host, host.centralWidget())
    overlay.show()
    overlay.raise_()
    app.processEvents()
    try:
        render_scene(overlay, "09-four-up-browse")
        current_sequence = round(overlay._arc_position)
        visible = [item for item in overlay._record_hit_rects if item[2].intersects(QRectF(overlay.rect()))]
        assert len({logical for _sequence, logical, _rect in visible}) == 4

        target = next(item for item in reversed(visible) if item[0] != current_sequence)
        target_sequence, target_logical, target_rect = target
        target_point = target_rect.center().toPoint()

        # Hover is animated by the ambient clock and must not change selection.
        QTest.mouseMove(overlay, target_point, 8)
        QTest.qWait(180)
        app.processEvents()
        assert overlay._hover_sequence == target_sequence
        assert overlay._hover_strengths.get(target_sequence, 0.0) > 0.45
        assert overlay.current_index == current_sequence % len(records)
        render_scene(overlay, "10-four-up-hover")

        # First click on a non-current package only moves it into the primary slot.
        QTest.mouseClick(overlay, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target_point, 8)
        QTest.qWait(overlay._arc_anim.duration() + 80)
        app.processEvents()
        assert round(overlay._arc_position) == target_sequence
        assert overlay.current_index == target_logical
        assert not overlay.focused
        render_scene(overlay, "11-four-up-selected")

        # Second click on the settled primary package enters short-info focus.
        main_point = overlay._main_rect.center().toPoint()
        QTest.mouseClick(overlay, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, main_point, 8)
        QTest.qWait(overlay._focus_anim.duration() + 40)
        app.processEvents()
        assert overlay.focused
        assert not overlay._more_rect.isNull()

        # Double-clicking the primary package keeps the launch behavior.
        QTest.mouseDClick(overlay, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, overlay._main_rect.center().toPoint(), 8)
        app.processEvents()
        assert host.launch_count == 1

        # Wrap across the logical end without normalizing the live arc coordinate.
        overlay._set_focused(False)
        overlay._focus_anim.stop()
        overlay._focus_progress = 0.0
        overlay._arc_anim.stop()
        overlay._arc_position = float(len(records) - 1)
        overlay._arc_target = overlay._arc_position
        overlay.current_index = len(records) - 1
        render_scene(overlay, "12-wrap-before")
        overlay._start_arc(1)
        QTest.qWait(max(50, overlay._arc_anim.duration() // 2))
        app.processEvents()
        assert len({logical for _seq, logical, rect in overlay._record_hit_rects if rect.intersects(QRectF(overlay.rect()))}) >= 4
        render_scene(overlay, "13-wrap-mid")
        QTest.qWait(overlay._arc_anim.duration() + 80)
        app.processEvents()
        assert round(overlay._arc_position) == len(records)
        assert overlay.current_index == 0
    finally:
        host.close()
        app.processEvents()
