from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QUrl, Signal, Qt
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.movie import MovieMetadataPatch, MovieRecord
from app.services.player_service import PlaybackError


class MovieDetailDialog(QDialog):
    movie_updated = Signal(str)
    movie_deleted = Signal(str)

    def __init__(
        self,
        record: MovieRecord,
        catalog_service,
        cover_service,
        player_service,
        viewing_service,
        settings,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.record = record
        self.catalog = catalog_service
        self.cover_service = cover_service
        self.player_service = player_service
        self.viewing_service = viewing_service
        self.settings = settings
        self.setWindowTitle(record.metadata.code or record.metadata.title or "影片详情")
        self.resize(920, 680)
        self._build_ui()
        self._load_record(record)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(14)

        heading = QLabel("影片档案")
        heading.setObjectName("dialogHeading")
        root.addWidget(heading)
        subtitle = QLabel("编辑影片资料、观看状态与本地文件关联。")
        subtitle.setObjectName("secondaryLabel")
        root.addWidget(subtitle)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        cover_panel = QWidget()
        cover_panel.setObjectName("panelCard")
        cover_layout = QVBoxLayout(cover_panel)
        cover_layout.setContentsMargins(14, 14, 14, 14)
        cover_title = QLabel("封面")
        cover_title.setObjectName("dialogSectionTitle")
        cover_layout.addWidget(cover_title)
        self.cover_label = QLabel("无封面")
        self.cover_label.setMinimumSize(300, 430)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setObjectName("previewFrame")
        cover_layout.addWidget(self.cover_label, 1)
        self.replace_cover_button = QPushButton("更换封面")
        cover_layout.addWidget(self.replace_cover_button)
        splitter.addWidget(cover_panel)

        form_panel = QWidget()
        form_panel.setObjectName("panelCard")
        form_outer = QVBoxLayout(form_panel)
        form_outer.setContentsMargins(16, 14, 16, 14)
        form_outer.setSpacing(10)
        form_title = QLabel("影片资料")
        form_title.setObjectName("dialogSectionTitle")
        form_outer.addWidget(form_title)
        form = QFormLayout()
        form.setSpacing(9)
        self.code_edit = QLineEdit()
        self.cover_key_edit = QLineEdit()
        self.cover_key_edit.setToolTip("集中封面目录使用这个名称匹配图片。修改编号不会自动修改它。")
        self.title_edit = QLineEdit()
        self.actors_edit = QLineEdit()
        self.series_edit = QLineEdit()
        self.studio_edit = QLineEdit()
        self.release_date_edit = QLineEdit()
        self.tags_edit = QLineEdit()
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(0, 5)
        self.watched_check = QCheckBox("已观看")
        self.favorite_check = QCheckBox("收藏")
        self.subtitle_label = QLabel()
        self.availability_label = QLabel()
        self.history_label = QLabel()
        self.tech_label = QLabel()
        self.tech_label.setWordWrap(True)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(110)

        form.addRow("编号", self.code_edit)
        form.addRow("封面键", self.cover_key_edit)
        form.addRow("标题", self.title_edit)
        form.addRow("演员", self.actors_edit)
        form.addRow("系列", self.series_edit)
        form.addRow("厂商", self.studio_edit)
        form.addRow("发行日期", self.release_date_edit)
        form.addRow("标签", self.tags_edit)
        form.addRow("评分", self.rating_spin)
        form.addRow("观看", self.watched_check)
        form.addRow("收藏", self.favorite_check)
        form.addRow("字幕", self.subtitle_label)
        form.addRow("本地状态", self.availability_label)
        form.addRow("观看痕迹", self.history_label)
        form.addRow("媒体信息", self.tech_label)
        form.addRow("备注", self.notes_edit)
        form_outer.addLayout(form)
        form_outer.addStretch(1)
        splitter.addWidget(form_panel)
        splitter.setStretchFactor(1, 1)

        buttons = QHBoxLayout()
        self.play_button = QPushButton("▶ 播放")
        self.play_button.setObjectName("primaryButton")
        self.open_folder_button = QPushButton("打开目录")
        self.relink_button = QPushButton("关联本地文件")
        self.save_button = QPushButton("保存")
        self.delete_button = QPushButton("删除影片档案")
        self.delete_button.setObjectName("dangerButton")
        self.close_button = QPushButton("关闭")
        self.close_button.setObjectName("quietButton")
        for button in (
            self.play_button,
            self.open_folder_button,
            self.relink_button,
            self.save_button,
            self.delete_button,
            self.close_button,
        ):
            buttons.addWidget(button)
        root.addLayout(buttons)

        self.play_button.clicked.connect(self._play)
        self.open_folder_button.clicked.connect(self._open_folder)
        self.relink_button.clicked.connect(self._relink)
        self.replace_cover_button.clicked.connect(self._replace_cover)
        self.save_button.clicked.connect(self._save)
        self.delete_button.clicked.connect(self._delete_archive)
        self.close_button.clicked.connect(self.reject)

    def _load_record(self, record: MovieRecord) -> None:
        self.record = record
        m, r = record.metadata, record.runtime
        self.code_edit.setText(m.code)
        self.cover_key_edit.setText(m.cover_key)
        self.title_edit.setText(m.title)
        self.actors_edit.setText(" / ".join(m.actors))
        self.series_edit.setText(m.series)
        self.studio_edit.setText(m.studio)
        self.release_date_edit.setText(m.release_date)
        self.tags_edit.setText(" / ".join(m.tags))
        self.rating_spin.setValue(m.rating)
        self.watched_check.setChecked(m.watched)
        self.favorite_check.setChecked(m.favorite)
        self.subtitle_label.setText("有字幕" if r.subtitle_status else "无字幕")
        self.availability_label.setText("本地可播放" if r.availability_status == "available" else "仅档案 / 当前无本地视频")
        first = _fmt_dt(m.first_watched_at)
        last = _fmt_dt(m.last_watched_at)
        self.history_label.setText(f"播放 {m.play_count} 次 · 首次 {first} · 最后 {last}")
        resolution = f"{r.width}×{r.height}" if r.width and r.height else "未知分辨率"
        duration = _fmt_duration(r.duration)
        codecs = " / ".join(item for item in (r.video_codec, r.audio_codec) if item) or "未知编码"
        self.tech_label.setText(f"{resolution} · {duration} · {codecs}")
        self.notes_edit.setPlainText(m.notes)
        available = r.availability_status == "available" and bool(r.video_path) and Path(r.video_path).is_file()
        self.play_button.setEnabled(available)
        self.open_folder_button.setEnabled(available)
        self.relink_button.setEnabled(True)
        self._show_cover(r.cover_path)

    def _show_cover(self, path: str | None) -> None:
        pixmap = QPixmap(path) if path and Path(path).is_file() else QPixmap()
        if pixmap.isNull():
            self.cover_label.setPixmap(QPixmap())
            self.cover_label.setText("无封面")
            return
        self.cover_label.setText("")
        self.cover_label.setPixmap(
            pixmap.scaled(
                self.cover_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _save(self) -> None:
        if self.catalog is None:
            return
        try:
            record = self.catalog.update_metadata(
                self.record.metadata.uuid,
                MovieMetadataPatch(
                    code=self.code_edit.text(),
                    cover_key=self.cover_key_edit.text(),
                    title=self.title_edit.text(),
                    actors=_split_values(self.actors_edit.text()),
                    series=self.series_edit.text(),
                    studio=self.studio_edit.text(),
                    release_date=self.release_date_edit.text(),
                    tags=_split_values(self.tags_edit.text()),
                    rating=self.rating_spin.value(),
                    watched=self.watched_check.isChecked(),
                    favorite=self.favorite_check.isChecked(),
                    notes=self.notes_edit.toPlainText(),
                ),
            )
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        self._load_record(record)
        self.movie_updated.emit(record.metadata.uuid)

    def _play(self) -> None:
        if not (self.player_service and self.viewing_service and self.settings):
            return
        path = self.record.runtime.video_path
        if not path:
            return
        try:
            self.player_service.play(Path(path), self.settings)
            self.viewing_service.record_launch(self.record.metadata.uuid)
            updated = self.catalog.get(self.record.metadata.uuid) if self.catalog else None
            if updated:
                self._load_record(updated)
                self.movie_updated.emit(updated.metadata.uuid)
        except PlaybackError as exc:
            QMessageBox.warning(self, "无法播放", str(exc))
        except Exception as exc:
            QMessageBox.warning(self, "播放记录失败", str(exc))

    def _open_folder(self) -> None:
        path = self.record.runtime.video_path
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).parent)))

    def _relink(self) -> None:
        if self.catalog is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "关联本地影片",
            "",
            "影片文件 (*.mp4 *.mkv *.avi *.mov *.wmv *.m4v *.ts *.webm)",
        )
        if not path:
            return
        try:
            record = self.catalog.relink_video(self.record.metadata.uuid, Path(path))
        except Exception as exc:
            QMessageBox.warning(self, "关联失败", str(exc))
            return
        self._load_record(record)
        self.movie_updated.emit(record.metadata.uuid)

    def _replace_cover(self) -> None:
        if self.cover_service is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择封面",
            "",
            "图片 (*.jpg *.jpeg *.png *.webp *.bmp *.gif)",
        )
        if not path:
            return
        try:
            self.cover_service.replace(self.record.metadata.cover_key, Path(path))
            record = self.catalog.refresh_cover(self.record.metadata.uuid) if self.catalog else self.record
        except Exception as exc:
            QMessageBox.warning(self, "更换封面失败", str(exc))
            return
        self._load_record(record)
        self.movie_updated.emit(record.metadata.uuid)

    def _delete_archive(self) -> None:
        if self.catalog is None:
            return
        reply = QMessageBox.question(
            self,
            "删除影片档案",
            "确定永久删除这条影片档案吗？\n\n视频文件和集中封面不会被删除。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.catalog.delete_archive(self.record.metadata.uuid)
        except Exception as exc:
            QMessageBox.critical(self, "删除失败", str(exc))
            return
        uuid = self.record.metadata.uuid
        self.movie_deleted.emit(uuid)
        self.accept()


def _split_values(text: str) -> list[str]:
    normalized = text.replace(",", "/").replace("，", "/")
    return [item.strip() for item in normalized.split("/") if item.strip()]


def _fmt_dt(value) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M") if value else "—"


def _fmt_duration(seconds: float | None) -> str:
    if seconds is None:
        return "未知时长"
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
