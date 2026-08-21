from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen
from PySide6.QtWidgets import QPushButton, QStyle, QStyleOptionButton, QStylePainter

from app.ui.flat_icons import flat_icon
from app.ui.flat_theme import FlatTokens
from app.ui.sidebar_motion import sidebar_text_progress


class NavigationButton(QPushButton):
    """Sidebar navigation button with skin-controlled selection treatments."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self._nav_icon_kind: str | None = None
        self._sidebar_motion_progress: float | None = None
        self.toggled.connect(self._refresh_nav_icon)


    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt override
        hint = super().minimumSizeHint()
        if self._sidebar_motion_progress is not None:
            hint.setWidth(0)
        return hint

    def set_sidebar_motion_progress(self, progress: float | None) -> None:
        """Blend Flat Pro rail contents directly with the splitter drag position."""
        if progress is None:
            self._sidebar_motion_progress = None
        else:
            self._sidebar_motion_progress = max(0.0, min(1.0, float(progress)))
        self.update()

    def _paint_motion_content(self) -> None:
        progress = self._sidebar_motion_progress
        if progress is None:
            return

        option = QStyleOptionButton()
        self.initStyleOption(option)
        full_text = option.text
        option.text = ""
        option.icon = QIcon()

        painter = QStylePainter(self)
        painter.drawControl(QStyle.ControlElement.CE_PushButton, option)

        icon = self.icon()
        icon_size = self.iconSize()
        compact_x = max(0.0, (self.width() - icon_size.width()) / 2.0)
        full_x = 14.0
        icon_progress = progress * progress * (3.0 - 2.0 * progress)
        icon_x = compact_x + (full_x - compact_x) * icon_progress
        icon_y = max(0.0, (self.height() - icon_size.height()) / 2.0)
        icon_mode = QIcon.Mode.Disabled if not self.isEnabled() else (QIcon.Mode.Active if self.underMouse() else QIcon.Mode.Normal)
        icon_state = QIcon.State.On if self.isChecked() else QIcon.State.Off
        icon.paint(
            painter,
            QRect(round(icon_x), round(icon_y), icon_size.width(), icon_size.height()),
            Qt.AlignmentFlag.AlignCenter,
            icon_mode,
            icon_state,
        )

        text_progress = sidebar_text_progress(progress)
        if full_text and text_progress > 0.0:
            painter.setOpacity(text_progress)
            if not self.isEnabled():
                text_color = FlatTokens.TEXT_MUTED
            elif self.isChecked():
                text_color = FlatTokens.NAV_SELECTED_TEXT
            elif self.underMouse():
                text_color = FlatTokens.TEXT_PRIMARY
            else:
                text_color = FlatTokens.TEXT_SECONDARY
            painter.setPen(QColor(text_color))
            font = painter.font()
            if self.isChecked():
                font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)
            text_left = round(icon_x + icon_size.width() + 10.0)
            text_rect = self.rect().adjusted(text_left, 0, -8, 0)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, full_text)
        painter.end()

    def set_nav_icon(self, kind: str) -> None:
        """Remember the icon kind so skins can recolor it for checked state."""
        self._nav_icon_kind = kind
        self._refresh_nav_icon()

    def _refresh_nav_icon(self, _checked: bool | None = None) -> None:
        if not self._nav_icon_kind:
            return
        if FlatTokens.NAV_STYLE == "sunken_card" and self.isChecked():
            self.setIcon(flat_icon(self._nav_icon_kind, color=FlatTokens.ACCENT))
        else:
            self.setIcon(flat_icon(self._nav_icon_kind, color=FlatTokens.TEXT_SECONDARY))

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self.isChecked() and FlatTokens.NAV_STYLE == "sunken_card":
            self._paint_sunken_card()
        elif self.isChecked() and FlatTokens.NAV_STYLE == "pressed_card":
            self._paint_pressed_card()
        if self._sidebar_motion_progress is None:
            super().paintEvent(event)
        else:
            self._paint_motion_content()
        if self.isChecked() and FlatTokens.NAV_STYLE == "inset":
            self._paint_inset_slot()

    def _paint_sunken_card(self) -> None:
        """Paint a subtle depressed card with slightly clearer separation from the rail."""
        rect = self.rect()
        if rect.width() <= 12 or rect.height() <= 12:
            return

        radius = max(2.0, float(FlatTokens.RADIUS_SMALL))
        card_rect = QRectF(rect.adjusted(2, 2, -2, -2))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.setBrush(QColor(FlatTokens.NAV_SELECTED_BG))
        border = QColor(FlatTokens.BORDER_STRONG)
        border.setAlpha(150)
        painter.setPen(QPen(border, 1.0))
        painter.drawRoundedRect(card_rect, radius, radius)

        left = card_rect.left()
        top = card_rect.top()
        right = card_rect.right()
        bottom = card_rect.bottom()

        # Delicate top/left pressure line so the card reads as pressed into the rail.
        dark = QColor(FlatTokens.NAV_INSET_DARK)
        dark.setAlpha(165)
        dark_pen = QPen(dark, 1.0)
        dark_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(dark_pen)
        painter.drawLine(QPointF(left + radius, top + 1.0), QPointF(right - radius, top + 1.0))
        painter.drawLine(QPointF(left + 1.0, top + radius), QPointF(left + 1.0, bottom - radius))

        # Extremely soft reflected edge, weaker than before to avoid reading as a raised card.
        light = QColor(FlatTokens.NAV_INSET_LIGHT)
        light.setAlpha(58)
        light_pen = QPen(light, 1.0)
        light_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(light_pen)
        painter.drawLine(QPointF(left + radius, bottom - 1.0), QPointF(right - radius, bottom - 1.0))
        painter.drawLine(QPointF(right - 1.0, top + radius), QPointF(right - 1.0, bottom - radius))

        # A nearly invisible center glaze keeps the face readable against the rail.
        glaze = QColor(FlatTokens.BORDER_STRONG)
        glaze.setAlpha(16)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glaze)
        inner = card_rect.adjusted(1.0, 1.0, -1.0, -1.0)
        painter.drawRoundedRect(inner, max(1.0, radius - 1.0), max(1.0, radius - 1.0))
        painter.end()

    def _paint_pressed_card(self) -> None:
        """Legacy thin raised-card treatment retained for skins that explicitly request it."""
        rect = self.rect()
        if rect.width() <= 12 or rect.height() <= 12:
            return

        radius = max(2.0, float(FlatTokens.RADIUS_SMALL))
        card_rect = QRectF(rect.adjusted(2, 1, -2, -3))
        shadow_rect = card_rect.translated(0.0, 2.0)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        shadow = QColor(FlatTokens.NAV_INSET_DARK)
        shadow.setAlpha(210)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shadow)
        painter.drawRoundedRect(shadow_rect, radius, radius)

        painter.setBrush(QColor(FlatTokens.NAV_SELECTED_BG))
        painter.setPen(QPen(QColor(FlatTokens.BORDER_STRONG), 1.0))
        painter.drawRoundedRect(card_rect, radius, radius)

        left = card_rect.left()
        top = card_rect.top()
        right = card_rect.right()
        bottom = card_rect.bottom()

        highlight = QColor(FlatTokens.NAV_INSET_LIGHT)
        highlight.setAlpha(190)
        high_pen = QPen(highlight, 1.0)
        high_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(high_pen)
        painter.drawLine(QPointF(left + radius, top + 1.0), QPointF(right - radius, top + 1.0))

        low_pen = QPen(QColor(FlatTokens.NAV_INSET_DARK), 1.0)
        low_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(low_pen)
        painter.drawLine(QPointF(left + radius, bottom), QPointF(right - radius, bottom))
        painter.end()

    def _paint_inset_slot(self) -> None:
        """Legacy inset treatment retained for skins that explicitly request it."""
        rect = self.rect().adjusted(2, 2, -2, -2)
        if rect.width() <= 8 or rect.height() <= 8:
            return

        radius = max(2, FlatTokens.RADIUS_SMALL)
        left = float(rect.left())
        top = float(rect.top())
        right = float(rect.right())
        bottom = float(rect.bottom())

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        dark_pen = QPen(QColor(FlatTokens.NAV_INSET_DARK), 2.0)
        dark_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(dark_pen)
        painter.drawLine(QPointF(left + radius, top), QPointF(right - radius, top))
        painter.drawLine(QPointF(left, top + radius), QPointF(left, bottom - radius))

        light_pen = QPen(QColor(FlatTokens.NAV_INSET_LIGHT), 1.0)
        light_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(light_pen)
        painter.drawLine(QPointF(left + radius, bottom), QPointF(right - radius, bottom))
        painter.drawLine(QPointF(right, top + radius), QPointF(right, bottom - radius))
        painter.end()
