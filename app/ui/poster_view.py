from __future__ import annotations

import time

from PySide6.QtCore import QEvent, QPoint, QPointF, QTimer, Qt
from PySide6.QtWidgets import QListView

from app.ui.flat_theme import FlatTokens
from app.ui.poster_layout import poster_wall_targets
from app.ui.poster_scroll import accumulate_scroll_target, smooth_scroll_value


class PosterWallListView(QListView):
    """Poster wall with restrained Flat Pro motion.

    Layout/caching responsibilities stay with the delegates.  The view only
    coordinates poster placement, hover progress, responsive reflow and wheel
    position. Traditional mouse wheels use a target position while precision
    touchpads keep Qt's native pixel scrolling.
    """

    MODEL_LAYOUT_INTERVAL_MS = 16
    MOTION_TICK_MS = 16
    REFLOW_DURATION_MS = 220
    LAYOUT_HYSTERESIS_PX = 24
    LAYOUT_ALIGNMENT = "fixed_left"
    MINIMUM_SPACING = 10
    HOVER_DURATION_MS = 110
    SCROLL_STOP_DISTANCE_PX = 0.45

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._poster_delegate = None
        self._model_layout_timer = QTimer(self)
        self._model_layout_timer.setSingleShot(True)
        self._model_layout_timer.setInterval(self.MODEL_LAYOUT_INTERVAL_MS)
        self._model_layout_timer.timeout.connect(self._apply_poster_layout)
        self._motion_timer = QTimer(self)
        self._motion_timer.setInterval(self.MOTION_TICK_MS)
        self._motion_timer.timeout.connect(self._motion_tick)
        self._last_motion_time = 0.0
        self._scroll_position = 0.0
        self._scroll_target = 0.0
        self._hover_row = -1
        self._hover_values: dict[int, float] = {}
        self._reflow_offsets: dict[int, QPointF] = {}
        self._reflow_progress = 1.0
        self._minimum_spacing = self.MINIMUM_SPACING
        self._layout_columns: int | None = None
        self._item_height_cache: tuple[int, ...] | None = None
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)

    def _motion_enabled(self) -> bool:
        return str(getattr(FlatTokens, "MOTION_LEVEL", "off")) != "off"

    def _ensure_motion_timer(self) -> None:
        if not self._motion_enabled():
            return
        if not self._motion_timer.isActive():
            self._last_motion_time = time.monotonic()
            self._motion_timer.start()

    def set_poster_delegate(self, delegate) -> None:
        self._poster_delegate = delegate
        self._minimum_spacing = self.MINIMUM_SPACING
        self._invalidate_item_height_cache()
        if hasattr(delegate, "set_cell_width"):
            delegate.set_cell_width(delegate.CARD_WIDTH)
        self._apply_poster_layout()

    def _invalidate_item_height_cache(self) -> None:
        self._item_height_cache = None

    def _poster_item_heights(self) -> tuple[int, ...]:
        model = self.model()
        if model is None:
            return ()
        row_count = model.rowCount()
        cached = self._item_height_cache
        if cached is not None and len(cached) == row_count:
            return cached
        heights: list[int] = []
        for row in range(row_count):
            index = model.index(row, 0)
            heights.append(max(1, self.sizeHintForIndex(index).height()))
        self._item_height_cache = tuple(heights)
        return self._item_height_cache

    def _schedule_poster_layout(self, *_args) -> None:
        self._invalidate_item_height_cache()
        if not self._model_layout_timer.isActive():
            self._model_layout_timer.start()

    def setModel(self, model) -> None:  # noqa: N802 - Qt override
        old_model = self.model()
        if old_model is not None:
            for signal_name in ("modelReset", "rowsInserted", "rowsRemoved", "layoutChanged", "dataChanged"):
                signal = getattr(old_model, signal_name, None)
                if signal is not None:
                    try:
                        signal.disconnect(self._schedule_poster_layout)
                    except (RuntimeError, TypeError):
                        pass
        super().setModel(model)
        self._invalidate_item_height_cache()
        if model is not None:
            for signal_name in ("modelReset", "rowsInserted", "rowsRemoved", "layoutChanged", "dataChanged"):
                signal = getattr(model, signal_name, None)
                if signal is not None:
                    signal.connect(self._schedule_poster_layout)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        # Native Windows resizing must never outrun the poster wall. Apply the
        # deterministic target geometry in the same resize event and suppress
        # reflow animation while the user is dragging the window edge.
        self._apply_poster_layout(animate=False)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        if watched is self.viewport():
            if event.type() == QEvent.Type.MouseMove:
                index = self.indexAt(event.position().toPoint())
                row = index.row() if index.isValid() else -1
                if row != self._hover_row:
                    self._hover_row = row
                    self._ensure_motion_timer()
            elif event.type() in (QEvent.Type.Leave, QEvent.Type.Hide):
                if self._hover_row != -1:
                    self._hover_row = -1
                    self._ensure_motion_timer()
        return super().eventFilter(watched, event)

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt override
        if not self._motion_enabled():
            super().wheelEvent(event)
            return

        # Precision touchpads already provide smooth pixel deltas through Qt;
        # do not layer synthetic smoothing on top of the OS gesture.
        if event.pixelDelta().y():
            super().wheelEvent(event)
            bar = self.verticalScrollBar()
            self._scroll_position = float(bar.value())
            self._scroll_target = self._scroll_position
            return

        angle_delta = event.angleDelta().y()
        if not angle_delta:
            super().wheelEvent(event)
            return

        bar = self.verticalScrollBar()
        if abs(self._scroll_target - self._scroll_position) <= self.SCROLL_STOP_DISTANCE_PX:
            self._scroll_position = float(bar.value())
            self._scroll_target = self._scroll_position

        self._scroll_target = accumulate_scroll_target(
            self._scroll_position,
            self._scroll_target,
            angle_delta,
            float(bar.minimum()),
            float(bar.maximum()),
        )
        self._ensure_motion_timer()
        event.accept()

    def hover_progress(self, row: int) -> float:
        if not self._motion_enabled():
            return 1.0 if row == self._hover_row else 0.0
        return float(self._hover_values.get(int(row), 0.0))

    def motion_offset(self, row: int) -> QPointF:
        if not self._motion_enabled():
            return QPointF()
        offset = self._reflow_offsets.get(int(row))
        if offset is None:
            return QPointF()
        remaining = max(0.0, 1.0 - self._ease_out_quint(self._reflow_progress))
        return QPointF(offset.x() * remaining, offset.y() * remaining)

    def _capture_visible_rects(self, *, include_motion: bool = False) -> dict[int, object]:
        model = self.model()
        if model is None:
            return {}
        viewport_rect = self.viewport().rect()
        result: dict[int, object] = {}
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            rect = self.visualRect(index)
            if not rect.isValid():
                continue
            if include_motion:
                offset = self.motion_offset(row)
                rect.translate(round(offset.x()), round(offset.y()))
            if rect.top() > viewport_rect.bottom() and result:
                break
            if rect.intersects(viewport_rect):
                result[row] = rect
        return result

    def _apply_poster_layout(self, *, animate: bool = True) -> None:
        delegate = self._poster_delegate
        model = self.model()
        if delegate is None or model is None or not hasattr(delegate, "set_cell_width"):
            return

        delegate.set_cell_width(delegate.CARD_WIDTH)
        item_heights = self._poster_item_heights()
        if not animate:
            self._reflow_offsets.clear()
            self._reflow_progress = 1.0
        layout = poster_wall_targets(
            self.viewport().width(),
            item_heights,
            card_width=delegate.CARD_WIDTH,
            min_spacing=self._minimum_spacing,
            previous_columns=self._layout_columns,
            hysteresis=self.LAYOUT_HYSTERESIS_PX,
            alignment=self.LAYOUT_ALIGNMENT,
        )
        old_rects = (
            self._capture_visible_rects(include_motion=True)
            if animate and self._motion_enabled()
            else {}
        )
        changed = self._layout_columns != layout.columns
        if not changed and len(layout.targets) == model.rowCount():
            for row, target in enumerate(layout.targets):
                rect = self.rectForIndex(model.index(row, 0))
                if rect.left() != target.x or rect.top() != target.y:
                    changed = True
                    break
        self._layout_columns = layout.columns
        for row, target in enumerate(layout.targets):
            self.setPositionForIndex(QPoint(target.x, target.y), model.index(row, 0))

        content_width = max(self.viewport().width(), delegate.CARD_WIDTH + self._minimum_spacing * 2)
        self.resizeContents(content_width, layout.content_height)

        if changed and old_rects:
            self._start_reflow_motion(old_rects)
        else:
            self.viewport().update()

    def _start_reflow_motion(self, old_rects: dict[int, object]) -> None:
        new_rects = self._capture_visible_rects()
        offsets: dict[int, QPointF] = {}
        for row, old_rect in old_rects.items():
            new_rect = new_rects.get(row)
            if new_rect is None:
                continue
            dx = old_rect.left() - new_rect.left()
            dy = old_rect.top() - new_rect.top()
            if dx or dy:
                offsets[row] = QPointF(float(dx), float(dy))
        self._reflow_offsets = offsets
        self._reflow_progress = 0.0 if offsets else 1.0
        if offsets:
            self._ensure_motion_timer()
            self.viewport().update()

    @staticmethod
    def _ease_out_quint(value: float) -> float:
        value = max(0.0, min(1.0, float(value)))
        return 1.0 - (1.0 - value) ** 5

    def _motion_tick(self) -> None:
        now = time.monotonic()
        dt = now - self._last_motion_time if self._last_motion_time else self.MOTION_TICK_MS / 1000.0
        self._last_motion_time = now
        dt = max(0.001, min(0.050, dt))
        needs_update = False

        # Traditional wheel input extends one shared destination. The timer
        # continuously eases toward it, so rapid wheel notches feel continuous
        # instead of repeatedly starting short velocity tails.
        scroll_animating = abs(self._scroll_target - self._scroll_position) > self.SCROLL_STOP_DISTANCE_PX
        if scroll_animating:
            bar = self.verticalScrollBar()
            minimum = float(bar.minimum())
            maximum = float(bar.maximum())
            self._scroll_target = max(minimum, min(maximum, self._scroll_target))
            self._scroll_position = smooth_scroll_value(self._scroll_position, self._scroll_target, dt)
            if abs(self._scroll_target - self._scroll_position) <= self.SCROLL_STOP_DISTANCE_PX:
                self._scroll_position = self._scroll_target
                scroll_animating = False
            bar.setValue(round(self._scroll_position))
            needs_update = True

        # Hover progress is independent from layout. Both the incoming and the
        # outgoing card ease over the same short duration.
        hover_step = dt / (self.HOVER_DURATION_MS / 1000.0)
        hover_animating = False
        rows = set(self._hover_values)
        if self._hover_row >= 0:
            rows.add(self._hover_row)
        for row in rows:
            current = self._hover_values.get(row, 0.0)
            before = current
            target = 1.0 if row == self._hover_row else 0.0
            if target > current:
                current = min(1.0, current + hover_step)
            elif target < current:
                current = max(0.0, current - hover_step)
            if current <= 0.0 and target == 0.0:
                self._hover_values.pop(row, None)
            else:
                self._hover_values[row] = current
            if current != before:
                hover_animating = True
                needs_update = True

        if self._reflow_progress < 1.0:
            self._reflow_progress = min(
                1.0,
                self._reflow_progress + dt / (self.REFLOW_DURATION_MS / 1000.0),
            )
            if self._reflow_progress >= 1.0:
                self._reflow_offsets.clear()
            needs_update = True

        if needs_update:
            self.viewport().update()
        if not scroll_animating and not hover_animating and self._reflow_progress >= 1.0:
            self._motion_timer.stop()
