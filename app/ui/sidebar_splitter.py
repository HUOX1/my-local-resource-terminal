from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPointF, QVariantAnimation, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSplitter, QSplitterHandle

from app.ui.flat_theme import FlatTokens


class SidebarToggleHandle(QSplitterHandle):
    """Transparent seam with a compact directional arrow painted into one side."""

    SHAPE_WIDTH = 18
    SHAPE_HEIGHT = 44

    def __init__(self, orientation: Qt.Orientation, parent: QSplitter) -> None:
        super().__init__(orientation, parent)
        self._expanded = True
        self._hovered = False
        self._pressed = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("收起主轴")

    def _toggle(self) -> None:
        splitter = self.splitter()
        if hasattr(splitter, "toggle_sidebar"):
            splitter.toggle_sidebar()

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = bool(expanded)
        self.setToolTip("收起主轴" if self._expanded else "展开主轴")
        self.update()

    def _control_rect(self):
        """Return a compact flat arrow button area."""
        width = max(1, self.width())
        height = max(1, self.height())
        button_w = 18
        button_h = 42
        x = 1 if self._expanded else max(1, width - button_w - 1)
        y = (height - button_h) / 2
        return x, y, button_w, button_h

    def _hit_rect(self):
        # Keep the full handle area clickable. The arrow is only a visual cue;
        # the splitter handle remains the interaction target.
        return self.rect()


    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Paint the invisible seam as two continuations of its neighboring
        # surfaces. The arrow moves between the rail and content side without
        # introducing a permanent divider line.
        mid = self.width() // 2
        painter.fillRect(0, 0, mid, self.height(), QColor(FlatTokens.SURFACE))
        painter.fillRect(mid, 0, self.width() - mid, self.height(), QColor(FlatTokens.BACKGROUND))

        fill = FlatTokens.SURFACE
        border = FlatTokens.CHROME_BORDER
        text = FlatTokens.TEXT_MUTED
        if self._hovered:
            fill = FlatTokens.SURFACE_HOVER
            border = FlatTokens.BORDER_STRONG
            text = FlatTokens.TEXT_PRIMARY
        if self._pressed:
            fill = FlatTokens.SURFACE_RAISED
            text = FlatTokens.ACCENT_SOFT_TEXT

        x, y, w, h = self._control_rect()
        # Flat style: only a subtle rounded hover target, no physical handle shape.
        if self._hovered or self._pressed:
            painter.setPen(QPen(QColor(border), 1.0))
            painter.setBrush(QColor(fill))
            painter.drawRoundedRect(int(x), int(y), int(w), int(h), 5, 5)

        arrow = "‹" if self._expanded else "›"
        painter.setPen(QColor(text))
        font = painter.font()
        font.setPointSize(16)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(int(x), int(y), int(w), int(h), Qt.AlignmentFlag.AlignCenter, arrow)
        painter.end()

    def enterEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._hovered = False
        self._pressed = False
        self.update()
        super().leaveEvent(event)

    # The seam itself is not draggable. The whole arrow area is a two-state
    # control, so the rail can never be left at an intermediate width.
    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._hit_rect().contains(event.position().toPoint())
        ):
            self._pressed = True
            self.update()
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        should_toggle = (
            self._pressed
            and event.button() == Qt.MouseButton.LeftButton
            and self._hit_rect().contains(event.position().toPoint())
        )
        self._pressed = False
        self.update()
        if should_toggle:
            self._toggle()
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt override
        event.accept()


class TwoStateSidebarSplitter(QSplitter):
    COMPACT_WIDTH = 72
    HANDLE_WIDTH = 36
    ANIMATION_MS = 210

    sidebar_width_changed = Signal(int)
    sidebar_state_changed = Signal(bool)

    def __init__(self, orientation: Qt.Orientation, parent=None) -> None:
        super().__init__(orientation, parent)
        # Keep the toggle handle as a real visual area instead of a thin splitter seam.
        # The arrow can move inside the active side without being clipped.
        self.setHandleWidth(self.HANDLE_WIDTH)
        self._expanded_width = 196
        self._expanded = True
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(self.ANIMATION_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(self._apply_animated_width)
        self._animation.finished.connect(self._animation_finished)

    def createHandle(self) -> QSplitterHandle:  # noqa: N802 - Qt override
        handle = SidebarToggleHandle(self.orientation(), self)
        handle.set_expanded(self._expanded)
        return handle

    def configure_widths(self, *, expanded: int) -> None:
        self._expanded_width = max(self.COMPACT_WIDTH, int(expanded))

    @property
    def sidebar_expanded(self) -> bool:
        return self._expanded

    def toggle_sidebar(self) -> None:
        self.set_sidebar_expanded(not self._expanded, animated=True)

    def set_sidebar_expanded(self, expanded: bool, *, animated: bool = True) -> None:
        expanded = bool(expanded)
        target = self._expanded_width if expanded else self.COMPACT_WIDTH
        self._expanded = expanded
        handle = self.handle(1)
        if isinstance(handle, SidebarToggleHandle):
            handle.set_expanded(expanded)
        self.sidebar_state_changed.emit(expanded)

        current = self.sizes()[0] if self.count() else target
        if not animated or current == target:
            self._animation.stop()
            self._set_sidebar_width(target)
            return

        self._animation.stop()
        self._animation.setStartValue(int(current))
        self._animation.setEndValue(int(target))
        self._animation.start()

    def _apply_animated_width(self, value) -> None:
        self._set_sidebar_width(int(round(float(value))))

    def _set_sidebar_width(self, width: int) -> None:
        if self.count() < 2:
            return
        width = max(self.COMPACT_WIDTH, min(int(width), self._expanded_width))
        available = max(1, self.width() - self.handleWidth() - width)
        self.setSizes([width, available])
        actual = self.sizes()[0]
        self.sidebar_width_changed.emit(actual)

    def _animation_finished(self) -> None:
        target = self._expanded_width if self._expanded else self.COMPACT_WIDTH
        self._set_sidebar_width(target)
