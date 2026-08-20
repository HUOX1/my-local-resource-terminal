from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from app.ui.flat_theme import FlatTokens


def flat_icon(kind: str, size: int = 22, color: str | None = None) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color or FlatTokens.TEXT_SECONDARY), max(1.5, size / 13.0))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if kind == "movie":
        painter.drawRoundedRect(QRectF(3.5, 4.5, size - 7, size - 9), 2.0, 2.0)
        painter.drawLine(QPointF(8, 4.5), QPointF(8, size - 4.5))
        painter.drawLine(QPointF(size - 8, 4.5), QPointF(size - 8, size - 4.5))
        for y in (7.5, size - 7.5):
            painter.drawPoint(QPointF(5.7, y))
            painter.drawPoint(QPointF(size - 5.7, y))
    elif kind == "game":
        path = QPainterPath()
        path.moveTo(6, 9)
        path.cubicTo(7, 5.5, 9, 5, 11, 6.5)
        path.cubicTo(13, 5, 15, 5.5, 16, 9)
        path.lineTo(18.5, 15)
        path.cubicTo(19.2, 17, 17.5, 18.5, 16, 17)
        path.lineTo(13.5, 14.2)
        path.lineTo(8.5, 14.2)
        path.lineTo(6, 17)
        path.cubicTo(4.5, 18.5, 2.8, 17, 3.5, 15)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(7.3, 9.3), QPointF(7.3, 12.5))
        painter.drawLine(QPointF(5.7, 10.9), QPointF(8.9, 10.9))
        painter.drawPoint(QPointF(14.3, 10.2))
        painter.drawPoint(QPointF(16, 12))
    elif kind == "settings":
        painter.drawEllipse(QRectF(7.1, 7.1, size - 14.2, size - 14.2))
        painter.drawEllipse(QRectF(3.7, 3.7, size - 7.4, size - 7.4))
        for angle in range(0, 360, 45):
            import math
            radians = math.radians(angle)
            inner = size * 0.34
            outer = size * 0.45
            center = size / 2
            painter.drawLine(
                QPointF(center + math.cos(radians) * inner, center + math.sin(radians) * inner),
                QPointF(center + math.cos(radians) * outer, center + math.sin(radians) * outer),
            )
    elif kind == "grid":
        for row in range(2):
            for col in range(2):
                painter.drawRoundedRect(QRectF(3.5 + col * 9, 3.5 + row * 9, 6.5, 6.5), 1.2, 1.2)
    elif kind == "list":
        for y in (6, 11, 16):
            painter.drawLine(QPointF(5, y), QPointF(size - 4, y))
    elif kind == "scan":
        painter.drawArc(QRectF(4, 4, size - 8, size - 8), 35 * 16, 250 * 16)
        painter.drawLine(QPointF(size - 5, 7), QPointF(size - 5, 12))
        painter.drawLine(QPointF(size - 5, 7), QPointF(size - 10, 7))
    elif kind == "cover":
        painter.drawRoundedRect(QRectF(4, 3.5, size - 8, size - 7), 2, 2)
        painter.drawEllipse(QRectF(7, 6.5, 3, 3))
        path = QPainterPath()
        path.moveTo(5.5, size - 6)
        path.lineTo(10.5, 11)
        path.lineTo(13, 13.5)
        path.lineTo(16, 10.5)
        path.lineTo(size - 5.5, size - 6)
        painter.drawPath(path)
    elif kind == "search":
        lens = QRectF(4.2, 4.2, size - 10.2, size - 10.2)
        painter.drawEllipse(lens)
        painter.drawLine(QPointF(size - 7.2, size - 7.2), QPointF(size - 3.8, size - 3.8))
    elif kind == "search_add":
        lens = QRectF(4.2, 4.2, size - 10.2, size - 10.2)
        painter.drawEllipse(lens)
        painter.drawLine(QPointF(size - 7.2, size - 7.2), QPointF(size - 3.8, size - 3.8))
        center = size / 2 - 1.0
        arm = max(2.4, size * 0.14)
        painter.drawLine(QPointF(center - arm, center), QPointF(center + arm, center))
        painter.drawLine(QPointF(center, center - arm), QPointF(center, center + arm))
    elif kind == "cartridge":
        body = QPainterPath()
        body.moveTo(5.0, 4.0)
        body.lineTo(size - 5.0, 4.0)
        body.lineTo(size - 3.5, 6.0)
        body.lineTo(size - 3.5, size - 4.0)
        body.lineTo(3.5, size - 4.0)
        body.lineTo(3.5, 6.0)
        body.closeSubpath()
        painter.drawPath(body)
        painter.drawRoundedRect(QRectF(6.0, 7.0, size - 12.0, size - 13.0), 1.2, 1.2)
        painter.drawLine(QPointF(6.0, size - 6.5), QPointF(size - 6.0, size - 6.5))
        for x in (7.5, size / 2, size - 7.5):
            painter.drawLine(QPointF(x, size - 6.5), QPointF(x, size - 4.5))
    elif kind == "add":
        painter.drawEllipse(QRectF(4, 4, size - 8, size - 8))
        painter.drawLine(QPointF(size / 2, 7), QPointF(size / 2, size - 7))
        painter.drawLine(QPointF(7, size / 2), QPointF(size - 7, size / 2))
    else:
        painter.drawRoundedRect(QRectF(4, 4, size - 8, size - 8), 3, 3)

    painter.end()
    return QIcon(pixmap)
