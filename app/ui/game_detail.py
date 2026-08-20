from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon, QMovie, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.game import GameRecord
from app.services.giga_cover_cropper import GigaCoverCropper
from app.ui.manual_cover_crop_dialog import ManualCoverCropDialog


@dataclass(frozen=True, slots=True)
class GameArchiveEditResult:
    title: str
    series: str
    developer: str
    publisher: str
    release_date: str
    tags: list[str]
    rating: int
    favorite: bool
    description: str
    notes: str
    launch_exe: Path
    timing_exe: Path
    launch_args: str
    working_directory: Path
    screenshot_directory: Path | None
    cover_source: Path | None
    preview_source: Path | None
    remove_cover: bool
    remove_preview: bool


class GameDetailDialog(QDialog):
    launch_requested = Signal(str)
    save_requested = Signal(object)

    def __init__(self, record: GameRecord, screenshot_service, parent=None) -> None:
        super().__init__(parent)
        self.record = record
        self.screenshot_service = screenshot_service
        self._media_movie: QMovie | None = None
        self._selected_media_path: Path | None = None
        self._cover_source: Path | None = None
        self._preview_source: Path | None = None
        self._remove_cover = False
        self._remove_preview = False
        self._cover_cropper = GigaCoverCropper()
        self._cover_crop_tempdirs: list[TemporaryDirectory] = []
        self.setWindowTitle(f"游戏档案：{record.metadata.title}")
        self.resize(920, 720)
        self._build_ui()
        self._load_record()
        self._refresh_screenshots()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        header = QHBoxLayout()
        self.heading_label = QLabel()
        self.heading_label.setObjectName("dialogHeading")
        header.addWidget(self.heading_label)
        header.addStretch(1)
        self.launch_button = QPushButton("▶ 启动游戏")
        self.launch_button.setObjectName("primaryButton")
        header.addWidget(self.launch_button)
        root.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_info_tab(), "资料")
        self.tabs.addTab(self._build_play_tab(), "游玩")
        self.tabs.addTab(self._build_media_tab(), "媒体")
        root.addWidget(self.tabs, 1)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_button = QPushButton("关闭")
        close_button.setObjectName("quietButton")
        close_row.addWidget(close_button)
        root.addLayout(close_row)

        self.launch_button.clicked.connect(lambda: self.launch_requested.emit(self.record.metadata.uuid))
        close_button.clicked.connect(self.accept)

    def _build_info_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        form = QFormLayout()

        self.title_edit = QLineEdit()
        self.series_edit = QLineEdit()
        self.developer_edit = QLineEdit()
        self.publisher_edit = QLineEdit()
        self.release_edit = QLineEdit()
        self.tags_edit = QLineEdit()
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(0, 5)
        self.favorite_check = QCheckBox("收藏")

        form.addRow("游戏名称 *", self.title_edit)
        form.addRow("系列", self.series_edit)
        form.addRow("开发商", self.developer_edit)
        form.addRow("发行商", self.publisher_edit)
        form.addRow("发行日期", self.release_edit)
        form.addRow("标签", self.tags_edit)
        form.addRow("评分", self.rating_spin)
        form.addRow("", self.favorite_check)

        self.description_edit = QTextEdit()
        self.description_edit.setMinimumHeight(90)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(90)
        form.addRow("作品介绍", self.description_edit)
        form.addRow("我的记录", self.notes_edit)

        self.launch_edit = QLineEdit()
        self.timing_edit = QLineEdit()
        self.args_edit = QLineEdit()
        self.workdir_edit = QLineEdit()
        form.addRow("启动 EXE *", self._path_row(self.launch_edit, self._browse_launch))
        form.addRow("计时 EXE *", self._path_row(self.timing_edit, self._browse_timing))
        form.addRow("启动参数", self.args_edit)
        form.addRow("工作目录", self._path_row(self.workdir_edit, self._browse_workdir))

        self.cover_edit = QLineEdit()
        self.cover_edit.setReadOnly(True)
        self.preview_edit = QLineEdit()
        self.preview_edit.setReadOnly(True)
        self.screenshot_edit = QLineEdit()
        form.addRow("静态封面", self._path_row(self.cover_edit, self._browse_cover, self._clear_cover, self._crop_cover))
        form.addRow("GIF 动态预览", self._path_row(self.preview_edit, self._browse_preview, self._clear_preview))
        form.addRow("截图目录", self._path_row(self.screenshot_edit, self._browse_screenshots))

        root.addLayout(form)
        save_row = QHBoxLayout()
        save_row.addStretch(1)
        self.save_button = QPushButton("保存")
        self.save_button.setObjectName("primaryButton")
        save_row.addWidget(self.save_button)
        root.addLayout(save_row)
        self.save_button.clicked.connect(self._request_save)
        return page

    def _build_play_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        form = QFormLayout()
        self.status_label = QLabel()
        self.time_label = QLabel()
        self.play_count_label = QLabel()
        self.first_label = QLabel()
        self.last_label = QLabel()
        form.addRow("状态", self.status_label)
        form.addRow("累计游玩", self.time_label)
        form.addRow("游玩次数", self.play_count_label)
        form.addRow("首次游玩", self.first_label)
        form.addRow("最近游玩", self.last_label)
        root.addLayout(form)

        session_title = QLabel("游玩记录")
        session_title.setObjectName("dialogSectionTitle")
        root.addWidget(session_title)
        self.session_table = QTableWidget(0, 3)
        self.session_table.setHorizontalHeaderLabels(["开始时间", "时长", "状态"])
        self.session_table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.session_table, 1)
        return page

    def _build_media_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        shot_header = QHBoxLayout()
        shot_title = QLabel("截图")
        shot_title.setObjectName("dialogSectionTitle")
        shot_header.addWidget(shot_title)
        shot_header.addStretch(1)
        self.refresh_button = QPushButton("刷新")
        self.open_screenshot_dir_button = QPushButton("打开目录")
        shot_header.addWidget(self.refresh_button)
        shot_header.addWidget(self.open_screenshot_dir_button)
        root.addLayout(shot_header)

        self.screenshot_status = QLabel()
        root.addWidget(self.screenshot_status)

        self.media_preview_label = QLabel("选择下方媒体")
        self.media_preview_label.setObjectName("previewFrame")
        self.media_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Ignore QLabel's pixmap-derived sizeHint. Animated GIF frames are updated
        # repeatedly; letting each frame feed its current pixmap size back into the
        # layout can make the top-level archive dialog grow a little every frame.
        self.media_preview_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored,
        )
        self.media_preview_label.setMinimumHeight(280)
        root.addWidget(self.media_preview_label, 1)

        self.screenshot_list = QListWidget()
        self.screenshot_list.setViewMode(QListView.ViewMode.IconMode)
        self.screenshot_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.screenshot_list.setFlow(QListView.Flow.LeftToRight)
        self.screenshot_list.setWrapping(False)
        self.screenshot_list.setMovement(QListView.Movement.Static)
        self.screenshot_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.screenshot_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.screenshot_list.setIconSize(QSize(144, 90))
        self.screenshot_list.setSpacing(6)
        self.screenshot_list.setFixedHeight(122)
        root.addWidget(self.screenshot_list)

        self.refresh_button.clicked.connect(self._refresh_screenshots)
        self.open_screenshot_dir_button.clicked.connect(self._open_screenshot_dir)
        self.screenshot_list.itemClicked.connect(self._select_screenshot)
        self.screenshot_list.itemDoubleClicked.connect(self._open_screenshot)
        return page

    def _path_row(self, edit: QLineEdit, browse_callback, clear_callback=None, crop_callback=None) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(edit, 1)
        browse = QPushButton("浏览…")
        browse.clicked.connect(browse_callback)
        layout.addWidget(browse)
        if crop_callback is not None:
            crop = QPushButton("裁剪导入…")
            crop.clicked.connect(crop_callback)
            layout.addWidget(crop)
        if clear_callback is not None:
            clear = QPushButton("清除")
            clear.clicked.connect(clear_callback)
            layout.addWidget(clear)
        return widget

    def _load_record(self) -> None:
        game = self.record.metadata
        self.setWindowTitle(f"游戏档案：{game.title}")
        self.heading_label.setText(game.title)
        self.title_edit.setText(game.title)
        self.series_edit.setText(game.series)
        self.developer_edit.setText(game.developer)
        self.publisher_edit.setText(game.publisher)
        self.release_edit.setText(game.release_date)
        self.tags_edit.setText(" / ".join(game.tags))
        self.rating_spin.setValue(game.rating)
        self.favorite_check.setChecked(game.favorite)
        self.description_edit.setPlainText(game.description)
        self.notes_edit.setPlainText(game.notes)
        self.launch_edit.setText(game.launch_exe)
        self.timing_edit.setText(game.timing_exe)
        self.args_edit.setText(game.launch_args)
        self.workdir_edit.setText(game.working_directory)
        self.cover_edit.setText(game.cover_path or "")
        self.preview_edit.setText(game.preview_gif_path or "")
        self.screenshot_edit.setText(game.screenshot_directory or "")
        self._cover_source = None
        self._preview_source = None
        self._remove_cover = False
        self._remove_preview = False

        self.status_label.setText("已安装" if self.record.installed else "未安装 / 仅档案")
        self.time_label.setText(_format_duration(game.total_play_seconds))
        self.play_count_label.setText(str(game.play_count))
        self.first_label.setText(_format_dt(game.first_played_at))
        self.last_label.setText(_format_dt(game.last_played_at))
        self.launch_button.setEnabled(self.record.installed)

        self.session_table.setRowCount(0)
        for session in sorted(game.sessions, key=lambda item: item.started_at, reverse=True):
            row = self.session_table.rowCount()
            self.session_table.insertRow(row)
            self.session_table.setItem(row, 0, QTableWidgetItem(_format_dt(session.started_at)))
            self.session_table.setItem(row, 1, QTableWidgetItem(_format_duration(session.duration_seconds)))
            status = "已恢复" if session.status == "recovered" else "正常结束"
            self.session_table.setItem(row, 2, QTableWidgetItem(status))

    def set_record(self, record: GameRecord) -> None:
        self._cleanup_cover_crop_tempdirs()
        self.record = record
        self._load_record()
        self._refresh_screenshots()

    def _browse_launch(self) -> None:
        previous = self.launch_edit.text().strip()
        path, _ = QFileDialog.getOpenFileName(self, "选择启动 EXE", previous, "程序 (*.exe);;所有文件 (*)")
        if not path:
            return
        self.launch_edit.setText(path)
        if not self.timing_edit.text().strip() or self.timing_edit.text().strip() == previous:
            self.timing_edit.setText(path)
        if not self.workdir_edit.text().strip() or (
            previous and self.workdir_edit.text().strip() == str(Path(previous).parent)
        ):
            self.workdir_edit.setText(str(Path(path).parent))

    def _browse_timing(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择计时 EXE", self.timing_edit.text(), "程序 (*.exe);;所有文件 (*)"
        )
        if path:
            self.timing_edit.setText(path)

    def _browse_workdir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择工作目录", self.workdir_edit.text())
        if path:
            self.workdir_edit.setText(path)

    def _browse_screenshots(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择截图目录", self.screenshot_edit.text())
        if path:
            self.screenshot_edit.setText(path)

    def _browse_cover(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择游戏封面", "", "图片 (*.jpg *.jpeg *.png *.webp *.bmp)"
        )
        if path:
            self._cover_source = Path(path)
            self._remove_cover = False
            self.cover_edit.setText(path)

    def _crop_cover(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择需要裁剪的游戏封面",
            "",
            "图片 (*.jpg *.jpeg *.png *.webp)",
        )
        if not path:
            return

        temporary = TemporaryDirectory(prefix="local-resource-terminal-game-cover-")
        try:
            crop_dialog = ManualCoverCropDialog(
                Path(path),
                Path(temporary.name),
                self._cover_cropper,
                parent=self,
            )
        except (OSError, ValueError) as exc:
            temporary.cleanup()
            QMessageBox.warning(self, "无法打开封面", str(exc))
            return

        if crop_dialog.exec() != QDialog.DialogCode.Accepted or crop_dialog.saved_candidate is None:
            temporary.cleanup()
            return

        cropped_path = crop_dialog.saved_candidate.output_path
        if not cropped_path.is_file():
            temporary.cleanup()
            QMessageBox.warning(self, "裁剪失败", "裁剪后的封面文件不存在。")
            return

        self._cover_crop_tempdirs.append(temporary)
        self._cover_source = cropped_path
        self._remove_cover = False
        self.cover_edit.setText(f"裁剪待保存：{Path(path).name}")

    def _browse_preview(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 GIF 动态预览", "", "GIF 动图 (*.gif)")
        if path:
            self._preview_source = Path(path)
            self._remove_preview = False
            self.preview_edit.setText(path)

    def _clear_cover(self) -> None:
        self._cover_source = None
        self._remove_cover = bool(self.record.metadata.cover_path)
        self.cover_edit.clear()

    def _clear_preview(self) -> None:
        self._preview_source = None
        self._remove_preview = bool(self.record.metadata.preview_gif_path)
        self.preview_edit.clear()

    def _request_save(self) -> None:
        title = self.title_edit.text().strip()
        launch = self.launch_edit.text().strip()
        timing = self.timing_edit.text().strip()
        if not title or not launch or not timing:
            QMessageBox.information(self, "信息不完整", "游戏名称、启动 EXE 和计时 EXE 为必填项。")
            return
        workdir = self.workdir_edit.text().strip() or str(Path(launch).parent)
        screenshot = self.screenshot_edit.text().strip()
        result = GameArchiveEditResult(
            title=title,
            series=self.series_edit.text().strip(),
            developer=self.developer_edit.text().strip(),
            publisher=self.publisher_edit.text().strip(),
            release_date=self.release_edit.text().strip(),
            tags=_split_values(self.tags_edit.text()),
            rating=self.rating_spin.value(),
            favorite=self.favorite_check.isChecked(),
            description=self.description_edit.toPlainText(),
            notes=self.notes_edit.toPlainText(),
            launch_exe=Path(launch),
            timing_exe=Path(timing),
            launch_args=self.args_edit.text().strip(),
            working_directory=Path(workdir),
            screenshot_directory=Path(screenshot) if screenshot else None,
            cover_source=self._cover_source,
            preview_source=self._preview_source,
            remove_cover=self._remove_cover,
            remove_preview=self._remove_preview,
        )
        self.save_requested.emit(result)

    def _cleanup_cover_crop_tempdirs(self) -> None:
        for temporary in self._cover_crop_tempdirs:
            temporary.cleanup()
        self._cover_crop_tempdirs.clear()

    def done(self, result: int) -> None:
        self._cleanup_cover_crop_tempdirs()
        super().done(result)

    def _refresh_screenshots(self) -> None:
        self._stop_media_movie()
        self._selected_media_path = None
        self.media_preview_label.setPixmap(QPixmap())
        self.screenshot_list.clear()
        directory = self.record.metadata.screenshot_directory
        result = self.screenshot_service.list_images(directory)
        if not result.available:
            self.screenshot_status.setText("截图目录不可用或尚未设置。")
            self.media_preview_label.setText("截图目录不可用或尚未设置。")
            self.open_screenshot_dir_button.setEnabled(False)
            return
        self.screenshot_status.setText(f"{len(result.items)} 张截图")
        self.open_screenshot_dir_button.setEnabled(True)
        for shot in result.items:
            try:
                thumbnail = self.screenshot_service.thumbnail_for(self.record.metadata.uuid, shot.path)
                item = QListWidgetItem(QIcon(str(thumbnail)), shot.path.name)
            except Exception:
                item = QListWidgetItem(shot.path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(shot.path))
            item.setSizeHint(QSize(154, 106))
            self.screenshot_list.addItem(item)
        if self.screenshot_list.count():
            first = self.screenshot_list.item(0)
            self.screenshot_list.setCurrentItem(first)
            self._select_screenshot(first)
        else:
            self.media_preview_label.setText("截图目录中没有可展示的图片或 GIF。")

    def _select_screenshot(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self._show_media(Path(str(path)))

    def _show_media(self, path: Path) -> None:
        self._stop_media_movie()
        self._selected_media_path = path
        self.media_preview_label.setText("")
        self.media_preview_label.setPixmap(QPixmap())
        if not path.is_file():
            self.media_preview_label.setText("原始媒体文件已不存在。")
            return
        if path.suffix.lower() == ".gif":
            movie = QMovie(str(path))
            if not movie.isValid():
                self.media_preview_label.setText("GIF 无法读取。")
                return
            self._media_movie = movie
            movie.frameChanged.connect(self._render_movie_frame)
            movie.start()
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.media_preview_label.setText("图片无法读取。")
            return
        self.media_preview_label.setPixmap(self._fit_media_pixmap(pixmap))

    def _render_movie_frame(self, _frame_number: int) -> None:
        if self._media_movie is None:
            return
        pixmap = self._media_movie.currentPixmap()
        if not pixmap.isNull():
            self.media_preview_label.setPixmap(self._fit_media_pixmap(pixmap))

    def _fit_media_pixmap(self, pixmap: QPixmap) -> QPixmap:
        return pixmap.scaled(
            self.media_preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _stop_media_movie(self) -> None:
        if self._media_movie is not None:
            self._media_movie.stop()
            self._media_movie = None

    def _open_screenshot(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and Path(str(path)).is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _open_screenshot_dir(self) -> None:
        path = self.record.metadata.screenshot_directory
        if path and Path(path).is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def closeEvent(self, event) -> None:
        self._stop_media_movie()
        super().closeEvent(event)


def _split_values(text: str) -> list[str]:
    normalized = text.replace("，", ",").replace("、", ",").replace("/", ",").replace(";", ",").replace("；", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def _format_duration(duration_seconds: int) -> str:
    total = max(0, int(duration_seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _format_dt(value) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S") if value else "—"
