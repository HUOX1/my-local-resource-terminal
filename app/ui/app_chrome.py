from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from app.ui.flat_theme import FlatTokens


class AppTitleBar(QWidget):
    """Theme-owned main-window chrome while Windows still owns move/min/max/close behavior."""

    def __init__(self, host_window, parent=None) -> None:
        super().__init__(parent or host_window)
        self.host_window = host_window
        self.setObjectName("appTitleBar")
        self.setFixedHeight(FlatTokens.TITLEBAR_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(8)
        self.title_label = QLabel("本地资源终端")
        self.title_label.setObjectName("appTitleText")
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.title_label)
        self.version_label = QLabel("v0.5.0.17.1")
        self.version_label.setObjectName("appTitleVersion")
        self.version_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.version_label)
        layout.addStretch(1)
        self.minimize_button = self._make_button("-", "最小化")
        self.maximize_button = self._make_button("□", "最大化 / 恢复")
        self.close_button = self._make_button("×", "关闭", close=True)
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(self.close_button)
        self.minimize_button.clicked.connect(self.host_window.showMinimized)
        self.maximize_button.clicked.connect(self.toggle_maximize)
        self.close_button.clicked.connect(self.host_window.close)
        self.host_window.installEventFilter(self)
        self._sync_maximize_glyph()

    def _make_button(self, text: str, tooltip: str, *, close: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("titleBarCloseButton" if close else "titleBarButton")
        button.setToolTip(tooltip)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def toggle_maximize(self) -> None:
        if self.host_window.isMaximized():
            self.host_window.showNormal()
        else:
            self.host_window.showMaximized()
        self._sync_maximize_glyph()

    def _sync_maximize_glyph(self) -> None:
        self.maximize_button.setText("❐" if self.host_window.isMaximized() else "□")

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        if watched is self.host_window and event.type() == QEvent.Type.WindowStateChange:
            self._sync_maximize_glyph()
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.host_window.windowHandle()
            if handle is not None:
                handle.startSystemMove()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
