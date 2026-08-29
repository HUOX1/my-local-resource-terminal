from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QElapsedTimer,
    QEvent,
    QPoint,
    QPointF,
    Property,
    QPropertyAnimation,
    Signal,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QAbstractAnimation,
    QSettings,
)
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
    QWheelEvent,
)
from PySide6.QtWidgets import QComboBox, QDialog, QFileDialog, QLineEdit, QMenu, QMessageBox, QWidget

from app.models.game import GameRecord
from app.models.movie import MovieRecord
from app.services.audio_import_service import AudioImportError, AudioImportService
from app.services.catalog_service import MovieFilter
from app.services.sound_pack_store import SOUND_EVENTS, SoundPackStore
from app.services.ui_sound_service import UISoundService
from app.ui.retro_edit_dialogs import RetroGameArchiveEditDialog, RetroMovieArchiveEditDialog
from app.ui.retro_showcase_state import (
    AMBIENT_ACTIVE_INTERVAL_MS,
    AMBIENT_IDLE_INTERVAL_MS,
    PackageProfile,
    RETRO_MAX_VISIBLE_ITEMS,
    RETRO_MIN_WINDOW_HEIGHT,
    RETRO_MIN_WINDOW_WIDTH,
    ambient_phase_step,
    ambient_refresh_interval_ms,
    anchored_equal_gap_centers,
    arc_pose,
    carousel_segment,
    carousel_slots,
    effective_package_face_ratio,
    focus_info_layout,
    format_duration,
    hover_pose,
    library_filter_options,
    library_sort_options,
    persistent_filter_key,
    rail_center_x,
    showcase_click_intent,
    resolve_game_package_profile,
)


CYAN = QColor(90, 224, 224)
CYAN_DIM = QColor(53, 151, 159)
TEXT = QColor(225, 239, 239)
TEXT_DIM = QColor(143, 171, 174)
TEXT_FAINT = QColor(95, 122, 125)
PANEL = QColor(10, 23, 28, 220)

DETAIL_PANEL_WIDTH_RATIO = 0.42
DETAIL_PANEL_HEIGHT_RATIO = 0.78
SYSTEM_PANEL_WIDTH_RATIO = 0.34
SYSTEM_PANEL_HEIGHT_RATIO = 0.78
FOCUS_BACKDROP_ALPHA = 96
RETRO_VERSION = "0.5.0.17.1"

SOUND_EVENT_LABELS = {
    "navigate": "盒子切换",
    "select": "点击其它盒进入主位",
    "focus": "进入聚焦",
    "confirm": "确认 / 启动",
    "back": "返回 / 退出",
    "open_panel": "打开 MORE / Settings",
    "close_panel": "关闭面板",
}


