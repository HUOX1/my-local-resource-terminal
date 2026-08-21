from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.models.movie import MovieEpisodeRecord, MovieRecord
from app.ui.movie_episode_presenter import build_episode_actions


class MovieEpisodeDialog(QDialog):
    relink_requested = Signal(str, str)
    open_folder_requested = Signal(str, str)

    def __init__(self, record: MovieRecord, parent=None) -> None:
        super().__init__(parent)
        self.record = record
        self.setWindowTitle("剧集详情")
        self.setObjectName("movieEpisodeDialog")
        self.resize(720, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel(record.metadata.title or record.metadata.code or record.metadata.cover_key)
        title.setObjectName("movieEpisodeDialogTitle")
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setObjectName("movieEpisodeDialogScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(scroll, 1)

        content = QWidget()
        content.setObjectName("movieEpisodeDialogContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 4, 0)
        content_layout.setSpacing(10)
        scroll.setWidget(content)

        actions = {
            action.episode_uuid: action
            for action in build_episode_actions(record.episodes)
        }
        for episode in record.episodes:
            content_layout.addWidget(
                self._episode_card(
                    episode,
                    actions[episode.metadata.uuid].label,
                )
            )
        content_layout.addStretch(1)

        close_button = QPushButton("关闭")
        close_button.setObjectName("quietButton")
        close_button.clicked.connect(self.accept)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_row.addWidget(close_button)
        root.addLayout(close_row)

    def _episode_card(self, episode: MovieEpisodeRecord, label: str) -> QFrame:
        card = QFrame()
        card.setObjectName("movieEpisodeDetailCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(7)

        heading = QLabel(label)
        heading.setObjectName("movieEpisodeDetailHeading")
        layout.addWidget(heading)

        details = QLabel(_episode_details(episode))
        details.setObjectName("movieEpisodeDetailText")
        details.setWordWrap(True)
        details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(details)

        actions = QHBoxLayout()
        open_button = QPushButton("打开目录")
        open_button.setObjectName("quietButton")
        open_button.setEnabled(bool(episode.runtime.video_path))
        open_button.clicked.connect(
            lambda _checked=False, episode_uuid=episode.metadata.uuid: self.open_folder_requested.emit(
                self.record.metadata.uuid,
                episode_uuid,
            )
        )
        relink_button = QPushButton("重新关联")
        relink_button.setObjectName("quietButton")
        relink_button.clicked.connect(
            lambda _checked=False, episode_uuid=episode.metadata.uuid: self.relink_requested.emit(
                self.record.metadata.uuid,
                episode_uuid,
            )
        )
        actions.addWidget(open_button)
        actions.addWidget(relink_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        return card


def _episode_details(episode: MovieEpisodeRecord) -> str:
    runtime = episode.runtime
    source = episode.metadata.source_name or "未知文件名"
    path = runtime.video_path or "当前没有关联的本地文件"
    status = "本地可用" if runtime.availability_status == "available" else "当前离线"
    resolution = (
        f"{runtime.width}×{runtime.height}"
        if runtime.width and runtime.height
        else "未知分辨率"
    )
    codecs = " / ".join(
        value for value in (runtime.video_codec, runtime.audio_codec) if value
    ) or "未知编码"
    subtitle = "有字幕" if runtime.subtitle_status else "无字幕"
    return (
        f"{source}\n{path}\n"
        f"{status}  ·  {_format_duration(runtime.duration)}  ·  {resolution}\n"
        f"{codecs}  ·  {_format_size(runtime.file_size)}  ·  {subtitle}"
    )


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "未知时长"
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _format_size(value: int | None) -> str:
    if value is None or value < 0:
        return "未知大小"
    size = float(value)
    units = ("B", "KB", "MB", "GB", "TB")
    unit = units[0]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            break
        size /= 1024
    return f"{size:.1f} {unit}"
