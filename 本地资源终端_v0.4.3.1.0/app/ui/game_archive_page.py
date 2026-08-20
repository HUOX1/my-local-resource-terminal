from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageStat
from PySide6.QtCore import QEasingCurve, QRectF, QSize, QTimer, Qt, QUrl, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QLinearGradient, QMovie, QPainter, QPainterPath, QPalette, QPixmap
from PySide6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.game import GameMetadataPatch, GameRecord
from app.services.game_archive_media import resolve_game_archive_media, usable_archive_media_path
from app.ui.flat_theme import FlatTokens
from app.ui.motion import animate_responsive_reflow, motion_enabled
from app.ui.movie_archive_page import InlineEditableField, StarRatingEditor


class _AutoSaveTextEdit(QTextEdit):
    editing_finished = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._value = ""

    def set_value(self, value: str | None) -> None:
        self._value = str(value or "")
        self.setPlainText(self._value)

    def focusOutEvent(self, event) -> None:  # noqa: N802 - Qt override
        value = self.toPlainText()
        if value != self._value:
            self.editing_finished.emit(value)
        super().focusOutEvent(event)


class GameArchiveHero(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("gameArchiveHero")
        self.setMinimumHeight(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._pixmap = QPixmap()
        self._movie: QMovie | None = None
        self._previous_pixmap = QPixmap()
        self._media_mix = 1.0
        self._media_fade = QVariantAnimation(self)
        self._media_fade.setDuration(180)
        self._media_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._media_fade.valueChanged.connect(self._set_media_mix)
        self._media_fade.finished.connect(self._finish_media_crossfade)

    def set_media(self, path: Path | None, *, animated: bool = True) -> None:
        previous = self._current_pixmap().copy()
        self.stop()
        self._pixmap = QPixmap()
        if path is None or not path.is_file():
            self.update()
            return
        if path.suffix.lower() == ".gif":
            movie = QMovie(str(path))
            if movie.isValid():
                self._movie = movie
                movie.frameChanged.connect(lambda _frame: self.update())
                movie.jumpToFrame(0)
                movie.start()
                if animated and motion_enabled() and not previous.isNull() and self.isVisible():
                    self._start_media_crossfade(previous)
                else:
                    self._previous_pixmap = QPixmap()
                    self._media_mix = 1.0
                return
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            self._pixmap = pixmap
        if animated and motion_enabled() and not previous.isNull() and self.isVisible():
            self._start_media_crossfade(previous)
        else:
            self._previous_pixmap = QPixmap()
            self._media_mix = 1.0
        self.update()

    def _start_media_crossfade(self, previous: QPixmap) -> None:
        self._media_fade.stop()
        self._previous_pixmap = previous.copy()
        self._media_mix = 0.0
        self._media_fade.setStartValue(0.0)
        self._media_fade.setEndValue(1.0)
        self._media_fade.start()
        self.update()

    def _set_media_mix(self, value) -> None:
        self._media_mix = max(0.0, min(1.0, float(value)))
        self.update()

    def _finish_media_crossfade(self) -> None:
        self._media_mix = 1.0
        self._previous_pixmap = QPixmap()
        self.update()

    def stop(self) -> None:
        if self._movie is not None:
            self._movie.stop()
            self._movie = None

    def _current_pixmap(self) -> QPixmap:
        if self._movie is not None:
            current = self._movie.currentPixmap()
            if not current.isNull():
                return current
        return self._pixmap

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        bounds = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QPainterPath()
        clip.addRoundedRect(bounds, FlatTokens.RADIUS_LARGE, FlatTokens.RADIUS_LARGE)
        painter.setClipPath(clip)
        painter.fillRect(self.rect(), QColor(FlatTokens.SURFACE))
        current = self._current_pixmap()
        if not self._previous_pixmap.isNull() and self._media_mix < 1.0:
            painter.setOpacity(1.0 - self._media_mix)
            self._draw_cover(painter, self._previous_pixmap)
        if not current.isNull():
            painter.setOpacity(self._media_mix if not self._previous_pixmap.isNull() else 1.0)
            self._draw_cover(painter, current)
        painter.setOpacity(1.0)
        top = QColor(FlatTokens.BACKGROUND)
        top.setAlpha(30)
        bottom = QColor(FlatTokens.BACKGROUND)
        bottom.setAlpha(228)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, top)
        gradient.setColorAt(0.58, QColor(top.red(), top.green(), top.blue(), 58))
        gradient.setColorAt(1.0, bottom)
        painter.fillRect(self.rect(), gradient)
        painter.setClipping(False)
        painter.setPen(QColor(FlatTokens.BORDER))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(bounds, FlatTokens.RADIUS_LARGE, FlatTokens.RADIUS_LARGE)
        painter.end()

    def _draw_cover(self, painter: QPainter, pixmap: QPixmap) -> None:
        if pixmap.isNull() or self.width() <= 0 or self.height() <= 0:
            return
        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawPixmap(
            (self.width() - scaled.width()) // 2,
            (self.height() - scaled.height()) // 2,
            scaled,
        )


class GameArchivePage(QWidget):
    back_requested = Signal()
    launch_requested = Signal(str)
    metadata_patch_requested = Signal(str, object)
    archive_media_change_requested = Signal(str)
    archive_media_clear_requested = Signal(str)
    cover_change_requested = Signal(str)
    cover_crop_requested = Signal(str)
    cover_clear_requested = Signal(str)
    preview_change_requested = Signal(str)
    preview_clear_requested = Signal(str)
    launch_exe_browse_requested = Signal(str)
    timing_exe_browse_requested = Signal(str)
    workdir_browse_requested = Signal(str)
    screenshot_dir_browse_requested = Signal(str)

    def __init__(self, screenshot_service=None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("gameArchivePage")
        self.screenshot_service = screenshot_service
        self.record: GameRecord | None = None
        self._hero_source: Path | None = None
        self._build_ui()
        self._responsive_narrow: bool | None = None
        self._pending_responsive_narrow: bool | None = None
        self._responsive_timer = QTimer(self)
        self._responsive_timer.setSingleShot(True)
        self._responsive_timer.setInterval(90)
        self._responsive_timer.timeout.connect(self._commit_responsive_layout)

    @property
    def game_uuid(self) -> str | None:
        return self.record.metadata.uuid if self.record is not None else None

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        self.back_button = QPushButton("←")
        self.back_button.setObjectName("gameArchiveBackButton")
        self.back_button.setToolTip("返回游戏库")
        self.back_button.setFixedWidth(40)
        top_row.addWidget(self.back_button)
        top_row.addStretch(1)

        self.change_hero_button = QPushButton("更换展示图")
        self.change_hero_button.setObjectName("quietButton")
        self.clear_hero_button = QPushButton("清除展示图")
        self.clear_hero_button.setObjectName("quietButton")
        top_row.addWidget(self.change_hero_button)
        top_row.addWidget(self.clear_hero_button)
        root.addLayout(top_row)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("gameArchiveScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(self.scroll, 1)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("gameArchiveScrollContent")
        self.scroll.setWidget(self.scroll_content)
        content = QVBoxLayout(self.scroll_content)
        content.setContentsMargins(0, 0, 6, 8)
        content.setSpacing(16)

        self.hero = GameArchiveHero()
        hero_overlay = QVBoxLayout(self.hero)
        hero_overlay.setContentsMargins(24, 20, 24, 22)
        hero_overlay.setSpacing(8)
        hero_overlay.addStretch(1)

        self.title_field = InlineEditableField(
            display_object_name="gameArchiveTitle",
            editor_object_name="gameArchiveTitleEdit",
            word_wrap=True,
        )
        hero_overlay.addWidget(self.title_field)
        self.hero_meta_label = QLabel()
        self.hero_meta_label.setObjectName("gameArchiveHeroMeta")
        self.hero_meta_label.setWordWrap(True)
        hero_overlay.addWidget(self.hero_meta_label)

        self.rating_editor = StarRatingEditor()
        hero_overlay.addWidget(self.rating_editor)

        hero_stats = QHBoxLayout()
        self.hero_stats_layout = hero_stats
        hero_stats.setSpacing(14)
        self.play_time_label = QLabel()
        self.play_time_label.setObjectName("gameArchiveStat")
        hero_stats.addWidget(self.play_time_label)
        self.install_label = QLabel()
        self.install_label.setObjectName("gameArchiveStat")
        hero_stats.addWidget(self.install_label)
        hero_stats.addStretch(1)
        self.launch_button = QPushButton("启动游戏")
        self.launch_button.setObjectName("primaryButton")
        hero_stats.addWidget(self.launch_button)
        hero_overlay.addLayout(hero_stats)
        content.addWidget(self.hero)

        columns = QHBoxLayout()
        self.columns_layout = columns
        columns.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(16)
        right = QVBoxLayout()
        right.setSpacing(16)
        columns.addLayout(left, 7)
        columns.addLayout(right, 3)
        content.addLayout(columns)
        content.addStretch(1)

        intro_card, intro_layout = self._card("作品介绍")
        self.description_edit = _AutoSaveTextEdit()
        self.description_edit.setObjectName("gameArchiveNotesEdit")
        self.description_edit.setPlaceholderText("点击这里补充作品介绍…")
        self.description_edit.setToolTip("移开焦点自动保存")
        self.description_edit.setMinimumHeight(92)
        intro_layout.addWidget(self.description_edit)
        left.addWidget(intro_card)

        media_card, media_layout = self._card("媒体")
        self.media_status_label = QLabel()
        self.media_status_label.setObjectName("gameArchiveMutedText")
        media_layout.addWidget(self.media_status_label)
        self.media_list = QListWidget()
        self.media_list.setObjectName("gameArchiveMediaList")
        self.media_list.setViewMode(QListView.ViewMode.IconMode)
        self.media_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.media_list.setMovement(QListView.Movement.Static)
        self.media_list.setWrapping(True)
        self.media_list.setIconSize(QSize(196, 110))
        self.media_list.setSpacing(8)
        self.media_list.setMinimumHeight(260)
        self.media_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.media_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        media_layout.addWidget(self.media_list)
        left.addWidget(media_card, 1)

        notes_card, notes_layout = self._card("我的记录")
        self.notes_edit = _AutoSaveTextEdit()
        self.notes_edit.setObjectName("gameArchiveNotesEdit")
        self.notes_edit.setPlaceholderText("点击这里记录进度、配置或个人备注…")
        self.notes_edit.setToolTip("移开焦点自动保存")
        self.notes_edit.setMinimumHeight(92)
        notes_layout.addWidget(self.notes_edit)
        left.addWidget(notes_card)

        details_card, details_layout = self._card("档案资料")
        details_form = QFormLayout()
        details_form.setContentsMargins(0, 2, 0, 0)
        details_form.setSpacing(8)
        self.series_field = self._inline_field()
        self.developer_field = self._inline_field()
        self.publisher_field = self._inline_field()
        self.release_field = self._inline_field()
        self.tags_field = self._inline_field(word_wrap=True)
        details_form.addRow("系列", self.series_field)
        details_form.addRow("开发", self.developer_field)
        details_form.addRow("发行", self.publisher_field)
        details_form.addRow("日期", self.release_field)
        details_form.addRow("标签", self.tags_field)
        details_layout.addLayout(details_form)
        right.addWidget(details_card)

        play_card, play_layout = self._card("游玩")
        self.play_summary_label = QLabel()
        self.play_summary_label.setObjectName("gameArchiveBodyText")
        self.play_summary_label.setWordWrap(True)
        play_layout.addWidget(self.play_summary_label)
        self.session_summary_label = QLabel()
        self.session_summary_label.setObjectName("gameArchiveMutedText")
        self.session_summary_label.setWordWrap(True)
        self.session_summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        play_layout.addWidget(self.session_summary_label)
        right.addWidget(play_card)

        runtime_card, runtime_layout = self._card("运行与媒体")
        runtime_form = QFormLayout()
        runtime_form.setContentsMargins(0, 2, 0, 0)
        runtime_form.setSpacing(8)
        self.launch_field = self._inline_field(word_wrap=True)
        self.timing_field = self._inline_field(word_wrap=True)
        self.args_field = self._inline_field(word_wrap=True)
        self.workdir_field = self._inline_field(word_wrap=True)
        self.screenshot_field = self._inline_field(word_wrap=True)
        runtime_form.addRow("启动 EXE", self._path_field_row(self.launch_field, "浏览…", self._request_launch_exe_browse))
        runtime_form.addRow("计时 EXE", self._path_field_row(self.timing_field, "浏览…", self._request_timing_exe_browse))
        runtime_form.addRow("启动参数", self.args_field)
        runtime_form.addRow("工作目录", self._path_field_row(self.workdir_field, "浏览…", self._request_workdir_browse))
        runtime_form.addRow("截图目录", self._path_field_row(self.screenshot_field, "浏览…", self._request_screenshot_dir_browse))
        runtime_layout.addLayout(runtime_form)

        cover_row = QHBoxLayout()
        cover_row.addWidget(QLabel("海报封面"))
        cover_row.addStretch(1)
        self.change_cover_button = QPushButton("更换")
        self.crop_cover_button = QPushButton("裁剪导入")
        self.clear_cover_button = QPushButton("清除")
        for button in (self.change_cover_button, self.crop_cover_button, self.clear_cover_button):
            button.setObjectName("quietButton")
            cover_row.addWidget(button)
        runtime_layout.addLayout(cover_row)

        preview_row = QHBoxLayout()
        preview_row.addWidget(QLabel("悬停 GIF"))
        preview_row.addStretch(1)
        self.change_preview_button = QPushButton("更换")
        self.clear_preview_button = QPushButton("清除")
        for button in (self.change_preview_button, self.clear_preview_button):
            button.setObjectName("quietButton")
            preview_row.addWidget(button)
        runtime_layout.addLayout(preview_row)
        right.addWidget(runtime_card)
        right.addStretch(1)

        self.back_button.clicked.connect(self.back_requested.emit)
        self.launch_button.clicked.connect(self._request_launch)
        self.change_hero_button.clicked.connect(self._request_change_hero)
        self.clear_hero_button.clicked.connect(self._request_clear_hero)
        self.change_cover_button.clicked.connect(self._request_cover_change)
        self.crop_cover_button.clicked.connect(self._request_cover_crop)
        self.clear_cover_button.clicked.connect(self._request_cover_clear)
        self.change_preview_button.clicked.connect(self._request_preview_change)
        self.clear_preview_button.clicked.connect(self._request_preview_clear)
        self.media_list.itemClicked.connect(self._preview_media_item)
        self.media_list.itemDoubleClicked.connect(self._open_media_item)

        self.title_field.value_changed.connect(lambda value: self._emit_text_patch("title", value))
        self.series_field.value_changed.connect(lambda value: self._emit_text_patch("series", value))
        self.developer_field.value_changed.connect(lambda value: self._emit_text_patch("developer", value))
        self.publisher_field.value_changed.connect(lambda value: self._emit_text_patch("publisher", value))
        self.release_field.value_changed.connect(lambda value: self._emit_text_patch("release_date", value))
        self.tags_field.value_changed.connect(lambda value: self._emit_list_patch("tags", value))
        self.rating_editor.rating_changed.connect(lambda value: self._emit_patch(GameMetadataPatch(rating=value)))
        self.description_edit.editing_finished.connect(lambda value: self._emit_patch(GameMetadataPatch(description=value)))
        self.notes_edit.editing_finished.connect(lambda value: self._emit_patch(GameMetadataPatch(notes=value)))
        self.launch_field.value_changed.connect(lambda value: self._emit_text_patch("launch_exe", value))
        self.timing_field.value_changed.connect(lambda value: self._emit_text_patch("timing_exe", value))
        self.args_field.value_changed.connect(lambda value: self._emit_text_patch("launch_args", value))
        self.workdir_field.value_changed.connect(lambda value: self._emit_text_patch("working_directory", value))
        self.screenshot_field.value_changed.connect(lambda value: self._emit_text_patch("screenshot_directory", value))


    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._apply_responsive_layout(self.width())

    def _apply_responsive_layout(self, width: int) -> None:
        narrow = int(width) < 760
        self._pending_responsive_narrow = narrow
        if self._responsive_narrow is None or not self.isVisible():
            self._commit_responsive_layout(animated=False)
            return
        if narrow == self._responsive_narrow:
            self._responsive_timer.stop()
            return
        self._responsive_timer.start()

    def _commit_responsive_layout(self, *, animated: bool = True) -> None:
        narrow = self._pending_responsive_narrow
        if narrow is None or narrow == self._responsive_narrow:
            return
        direction = (
            QBoxLayout.Direction.TopToBottom
            if narrow
            else QBoxLayout.Direction.LeftToRight
        )

        def apply_change() -> None:
            self.columns_layout.setDirection(direction)
            self.hero_stats_layout.setDirection(direction)
            self.scroll_content.layout().activate()

        if animated and self._responsive_narrow is not None:
            animate_responsive_reflow(
                self.scroll.viewport(),
                apply_change,
                direction=1 if narrow else -1,
            )
        else:
            apply_change()
        self._responsive_narrow = narrow

    @staticmethod
    def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("gameArchiveCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("gameArchiveSectionTitle")
        layout.addWidget(title_label)
        return card, layout

    @staticmethod
    def _inline_field(*, word_wrap: bool = False) -> InlineEditableField:
        return InlineEditableField(
            display_object_name="gameArchiveEditableValue",
            editor_object_name="gameArchiveInlineEdit",
            word_wrap=word_wrap,
        )

    @staticmethod
    def _path_field_row(field: InlineEditableField, text: str, callback) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(field, 1)
        button = QPushButton(text)
        button.setObjectName("quietButton")
        button.clicked.connect(callback)
        layout.addWidget(button)
        return widget

    def set_record(self, record: GameRecord) -> None:
        self.record = record
        game = record.metadata
        self.title_field.set_value(game.title, fallback="未命名游戏")
        hero_bits = [value for value in (game.series, game.developer, game.release_date) if value]
        self.hero_meta_label.setText("  ·  ".join(hero_bits) or "本地游戏档案")
        self.play_time_label.setText(f"游玩 {_format_hours(game.total_play_seconds)}")
        self.rating_editor.set_rating(game.rating)
        self.install_label.setText("已安装" if record.installed else "仅档案")
        self.launch_button.setEnabled(record.installed)
        self.description_edit.set_value(game.description)
        self.notes_edit.set_value(game.notes)
        self.series_field.set_value(game.series, fallback="点击填写")
        self.developer_field.set_value(game.developer, fallback="点击填写")
        self.publisher_field.set_value(game.publisher, fallback="点击填写")
        self.release_field.set_value(game.release_date, fallback="点击填写")
        self.tags_field.set_value(" / ".join(game.tags), fallback="点击填写")
        self.play_summary_label.setText(f"累计 {_format_hours(game.total_play_seconds)}")
        sessions = sorted(game.sessions, key=lambda item: item.started_at, reverse=True)[:5]
        if sessions:
            lines = [
                f"{_format_dt(item.started_at)}  ·  {_format_duration_compact(item.duration_seconds)}"
                for item in sessions
            ]
            self.session_summary_label.setText("最近记录\n" + "\n".join(lines))
        else:
            self.session_summary_label.setText("暂无游玩记录。")

        self.launch_field.set_value(game.launch_exe, fallback="点击填写")
        self.timing_field.set_value(game.timing_exe, fallback="点击填写")
        self.args_field.set_value(game.launch_args, fallback="点击填写")
        self.workdir_field.set_value(game.working_directory, fallback="点击填写")
        self.screenshot_field.set_value(game.screenshot_directory, fallback="点击填写")
        self.clear_cover_button.setEnabled(bool(game.cover_path))
        self.clear_preview_button.setEnabled(bool(game.preview_gif_path))

        self._hero_source = resolve_game_archive_media(record, self.screenshot_service)
        self.hero.set_media(self._hero_source, animated=False)
        self.clear_hero_button.setEnabled(bool(game.archive_media_path))
        self._apply_media_tint(self._hero_source)
        self._refresh_media_list()

    def deactivate(self) -> None:
        self.hero.stop()

    def _refresh_media_list(self) -> None:
        self.media_list.clear()
        if self.record is None:
            self.media_status_label.setText("暂无媒体")
            return
        game = self.record.metadata
        paths: list[Path] = []
        seen: set[str] = set()
        for value in (game.archive_media_path, game.preview_gif_path):
            path = usable_archive_media_path(value)
            if path is not None:
                key = str(path.resolve())
                if key not in seen:
                    seen.add(key)
                    paths.append(path)
        if self.screenshot_service is not None:
            result = self.screenshot_service.list_images(game.screenshot_directory)
            if result.available:
                for item in result.items:
                    path = usable_archive_media_path(item.path)
                    if path is None:
                        continue
                    key = str(path.resolve())
                    if key not in seen:
                        seen.add(key)
                        paths.append(path)

        for path in paths:
            try:
                if self.screenshot_service is not None:
                    thumb = self.screenshot_service.thumbnail_for(game.uuid, path)
                    item = QListWidgetItem(QIcon(str(thumb)), path.name)
                else:
                    item = QListWidgetItem(path.name)
            except Exception:
                item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip("单击在上方预览，双击打开原图")
            item.setSizeHint(QSize(210, 142))
            self.media_list.addItem(item)
        self.media_status_label.setText(f"{len(paths)} 项图片 / GIF" if paths else "暂无图片 / GIF")

    def _preview_media_item(self, item: QListWidgetItem) -> None:
        path = usable_archive_media_path(item.data(Qt.ItemDataRole.UserRole))
        if path is None:
            return
        self.hero.set_media(path, animated=True)
        self._apply_media_tint(path)

    def _open_media_item(self, item: QListWidgetItem) -> None:
        path = usable_archive_media_path(item.data(Qt.ItemDataRole.UserRole))
        if path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _emit_text_patch(self, field: str, value: str) -> None:
        self._emit_patch(GameMetadataPatch(**{field: value}))

    def _emit_list_patch(self, field: str, value: str) -> None:
        self._emit_patch(GameMetadataPatch(**{field: _split_values(value)}))

    def _emit_patch(self, patch: GameMetadataPatch) -> None:
        if self.record is not None:
            self.metadata_patch_requested.emit(self.record.metadata.uuid, patch)

    def _request_launch(self) -> None:
        if self.record is not None:
            self.launch_requested.emit(self.record.metadata.uuid)

    def _request_change_hero(self) -> None:
        if self.record is not None:
            self.archive_media_change_requested.emit(self.record.metadata.uuid)

    def _request_clear_hero(self) -> None:
        if self.record is not None:
            self.archive_media_clear_requested.emit(self.record.metadata.uuid)

    def _request_cover_change(self) -> None:
        if self.record is not None:
            self.cover_change_requested.emit(self.record.metadata.uuid)

    def _request_cover_crop(self) -> None:
        if self.record is not None:
            self.cover_crop_requested.emit(self.record.metadata.uuid)

    def _request_cover_clear(self) -> None:
        if self.record is not None:
            self.cover_clear_requested.emit(self.record.metadata.uuid)

    def _request_preview_change(self) -> None:
        if self.record is not None:
            self.preview_change_requested.emit(self.record.metadata.uuid)

    def _request_preview_clear(self) -> None:
        if self.record is not None:
            self.preview_clear_requested.emit(self.record.metadata.uuid)

    def _request_launch_exe_browse(self) -> None:
        if self.record is not None:
            self.launch_exe_browse_requested.emit(self.record.metadata.uuid)

    def _request_timing_exe_browse(self) -> None:
        if self.record is not None:
            self.timing_exe_browse_requested.emit(self.record.metadata.uuid)

    def _request_workdir_browse(self) -> None:
        if self.record is not None:
            self.workdir_browse_requested.emit(self.record.metadata.uuid)

    def _request_screenshot_dir_browse(self) -> None:
        if self.record is not None:
            self.screenshot_dir_browse_requested.emit(self.record.metadata.uuid)

    def _apply_media_tint(self, path: Path | None) -> None:
        palette = self.scroll_content.palette()
        base = QColor(FlatTokens.BACKGROUND)
        sampled = _sample_media_color(path)
        if sampled is not None:
            blend = 0.11
            base = QColor(
                round(base.red() * (1.0 - blend) + sampled[0] * blend),
                round(base.green() * (1.0 - blend) + sampled[1] * blend),
                round(base.blue() * (1.0 - blend) + sampled[2] * blend),
            )
        palette.setColor(QPalette.ColorRole.Window, base)
        self.scroll_content.setAutoFillBackground(True)
        self.scroll_content.setPalette(palette)


def _sample_media_color(path: Path | None) -> tuple[int, int, int] | None:
    if path is None or not path.is_file():
        return None
    try:
        with Image.open(path) as image:
            image.seek(0)
            sample = image.convert("RGB")
            sample.thumbnail((48, 28), Image.Resampling.BILINEAR)
            stat = ImageStat.Stat(sample)
            return tuple(int(value) for value in stat.mean[:3])
    except (OSError, ValueError, EOFError):
        return None


def _split_values(value: str) -> list[str]:
    normalized = str(value or "").replace("，", ",").replace("/", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def _format_hours(duration_seconds: int) -> str:
    return f"{max(0, int(duration_seconds)) / 3600:.1f} 小时"


def _format_duration_compact(duration_seconds: int) -> str:
    total = max(0, int(duration_seconds))
    hours, remainder = divmod(total, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours} 小时 {minutes:02d} 分"
    return f"{minutes} 分"


def _format_dt(value) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M") if value else "—"
