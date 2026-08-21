from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QAbstractListModel, QAbstractTableModel, QModelIndex, Qt

from app.models.movie import MovieRecord


class MovieListModel(QAbstractListModel):
    MovieUuidRole = int(Qt.ItemDataRole.UserRole) + 1
    CoverPathRole = MovieUuidRole + 1
    AvailabilityRole = MovieUuidRole + 2
    SubtitleRole = MovieUuidRole + 3
    FavoriteRole = MovieUuidRole + 4
    WatchedRole = MovieUuidRole + 5
    TitleRole = MovieUuidRole + 6

    def __init__(self, movies: Sequence[MovieRecord] = (), parent=None) -> None:
        super().__init__(parent)
        self._movies = list(movies)

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._movies)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._movies):
            return None
        record = self._movies[index.row()]
        values = {
            int(Qt.ItemDataRole.DisplayRole): record.metadata.code or record.metadata.title,
            self.MovieUuidRole: record.metadata.uuid,
            self.CoverPathRole: record.runtime.cover_path,
            self.AvailabilityRole: record.runtime.availability_status,
            self.SubtitleRole: record.runtime.subtitle_status,
            self.FavoriteRole: record.metadata.favorite,
            self.WatchedRole: record.metadata.watched,
            self.TitleRole: record.metadata.title,
        }
        return values.get(role)

    def roleNames(self):
        roles = super().roleNames()
        roles.update({
            self.MovieUuidRole: b"movieUuid",
            self.CoverPathRole: b"coverPath",
            self.AvailabilityRole: b"availability",
            self.SubtitleRole: b"subtitle",
            self.FavoriteRole: b"favorite",
            self.WatchedRole: b"watched",
            self.TitleRole: b"title",
        })
        return roles

    def set_movies(self, movies: Sequence[MovieRecord]) -> None:
        self.beginResetModel()
        self._movies = list(movies)
        self.endResetModel()

    def movie_at(self, row: int) -> MovieRecord | None:
        return self._movies[row] if 0 <= row < len(self._movies) else None


class MovieTableModel(QAbstractTableModel):
    COLUMNS = (
        "封面", "编号", "标题", "演员", "系列", "厂商",
        "发行日期", "评分", "字幕", "观看状态", "本地状态", "文件大小",
    )

    def __init__(self, movies: Sequence[MovieRecord] = (), parent=None) -> None:
        super().__init__(parent)
        self._movies = list(movies)

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._movies)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal and 0 <= section < len(self.COLUMNS):
            return self.COLUMNS[section]
        return super().headerData(section, orientation, role)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._movies):
            return None
        record = self._movies[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return record.metadata.uuid
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        size = record.runtime.file_size
        values = (
            "",
            record.metadata.code,
            record.metadata.title,
            " / ".join(record.metadata.actors),
            record.metadata.series,
            record.metadata.studio,
            record.metadata.release_date,
            "★" * record.metadata.rating,
            "有" if record.runtime.subtitle_status else "无",
            "已观看" if record.metadata.watched else "未观看",
            "本地" if record.runtime.availability_status == "available" else "仅档案",
            _format_size(size),
        )
        return values[index.column()]

    def set_movies(self, movies: Sequence[MovieRecord]) -> None:
        self.beginResetModel()
        self._movies = list(movies)
        self.endResetModel()

    def movie_at(self, row: int) -> MovieRecord | None:
        return self._movies[row] if 0 <= row < len(self._movies) else None


def _format_size(size: int | None) -> str:
    if size is None:
        return ""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return ""
