from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QWidget


_ZONE_EDGES = {
    "left": Qt.Edge.LeftEdge,
    "right": Qt.Edge.RightEdge,
    "top": Qt.Edge.TopEdge,
    "bottom": Qt.Edge.BottomEdge,
    "top_left": Qt.Edge.TopEdge | Qt.Edge.LeftEdge,
    "top_right": Qt.Edge.TopEdge | Qt.Edge.RightEdge,
    "bottom_left": Qt.Edge.BottomEdge | Qt.Edge.LeftEdge,
    "bottom_right": Qt.Edge.BottomEdge | Qt.Edge.RightEdge,
}

_ZONE_CURSORS = {
    "left": Qt.CursorShape.SizeHorCursor,
    "right": Qt.CursorShape.SizeHorCursor,
    "top": Qt.CursorShape.SizeVerCursor,
    "bottom": Qt.CursorShape.SizeVerCursor,
    "top_left": Qt.CursorShape.SizeFDiagCursor,
    "bottom_right": Qt.CursorShape.SizeFDiagCursor,
    "top_right": Qt.CursorShape.SizeBDiagCursor,
    "bottom_left": Qt.CursorShape.SizeBDiagCursor,
}


class _ResizeHandle(QWidget):
    def __init__(self, host_window, zone: str) -> None:
        super().__init__(host_window)
        self.host_window = host_window
        self.zone = zone
        self.setObjectName(f"windowResizeHandle_{zone}")
        self.setCursor(QCursor(_ZONE_CURSORS[zone]))
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton and not self.host_window.isMaximized():
            handle = self.host_window.windowHandle()
            if handle is not None and handle.startSystemResize(_ZONE_EDGES[self.zone]):
                event.accept()
                return
        super().mousePressEvent(event)


class WindowResizeFrame(QObject):
    """Invisible edge/corner hit targets for a frameless top-level window.

    QStatusBar used to provide the only reliable visible size grip. Flat Pro hides that
    status bar, so these thin transparent targets restore native system resizing without
    bringing the old status bar or a permanent resize glyph back.
    """

    def __init__(self, host_window, *, border: int = 7, corner: int = 16) -> None:
        super().__init__(host_window)
        self.host_window = host_window
        self.border = max(4, int(border))
        self.corner = max(self.border * 2, int(corner))
        self.handles = {zone: _ResizeHandle(host_window, zone) for zone in _ZONE_EDGES}
        host_window.installEventFilter(self)
        self.update_geometry()

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        if watched is self.host_window and event.type() in {
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.WindowStateChange,
        }:
            self.update_geometry()
        return super().eventFilter(watched, event)

    def update_geometry(self) -> None:
        width = max(0, self.host_window.width())
        height = max(0, self.host_window.height())
        maximized = self.host_window.isMaximized()
        for handle in self.handles.values():
            handle.setVisible(not maximized)
        if maximized or width <= 0 or height <= 0:
            return

        b = self.border
        c = min(self.corner, max(b, width // 2), max(b, height // 2))
        mid_w = max(0, width - 2 * c)
        mid_h = max(0, height - 2 * c)
        geometries = {
            "top_left": (0, 0, c, c),
            "top": (c, 0, mid_w, b),
            "top_right": (max(0, width - c), 0, c, c),
            "left": (0, c, b, mid_h),
            "right": (max(0, width - b), c, b, mid_h),
            "bottom_left": (0, max(0, height - c), c, c),
            "bottom": (c, max(0, height - b), mid_w, b),
            "bottom_right": (max(0, width - c), max(0, height - c), c, c),
        }
        for zone, geometry in geometries.items():
            handle = self.handles[zone]
            handle.setGeometry(*geometry)
            handle.raise_()