class RetroShowcaseOverlay(QWidget):
    """Retro primary scene backed by the existing movie/game services.

    Flat Pro implementation code remains in the repository as historical
    baseline, but the Retro presentation no longer exposes a user fallback.
    """

    view_state_changed = Signal(str, str, bool, str)
    folder_state_changed = Signal(str, object)

    def __init__(self, host_window, parent: QWidget) -> None:
        super().__init__(parent)
        self.host = host_window
        self.setObjectName("retroShowcaseOverlay")
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self.domain = "games"
        self.records: list[GameRecord | MovieRecord] = []
        self.current_index = 0
        self.focused = False
        self.details_open = False
        self.system_open = False
        self._panel_mode: str | None = None
        self.detail_tab = "概览"
        self.menu_corner = "bottom_right"
        self.box_style = "neo"

        # Retro owns its browsing state instead of driving the hidden Flat Pro
        # controls. The existing catalog services remain the query source.
        self._search_text = {"games": "", "movies": ""}
        self._filter_keys = {
            "games": persistent_filter_key("games", str(getattr(host_window.settings, "game_filter", "all"))),
            "movies": persistent_filter_key("movies", str(getattr(host_window.settings, "movie_filter", "all"))),
        }
        self._filter_payloads = {
            domain: self._base_filter_payload(domain, key)
            for domain, key in self._filter_keys.items()
        }
        self._sort_keys = {
            "games": str(getattr(host_window.settings, "game_sort_key", "last_played_at")),
            "movies": str(getattr(host_window.settings, "sort_key", "last_watched_at")),
        }
        self._sort_desc = {
            "games": bool(getattr(host_window.settings, "game_sort_desc", True)),
            "movies": bool(getattr(host_window.settings, "sort_desc", True)),
        }
        self._folder_ids = {
            "games": getattr(host_window.settings, "game_folder_id", None),
            "movies": getattr(host_window.settings, "movie_folder_id", None),
        }

        self._phase = 0.0
        self._ambient_symbol_bases = self._build_ambient_symbol_bases()
        self._mouse_norm = QPointF(0.0, 0.0)
        self._pixmap_cache: dict[str, QPixmap] = {}
        self._main_rect = QRectF()
        self._more_rect = QRectF()
        self._menu_button_rects: dict[str, QRectF] = {}
        self._detail_tab_rects: dict[str, QRectF] = {}
        self._system_action_rects: dict[str, QRectF] = {}
        self._detail_panel_rect = QRectF()
        self._system_panel_rect = QRectF()
        self._press_pos = QPoint()
        self._window_controls_visible = False
        self._window_control_rects: dict[str, QRectF] = {}
        self._record_hit_rects: list[tuple[int, int, QRectF]] = []
        self._hover_sequence: int | None = None
        self._hover_strengths: dict[int, float] = {}
        self._mouse_pos = QPointF(-10_000.0, -10_000.0)

        # Scene-native controls stay inside the Retro overlay instead of
        # spawning independent search/settings windows.
        self._retro_settings = QSettings("LocalMovieManager", "LocalMovieManager")
        self._system_page = "settings"
        self._sound_status = ""
        self._sound_name_mode: str | None = None
        data_dir = Path(getattr(host_window.settings, "data_dir", Path.cwd() / "data"))
        self._sound_store = SoundPackStore(data_dir / "soundpacks")
        self._audio_importer = AudioImportService(
            self._sound_store,
            ffmpeg_path=str(getattr(host_window.settings, "ffmpeg_path", "ffmpeg")),
        )
        self._ui_sound = UISoundService(self._sound_store, self)
        try:
            self._sound_volume = max(0.0, min(float(self._retro_settings.value("retro/sound_volume", 0.70)), 1.0))
        except (TypeError, ValueError):
            self._sound_volume = 0.70
        saved_sound_pack = str(self._retro_settings.value("retro/sound_pack_id", "") or "").strip()
        available_sound_packs = self._sound_store.list_packs()
        available_ids = {pack.id for pack in available_sound_packs}
        self._sound_pack_id = saved_sound_pack if saved_sound_pack in available_ids else (available_sound_packs[0].id if available_sound_packs else None)
        self._sound_enabled = bool(self._retro_settings.value("retro/sound_enabled", False, type=bool)) and self._sound_pack_id is not None
        self._ui_sound.configure(self._sound_enabled, self._sound_pack_id, self._sound_volume)
        families = sorted(
            {str(name).strip() for name in QFontDatabase.families() if str(name).strip()},
            key=str.casefold,
        )
        saved_family = str(self._retro_settings.value("retro/ui_font_family", "") or "").strip()
        fallback_family = "Segoe UI" if "Segoe UI" in families else (families[0] if families else QFont().family())
        self._ui_font_family = saved_family if saved_family in families else fallback_family

        self._search_edit = QLineEdit(self)
        self._search_edit.setObjectName("retroSearchCapsule")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.setFrame(False)
        self._search_edit.setStyleSheet(
            "QLineEdit#retroSearchCapsule {"
            "background: rgba(10, 25, 30, 232);"
            "border: 1px solid rgba(90, 224, 224, 92);"
            "border-radius: 21px;"
            "padding: 0 22px;"
            "color: rgb(225, 239, 239);"
            "selection-background-color: rgba(90, 224, 224, 90);"
            "}"
        )
        self._search_edit.setFont(self._ui_font(11))
        self._search_edit.hide()
        self._search_edit.installEventFilter(self)
        self._search_edit.textChanged.connect(self._on_search_text_changed)

        self._sound_name_edit = QLineEdit(self)
        self._sound_name_edit.setObjectName("retroSoundPackNameEdit")
        self._sound_name_edit.setFrame(False)
        self._sound_name_edit.setStyleSheet(
            "QLineEdit#retroSoundPackNameEdit {"
            "background: rgba(14, 37, 42, 238);"
            "border: 1px solid rgba(90, 224, 224, 90);"
            "border-radius: 8px;"
            "padding: 0 12px;"
            "color: rgb(225, 239, 239);"
            "}"
        )
        self._sound_name_edit.setFont(self._ui_font(10))
        self._sound_name_edit.installEventFilter(self)
        self._sound_name_edit.returnPressed.connect(self._commit_sound_name_edit)
        self._sound_name_edit.hide()

        self._search_debounce_timer = QTimer(self)
        self._search_debounce_timer.setSingleShot(True)
        self._search_debounce_timer.setInterval(120)
        self._search_debounce_timer.timeout.connect(self._apply_search_query)

        self._font_selector = QComboBox(self)
        self._font_selector.setObjectName("retroFontSelector")
        self._font_selector.addItems(families)
        if self._ui_font_family:
            self._font_selector.setCurrentText(self._ui_font_family)
        self._font_selector.setMaxVisibleItems(18)
        self._font_selector.setStyleSheet(
            "QComboBox#retroFontSelector {"
            "background: rgba(16, 42, 47, 210);"
            "border: 1px solid rgba(90, 224, 224, 64);"
            "border-radius: 8px;"
            "padding: 6px 12px;"
            "color: rgb(225, 239, 239);"
            "}"
            "QComboBox#retroFontSelector QAbstractItemView {"
            "background: rgb(12, 30, 34);"
            "color: rgb(225, 239, 239);"
            "selection-background-color: rgb(31, 78, 83);"
            "}"
        )
        self._font_selector.setFont(self._ui_font(10))
        self._font_selector.hide()
        self._font_selector.currentTextChanged.connect(self._set_retro_font_family)

        self._menu_opacity = 0.0
        self._focus_progress = 0.0
        self._panel_progress = 0.0
        self._arc_position = 0.0
        self._arc_target = 0.0
        self._arc_direction = 1

        self._ambient_clock = QElapsedTimer()
        self._ambient_clock.start()
        self._ambient_timer = QTimer(self)
        self._ambient_timer.setInterval(AMBIENT_IDLE_INTERVAL_MS)
        self._ambient_timer.timeout.connect(self._ambient_tick)
        self._ambient_timer.start()

        self._menu_hide_timer = QTimer(self)
        self._menu_hide_timer.setSingleShot(True)
        self._menu_hide_timer.setInterval(450)
        self._menu_hide_timer.timeout.connect(lambda: self._animate_menu(False))

        self._menu_anim = QPropertyAnimation(self, b"menuOpacity", self)
        self._menu_anim.setDuration(190)
        self._menu_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._focus_anim = QPropertyAnimation(self, b"focusProgress", self)
        self._focus_anim.setDuration(240)
        self._focus_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._panel_anim = QPropertyAnimation(self, b"panelProgress", self)
        self._panel_anim.setDuration(260)
        self._panel_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._panel_anim.finished.connect(self._finish_panel_motion)

        self._arc_anim = QPropertyAnimation(self, b"arcPosition", self)
        self._arc_anim.setDuration(250)
        self._arc_anim.setEasingCurve(QEasingCurve.Type.OutQuart)
        self._arc_anim.finished.connect(self._finish_arc)

        parent.installEventFilter(self)
        self._fit_parent()
        self.refresh_records()

    # ----- animated properties -------------------------------------------------
    def _get_menu_opacity(self) -> float:
        return self._menu_opacity

    def _set_menu_opacity(self, value: float) -> None:
        self._menu_opacity = max(0.0, min(float(value), 1.0))
        self.update()

    menuOpacity = Property(float, _get_menu_opacity, _set_menu_opacity)

    def _get_focus_progress(self) -> float:
        return self._focus_progress

    def _set_focus_progress(self, value: float) -> None:
        self._focus_progress = max(0.0, min(float(value), 1.0))
        self.update()

    focusProgress = Property(float, _get_focus_progress, _set_focus_progress)

    def _get_panel_progress(self) -> float:
        return self._panel_progress

    def _set_panel_progress(self, value: float) -> None:
        self._panel_progress = max(0.0, min(float(value), 1.0))
        self.update()

    panelProgress = Property(float, _get_panel_progress, _set_panel_progress)

    def _get_arc_position(self) -> float:
        return self._arc_position

    def _set_arc_position(self, value: float) -> None:
        self._arc_position = float(value)
        if self.records:
            self.current_index = round(self._arc_position) % len(self.records)
        self.update()

    arcPosition = Property(float, _get_arc_position, _set_arc_position)

    # ----- lifecycle -----------------------------------------------------------
    def eventFilter(self, watched, event) -> bool:
        if watched is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self._fit_parent()
        if watched is self._search_edit and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self._hide_search_bar()
                return True
        if watched is self._sound_name_edit and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self._cancel_sound_name_edit()
                return True
        return super().eventFilter(watched, event)

    def _fit_parent(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        top = 0
        title_bar = getattr(self.host, "title_bar", None)
        if title_bar is not None and title_bar.isVisible():
            top = max(0, title_bar.height())
        self.setGeometry(0, top, parent.width(), max(1, parent.height() - top))
        self._layout_search_bar()
        self.raise_()
        if self._search_edit.isVisible():
            self._search_edit.raise_()
        if self._font_selector.isVisible():
            self._font_selector.raise_()
        if self._sound_name_edit.isVisible():
            self._sound_name_edit.raise_()

    def _ui_font(
        self,
        point_size: int,
        *,
        weight: QFont.Weight | None = None,
        spacing_percent: float | None = None,
    ) -> QFont:
        font = QFont(self._ui_font_family or "Segoe UI", max(1, int(point_size)))
        if weight is not None:
            font.setWeight(weight)
        if spacing_percent is not None:
            font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, float(spacing_percent))
        return font

    def _set_retro_font_family(self, family: str, *, persist: bool = True) -> None:
        family = str(family or "").strip()
        if not family or family == self._ui_font_family:
            return
        available = {str(name) for name in QFontDatabase.families()}
        if family not in available:
            return
        self._ui_font_family = family
        self._search_edit.setFont(self._ui_font(11))
        self._font_selector.setFont(self._ui_font(10))
        if persist:
            self._retro_settings.setValue("retro/ui_font_family", family)
        self.update()

    def _layout_search_bar(self) -> None:
        width = min(720, max(430, int(self.width() * 0.56)))
        height = 44
        left = max(20, (self.width() - width) // 2)
        top = max(20, int(self.height() * 0.045))
        self._search_edit.setGeometry(left, top, width, height)

    def _update_search_placeholder(self) -> None:
        self._search_edit.setPlaceholderText(
            "搜索游戏、系列、开发商、发行商或标签…"
            if self.domain == "games"
            else "搜索编号、标题、演员、系列、厂商或标签…"
        )

    def _show_search_bar(self) -> None:
        if self.system_open:
            self._set_system_open(False)
        if self.details_open:
            self._set_details_open(False)
        self._update_search_placeholder()
        self._search_edit.blockSignals(True)
        self._search_edit.setText(self._search_text[self.domain])
        self._search_edit.blockSignals(False)
        self._layout_search_bar()
        self._search_edit.show()
        self._search_edit.raise_()
        self._search_edit.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self._search_edit.selectAll()

    def _hide_search_bar(self) -> None:
        self._search_debounce_timer.stop()
        self._search_edit.hide()
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def _on_search_text_changed(self, text: str) -> None:
        self._search_text[self.domain] = str(text).strip()
        self._search_debounce_timer.start()

    def _apply_search_query(self) -> None:
        self._reset_collection_position()

    def _ambient_tick(self) -> None:
        # PERF HOTFIX: when the scene cannot be seen, keep the elapsed clock
        # fresh but do not schedule a full-window repaint.
        if not self.isVisible() or self.window().isMinimized():
            self._ambient_clock.restart()
            return

        elapsed_ms = max(1, self._ambient_clock.restart())
        # Time-based phase preserves the visual travel speed while allowing the
        # idle refresh rate to drop from ~30 fps to ~15 fps.
        self._phase += ambient_phase_step(elapsed_ms)

        # Hover keeps the former 30 fps cadence only while easing is moving.
        active = set(self._hover_strengths)
        if self._hover_sequence is not None:
            active.add(self._hover_sequence)
        for sequence in active:
            current = float(self._hover_strengths.get(sequence, 0.0))
            target = 1.0 if sequence == self._hover_sequence else 0.0
            rate = 0.24 if target > current else 0.16
            value = current + (target - current) * rate
            if target == 0.0 and value < 0.015:
                self._hover_strengths.pop(sequence, None)
            else:
                self._hover_strengths[sequence] = value

        interval = ambient_refresh_interval_ms(self._hover_sequence, self._hover_strengths)
        if self._ambient_timer.interval() != interval:
            self._ambient_timer.setInterval(interval)
        self.update()

    def refresh_records(self) -> None:
        try:
            if self.domain == "games":
                payload = dict(self._filter_payloads["games"])
                self.records = list(
                    self.host.game_catalog.list_games(
                        self._search_text[self.domain],
                        favorite=payload.get("favorite"),
                        installed=payload.get("installed"),
                        recently_played=payload.get("recently_played"),
                        tag=payload.get("tag"),
                        folder_id=self._folder_ids["games"],
                        sort=self._sort_keys["games"],
                        descending=self._sort_desc["games"],
                    )
                ) if self.host.game_catalog is not None else []
            else:
                payload = dict(self._filter_payloads["movies"])
                self.records = list(
                    self.host.catalog.list_movies(
                        self._search_text[self.domain],
                        MovieFilter(
                            library_id=payload.get("library_id"),
                            favorite=payload.get("favorite"),
                            watched=payload.get("watched"),
                            subtitle_status=payload.get("subtitle_status"),
                            availability_status=payload.get("availability_status"),
                            tag=payload.get("tag"),
                            folder_id=self._folder_ids["movies"],
                        ),
                        sort=self._sort_keys["movies"],
                        descending=self._sort_desc["movies"],
                    )
                )
        except Exception as exc:
            self.records = []
            QMessageBox.warning(self.host, "Retro 展示读取失败", str(exc))
        if self.records:
            self.current_index %= len(self.records)
        else:
            self.current_index = 0
        self.update()

    # ----- Retro UI sound ------------------------------------------------------
    def refresh_sound_environment(self) -> None:
        data_dir = Path(getattr(self.host.settings, "data_dir", Path.cwd() / "data"))
        try:
            self._ui_sound.stop_preview()
            self._ui_sound.deleteLater()
        except Exception:
            pass
        self._sound_store = SoundPackStore(data_dir / "soundpacks")
        self._audio_importer = AudioImportService(
            self._sound_store,
            ffmpeg_path=str(getattr(self.host.settings, "ffmpeg_path", "ffmpeg")),
        )
        packs = self._sound_store.list_packs()
        ids = {pack.id for pack in packs}
        if self._sound_pack_id not in ids:
            self._sound_pack_id = packs[0].id if packs else None
        if self._sound_pack_id is None:
            self._sound_enabled = False
        self._ui_sound = UISoundService(self._sound_store, self)
        self._ui_sound.configure(self._sound_enabled, self._sound_pack_id, self._sound_volume)
        self._persist_sound_preferences()
        self.update()

    def _persist_sound_preferences(self) -> None:
        self._retro_settings.setValue("retro/sound_enabled", bool(self._sound_enabled))
        self._retro_settings.setValue("retro/sound_pack_id", self._sound_pack_id or "")
        self._retro_settings.setValue("retro/sound_volume", float(self._sound_volume))
        self._retro_settings.sync()

    def _configure_sound_service(self) -> None:
        if self._sound_pack_id not in {pack.id for pack in self._sound_store.list_packs()}:
            self._sound_pack_id = None
            self._sound_enabled = False
        self._ui_sound.configure(self._sound_enabled, self._sound_pack_id, self._sound_volume)
        self._persist_sound_preferences()
        self.update()

    def _play_ui_sound(self, event: str) -> None:
        self._ui_sound.play(event)

    def _current_sound_pack(self):
        for pack in self._sound_store.list_packs():
            if pack.id == self._sound_pack_id:
                return pack
        return None

    def _cycle_sound_pack(self, direction: int) -> None:
        packs = self._sound_store.list_packs()
        if not packs:
            self._sound_pack_id = None
            self._sound_enabled = False
            self._sound_status = "还没有音效包。先创建一个，再导入声音。"
            self._configure_sound_service()
            return
        ids = [pack.id for pack in packs]
        if self._sound_pack_id not in ids:
            index = 0
        else:
            index = ids.index(self._sound_pack_id)
            index = (index + (-1 if direction < 0 else 1)) % len(ids)
        self._sound_pack_id = ids[index]
        self._sound_status = f"当前音效包：{packs[index].name}"
        self._configure_sound_service()

    def _begin_sound_name_edit(self, mode: str) -> None:
        if mode not in {"create", "rename"}:
            return
        self._sound_name_mode = mode
        pack = self._current_sound_pack()
        self._sound_name_edit.setText(pack.name if mode == "rename" and pack is not None else "")
        self._sound_name_edit.setPlaceholderText("输入音效包名称，Enter 确认")
        self._sound_name_edit.show()
        self._sound_name_edit.raise_()
        self._sound_name_edit.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self._sound_name_edit.selectAll()
        self.update()

    def _cancel_sound_name_edit(self) -> None:
        self._sound_name_mode = None
        self._sound_name_edit.hide()
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.update()

    def _commit_sound_name_edit(self) -> None:
        mode = self._sound_name_mode
        name = self._sound_name_edit.text().strip()
        if not mode or not name:
            self._sound_status = "音效包名称不能为空。"
            self.update()
            return
        try:
            if mode == "create":
                pack = self._sound_store.create_pack(name)
                self._sound_pack_id = pack.id
            else:
                pack = self._current_sound_pack()
                if pack is None:
                    self._sound_status = "没有可重命名的音效包。"
                    return
                self._sound_store.rename_pack(pack.id, name)
            self._sound_status = "音效包已保存。"
            self._cancel_sound_name_edit()
            self._configure_sound_service()
        except (OSError, ValueError) as exc:
            self._sound_status = str(exc)
            self.update()

    def _duplicate_sound_pack(self) -> None:
        pack = self._current_sound_pack()
        if pack is None:
            self._sound_status = "没有可复制的音效包。"
            self.update()
            return
        try:
            copied = self._sound_store.duplicate_pack(pack.id, f"{pack.name} 副本")
            self._sound_pack_id = copied.id
            self._sound_status = f"已复制：{copied.name}"
            self._configure_sound_service()
        except (OSError, ValueError) as exc:
            self._sound_status = str(exc)
            self.update()

    def _delete_current_sound_pack(self) -> None:
        pack = self._current_sound_pack()
        packs = self._sound_store.list_packs()
        if pack is None:
            self._sound_status = "没有可删除的音效包。"
            self.update()
            return
        alternatives = [candidate for candidate in packs if candidate.id != pack.id]
        if not alternatives:
            self._sound_status = "当前是唯一音效包。请先新建或复制另一个音效包。"
            self.update()
            return
        try:
            self._sound_pack_id = alternatives[0].id
            self._sound_store.delete_pack(pack.id)
            self._sound_status = f"已删除 {pack.name}，已切换到 {alternatives[0].name}。"
            self._configure_sound_service()
        except OSError as exc:
            self._sound_status = str(exc)
            self.update()

    def _import_sound_event(self, event: str) -> None:
        pack = self._current_sound_pack()
        if pack is None:
            self._sound_status = "请先创建一个音效包。"
            self.update()
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            f"选择 {SOUND_EVENT_LABELS.get(event, event)} 音效",
            "",
            "音频文件 (*.wav *.mp3 *.ogg *.flac *.m4a *.aac *.wma);;所有文件 (*)",
        )
        if not path:
            return
        try:
            imported = self._audio_importer.import_for_event(pack.id, event, Path(path))
        except AudioImportError as exc:
            self._sound_status = f"导入失败：{exc}"
            self.update()
            return
        self._sound_status = f"已导入：{Path(path).name}"
        self._ui_sound.reload_pack()
        self._ui_sound.preview(imported.runtime_path)
        self.update()

    def _preview_sound_event(self, event: str) -> None:
        if not self._sound_pack_id:
            return
        path = self._sound_store.resolve_audio_path(self._sound_pack_id, event)
        if path is not None:
            self._ui_sound.preview(path)

    def _clear_sound_event(self, event: str) -> None:
        if not self._sound_pack_id:
            return
        try:
            self._sound_store.clear_mapping(self._sound_pack_id, event)
        except (OSError, ValueError, FileNotFoundError) as exc:
            self._sound_status = str(exc)
            self.update()
            return
        self._sound_status = f"已清除：{SOUND_EVENT_LABELS.get(event, event)}"
        self._ui_sound.reload_pack()
        self.update()

    # ----- painting ------------------------------------------------------------
    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self._draw_background(painter)
        if self.focused and not self.details_open and not self.system_open:
            self._draw_focus_backdrop(painter)

        showcase_opacity = 1.0 - 0.42 * self._panel_progress if self._panel_mode == "system" else 1.0
        painter.save()
        painter.setOpacity(showcase_opacity)
        self._draw_showcase(painter)
        painter.restore()


        if self.focused and not self.details_open and not self.system_open:
            self._draw_focus_info(painter)
        if self._panel_mode == "details" and self._panel_progress > 0.001:
            self._draw_detail_panel(painter)
        if self._panel_mode == "system" and self._panel_progress > 0.001:
            self._draw_system_panel(painter)
        self._draw_corner_menu(painter)
        self._draw_window_controls(painter)

    def _draw_background(self, painter: QPainter) -> None:
        rect = QRectF(self.rect())
        base = QLinearGradient(0.0, rect.top(), 0.0, rect.bottom())
        base.setColorAt(0.0, QColor(4, 14, 18))
        base.setColorAt(0.52, QColor(6, 20, 24))
        base.setColorAt(1.0, QColor(2, 9, 12))
        painter.fillRect(rect, base)

        # CLEAN AMBIENT: the broad PS-style wave bands are the whole ambient
        # treatment.  Earlier radial glow/stage overlays created visible alpha
        # strata that made the background look dirty and segmented.
        self._draw_ambient_waves(painter, rect)
        self._draw_ambient_symbols(painter, rect)

    def _draw_focus_backdrop(self, painter: QPainter) -> None:
        """Darken only the ambient scene behind light-focus content."""
        alpha = round(FOCUS_BACKDROP_ALPHA * self._focus_progress)
        if alpha <= 0:
            return
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 5, 7, alpha))
        painter.drawRect(QRectF(self.rect()))
        painter.restore()

    def _draw_ambient_waves(self, painter: QPainter, rect: QRectF) -> None:
        # AMBIENT_BAND: emphasize upper and lower screen space so the ambient
        # scene fills the frame without competing with the centered hero box.
        configs = (
            (0.18, 0.070, 0.074, 0.16, 18, QColor(42, 150, 165)),
            (0.31, 0.056, 0.050, 0.27, 20, QColor(56, 182, 194)),
            (0.70, 0.066, 0.072, 0.38, 22, QColor(52, 173, 186)),
            (0.84, 0.074, 0.082, 0.54, 18, QColor(44, 148, 160)),
            (0.49, 0.026, 0.026, 0.73, 10, QColor(92, 222, 226)),
        )
        for index, (base_y, amplitude, thickness, speed, alpha, color) in enumerate(configs):
            self._draw_wave_band(
                painter, rect, base_y, amplitude, thickness, speed, alpha, color, index
            )

    def _build_ambient_symbol_bases(self) -> list[tuple[int, float, float, float, float, float, float, int, QColor, str, float, float, int]]:
        symbols = ("△", "○", "□", "×")
        layers = (
            (10, 0.06, 0.28, 0.036, 0.018, (36.0, 88.0), 7, QColor(108, 217, 223, 20)),
            (8, 0.32, 0.46, 0.060, 0.022, (34.0, 72.0), 8, QColor(116, 226, 231, 14)),
            (10, 0.58, 0.78, 0.070, 0.026, (42.0, 96.0), 11, QColor(126, 232, 236, 22)),
            (8, 0.82, 0.95, 0.088, 0.020, (38.0, 84.0), 9, QColor(118, 223, 228, 18)),
        )
        bases: list[tuple[int, float, float, float, float, float, float, int, QColor, str, float, float, int]] = []
        for layer_index, (count, y_min, y_max, speed, drift, size_range, alpha_step, color) in enumerate(layers):
            min_size, max_size = size_range
            for index in range(count):
                seed = index + layer_index * 19
                norm_x = (math.sin(seed * 12.9898) * 43758.5453) % 1.0
                norm_y = (math.sin(seed * 7.313 + 1.17) * 24634.6345) % 1.0
                size = min_size + (max_size - min_size) * ((math.sin(seed * 4.17 + 0.9) * 0.5) + 0.5)
                symbol = symbols[(seed + layer_index) % len(symbols)]
                bases.append((layer_index, y_min, y_max, speed, drift, max_size, size, alpha_step, QColor(color), symbol, norm_x, norm_y, seed))
        return bases

    def _ambient_symbol_specs(self, rect: QRectF) -> list[tuple[str, QPointF, float, float, QColor]]:
        width = max(1.0, rect.width())
        height = max(1.0, rect.height())
        specs: list[tuple[str, QPointF, float, float, QColor]] = []
        for layer_index, y_min, y_max, speed, drift, max_size, size, alpha_step, color, symbol, norm_x, norm_y, seed in self._ambient_symbol_bases:
            travel = width + max_size * 2.8
            margin = max_size * 1.4
            x = ((1.0 - norm_x) * travel - (self._phase * speed * width * 7.2)) % travel - margin
            base_y = height * (y_min + (y_max - y_min) * norm_y)
            y = base_y + math.sin(self._phase * (0.52 + layer_index * 0.17) + seed * 0.83) * height * drift
            rotation = math.sin(self._phase * (0.32 + layer_index * 0.06) + seed * 0.41) * (8.0 + layer_index * 3.0)
            alpha = max(6, color.alpha() + int(math.sin(self._phase * 0.22 + seed * 0.29) * alpha_step))
            tint = QColor(color.red(), color.green(), color.blue(), alpha)
            specs.append((symbol, QPointF(x, y), size, rotation, tint))
        return specs

    def _draw_ambient_symbols(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        hero_soft_zone = self._main_rect.adjusted(-56.0, -42.0, 56.0, 42.0) if not self._main_rect.isNull() else QRectF()
        for symbol, center, size, rotation, color in self._ambient_symbol_specs(rect):
            symbol_rect = QRectF(center.x() - size * 0.75, center.y() - size * 0.75, size * 1.5, size * 1.5)
            if not rect.adjusted(-90.0, -90.0, 90.0, 90.0).intersects(symbol_rect):
                continue
            tint = QColor(color)
            if not hero_soft_zone.isNull() and hero_soft_zone.intersects(symbol_rect):
                tint.setAlpha(max(4, tint.alpha() // 2))
            painter.save()
            painter.translate(symbol_rect.center())
            painter.rotate(rotation)
            font = self._ui_font(max(12, int(size * 0.58)), weight=QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.setPen(tint)
            local_rect = QRectF(-symbol_rect.width() / 2.0, -symbol_rect.height() / 2.0, symbol_rect.width(), symbol_rect.height())
            painter.drawText(local_rect, int(Qt.AlignmentFlag.AlignCenter), symbol)
            painter.restore()
        painter.restore()

    def _draw_wave_band(
        self,
        painter: QPainter,
        rect: QRectF,
        base_y: float,
        amplitude: float,
        thickness: float,
        speed: float,
        alpha: int,
        color: QColor,
        layer: int,
    ) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width = rect.width()
        height = rect.height()
        points = 86
        upper: list[QPointF] = []
        lower: list[QPointF] = []
        phase = self._phase * speed + layer * 1.173
        for i in range(points + 1):
            t = i / points
            x = t * width
            wave = (
                math.sin(t * math.tau * 1.03 + phase)
                + 0.34 * math.sin(t * math.tau * 0.47 - phase * 0.61 + layer * 0.73)
                + 0.16 * math.sin(t * math.tau * 2.17 + phase * 0.29 + layer)
            )
            center = height * (base_y + amplitude * wave)
            breathing = 0.72 + 0.18 * math.sin(t * math.tau * 0.71 + phase * 0.33 + layer)
            half = height * thickness * breathing * 0.5
            upper.append(QPointF(x, center - half))
            lower.append(QPointF(x, center + half))

        path = QPainterPath()
        path.moveTo(upper[0])
        for point in upper[1:]:
            path.lineTo(point)
        for point in reversed(lower):
            path.lineTo(point)
        path.closeSubpath()

        bounds = path.boundingRect()
        fill = QLinearGradient(0, bounds.top(), 0, bounds.bottom())
        fill.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), max(2, alpha // 6)))
        fill.setColorAt(0.46, QColor(color.red(), color.green(), color.blue(), alpha))
        fill.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), max(2, alpha // 8)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        painter.drawPath(path)

        edge = QColor(color.red(), color.green(), color.blue(), max(4, alpha // 2))
        painter.setPen(QPen(edge, 0.85, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        edge_path = QPainterPath()
        edge_path.moveTo(upper[0])
        for point in upper[1:]:
            edge_path.lineTo(point)
        painter.drawPath(edge_path)
        painter.restore()

    def _static_rail_centers(
        self, base_index: int, slots: tuple[int, ...], width: float, height: float
    ) -> dict[int, float]:
        """Pixel centers for one settled rail, using real package widths."""
        if not slots or not self.records:
            return {}
        widths: list[float] = []
        sequences: list[int] = []
        for slot in slots:
            sequence = base_index + slot
            record = self.records[sequence % len(self.records)]
            pose = arc_pose(float(slot), focus=0.0)
            object_width, _ = self._record_object_size(record, pose.scale, width, height)
            sequences.append(sequence)
            widths.append(object_width)

        anchor_index = slots.index(0) if 0 in slots else len(slots) // 2
        # Even rails have one extra item on the right of the selected object; a
        # slight left anchor keeps the *group* visually centered.
        anchor_x = 0.50 if len(slots) % 2 else 0.455
        centers = anchored_equal_gap_centers(
            widths,
            anchor_index=anchor_index,
            viewport_width=width,
            desired_gap=max(14.0, width * 0.015),
            padding=max(14.0, width * 0.012),
            anchor_x=anchor_x,
        )
        return dict(zip(sequences, centers))

    def _draw_showcase(self, painter: QPainter) -> None:
        if not self.records:
            self._draw_empty_state(painter)
            self._main_rect = QRectF()
            self._record_hit_rects = []
            self._hover_sequence = None
            return

        self._record_hit_rects = []
        focus = self._focus_progress
        width, height = float(self.width()), float(self.height())
        count = len(self.records)
        slots = carousel_slots(count, RETRO_MAX_VISIBLE_ITEMS)
        start_base, end_base, progress = carousel_segment(
            self._arc_position, self._arc_direction
        )
        start_centers = self._static_rail_centers(start_base, slots, width, height)
        end_centers = self._static_rail_centers(end_base, slots, width, height)

        start_slot_by_sequence = {start_base + slot: slot for slot in slots}
        end_slot_by_sequence = {end_base + slot: slot for slot in slots}
        sequences = set(start_slot_by_sequence) | set(end_slot_by_sequence)

        geometry: list[tuple[float, int, GameRecord | MovieRecord, QRectF, float, float]] = []
        nearest_rect = QRectF()
        nearest_sequence: int | None = None
        nearest_distance = 99.0
        panel_p = self._panel_progress

        for sequence in sequences:
            record = self.records[sequence % count]
            if sequence in start_slot_by_sequence:
                start_slot = float(start_slot_by_sequence[sequence])
            else:
                # New cyclic copy starts one slot outside the settled rail.
                start_slot = float(min(slots) - 1 if self._arc_direction < 0 else max(slots) + 1)
            if sequence in end_slot_by_sequence:
                end_slot = float(end_slot_by_sequence[sequence])
            else:
                # Outgoing instance continues off-screen; never modulo-jump it.
                end_slot = float(max(slots) + 1 if self._arc_direction < 0 else min(slots) - 1)

            position = start_slot + (end_slot - start_slot) * progress
            pose = arc_pose(position, focus=focus)
            scale = pose.scale
            opacity = pose.opacity

            object_width, object_height = self._record_object_size(record, scale, width, height)
            if sequence in start_centers:
                start_x = start_centers[sequence]
            else:
                start_x = (
                    -object_width / 2.0 - 30.0
                    if self._arc_direction < 0
                    else width + object_width / 2.0 + 30.0
                )
            if sequence in end_centers:
                end_x = end_centers[sequence]
            else:
                end_x = (
                    width + object_width / 2.0 + 30.0
                    if self._arc_direction < 0
                    else -object_width / 2.0 - 30.0
                )
            browse_x = start_x + (end_x - start_x) * progress
            # Focus mode keeps its established left-hero composition; browse
            # mode uses the width-aware EDGE GAP RAIL above.
            focus_x = width * pose.center_x
            center_x = browse_x + (focus_x - browse_x) * focus
            center_y = pose.center_y

            if self._panel_mode == "details" and panel_p > 0.0:
                target_x = (center_x / width) * 0.78 - 0.006
                center_x += (width * target_x - center_x) * panel_p
                target_scale = 1.12 if abs(position) < 0.5 else 0.88
                scale *= 1.0 + (target_scale - 1.0) * panel_p
                if abs(position) < 0.5:
                    center_y -= 0.060 * panel_p
                target_opacity = 1.0 if abs(position) < 0.5 else 0.18
                opacity *= 1.0 + (target_opacity - 1.0) * panel_p
            elif self._panel_mode == "system" and panel_p > 0.0:
                target_x = (center_x / width) * 0.76 - 0.005
                center_x += (width * target_x - center_x) * panel_p
                center_y += 0.025 * panel_p
                scale *= 1.0 - 0.22 * panel_p
                opacity *= 1.0 - 0.44 * panel_p

            # Recompute size after panel scale adjustments.
            object_width, object_height = self._record_object_size(record, scale, width, height)
            rect = QRectF(
                center_x - object_width / 2.0,
                height * center_y - object_height / 2.0,
                object_width,
                object_height,
            )
            geometry.append((abs(position), sequence, record, rect, opacity, pose.angle))
            if abs(position) < nearest_distance:
                nearest_distance = abs(position)
                nearest_sequence = sequence

        # Paint distant/outgoing copies first.  During a wrap there may briefly
        # be N+1 draw instances: one leaving one edge and its cyclic successor
        # entering from the other, which is the SEAMLESS WRAP behavior.
        geometry.sort(key=lambda item: item[0], reverse=True)
        interaction_enabled = not self.system_open and not self.details_open and not self._search_edit.isVisible()
        for distance, sequence, record, rect, opacity, angle in geometry:
            if rect.right() < -6.0 or rect.left() > width + 6.0:
                continue

            draw_rect = QRectF(rect)
            selectedness = max(0.0, 1.0 - distance)
            strength = self._hover_strengths.get(sequence, 0.0) if interaction_enabled else 0.0
            if strength > 0.001:
                half_w = max(1.0, rect.width() * 0.5)
                half_h = max(1.0, rect.height() * 0.5)
                x_bias = (self._mouse_pos.x() - rect.center().x()) / half_w
                y_bias = (self._mouse_pos.y() - rect.center().y()) / half_h
                hover = hover_pose(strength, x_bias=x_bias, y_bias=y_bias)
                center = rect.center() + QPointF(0.0, hover.lift_px)
                draw_rect.setWidth(rect.width() * hover.scale_multiplier)
                draw_rect.setHeight(rect.height() * hover.scale_multiplier)
                draw_rect.moveCenter(center)
                angle += hover.angle_delta
                selectedness = min(1.25, selectedness + hover.emphasis_boost)

            self._draw_record_object(
                painter, record, draw_rect, opacity, angle, selectedness=selectedness
            )
            self._record_hit_rects.append((sequence, sequence % count, QRectF(draw_rect)))
            if sequence == nearest_sequence:
                nearest_rect = QRectF(draw_rect)

        self._main_rect = nearest_rect

        if not nearest_rect.isNull():
            painter.save()
            shadow_opacity = 0.34 if not self.system_open else 0.16
            painter.setOpacity(shadow_opacity)
            shadow = QRadialGradient(
                QPointF(nearest_rect.center().x(), nearest_rect.bottom() + 18),
                nearest_rect.width() * 0.88,
            )
            shadow.setColorAt(0.0, QColor(22, 124, 128, 66))
            shadow.setColorAt(0.46, QColor(0, 0, 0, 78))
            shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.scale(1.0, 0.23)
            painter.fillRect(
                QRectF(
                    nearest_rect.left() - 64,
                    (nearest_rect.bottom() + 10) / 0.23,
                    nearest_rect.width() + 128,
                    185,
                ),
                shadow,
            )
            painter.restore()

    def _record_object_size(self, record, scale: float, width: float, height: float) -> tuple[float, float]:
        hero_h = min(height * 0.61, 570.0)
        if self.domain == "games":
            profile = self._game_package_profile(record)
            face_ratio = effective_package_face_ratio(
                profile.face_ratio, self._cover_aspect(record.metadata.cover_path)
            )
            total_ratio = face_ratio + profile.depth_ratio
        else:
            total_ratio = self._movie_face_ratio(record) + 0.026

        # Square/Jewel packages are wider at the same height; cap hero width so
        # PS1 artwork does not swallow the scene while still reading as square.
        max_hero_w = width * 0.40
        if hero_h * total_ratio > max_hero_w:
            hero_h = max_hero_w / max(0.2, total_ratio)
        obj_h = hero_h * scale
        obj_w = obj_h * total_ratio
        return obj_w, obj_h

    def _draw_record_object(
        self, painter: QPainter, record, rect: QRectF, opacity: float, angle: float,
        *, selectedness: float = 0.0,
    ) -> None:
        painter.save()
        painter.setOpacity(max(0.05, opacity))
        center = rect.center()
        painter.translate(center)
        painter.rotate(angle)
        painter.translate(-center)

        # FOCUS CONTRAST: size is not the only selected-state cue.  The current
        # package gets a restrained outer edge while neighbors are already
        # dimmed by the rail opacity model.
        emphasis = max(0.0, min(1.0, float(selectedness)))
        if emphasis > 0.12:
            painter.save()
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(103, 229, 225, round(58 * emphasis)), 1.35))
            painter.drawRoundedRect(rect.adjusted(-2.2, -2.2, 2.2, 2.2), 7, 7)
            painter.restore()

        if self.domain == "games":
            self._draw_game_box(painter, record, rect)
        else:
            self._draw_movie_poster(painter, record, rect)
        painter.restore()

    def _draw_game_box(self, painter: QPainter, record: GameRecord, rect: QRectF) -> None:
        profile = self._game_package_profile(record)
        depth = max(5.0, rect.height() * profile.depth_ratio)
        front = QRectF(rect.left(), rect.top(), max(1.0, rect.width() - depth), rect.height())
        side = QPolygonF([
            QPointF(front.right(), front.top() + depth * 0.42),
            QPointF(rect.right(), rect.top()),
            QPointF(rect.right(), rect.bottom() - depth * 0.28),
            QPointF(front.right(), front.bottom()),
        ])
        top = QPolygonF([
            QPointF(front.left() + depth * 0.22, front.top()),
            QPointF(front.right(), front.top() + depth * 0.42),
            QPointF(rect.right(), rect.top()),
            QPointF(front.left() + depth * 0.72, rect.top() - depth * 0.08),
        ])
        # FRONT FACE CLIP: the package front shares the same slanted right edge
        # as the 3D side plane.  Artwork is clipped to this exact face so the
        # top-right corner can never protrude beyond the case geometry.
        front_face = QPolygonF([
            QPointF(front.left(), front.top()),
            QPointF(front.right(), front.top() + depth * 0.42),
            QPointF(front.right(), front.bottom()),
            QPointF(front.left(), front.bottom()),
        ])

        if self.box_style == "classic":
            self._draw_classic_game_case(painter, record, profile, front, side, top, front_face)
        else:
            self._draw_neo_game_case(painter, record, profile, front, side, top, front_face)

    def _draw_classic_game_case(
        self, painter: QPainter, record: GameRecord, profile: PackageProfile,
        front: QRectF, side: QPolygonF, top: QPolygonF, front_face: QPolygonF,
    ) -> None:
        side_grad = QLinearGradient(side.boundingRect().topLeft(), side.boundingRect().bottomRight())
        if profile.family == "jewel":
            side_grad.setColorAt(0.0, QColor(150, 164, 164, 115))
            side_grad.setColorAt(0.45, QColor(61, 73, 74, 190))
            side_grad.setColorAt(1.0, QColor(20, 28, 29, 225))
        else:
            side_grad.setColorAt(0.0, QColor(72, 89, 90))
            side_grad.setColorAt(0.45, QColor(32, 44, 46))
            side_grad.setColorAt(1.0, QColor(13, 20, 21))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(side_grad)
        painter.drawPolygon(side)
        painter.setBrush(QColor(116, 134, 134, 118))
        painter.drawPolygon(top)

        radius = 2.0 if profile.family == "jewel" else 5.0
        painter.save()
        front_clip = QPainterPath()
        front_clip.addPolygon(front_face)
        front_clip.closeSubpath()
        painter.setClipPath(front_clip)
        painter.setPen(QPen(QColor(230, 244, 241, 62), 1.0))
        painter.setBrush(QColor(10, 15, 16))
        painter.drawRoundedRect(front, radius, radius)

        cover_aspect = self._cover_aspect(record.metadata.cover_path)
        shell_y = max(2.0, front.height() * 0.0075)
        art = self._cover_inner_rect(front, cover_aspect, shell_y)
        self._draw_cover(painter, record.metadata.cover_path, art, record.metadata.title)

        # A very light clear-plastic film: material cue, not a sweeping effect.
        gloss = QLinearGradient(art.topLeft(), art.bottomRight())
        gloss.setColorAt(0.0, QColor(255, 255, 255, 30))
        gloss.setColorAt(0.20, QColor(255, 255, 255, 7))
        gloss.setColorAt(0.48, QColor(255, 255, 255, 0))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 8))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gloss)
        painter.drawRoundedRect(art, max(1.0, radius - 1.0), max(1.0, radius - 1.0))

        # Jewel cases get a subtle inner tray seam; keepcases get a soft hinge.
        painter.setPen(QPen(QColor(220, 237, 233, 32), 0.8))
        if profile.family == "jewel":
            seam_x = front.left() + front.width() * 0.075
            painter.drawLine(QPointF(seam_x, front.top() + 4), QPointF(seam_x, front.bottom() - 4))
        else:
            hinge_x = front.left() + max(3.0, front.width() * 0.018)
            painter.drawLine(QPointF(hinge_x, front.top() + 5), QPointF(hinge_x, front.bottom() - 5))
        painter.restore()
        self._draw_case_spine(painter, side, record.metadata.title, profile.label)

    def _draw_neo_game_case(
        self, painter: QPainter, record: GameRecord, profile: PackageProfile,
        front: QRectF, side: QPolygonF, top: QPolygonF, front_face: QPolygonF,
    ) -> None:
        side_grad = QLinearGradient(side.boundingRect().topLeft(), side.boundingRect().bottomRight())
        side_grad.setColorAt(0.0, QColor(45, 88, 93, 126))
        side_grad.setColorAt(0.5, QColor(14, 29, 33, 195))
        side_grad.setColorAt(1.0, QColor(5, 15, 18, 225))
        painter.setPen(QPen(QColor(CYAN.red(), CYAN.green(), CYAN.blue(), 30), 0.9))
        painter.setBrush(side_grad)
        painter.drawPolygon(side)
        painter.setBrush(QColor(38, 89, 94, 72))
        painter.drawPolygon(top)

        painter.save()
        front_clip = QPainterPath()
        front_clip.addPolygon(front_face)
        front_clip.closeSubpath()
        painter.setClipPath(front_clip)
        radius = 3.0 if profile.family == "jewel" else 6.0
        painter.setPen(QPen(QColor(CYAN.red(), CYAN.green(), CYAN.blue(), 38), 1.0))
        painter.setBrush(QColor(9, 25, 29, 170))
        painter.drawRoundedRect(front, radius, radius)

        cover_aspect = self._cover_aspect(record.metadata.cover_path)
        gap_y = max(2.5, front.height() * 0.009)
        art = self._cover_inner_rect(front, cover_aspect, gap_y)
        painter.setPen(QPen(QColor(117, 235, 231, 22), 0.8))
        painter.setBrush(QColor(1, 8, 11, 92))
        painter.drawRoundedRect(art.adjusted(-3, -3, 3, 3), max(2.0, radius - 1), max(2.0, radius - 1))
        self._draw_cover(painter, record.metadata.cover_path, art, record.metadata.title)
        painter.setPen(QPen(QColor(CYAN.red(), CYAN.green(), CYAN.blue(), 44), 0.9))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(front.adjusted(1.2, 1.2, -1.2, -1.2), radius, radius)
        painter.restore()
        self._draw_case_spine(painter, side, record.metadata.title, profile.label, neo=True)

    def _draw_case_spine(
        self, painter: QPainter, side: QPolygonF, title: str, label: str, *, neo: bool = False
    ) -> None:
        bounds = side.boundingRect()
        if bounds.width() < 5.0 or bounds.height() < 80.0:
            return
        painter.save()
        clip = QPainterPath()
        clip.addPolygon(side)
        clip.closeSubpath()
        painter.setClipPath(clip)
        painter.translate(bounds.center())
        painter.rotate(90)
        text_rect = QRectF(-bounds.height() * 0.44, -bounds.width() * 0.50, bounds.height() * 0.88, bounds.width())
        font = QFont("Bahnschrift", max(5, int(bounds.width() * 0.42)))
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(184, 235, 232, 145) if neo else QColor(228, 235, 232, 165))
        prefix = f"{label}  " if label else ""
        metrics = QFontMetrics(font)
        text = metrics.elidedText(prefix + (title or "UNTITLED"), Qt.TextElideMode.ElideRight, int(text_rect.width()))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()

    def _draw_movie_poster(self, painter: QPainter, record: MovieRecord, rect: QRectF) -> None:
        depth = max(4.0, rect.height() * 0.026)
        front = QRectF(rect.left(), rect.top(), max(1.0, rect.width() - depth), rect.height())
        side = QPolygonF([
            QPointF(front.right(), front.top() + depth * 0.36),
            QPointF(rect.right(), rect.top()),
            QPointF(rect.right(), rect.bottom() - depth * 0.24),
            QPointF(front.right(), front.bottom()),
        ])
        top = QPolygonF([
            QPointF(front.left() + depth * 0.20, front.top()),
            QPointF(front.right(), front.top() + depth * 0.36),
            QPointF(rect.right(), rect.top()),
            QPointF(front.left() + depth * 0.70, rect.top() - depth * 0.06),
        ])
        painter.setPen(Qt.PenStyle.NoPen)
        side_grad = QLinearGradient(side.boundingRect().topLeft(), side.boundingRect().bottomRight())
        side_grad.setColorAt(0.0, QColor(40, 83, 104, 190))
        side_grad.setColorAt(1.0, QColor(9, 24, 31, 226))
        painter.setBrush(side_grad)
        painter.drawPolygon(side)
        painter.setBrush(QColor(65, 126, 151, 92))
        painter.drawPolygon(top)

        painter.setPen(QPen(QColor(136, 213, 225, 42), 1.0))
        painter.setBrush(QColor(8, 16, 20))
        painter.drawRoundedRect(front, 4, 4)
        art = front.adjusted(4, 4, -4, -4)
        self._draw_cover(
            painter,
            record.runtime.cover_path,
            art,
            record.metadata.title or record.metadata.code,
        )
        # Thin translucent blue case lip reads as media packaging without
        # covering the poster artwork itself.
        lip = QRectF(front.left() + 2, front.top() + 2, front.width() - 4, max(3.0, front.height() * 0.012))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(58, 150, 184, 82))
        painter.drawRoundedRect(lip, 2, 2)
        self._draw_case_spine(
            painter, side, record.metadata.title or record.metadata.code, "MOVIE", neo=True
        )

    def _cover_inner_rect(
        self, front: QRectF, cover_aspect: float | None, vertical_inset: float
    ) -> QRectF:
        """Inset a face without changing the artwork aspect ratio.

        When the outer face already follows the real cover ratio, symmetric
        pixel insets would subtly change the inner ratio and reintroduce thin
        letterbox bars. Horizontal inset therefore scales with the cover ratio.
        """
        ratio = float(cover_aspect or 0.0)
        if ratio <= 0.0:
            ratio = front.width() / max(1.0, front.height())
        inset_y = max(0.0, min(float(vertical_inset), front.height() * 0.08))
        inset_x = inset_y * ratio
        return front.adjusted(inset_x, inset_y, -inset_x, -inset_y)

    def _draw_cover(self, painter: QPainter, path: str | None, rect: QRectF, title: str) -> None:
        pixmap = self._pixmap(path)
        if pixmap is not None and not pixmap.isNull():
            painter.save()
            painter.setClipRect(rect)
            painter.fillRect(rect, QColor(3, 8, 10))
            scaled = pixmap.scaled(
                QSize(max(1, int(rect.width())), max(1, int(rect.height()))),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            target = QRectF(
                rect.center().x() - scaled.width() / 2.0,
                rect.center().y() - scaled.height() / 2.0,
                float(scaled.width()),
                float(scaled.height()),
            )
            painter.drawPixmap(target, scaled, QRectF(scaled.rect()))
            painter.restore()
            return
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor(31, 90, 94))
        grad.setColorAt(1.0, QColor(9, 23, 27))
        painter.fillRect(rect, grad)
        painter.setPen(TEXT)
        font = QFont("Segoe UI", max(10, int(rect.width() * 0.075)))
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        elided = metrics.elidedText(title or "UNTITLED", Qt.TextElideMode.ElideRight, int(rect.width() * 0.82))
        painter.drawText(rect.adjusted(12, 12, -12, -12), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, elided)

    def _cover_aspect(self, path: str | None) -> float | None:
        pixmap = self._pixmap(path)
        if pixmap is None or pixmap.isNull() or pixmap.height() <= 0:
            return None
        return pixmap.width() / pixmap.height()

    def _game_package_profile(self, record: GameRecord) -> PackageProfile:
        metadata = record.metadata
        cover_path = metadata.cover_path or ""
        hint_parts = [*(metadata.tags or [])]
        if cover_path:
            hint_parts.append(Path(cover_path).stem)
        return resolve_game_package_profile(
            " ".join(str(value) for value in hint_parts if value),
            self._cover_aspect(metadata.cover_path),
        )

    def _movie_face_ratio(self, record: MovieRecord) -> float:
        ratio = self._cover_aspect(record.runtime.cover_path)
        if ratio is None:
            return 2.0 / 3.0
        return max(0.56, min(0.76, ratio))

    def _pixmap(self, path: str | None) -> QPixmap | None:
        if not path:
            return None
        key = str(path)
        if key not in self._pixmap_cache:
            pixmap = QPixmap(key)
            if len(self._pixmap_cache) > 48:
                self._pixmap_cache.clear()
            self._pixmap_cache[key] = pixmap
        return self._pixmap_cache[key]

    def _draw_empty_state(self, painter: QPainter) -> None:
        painter.setPen(TEXT_DIM)
        font = self._ui_font(13, spacing_percent=108)
        painter.setFont(font)
        label = "GAME LIBRARY IS EMPTY" if self.domain == "games" else "MOVIE LIBRARY IS EMPTY"
        painter.drawText(QRectF(0, self.height() * 0.46, self.width(), 50), Qt.AlignmentFlag.AlignCenter, label)

    def _draw_focus_info(self, painter: QPainter) -> None:
        record = self.current_record()
        if record is None:
            return
        nearest = round(self._arc_position)
        rail_settle = max(0.0, 1.0 - abs(self._arc_position - nearest) * 2.0)
        opacity = self._focus_progress * rail_settle
        painter.save()
        painter.setOpacity(opacity)

        # SHORT INFO: anchor the text to the real hero edge.  At the supported
        # minimum window this recovers the horizontal space that a fixed 59.5%
        # column wasted, while keeping the text clear of the next package.
        hero_right = self._main_rect.right() if not self._main_rect.isNull() else self.width() * 0.50
        info_layout = focus_info_layout(
            self.width(), self.height(), hero_right=hero_right
        )
        x = info_layout.left
        y = info_layout.top
        max_w = info_layout.width
        title, lines = self._focus_lines(record)
        title_h = self._draw_focus_title(
            painter,
            title,
            QRectF(x, y, max_w, info_layout.title_height),
            focus_title_max_lines=info_layout.title_max_lines,
            minimum_point_size=info_layout.title_min_point_size,
        )
        y += title_h + max(12.0, self.height() * 0.018)

        small = self._ui_font(max(10, int(self.height() * 0.016)), spacing_percent=110)
        painter.setFont(small)
        for line in lines:
            painter.setPen(TEXT_DIM)
            painter.drawText(
                QRectF(x, y, max_w, 28),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                line,
            )
            y += 29
        y += 18
        more = QRectF(x, y, 96, 32)
        painter.setPen(QPen(CYAN, 1))
        painter.drawText(more, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "MORE  +")
        self._more_rect = more if opacity > 0.35 else QRectF()
        painter.restore()

    def _draw_focus_title(
        self,
        painter: QPainter,
        title: str,
        rect: QRectF,
        *,
        focus_title_max_lines: int = 2,
        minimum_point_size: int = 15,
    ) -> float:
        """Draw a bounded console title without colliding with the next package."""
        text = (title or "UNTITLED").upper()
        size = max(18, int(self.height() * 0.034))
        flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap
        chosen = None
        line_height = 0
        minimum_size = max(10, int(minimum_point_size))
        while size >= minimum_size:
            font = self._ui_font(size, weight=QFont.Weight.DemiBold, spacing_percent=104)
            metrics = QFontMetrics(font)
            line_height = metrics.lineSpacing()
            bounds = metrics.boundingRect(
                0, 0, max(1, int(rect.width())), max(1, int(rect.height() * 3)),
                int(Qt.TextFlag.TextWordWrap), text,
            )
            chosen = font
            if bounds.height() <= line_height * focus_title_max_lines + 2:
                break
            size -= 1

        painter.save()
        painter.setClipRect(rect)
        painter.setFont(chosen or self._ui_font(minimum_size, weight=QFont.Weight.DemiBold, spacing_percent=104))
        painter.setPen(TEXT)
        max_h = min(rect.height(), max(1.0, line_height * focus_title_max_lines + 2.0))
        painter.drawText(QRectF(rect.left(), rect.top(), rect.width(), max_h), flags, text)
        painter.restore()
        return max_h

    def _focus_lines(self, record) -> tuple[str, list[str]]:
        if self.domain == "games":
            m = record.metadata
            profile = self._game_package_profile(record)
            lines: list[str] = []
            if profile.label:
                lines.append(profile.label)
            lines.append(f"PLAY TIME · {format_duration(m.total_play_seconds)}")
            return m.title, lines
        m = record.metadata
        title = m.title or m.code or "Untitled"
        year = m.release_date[:4] if m.release_date else "—"
        count = len(record.episodes)
        type_line = f"{count} EPISODES" if count > 1 else self._movie_runtime_text(record)
        last = self._format_date(m.last_watched_at, "Never watched")
        stars = "★" * m.rating + "☆" * (5 - m.rating) if m.rating else "UNRATED"
        return title, [f"{year} · {type_line}", stars, f"LAST WATCHED · {last}"]

    def _movie_runtime_text(self, record: MovieRecord) -> str:
        seconds = record.runtime.duration or 0
        minutes = int(seconds // 60) if seconds else 0
        return f"{minutes} MIN" if minutes else "MOVIE"

    def _draw_detail_panel(self, painter: QPainter) -> None:
        record = self.current_record()
        if record is None:
            return
        p = self._panel_progress
        panel_w = min(self.width() * DETAIL_PANEL_WIDTH_RATIO, 620.0)
        panel_h = min(self.height() * DETAIL_PANEL_HEIGHT_RATIO, 720.0)
        right_margin = max(30.0, self.width() * 0.045)
        final_left = self.width() - right_margin - panel_w
        left = self.width() + 24.0 + (final_left - self.width() - 24.0) * p
        top = (self.height() - panel_h) / 2.0
        panel = QRectF(left, top, panel_w, panel_h)
        self._detail_panel_rect = panel
        painter.save()
        painter.setOpacity(max(0.02, p))
        painter.setPen(QPen(QColor(103, 211, 213, 34), 1.0))
        painter.setBrush(PANEL)
        painter.drawRoundedRect(panel, 18, 18)
        edge = QLinearGradient(panel.left(), 0, panel.left() + 58, 0)
        edge.setColorAt(0.0, QColor(CYAN.red(), CYAN.green(), CYAN.blue(), 25))
        edge.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(edge)
        painter.drawRoundedRect(QRectF(panel.left(), panel.top(), 60, panel.height()), 18, 18)
        content = panel.adjusted(40, 34, -38, -34)
        tabs = self._detail_tabs(record)
        self._detail_tab_rects.clear()
        x = content.left()
        font = self._ui_font(11, spacing_percent=112)
        painter.setFont(font)
        for tab in tabs:
            width = QFontMetrics(font).horizontalAdvance(tab) + 24
            r = QRectF(x, content.top(), width, 31)
            self._detail_tab_rects[tab] = r
            painter.setPen(TEXT if tab == self.detail_tab else TEXT_FAINT)
            painter.drawText(r, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, tab)
            if tab == self.detail_tab:
                painter.setPen(QPen(CYAN, 1.2))
                painter.drawLine(QPointF(r.left(), r.bottom()), QPointF(r.right() - 14, r.bottom()))
            x += width + 8
        body = QRectF(content.left(), content.top() + 60, content.width(), content.height() - 60)
        self._draw_detail_body(painter, body, record)
        painter.restore()

    def _detail_tabs(self, record) -> list[str]:
        if self.domain == "games":
            return ["概览", "截图", "记录", "本地"]
        return ["概览", "剧集" if len(record.episodes) > 1 else "截图", "记录", "本地"]

    def _draw_detail_body(self, painter: QPainter, body: QRectF, record) -> None:
        painter.setPen(TEXT)
        heading = self._ui_font(24, weight=QFont.Weight.DemiBold)
        painter.setFont(heading)
        title = record.metadata.title if self.domain == "games" else (record.metadata.title or record.metadata.code)
        painter.drawText(QRectF(body.left(), body.top(), body.width(), 44), Qt.AlignmentFlag.AlignLeft, title)
        y = body.top() + 66
        if self.detail_tab == "概览":
            self._draw_overview(painter, body.left(), y, body.width(), record)
        elif self.detail_tab == "记录":
            self._draw_record_history(painter, body.left(), y, body.width(), record)
        elif self.detail_tab == "本地":
            self._draw_local_info(painter, body.left(), y, body.width(), record)
        elif self.detail_tab == "剧集":
            self._draw_episode_grid(painter, body.left(), y, body.width(), record)
        else:
            self._draw_screenshot_strip(painter, body.left(), y, body.width(), record)

    def _draw_overview(self, painter: QPainter, x: float, y: float, width: float, record) -> None:
        if self.domain == "games":
            m = record.metadata
            pairs = [
                ("DEVELOPER", m.developer or "—"),
                ("PUBLISHER", m.publisher or "—"),
                ("RELEASE", m.release_date or "—"),
                ("TAGS", " · ".join(m.tags) if m.tags else "—"),
            ]
            description = m.description or m.notes or "No description yet."
        else:
            m = record.metadata
            pairs = [
                ("STUDIO", m.studio or "—"),
                ("RELEASE", m.release_date or "—"),
                ("SERIES", m.series or "—"),
                ("TAGS", " · ".join(m.tags) if m.tags else "—"),
            ]
            description = m.notes or (" · ".join(m.actors[:8]) if m.actors else "No notes yet.")
        self._draw_pairs(painter, x, y, width, pairs)
        y += 176
        painter.setPen(TEXT_DIM)
        painter.setFont(self._ui_font(11))
        painter.drawText(QRectF(x, y, width * 0.82, 145), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, description)

    def _draw_pairs(self, painter: QPainter, x: float, y: float, width: float, pairs: list[tuple[str, str]]) -> None:
        key_font = self._ui_font(9, spacing_percent=108)
        value_font = self._ui_font(11)
        col = width * 0.48
        for idx, (key, value) in enumerate(pairs):
            col_x = x + (idx % 2) * col
            row_y = y + (idx // 2) * 78
            painter.setFont(key_font)
            painter.setPen(TEXT_FAINT)
            painter.drawText(QRectF(col_x, row_y, col - 24, 22), key)
            painter.setFont(value_font)
            painter.setPen(TEXT)
            painter.drawText(QRectF(col_x, row_y + 25, col - 24, 42), Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, value)

    def _draw_record_history(self, painter: QPainter, x: float, y: float, width: float, record) -> None:
        if self.domain == "games":
            m = record.metadata
            pairs = [
                ("TOTAL PLAY", format_duration(m.total_play_seconds)),
                ("SESSIONS", str(m.play_count)),
                ("FIRST PLAYED", self._format_date(m.first_played_at, "—")),
                ("LAST PLAYED", self._format_date(m.last_played_at, "—")),
            ]
            notes = m.notes or "No personal notes yet."
        else:
            m = record.metadata
            pairs = [
                ("TOTAL WATCH", format_duration(m.total_play_seconds)),
                ("PLAYS", str(m.play_count)),
                ("FIRST WATCHED", self._format_date(m.first_watched_at, "—")),
                ("LAST WATCHED", self._format_date(m.last_watched_at, "—")),
            ]
            notes = m.notes or "No personal notes yet."
        self._draw_pairs(painter, x, y, width, pairs)
        painter.setFont(self._ui_font(11))
        painter.setPen(TEXT_DIM)
        painter.drawText(QRectF(x, y + 176, width * 0.82, 160), Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, notes)

    def _draw_local_info(self, painter: QPainter, x: float, y: float, width: float, record) -> None:
        if self.domain == "games":
            m = record.metadata
            lines = [
                ("STATUS", "INSTALLED" if record.installed else "ARCHIVE ONLY"),
                ("LAUNCH", m.launch_exe or "—"),
                ("TIMING", m.timing_exe or "—"),
                ("SCREENSHOTS", m.screenshot_directory or "—"),
            ]
        else:
            runtime = record.runtime
            path = runtime.video_path or next((e.runtime.video_path for e in record.episodes if e.runtime.video_path), None)
            lines = [
                ("STATUS", runtime.availability_status.upper()),
                ("PATH", path or "—"),
                ("VIDEO", runtime.video_codec or "—"),
                ("AUDIO", runtime.audio_codec or "—"),
            ]
        row = y
        for key, value in lines:
            painter.setFont(self._ui_font(9, spacing_percent=108))
            painter.setPen(TEXT_FAINT)
            painter.drawText(QRectF(x, row, width, 20), key)
            row += 22
            painter.setFont(self._ui_font(10))
            painter.setPen(TEXT)
            painter.drawText(QRectF(x, row, width * 0.88, 42), Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, value)
            row += 58

    def _draw_episode_grid(self, painter: QPainter, x: float, y: float, width: float, record: MovieRecord) -> None:
        cell_w = 82.0
        cell_h = 38.0
        gap = 10.0
        columns = max(1, int(width // (cell_w + gap)))
        for idx, episode in enumerate(record.episodes):
            row, col = divmod(idx, columns)
            r = QRectF(x + col * (cell_w + gap), y + row * (cell_h + gap), cell_w, cell_h)
            available = episode.runtime.availability_status == "available"
            painter.setPen(QPen(QColor(90, 224, 224, 58) if available else QColor(90, 110, 112, 46), 1))
            painter.setBrush(QColor(20, 55, 59, 78) if available else QColor(18, 25, 27, 92))
            painter.drawRoundedRect(r, 5, 5)
            number = episode.metadata.episode_number or episode.metadata.display_order
            painter.setPen(TEXT if available else TEXT_FAINT)
            painter.setFont(self._ui_font(10, spacing_percent=108))
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, f"EP {number:02d}")

    def _draw_screenshot_strip(self, painter: QPainter, x: float, y: float, width: float, record) -> None:
        paths: list[Path] = []
        if self.domain == "games":
            directory = record.metadata.screenshot_directory
            if directory and Path(directory).is_dir():
                paths = [p for p in Path(directory).iterdir() if p.suffix.casefold() in {".jpg", ".jpeg", ".png", ".webp"}][:6]
        if not paths:
            painter.setFont(self._ui_font(11))
            painter.setPen(TEXT_DIM)
            painter.drawText(QRectF(x, y, width, 40), "No screenshot preview is available in this prototype.")
            return
        gap = 14.0
        thumb_w = (width - gap * 2) / 3
        thumb_h = thumb_w * 0.56
        for idx, path in enumerate(paths[:6]):
            row, col = divmod(idx, 3)
            r = QRectF(x + col * (thumb_w + gap), y + row * (thumb_h + gap), thumb_w, thumb_h)
            pixmap = self._pixmap(str(path))
            if pixmap and not pixmap.isNull():
                scaled = pixmap.scaled(int(r.width()), int(r.height()), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                painter.drawPixmap(r, scaled, QRectF(0, 0, min(scaled.width(), r.width()), min(scaled.height(), r.height())))

    def _draw_system_panel(self, painter: QPainter) -> None:
        p = self._panel_progress
        panel_w = min(self.width() * SYSTEM_PANEL_WIDTH_RATIO, 500.0)
        panel_h = min(self.height() * SYSTEM_PANEL_HEIGHT_RATIO, 700.0)
        right_margin = max(26.0, self.width() * 0.035)
        final_left = self.width() - right_margin - panel_w
        left = self.width() + 20.0 + (final_left - self.width() - 20.0) * p
        top = (self.height() - panel_h) / 2.0
        panel = QRectF(left, top, panel_w, panel_h)
        self._system_panel_rect = panel
        painter.save()
        painter.setOpacity(max(0.02, p))
        painter.setPen(QPen(QColor(103, 211, 213, 30), 1.0))
        painter.setBrush(QColor(9, 23, 28, 225))
        painter.drawRoundedRect(panel, 18, 18)
        content = panel.adjusted(34, 32, -32, -30)
        self._draw_system_body(painter, content)
        painter.restore()

    def _draw_system_body(self, painter: QPainter, body: QRectF) -> None:
        self._system_action_rects.clear()
        if self._system_page == "sound":
            self._font_selector.hide()
            self._draw_sound_mapping_body(painter, body)
            return

        self._sound_name_edit.hide()
        painter.setFont(self._ui_font(19, weight=QFont.Weight.DemiBold, spacing_percent=106))
        painter.setPen(TEXT)
        painter.drawText(QRectF(body.left(), body.top(), body.width(), 42), "SETTINGS")

        y = body.top() + 58
        painter.setFont(self._ui_font(9, spacing_percent=110))
        painter.setPen(TEXT_FAINT)
        painter.drawText(QRectF(body.left(), y, body.width(), 22), "RETRO UI FONT")
        combo_top = y + 24
        self._font_selector.setGeometry(
            int(body.left()), int(combo_top), max(120, int(body.width())), 36
        )
        self._font_selector.setVisible(self.system_open and self._panel_progress > 0.05)
        if self._font_selector.isVisible():
            self._font_selector.raise_()

        y = combo_top + 54
        painter.setPen(QPen(QColor(102, 220, 220, 26), 1))
        painter.drawLine(QPointF(body.left(), y), QPointF(body.right(), y))
        y += 18
        y = self._draw_sound_settings_section(painter, body, y)

        painter.setPen(QPen(QColor(102, 220, 220, 26), 1))
        painter.drawLine(QPointF(body.left(), y), QPointF(body.right(), y))
        y += 18
        painter.setFont(self._ui_font(9, spacing_percent=110))
        painter.setPen(TEXT_FAINT)
        painter.drawText(QRectF(body.left(), y, body.width(), 20), "ABOUT")
        y += 24
        painter.setFont(self._ui_font(11, weight=QFont.Weight.DemiBold))
        painter.setPen(TEXT_DIM)
        painter.drawText(QRectF(body.left(), y, body.width(), 24), "LOCAL RESOURCE TERMINAL")
        y += 27
        painter.setFont(self._ui_font(17, weight=QFont.Weight.DemiBold))
        painter.setPen(TEXT)
        painter.drawText(QRectF(body.left(), y, body.width(), 28), f"V{RETRO_VERSION}")

        advanced = QRectF(body.left(), body.bottom() - 44, body.width(), 40)
        self._system_action_rects["advanced_settings"] = advanced
        painter.setPen(QPen(QColor(102, 220, 220, 38), 1))
        painter.setBrush(QColor(20, 54, 58, 72))
        painter.drawRoundedRect(advanced, 8, 8)
        painter.setPen(TEXT_DIM)
        painter.setFont(self._ui_font(10))
        painter.drawText(
            advanced.adjusted(16, 0, -16, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "高级设置…",
        )

    def _draw_sound_settings_section(self, painter: QPainter, body: QRectF, y: float) -> float:
        painter.setFont(self._ui_font(9, spacing_percent=110))
        painter.setPen(TEXT_FAINT)
        painter.drawText(QRectF(body.left(), y, body.width(), 20), "SOUND")
        y += 25

        toggle = QRectF(body.left(), y, body.width(), 34)
        self._system_action_rects["sound_toggle"] = toggle
        painter.setPen(QPen(QColor(102, 220, 220, 30), 1))
        painter.setBrush(QColor(20, 54, 58, 66))
        painter.drawRoundedRect(toggle, 7, 7)
        painter.setFont(self._ui_font(10))
        painter.setPen(TEXT_DIM)
        painter.drawText(toggle.adjusted(12, 0, -70, 0), Qt.AlignmentFlag.AlignVCenter, "UI 音效")
        painter.setPen(CYAN if self._sound_enabled else TEXT_FAINT)
        painter.drawText(toggle.adjusted(0, 0, -12, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, "ON" if self._sound_enabled else "OFF")
        y += 40

        pack = self._current_sound_pack()
        pack_row = QRectF(body.left(), y, body.width(), 32)
        prev_rect = QRectF(pack_row.left(), pack_row.top(), 34, pack_row.height())
        next_rect = QRectF(pack_row.right() - 34, pack_row.top(), 34, pack_row.height())
        self._system_action_rects["sound_pack_prev"] = prev_rect
        self._system_action_rects["sound_pack_next"] = next_rect
        painter.setPen(TEXT_FAINT)
        painter.drawText(prev_rect, Qt.AlignmentFlag.AlignCenter, "‹")
        painter.drawText(next_rect, Qt.AlignmentFlag.AlignCenter, "›")
        painter.setPen(TEXT_DIM)
        painter.setFont(self._ui_font(9, weight=QFont.Weight.DemiBold))
        painter.drawText(pack_row.adjusted(38, 0, -38, 0), Qt.AlignmentFlag.AlignCenter, pack.name if pack else "无音效包")
        y += 38

        painter.setFont(self._ui_font(9))
        painter.setPen(TEXT_FAINT)
        painter.drawText(QRectF(body.left(), y, 48, 22), Qt.AlignmentFlag.AlignVCenter, "音量")
        volume_bar = QRectF(body.left() + 54, y + 6, body.width() - 54, 10)
        self._system_action_rects["sound_volume_bar"] = volume_bar.adjusted(0, -7, 0, 7)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(80, 116, 120, 90))
        painter.drawRoundedRect(volume_bar, 5, 5)
        fill = QRectF(volume_bar.left(), volume_bar.top(), volume_bar.width() * self._sound_volume, volume_bar.height())
        painter.setBrush(QColor(92, 224, 226, 155))
        painter.drawRoundedRect(fill, 5, 5)
        y += 29

        manage = QRectF(body.left(), y, body.width(), 34)
        self._system_action_rects["sound_manage"] = manage
        painter.setPen(QPen(QColor(102, 220, 220, 38), 1))
        painter.setBrush(QColor(20, 54, 58, 72))
        painter.drawRoundedRect(manage, 7, 7)
        painter.setPen(TEXT_DIM)
        painter.setFont(self._ui_font(9, weight=QFont.Weight.DemiBold))
        painter.drawText(manage.adjusted(12, 0, -12, 0), Qt.AlignmentFlag.AlignVCenter, "管理音效映射  ›")
        return y + 44

    def _draw_sound_mapping_body(self, painter: QPainter, body: QRectF) -> None:
        painter.setFont(self._ui_font(17, weight=QFont.Weight.DemiBold, spacing_percent=104))
        painter.setPen(TEXT)
        painter.drawText(QRectF(body.left(), body.top(), body.width() - 72, 34), "SOUND MAPPING")
        back = QRectF(body.right() - 62, body.top(), 62, 30)
        self._system_action_rects["sound_back"] = back
        painter.setFont(self._ui_font(9))
        painter.setPen(TEXT_DIM)
        painter.drawText(back, Qt.AlignmentFlag.AlignCenter, "‹ 返回")

        pack = self._current_sound_pack()
        y = body.top() + 40
        painter.setFont(self._ui_font(10, weight=QFont.Weight.DemiBold))
        painter.setPen(CYAN if pack else TEXT_FAINT)
        painter.drawText(QRectF(body.left(), y, body.width(), 26), pack.name if pack else "还没有音效包")
        y += 30

        gap = 5.0
        labels = (
            ("sound_pack_create", "新建"),
            ("sound_pack_duplicate", "复制"),
            ("sound_pack_rename", "改名"),
            ("sound_pack_delete", "删除"),
        )
        button_w = (body.width() - gap * 3) / 4
        for index, (key, label) in enumerate(labels):
            rect = QRectF(body.left() + index * (button_w + gap), y, button_w, 28)
            self._system_action_rects[key] = rect
            painter.setPen(QPen(QColor(102, 220, 220, 30), 1))
            painter.setBrush(QColor(20, 54, 58, 62))
            painter.drawRoundedRect(rect, 6, 6)
            painter.setPen(TEXT_DIM)
            painter.setFont(self._ui_font(8))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        y += 36

        if self._sound_name_mode:
            self._sound_name_edit.setGeometry(int(body.left()), int(y), max(120, int(body.width())), 32)
            self._sound_name_edit.show()
            self._sound_name_edit.raise_()
            y += 40
        else:
            self._sound_name_edit.hide()

        mappings = self._sound_store.load_mappings(pack.id) if pack is not None else {}
        for event in SOUND_EVENTS:
            row = QRectF(body.left(), y, body.width(), 44)
            painter.setPen(QPen(QColor(102, 220, 220, 18), 1))
            painter.drawLine(row.bottomLeft(), row.bottomRight())
            painter.setFont(self._ui_font(8, weight=QFont.Weight.DemiBold))
            painter.setPen(TEXT_DIM)
            painter.drawText(QRectF(row.left(), row.top() + 2, row.width() - 112, 18), SOUND_EVENT_LABELS[event])
            source_name = mappings.get(event, {}).get("original", "未设置")
            painter.setFont(self._ui_font(7))
            painter.setPen(TEXT_FAINT)
            painter.drawText(QRectF(row.left(), row.top() + 20, row.width() - 112, 17), source_name)

            button_w = 32.0
            clear = QRectF(row.right() - button_w, row.top() + 7, button_w, 28)
            import_rect = QRectF(clear.left() - button_w - 3, row.top() + 7, button_w, 28)
            preview = QRectF(import_rect.left() - button_w - 3, row.top() + 7, button_w, 28)
            self._system_action_rects[f"sound_preview:{event}"] = preview
            self._system_action_rects[f"sound_import:{event}"] = import_rect
            self._system_action_rects[f"sound_clear:{event}"] = clear
            for rect, label in ((preview, "▶"), (import_rect, "换"), (clear, "×")):
                painter.setPen(QPen(QColor(102, 220, 220, 28), 1))
                painter.setBrush(QColor(20, 54, 58, 52))
                painter.drawRoundedRect(rect, 6, 6)
                painter.setPen(TEXT_DIM)
                painter.setFont(self._ui_font(8))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
            y += 46

        if self._sound_status:
            painter.setFont(self._ui_font(7))
            painter.setPen(TEXT_FAINT)
            painter.drawText(
                QRectF(body.left(), min(y + 4, body.bottom() - 32), body.width(), 28),
                Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                self._sound_status,
            )

    def _draw_corner_menu(self, painter: QPainter) -> None:
        opacity = self._menu_opacity
        if opacity <= 0.01:
            self._menu_button_rects.clear()
            return
        painter.save()
        painter.setOpacity(opacity)
        size = 44.0
        gap = 10.0
        count = 3
        total = size * count + gap * (count - 1)
        margin = 20.0
        if self.menu_corner == "bottom_right":
            x = self.width() - margin - total
        else:
            x = margin
        y = self.height() - margin - size
        self._menu_button_rects.clear()
        for idx, key in enumerate(("movies", "games", "settings")):
            r = QRectF(x + idx * (size + gap), y, size, size)
            self._menu_button_rects[key] = r
            active = (key == self.domain) or (key == "settings" and self.system_open)
            fill = QColor(52, 70, 73, 205 if active else 154)
            border = QColor(CYAN.red(), CYAN.green(), CYAN.blue(), 90 if active else 34)
            painter.setPen(QPen(border, 1))
            painter.setBrush(fill)
            painter.drawRoundedRect(r, 11, 11)
            self._draw_menu_icon(painter, key, r, active)
        painter.restore()

    def _draw_menu_icon(self, painter: QPainter, key: str, r: QRectF, active: bool) -> None:
        color = TEXT if active else TEXT_DIM
        painter.setPen(QPen(color, 1.7))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        c = r.center()
        if key == "movies":
            rr = QRectF(c.x() - 10, c.y() - 8, 20, 16)
            painter.drawRoundedRect(rr, 3, 3)
            tri = QPolygonF([QPointF(c.x() - 2, c.y() - 4), QPointF(c.x() - 2, c.y() + 4), QPointF(c.x() + 5, c.y())])
            painter.setBrush(color)
            painter.drawPolygon(tri)
        elif key == "games":
            path = QPainterPath()
            path.moveTo(c.x() - 11, c.y() + 5)
            path.cubicTo(c.x() - 13, c.y() - 7, c.x() - 7, c.y() - 10, c.x(), c.y() - 7)
            path.cubicTo(c.x() + 7, c.y() - 10, c.x() + 13, c.y() - 7, c.x() + 11, c.y() + 5)
            path.cubicTo(c.x() + 10, c.y() + 9, c.x() + 6, c.y() + 8, c.x() + 3, c.y() + 4)
            path.lineTo(c.x() - 3, c.y() + 4)
            path.cubicTo(c.x() - 6, c.y() + 8, c.x() - 10, c.y() + 9, c.x() - 11, c.y() + 5)
            painter.drawPath(path)
            painter.drawLine(QPointF(c.x() - 6, c.y() - 1), QPointF(c.x() - 1, c.y() - 1))
            painter.drawLine(QPointF(c.x() - 3.5, c.y() - 3.5), QPointF(c.x() - 3.5, c.y() + 1.5))
            painter.drawEllipse(QPointF(c.x() + 5, c.y() - 2), 1.5, 1.5)
        else:
            painter.drawEllipse(QPointF(c.x(), c.y()), 8, 8)
            painter.drawEllipse(QPointF(c.x(), c.y()), 2.5, 2.5)
            for angle in range(0, 360, 45):
                a = math.radians(angle)
                painter.drawLine(
                    QPointF(c.x() + math.cos(a) * 9, c.y() + math.sin(a) * 9),
                    QPointF(c.x() + math.cos(a) * 12, c.y() + math.sin(a) * 12),
                )

    def _draw_window_controls(self, painter: QPainter) -> None:
        self._window_control_rects.clear()
        if not self._window_controls_visible:
            return
        size = 30.0
        gap = 4.0
        y = 8.0
        start = self.width() - 12.0 - size * 3 - gap * 2
        painter.save()
        painter.setOpacity(0.72)
        for idx, (key, glyph) in enumerate((("min", "—"), ("max", "□"), ("close", "×"))):
            r = QRectF(start + idx * (size + gap), y, size, size)
            self._window_control_rects[key] = r
            painter.setPen(QPen(QColor(105, 214, 214, 34), 1))
            painter.setBrush(QColor(16, 37, 41, 122))
            painter.drawRoundedRect(r, 7, 7)
            painter.setPen(TEXT_DIM if key != "close" else QColor(221, 167, 167))
            painter.setFont(self._ui_font(11))
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, glyph)
        painter.restore()

    # ----- interaction ---------------------------------------------------------
    def _record_hit_at(self, pos: QPointF) -> tuple[int, int, QRectF] | None:
        # Hit-test in reverse paint order so the visually frontmost package
        # wins when two perspective boxes overlap.
        for sequence, logical_index, rect in reversed(self._record_hit_rects):
            if rect.contains(pos):
                return sequence, logical_index, rect
        return None

    def _set_hover_sequence(self, sequence: int | None) -> None:
        if sequence == self._hover_sequence:
            return
        self._hover_sequence = sequence
        if sequence is not None:
            self._hover_strengths.setdefault(sequence, 0.0)
        # Start hover easing immediately at the active cadence; _ambient_tick
        # returns to the 15 fps idle cadence after the pose settles.
        self._ambient_timer.setInterval(AMBIENT_ACTIVE_INTERVAL_MS)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.width() and self.height():
            self._mouse_norm = QPointF(
                (event.position().x() / self.width() - 0.5) * 2.0,
                (event.position().y() / self.height() - 0.5) * 2.0,
            )
        pos = event.position()
        self._mouse_pos = QPointF(pos)
        controls_visible = pos.y() <= 52 and pos.x() >= self.width() - 170
        if controls_visible != self._window_controls_visible:
            self._window_controls_visible = controls_visible
            self.update()
        if self._in_corner_hot_zone(pos) or any(r.contains(pos) for r in self._menu_button_rects.values()):
            self._menu_hide_timer.stop()
            self._animate_menu(True)
        elif self._menu_opacity > 0.05 and not self._menu_hide_timer.isActive():
            self._menu_hide_timer.start()

        if self.system_open or self.details_open or self._search_edit.isVisible():
            self._set_hover_sequence(None)
        else:
            hit = self._record_hit_at(pos)
            self._set_hover_sequence(hit[0] if hit is not None else None)
        self.update()

    def leaveEvent(self, _event) -> None:
        self._window_controls_visible = False
        self._mouse_pos = QPointF(-10_000.0, -10_000.0)
        self._set_hover_sequence(None)
        if self._menu_opacity > 0.05:
            self._menu_hide_timer.start()
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._press_pos = event.position().toPoint()
        if event.button() == Qt.MouseButton.RightButton:
            if self._main_rect.contains(event.position()) and self.current_record() is not None:
                self._show_record_menu(event.globalPosition().toPoint())
            else:
                self._show_scene_menu(event.globalPosition().toPoint())
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()
        if self._search_edit.isVisible() and not self._search_edit.geometry().contains(pos.toPoint()):
            self._hide_search_bar()
        for key, rect in self._window_control_rects.items():
            if rect.contains(pos):
                if key == "min":
                    self.host.showMinimized()
                elif key == "max":
                    self.host.showNormal() if self.host.isMaximized() else self.host.showMaximized()
                else:
                    self.host.close()
                return
        if pos.y() <= 38:
            handle = self.host.windowHandle()
            if handle is not None:
                handle.startSystemMove()
                return
        for key, rect in self._menu_button_rects.items():
            if rect.contains(pos):
                self._activate_corner_action(key)
                return
        if self.system_open:
            if self._handle_system_click(pos):
                return
            if not self._system_panel_rect.contains(pos):
                self._set_system_open(False)
            return
        if self.details_open:
            if self._handle_detail_click(pos):
                return
            if not self._detail_panel_rect.contains(pos):
                self._set_details_open(False)
            return
        if self._more_rect.contains(pos) and self.focused:
            self._set_details_open(True)
            return

        hit = self._record_hit_at(pos)
        if hit is not None and self.current_record() is not None:
            sequence, _logical_index, _rect = hit
            current_sequence = round(self._arc_position)
            intent = showcase_click_intent(
                clicked_sequence=sequence,
                current_sequence=current_sequence,
                focused=self.focused,
            )
            if intent == "select":
                if self.focused:
                    self._set_focused(False)
                self._play_ui_sound("select")
                self._animate_arc_to(sequence)
                return
            if intent == "focus":
                self._play_ui_sound("focus")
                self._set_focused(True)
                return
            return

        if self.focused:
            self._play_ui_sound("back")
            self._set_focused(False)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if event.position().y() <= 38:
            self.host.showNormal() if self.host.isMaximized() else self.host.showMaximized()
            return
        hit = self._record_hit_at(event.position())
        if hit is None or hit[0] != round(self._arc_position):
            return
        record = self.current_record()
        if record is None:
            return
        self._play_ui_sound("confirm")
        if self.domain == "games":
            self.host._launch_game(record)
        else:
            self.host._play_record(record)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.system_open or self.details_open or len(self.records) < 2:
            event.accept()
            return
        delta = event.angleDelta().y()
        if not delta:
            return
        direction = -1 if delta > 0 else 1
        self._start_arc(direction)
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            if self._sound_name_edit.isVisible():
                self._cancel_sound_name_edit()
                return
            if self.system_open and self._system_page == "sound":
                self._system_page = "settings"
                self._play_ui_sound("back")
                self.update()
                return
            if self.details_open:
                self._set_details_open(False)
                return
            if self.system_open:
                self._set_system_open(False)
                return
            if self.focused:
                self._play_ui_sound("back")
                self._set_focused(False)
                return
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Up):
            self._start_arc(-1)
            return
        if event.key() in (Qt.Key.Key_Right, Qt.Key.Key_Down):
            self._start_arc(1)
            return
        super().keyPressEvent(event)

    def _in_corner_hot_zone(self, pos: QPointF) -> bool:
        width = 94.0
        height = 82.0
        if self.menu_corner == "bottom_right":
            return pos.x() >= self.width() - width and pos.y() >= self.height() - height
        return pos.x() <= width and pos.y() >= self.height() - height

    def _animate_menu(self, visible: bool) -> None:
        target = 1.0 if visible else 0.0
        if abs(self._menu_opacity - target) < 0.02:
            return
        self._menu_anim.stop()
        self._menu_anim.setStartValue(self._menu_opacity)
        self._menu_anim.setEndValue(target)
        self._menu_anim.setDuration(180 if visible else 245)
        self._menu_anim.start()

    def _set_focused(self, focused: bool) -> None:
        self.focused = bool(focused)
        if not self.focused:
            self.details_open = False
            self._panel_progress = 0.0
        self._focus_anim.stop()
        self._focus_anim.setStartValue(self._focus_progress)
        self._focus_anim.setEndValue(1.0 if self.focused else 0.0)
        self._focus_anim.start()

    def _set_details_open(self, opened: bool) -> None:
        opened = bool(opened)
        changed = opened != self.details_open
        if changed:
            if opened:
                self._play_ui_sound("open_panel")
            else:
                self._play_ui_sound("close_panel")
        if opened:
            self.details_open = True
            self.system_open = False
            self._font_selector.hide()
            self._panel_mode = "details"
            self.focused = True
            self.detail_tab = "概览"
            if self._focus_progress < 0.99:
                self._focus_progress = 1.0
        else:
            self.details_open = False
        self._panel_anim.stop()
        self._panel_anim.setStartValue(self._panel_progress)
        self._panel_anim.setEndValue(1.0 if opened else 0.0)
        self._panel_anim.start()
        self.update()

    def _set_system_open(self, opened: bool) -> None:
        opened = bool(opened)
        changed = opened != self.system_open
        if changed:
            if opened:
                self._play_ui_sound("open_panel")
            else:
                self._play_ui_sound("close_panel")
        if opened:
            self._hide_search_bar()
            self.system_open = True
            self.details_open = False
            self._panel_mode = "system"
            self._menu_hide_timer.stop()
            self._animate_menu(True)
        else:
            self.system_open = False
            self._system_page = "settings"
            self._font_selector.hide()
            self._sound_name_edit.hide()
            self._sound_name_mode = None
        self._panel_anim.stop()
        self._panel_anim.setStartValue(self._panel_progress)
        self._panel_anim.setEndValue(1.0 if opened else 0.0)
        self._panel_anim.start()
        self.update()

    def _finish_panel_motion(self) -> None:
        if self._panel_progress <= 0.001 and not self.details_open and not self.system_open:
            self._panel_mode = None
            self._detail_panel_rect = QRectF()
            self._system_panel_rect = QRectF()
        self.update()

    def _animate_arc_to(self, target_sequence: int | float) -> None:
        if len(self.records) < 2:
            return
        current = float(self._arc_position)
        target = float(target_sequence)
        distance = abs(target - current)
        if distance < 0.001:
            return
        self._arc_direction = -1 if target < current else 1
        self._arc_target = target
        self._arc_anim.stop()
        self._arc_anim.setStartValue(current)
        self._arc_anim.setEndValue(target)
        # One-slot wheel moves stay responsive; direct clicks can cross two
        # visible slots in one continuous eased motion without stepping.
        self._arc_anim.setDuration(
            max(195, min(445, round(225 + 92 * max(0.0, distance - 1.0))))
        )
        self._arc_anim.start()

    def _start_arc(self, direction: int) -> None:
        if len(self.records) < 2:
            return
        self._play_ui_sound("navigate")
        step = -1 if direction < 0 else 1
        # Consecutive wheel input extends/reverses the unwrapped target instead
        # of snapping through modulo indices.
        if self._arc_anim.state() != QAbstractAnimation.State.Running:
            self._arc_target = round(self._arc_position)
        self._animate_arc_to(self._arc_target + step)

    def _finish_arc(self) -> None:
        if self.records:
            self.current_index = round(self._arc_position) % len(self.records)
        self.update()

    def _activate_corner_action(self, key: str) -> None:
        if key == "settings":
            self._set_system_open(not self.system_open)
            return
        if key == self.domain:
            self._set_system_open(False)
            return
        self._hide_search_bar()
        self.domain = key
        self.current_index = 0
        self._arc_anim.stop()
        self._arc_position = 0.0
        self._arc_target = 0.0
        self.focused = False
        self.details_open = False
        self.system_open = False
        self._panel_mode = None
        self._focus_progress = 0.0
        self._panel_progress = 0.0
        self.detail_tab = "概览"
        self.refresh_records()

    def _handle_detail_click(self, pos: QPointF) -> bool:
        for tab, rect in self._detail_tab_rects.items():
            if rect.contains(pos):
                self.detail_tab = tab
                self.update()
                return True
        return False

    def _handle_system_click(self, pos: QPointF) -> bool:
        for key, rect in list(self._system_action_rects.items()):
            if not rect.contains(pos):
                continue
            if key == "advanced_settings":
                self._set_system_open(False)
                self.host.settings_requested.emit()
            elif key == "sound_toggle":
                if self._sound_pack_id is None:
                    self._sound_status = "请先创建一个音效包。"
                else:
                    self._sound_enabled = not self._sound_enabled
                    self._configure_sound_service()
            elif key == "sound_pack_prev":
                self._cycle_sound_pack(-1)
            elif key == "sound_pack_next":
                self._cycle_sound_pack(1)
            elif key == "sound_volume_bar":
                ratio = (pos.x() - rect.left()) / max(1.0, rect.width())
                self._sound_volume = max(0.0, min(float(ratio), 1.0))
                self._configure_sound_service()
            elif key == "sound_manage":
                self._system_page = "sound"
                self._sound_status = ""
                self._font_selector.hide()
                self.update()
            elif key == "sound_back":
                self._system_page = "settings"
                self._cancel_sound_name_edit()
                self._play_ui_sound("back")
                self.update()
            elif key == "sound_pack_create":
                self._begin_sound_name_edit("create")
            elif key == "sound_pack_duplicate":
                self._duplicate_sound_pack()
            elif key == "sound_pack_rename":
                self._begin_sound_name_edit("rename")
            elif key == "sound_pack_delete":
                self._delete_current_sound_pack()
            elif key.startswith("sound_preview:"):
                self._preview_sound_event(key.split(":", 1)[1])
            elif key.startswith("sound_import:"):
                self._import_sound_event(key.split(":", 1)[1])
            elif key.startswith("sound_clear:"):
                self._clear_sound_event(key.split(":", 1)[1])
            return True
        return False

    @staticmethod
    def _base_filter_payload(domain: str, key: str) -> dict:
        for _label, candidate, payload in library_filter_options(domain):
            if candidate == key:
                return dict(payload)
        return {}

    def _reset_collection_position(self) -> None:
        self._arc_anim.stop()
        self.current_index = 0
        self._arc_position = 0.0
        self._arc_target = 0.0
        self.focused = False
        self.details_open = False
        self._panel_mode = None if not self.system_open else self._panel_mode
        self._focus_progress = 0.0
        self.refresh_records()

    def _emit_view_state(self, domain: str) -> None:
        self.view_state_changed.emit(
            domain,
            self._sort_keys[domain],
            self._sort_desc[domain],
            persistent_filter_key(domain, self._filter_keys[domain]),
        )

    def _clear_search(self) -> None:
        if not self._search_text[self.domain]:
            return
        self._search_text[self.domain] = ""
        if self._search_edit.isVisible():
            self._search_edit.blockSignals(True)
            self._search_edit.clear()
            self._search_edit.blockSignals(False)
        self._reset_collection_position()

    def _set_filter(self, key: str, payload: dict | None = None) -> None:
        self._filter_keys[self.domain] = str(key or "all")
        self._filter_payloads[self.domain] = dict(payload or self._base_filter_payload(self.domain, key))
        self._emit_view_state(self.domain)
        self._reset_collection_position()

    def _set_sort(self, key: str) -> None:
        self._sort_keys[self.domain] = str(key)
        self._emit_view_state(self.domain)
        self._reset_collection_position()

    def _toggle_sort_direction(self) -> None:
        self._sort_desc[self.domain] = not self._sort_desc[self.domain]
        self._emit_view_state(self.domain)
        self._reset_collection_position()

    def _set_folder(self, folder_id: str | None) -> None:
        if folder_id and self.host.collection_folders is not None:
            folder = self.host.collection_folders.get(folder_id)
            if folder is None or folder.domain != self.domain:
                QMessageBox.warning(self, "分类失败", "目标分类不存在或不属于当前媒体库。")
                return
        self._folder_ids[self.domain] = str(folder_id) if folder_id else None
        self.folder_state_changed.emit(self.domain, self._folder_ids[self.domain])
        self._reset_collection_position()

    def _folder_entries(self, domain: str):
        if self.host.collection_folders is None:
            return []
        try:
            return list(self.host.collection_folders.list(domain))
        except Exception as exc:
            QMessageBox.warning(self, "读取分类失败", str(exc))
            return []

    def _populate_filter_menu(self, menu: QMenu) -> None:
        active = self._filter_keys[self.domain]
        for label, key, payload in library_filter_options(self.domain):
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(active == key)
            action.triggered.connect(
                lambda _checked=False, k=key, p=dict(payload): self._set_filter(k, p)
            )
        tags = []
        try:
            if self.domain == "games" and self.host.game_catalog is not None:
                tags = self.host.game_catalog.common_tags(20)
            elif self.domain == "movies":
                tags = self.host.catalog.common_tags(20)
        except Exception:
            tags = []
        if tags:
            tag_menu = menu.addMenu("标签")
            for tag in tags:
                key = f"tag:{tag}"
                action = tag_menu.addAction(tag)
                action.setCheckable(True)
                action.setChecked(active == key)
                action.triggered.connect(
                    lambda _checked=False, t=tag, k=key: self._set_filter(k, {"tag": t})
                )
        if self.domain == "movies":
            libraries = [item for item in getattr(self.host.settings, "libraries", []) if item.enabled]
            if libraries:
                library_menu = menu.addMenu("影片库")
                for library in libraries:
                    key = f"library:{library.id}"
                    action = library_menu.addAction(library.name)
                    action.setCheckable(True)
                    action.setChecked(active == key)
                    action.triggered.connect(
                        lambda _checked=False, library_id=library.id, k=key: self._set_filter(k, {"library_id": library_id})
                    )

    def _populate_sort_menu(self, menu: QMenu) -> None:
        active = self._sort_keys[self.domain]
        for label, key in library_sort_options(self.domain):
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(active == key)
            action.triggered.connect(lambda _checked=False, k=key: self._set_sort(k))
        menu.addSeparator()
        direction = menu.addAction("降序" if self._sort_desc[self.domain] else "升序")
        direction.setCheckable(True)
        direction.setChecked(self._sort_desc[self.domain])
        direction.triggered.connect(self._toggle_sort_direction)

    def _populate_folder_menu(self, menu: QMenu) -> None:
        current = self._folder_ids[self.domain]
        all_action = menu.addAction("全部内容")
        all_action.setCheckable(True)
        all_action.setChecked(current is None)
        all_action.triggered.connect(lambda: self._set_folder(None))
        folders = self._folder_entries(self.domain)
        if folders:
            menu.addSeparator()
        for folder in folders:
            action = menu.addAction(folder.name)
            action.setCheckable(True)
            action.setChecked(current == folder.id)
            action.triggered.connect(
                lambda _checked=False, folder_id=folder.id: self._set_folder(folder_id)
            )

    def _add_game(self) -> None:
        self.host._add_game()
        if self.domain == "games":
            self._reset_collection_position()

    def _move_current_to_folder(self, folder_id: str | None) -> None:
        record = self.current_record()
        if record is None:
            return
        catalog = self.host.game_catalog if self.domain == "games" else self.host.catalog
        if catalog is None:
            return
        if folder_id and self.host.collection_folders is not None:
            folder = self.host.collection_folders.get(folder_id)
            if folder is None or folder.domain != self.domain:
                QMessageBox.warning(self, "移动失败", "目标分类不存在或不属于当前媒体库。")
                return
        try:
            catalog.set_folder([record.metadata.uuid], folder_id)
        except Exception as exc:
            QMessageBox.warning(self, "移动失败", str(exc))
            return
        self.refresh_records()

    def _populate_move_to_folder_menu(self, menu: QMenu) -> None:
        move_menu = menu.addMenu("移动到分类")
        move_menu.addAction("未分类").triggered.connect(
            lambda: self._move_current_to_folder(None)
        )
        folders = self._folder_entries(self.domain)
        if folders:
            move_menu.addSeparator()
        for folder in folders:
            move_menu.addAction(folder.name).triggered.connect(
                lambda _checked=False, folder_id=folder.id: self._move_current_to_folder(folder_id)
            )

    # ----- menus ---------------------------------------------------------------
    def _show_scene_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        if self.domain == "games":
            menu.addAction("添加游戏…").triggered.connect(self._add_game)
        menu.addAction("搜索…").triggered.connect(self._show_search_bar)
        if self._search_text[self.domain]:
            menu.addAction(f"清除搜索 · {self._search_text[self.domain]}").triggered.connect(self._clear_search)
        filter_menu = menu.addMenu("筛选")
        self._populate_filter_menu(filter_menu)
        sort_menu = menu.addMenu("排序")
        self._populate_sort_menu(sort_menu)
        folder_menu = menu.addMenu("分类")
        self._populate_folder_menu(folder_menu)
        menu.addSeparator()
        if self.domain == "games":
            style = menu.addMenu("游戏盒体")
            neo = style.addAction("Neo Box")
            classic = style.addAction("Classic Box")
            neo.setCheckable(True)
            classic.setCheckable(True)
            neo.setChecked(self.box_style == "neo")
            classic.setChecked(self.box_style == "classic")
            neo.triggered.connect(lambda: self._set_box_style("neo"))
            classic.triggered.connect(lambda: self._set_box_style("classic"))
        else:
            menu.addAction("影片封面工具…").triggered.connect(lambda: self.host._open_cover_tools())
            menu.addAction("重新扫描影片资源").triggered.connect(self.host.start_scan)
        corner = menu.addMenu("角落菜单")
        corner.addAction("右下角").triggered.connect(lambda: self._set_menu_corner("bottom_right"))
        corner.addAction("左下角").triggered.connect(lambda: self._set_menu_corner("bottom_left"))
        menu.addSeparator()
        menu.addAction("刷新展示").triggered.connect(self.refresh_records)
        menu.exec(global_pos)

    def _show_record_menu(self, global_pos: QPoint) -> None:
        record = self.current_record()
        if record is None:
            return
        menu = QMenu(self)
        if self.domain == "games":
            launch = menu.addAction("启动游戏")
            launch.setEnabled(record.installed)
            launch.triggered.connect(lambda: self.host._launch_game(record))
            menu.addAction("展开详情").triggered.connect(lambda: self._set_details_open(True))
            menu.addAction("编辑游戏档案…").triggered.connect(self._edit_current_game)
            self._populate_move_to_folder_menu(menu)
            menu.addSeparator()
            game_dir = menu.addAction("打开游戏目录")
            game_dir.setEnabled(bool(record.metadata.launch_exe and Path(record.metadata.launch_exe).parent.is_dir()))
            game_dir.triggered.connect(lambda: self.host._open_path(Path(record.metadata.launch_exe).parent))
            menu.addSeparator()
            menu.addAction("删除游戏档案…").triggered.connect(lambda: self.host._delete_game(record))
        else:
            play = menu.addAction("播放")
            play.setEnabled(bool(record.playable_episodes()))
            play.triggered.connect(lambda: self.host._play_record(record))
            menu.addAction("展开详情").triggered.connect(lambda: self._set_details_open(True))
            menu.addAction("编辑影片档案…").triggered.connect(self._edit_current_movie)
            self._populate_move_to_folder_menu(menu)
            menu.addSeparator()
            menu.addAction("影片封面工具…").triggered.connect(lambda: self.host._open_cover_tools())
            menu.addAction("打开所在文件夹").triggered.connect(lambda: self.host._open_folder(record))
        menu.exec(global_pos)
        self.refresh_records()

    def _edit_current_game(self) -> None:
        record = self.current_record()
        if self.domain != "games" or record is None or self.host.game_catalog is None:
            return
        dialog = RetroGameArchiveEditDialog(record.metadata, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.host.game_catalog.update_game(record.metadata.uuid, dialog.result_patch)
        except Exception as exc:
            QMessageBox.warning(self, "保存游戏失败", str(exc))
            return
        self._pixmap_cache.clear()
        self.refresh_records()

    def _edit_current_movie(self) -> None:
        record = self.current_record()
        if self.domain != "movies" or record is None:
            return
        dialog = RetroMovieArchiveEditDialog(record.metadata, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.host.catalog.update_metadata(record.metadata.uuid, dialog.result_patch)
        except Exception as exc:
            QMessageBox.warning(self, "保存影片失败", str(exc))
            return
        self._pixmap_cache.clear()
        self.refresh_records()

    def _set_box_style(self, style: str) -> None:
        self.box_style = "classic" if style == "classic" else "neo"
        self.update()

    def _set_menu_corner(self, corner: str) -> None:
        self.menu_corner = "bottom_left" if corner == "bottom_left" else "bottom_right"
        self.update()

    # ----- helpers -------------------------------------------------------------
    def current_record(self):
        if not self.records:
            return None
        return self.records[self.current_index % len(self.records)]

    @staticmethod
    def _lerp_rect(a: QRectF, b: QRectF, t: float) -> QRectF:
        return QRectF(
            a.x() + (b.x() - a.x()) * t,
            a.y() + (b.y() - a.y()) * t,
            a.width() + (b.width() - a.width()) * t,
            a.height() + (b.height() - a.height()) * t,
        )

    @staticmethod
    def _format_date(value: datetime | None, fallback: str) -> str:
        if value is None:
            return fallback
        try:
            return value.astimezone().strftime("%Y.%m.%d")
        except Exception:
            return value.strftime("%Y.%m.%d")


def install_retro_showcase(host_window) -> RetroShowcaseOverlay:
    """Install and reveal the Retro primary presentation."""
    host_window.setMinimumSize(RETRO_MIN_WINDOW_WIDTH, RETRO_MIN_WINDOW_HEIGHT)
    host_window.root_stack.setCurrentWidget(host_window.main_shell)
    overlay = RetroShowcaseOverlay(host_window, host_window.centralWidget())
    overlay.show()
    overlay.raise_()
    overlay.setFocus(Qt.FocusReason.OtherFocusReason)
    host_window._retro_showcase_overlay = overlay
    return overlay
