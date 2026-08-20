from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, QSize, QTimer, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QMovie, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QListView, QStyle, QStyledItemDelegate

from app.ui.flat_theme import FlatTokens
from app.ui.game_models import GameListModel
from app.ui.poster_layout import poster_height_for_width


class GameCardDelegate(QStyledItemDelegate):
    """Poster-only game card with one delayed GIF preview at a time."""

    CARD_WIDTH = 190
    POSTER_WIDTH = 180
    FALLBACK_HEIGHT = 260
    MARGIN = 5
    HOVER_SCALE = 1.018
    HOVER_LIFT = 2.0

    def __init__(self, view: QListView) -> None:
        super().__init__(view)
        self.view = view
        self._hover_row = -1
        self._preview_row = -1
        self._movie: QMovie | None = None
        self._cover_size_cache: dict[str, tuple[int, int]] = {}
        self._scaled_pixmap_cache: dict[tuple[str, int, int], QPixmap] = {}
        self._grayscale_pixmap_cache: dict[int, QPixmap] = {}
        self._cell_width = self.CARD_WIDTH
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(250)
        self._hover_timer.timeout.connect(self._start_hover_preview)
        self.view.setMouseTracking(True)
        self.view.viewport().setMouseTracking(True)
        self.view.viewport().installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self.view.viewport():
            if event.type() == QEvent.Type.MouseMove:
                index = self.view.indexAt(event.position().toPoint())
                row = index.row() if index.isValid() else -1
                if row != self._hover_row:
                    self._hover_row = row
                    self._hover_timer.stop()
                    self._stop_movie()
                    if row >= 0:
                        self._hover_timer.start()
            elif event.type() in (QEvent.Type.Leave, QEvent.Type.Hide):
                self._hover_row = -1
                self._hover_timer.stop()
                self._stop_movie()
        return super().eventFilter(watched, event)

    def _start_hover_preview(self) -> None:
        if self._hover_row < 0:
            return
        index = self.view.model().index(self._hover_row, 0)
        if not bool(index.data(GameListModel.InstalledRole)):
            return
        preview = index.data(GameListModel.PreviewGifRole)
        if not preview or not Path(str(preview)).is_file():
            return
        self._stop_movie()
        movie = QMovie(str(preview), parent=self)
        if not movie.isValid():
            movie.deleteLater()
            return
        movie.setCacheMode(QMovie.CacheMode.CacheAll)
        movie.frameChanged.connect(lambda _frame: self.view.viewport().update())
        self._movie = movie
        self._preview_row = self._hover_row
        movie.start()

    def _stop_movie(self) -> None:
        if self._movie is not None:
            self._movie.stop()
            self._movie.deleteLater()
        self._movie = None
        self._preview_row = -1
        self.view.viewport().update()

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
        cover_path = index.data(GameListModel.CoverPathRole)
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
        if hover_progress > 0.0:
            eased_hover = 1.0 - (1.0 - min(1.0, float(hover_progress))) ** 3
            scale = 1.0 + (self.HOVER_SCALE - 1.0) * eased_hover
            grow_x = round(poster_rect.width() * (scale - 1.0) / 2.0)
            grow_y = round(poster_rect.height() * (scale - 1.0) / 2.0)
            lift = round(self.HOVER_LIFT * eased_hover)
            poster_rect = poster_rect.adjusted(-grow_x, -grow_y - lift, grow_x, grow_y - lift)
        rounded = QPainterPath()
        rounded.addRoundedRect(
            QRectF(poster_rect),
            FlatTokens.RADIUS_MEDIUM,
            FlatTokens.RADIUS_MEDIUM,
        )
        pixmap = QPixmap()
        is_preview_frame = False
        if self._movie is not None and index.row() == self._preview_row:
            pixmap = self._movie.currentPixmap()
            is_preview_frame = not pixmap.isNull()
        if pixmap.isNull():
            cover_path = index.data(GameListModel.CoverPathRole)
            pixmap = self._scaled_cover_pixmap(str(cover_path), poster_rect.size()) if cover_path else QPixmap()
        if not pixmap.isNull() and not bool(index.data(GameListModel.InstalledRole)):
            pixmap = self._grayscale_pixmap(pixmap)

        painter.save()
        painter.setClipPath(rounded)
        if pixmap.isNull():
            painter.fillPath(rounded, QColor(FlatTokens.SURFACE_RAISED))
        else:
            scaled = pixmap
            if is_preview_frame:
                scaled = pixmap.scaled(
                    poster_rect.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            x = poster_rect.left() + max(0, (poster_rect.width() - scaled.width()) // 2)
            y = poster_rect.top() + max(0, (poster_rect.height() - scaled.height()) // 2)
            painter.drawPixmap(x, y, scaled)
        painter.restore()

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
            painter.setPen(QPen(QColor(FlatTokens.BORDER_STRONG), 1))
            painter.drawPath(rounded)

        painter.restore()

