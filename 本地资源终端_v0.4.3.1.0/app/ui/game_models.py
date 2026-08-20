from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from app.models.game import GameRecord


class GameListModel(QAbstractListModel):
    GameUuidRole = int(Qt.ItemDataRole.UserRole) + 1
    CoverPathRole = GameUuidRole + 1
    PreviewGifRole = GameUuidRole + 2
    InstalledRole = GameUuidRole + 3
    FavoriteRole = GameUuidRole + 4
    TitleRole = GameUuidRole + 5

    def __init__(self, games: Sequence[GameRecord] = (), parent=None) -> None:
        super().__init__(parent)
        self._games = list(games)

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._games)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._games):
            return None
        record = self._games[index.row()]
        values = {
            int(Qt.ItemDataRole.DisplayRole): record.metadata.title,
            self.GameUuidRole: record.metadata.uuid,
            self.CoverPathRole: record.metadata.cover_path,
            self.PreviewGifRole: record.metadata.preview_gif_path,
            self.InstalledRole: record.installed,
            self.FavoriteRole: record.metadata.favorite,
            self.TitleRole: record.metadata.title,
        }
        return values.get(role)

    def roleNames(self):
        roles = super().roleNames()
        roles.update({
            self.GameUuidRole: b"gameUuid",
            self.CoverPathRole: b"coverPath",
            self.PreviewGifRole: b"previewGif",
            self.InstalledRole: b"installed",
            self.FavoriteRole: b"favorite",
            self.TitleRole: b"title",
        })
        return roles

    def set_games(self, games: Sequence[GameRecord]) -> None:
        self.beginResetModel()
        self._games = list(games)
        self.endResetModel()

    def game_at(self, row: int) -> GameRecord | None:
        return self._games[row] if 0 <= row < len(self._games) else None
