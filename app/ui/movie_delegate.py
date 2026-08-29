from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFontMetrics,
    QImage,
    QImageReader,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from app.ui.flat_theme import FlatTokens
from app.ui.movie_models import MovieListModel
from app.ui.poster_layout import poster_height_for_width


class MovieCardDelegate(QStyledItemDelegate):
    """Archive-wall movie poster with restrained focus and status cues."""

    CARD_WIDTH = 190
    POSTER_WIDTH = 180
    FALLBACK_HEIGHT = 260
    MARGIN = 5
    HOVER_SCALE = 1.035
    HOVER_LIFT = 4.0

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cover_size_cache: dict[str, tuple[int, int]] = {}
        self._scaled_pixmap_cache: dict[tuple[str, int, int], QPixmap] = {}
        self._grayscale_pixmap_cache: dict[int, QPixmap] = {}
        self._cell_width = self.CARD_WIDTH

    def set_cell_width(self, width: int) -> bool:
        width = max(self.CARD_WIDTH, int(width))
        if width == self._cell_width:
            return False
        self._cell_width = width
        return True

    def clear_cache(self) -> None:
        self._cover_size_cache.clear()
        self._scaled_pixmap_cache.clear()
        self._grayscale_pixmap_cache.clear()

    def _cover_dimensions(self, index) -> tuple[int, int]:
        cover_path = index.data(MovieListModel.CoverPathRole)
        if not cover_path:
            return 0, 0
        cache_key = str(cover_path)
        cached = self._cover_size_cache.get(cache_key)
        if cached is not None:
            return cached
        path = Path(cache_key)
        if not path.is_file():
            dimensions = (0, 0)
        else:
            size = QImageReader(cache_key).size()
            dimensions = (size.width(), size.height())
        self._cover_size_cache[cache_key] = dimensions
        return dimensions

    def _scaled_cover_pixmap(self, cover_path: str, target_size: QSize) -> QPixmap:
        cache_key = (cover_path, target_size.width(), target_size.height())
        cached = self._scaled_pixmap_cache.get(cache_key)
        if cached is not None:
            return cached
        path = Path(cover_path)
        pixmap = QPixmap(cover_path) if path.is_file() else QPixmap()
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self._scaled_pixmap_cache[cache_key] = pixmap
        return pixmap

    def _grayscale_pixmap(self, pixmap: QPixmap) -> QPixmap:
        if pixmap.isNull():
            return pixmap
        key = int(pixmap.cacheKey())
        cached = self._grayscale_pixmap_cache.get(key)
        if cached is not None:
            return cached
        image = pixmap.toImage().convertToFormat(QImage.Format.Format_Grayscale8)
        gray = QPixmap.fromImage(image)
        self._grayscale_pixmap_cache[key] = gray
        return gray

    def sizeHint(self, option, index) -> QSize:
        width, height = self._cover_dimensions(index)
        poster_height = poster_height_for_width(
            width,
            height,
            self.POSTER_WIDTH,
            fallback_height=self.FALLBACK_HEIGHT,
        )
        return QSize(self._cell_width, poster_height + self.MARGIN * 2)

    @staticmethod
    def _pill_rect(anchor: QRect, text: str, painter: QPainter, *, right: bool) -> QRect:
        metrics = QFontMetrics(painter.font())
        width = metrics.horizontalAdvance(text) + 14
        height = max(22, metrics.height() + 6)
        x = anchor.right() - width - 8 if right else anchor.left() + 8
        return QRect(x, anchor.top() + 8, width, height)

    def _draw_pill(self, painter: QPainter, anchor: QRect, text: str, *, right: bool) -> None:
        rect = self._pill_rect(anchor, text, painter, right=right)
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(12, 15, 19, 218))
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        painter.setPen(QColor(FlatTokens.TEXT_PRIMARY))
        font = painter.font()
        font.setPointSize(max(8, font.pointSize() - 1))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()

    def _draw_hover_caption(self, painter: QPainter, poster_rect: QRect, title: str, progress: float) -> None:
        if progress <= 0.0 or not title:
            return
        height = min(72, max(48, poster_rect.height() // 4))
        overlay = QRect(poster_rect.left(), poster_rect.bottom() - height + 1, poster_rect.width(), height)
        gradient = QLinearGradient(overlay.left(), overlay.top(), overlay.left(), overlay.bottom())
        gradient.setColorAt(0.0, QColor(8, 10, 13, 0))
        gradient.setColorAt(0.35, QColor(8, 10, 13, round(95 * progress)))
        gradient.setColorAt(1.0, QColor(8, 10, 13, round(225 * progress)))
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillRect(overlay, QBrush(gradient))
        painter.setOpacity(progress)
        painter.setPen(QColor(FlatTokens.TEXT_PRIMARY))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(max(9, font.pointSize()))
        painter.setFont(font)
        text_rect = overlay.adjusted(10, 16, -10, -8)
        metrics = QFontMetrics(font)
        elided = metrics.elidedText(title, Qt.TextElideMode.ElideRight, text_rect.width())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, elided)
        painter.restore()

    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        view = option.widget or self.parent()
        hover_progress = getattr(view, "hover_progress", lambda _row: 0.0)(index.row())
        motion_offset = getattr(view, "motion_offset", lambda _row: QPointF())(index.row())
        outer = option.rect.translated(round(motion_offset.x()), round(motion_offset.y()))
        poster_left = outer.left() + max(self.MARGIN, (outer.width() - self.POSTER_WIDTH) // 2)
        poster_rect = QRect(
            poster_left,
            outer.top() + self.MARGIN,
            self.POSTER_WIDTH,
            max(1, outer.height() - self.MARGIN * 2),
        )
        eased_hover = 0.0
        if hover_progress > 0.0:
            eased_hover = 1.0 - (1.0 - min(1.0, float(hover_progress))) ** 3
            scale = 1.0 + (self.HOVER_SCALE - 1.0) * eased_hover
            grow_x = round(poster_rect.width() * (scale - 1.0) / 2.0)
            grow_y = round(poster_rect.height() * (scale - 1.0) / 2.0)
            lift = round(self.HOVER_LIFT * eased_hover)
            poster_rect = poster_rect.adjusted(-grow_x, -grow_y - lift, grow_x, grow_y - lift)

        if eased_hover > 0.0:
            shadow = poster_rect.adjusted(-5, -3, 5, 8)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, round(80 * eased_hover)))
            painter.drawRoundedRect(QRectF(shadow), FlatTokens.RADIUS_MEDIUM + 4, FlatTokens.RADIUS_MEDIUM + 4)

        rounded = QPainterPath()
        rounded.addRoundedRect(
            QRectF(poster_rect),
            FlatTokens.RADIUS_MEDIUM,
            FlatTokens.RADIUS_MEDIUM,
        )
        cover_path = index.data(MovieListModel.CoverPathRole)
        pixmap = self._scaled_cover_pixmap(str(cover_path), poster_rect.size()) if cover_path else QPixmap()
        availability = str(index.data(MovieListModel.AvailabilityRole) or "")
        if not pixmap.isNull() and availability != "available":
            pixmap = self._grayscale_pixmap(pixmap)
        painter.save()
        painter.setClipPath(rounded)
        if pixmap.isNull():
            painter.fillPath(rounded, QColor(FlatTokens.SURFACE_RAISED))
        else:
            painter.drawPixmap(poster_rect.topLeft(), pixmap)
        title = str(index.data(MovieListModel.TitleRole) or index.data(Qt.ItemDataRole.DisplayRole) or "")
        self._draw_hover_caption(painter, poster_rect, title, eased_hover)
        painter.restore()

        episode_count = int(index.data(MovieListModel.EpisodeCountRole) or 0)
        if episode_count > 1:
            self._draw_pill(painter, poster_rect, f"{episode_count} 集", right=True)
        if bool(index.data(MovieListModel.FavoriteRole)):
            self._draw_pill(painter, poster_rect, "★", right=False)

        if pixmap.isNull():
            painter.setPen(QPen(QColor(FlatTokens.BORDER_STRONG), 1, Qt.PenStyle.DashLine))
            painter.drawPath(rounded)
        elif option.state & QStyle.StateFlag.State_Selected:
            selected_color = (
                FlatTokens.ACCENT_SOFT_TEXT
                if FlatTokens.NAV_STYLE == "sunken_card"
                else FlatTokens.ACCENT
            )
            selected_width = 1 if FlatTokens.NAV_STYLE == "sunken_card" else 2
            painter.setPen(QPen(QColor(selected_color), selected_width))
            painter.drawPath(rounded)
        elif option.state & QStyle.StateFlag.State_MouseOver:
            hover_color = QColor(FlatTokens.BORDER_STRONG)
            if eased_hover > 0.85:
                hover_color = QColor(FlatTokens.ACCENT_SOFT_TEXT)
            painter.setPen(QPen(hover_color, 1))
            painter.drawPath(rounded)
        painter.restore()
