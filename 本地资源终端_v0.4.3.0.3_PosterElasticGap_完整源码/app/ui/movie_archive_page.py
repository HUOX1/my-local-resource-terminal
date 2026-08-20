from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QBoxLayout,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.movie import MovieMetadataPatch, MovieRecord
from app.ui.motion import animate_responsive_reflow, pulse_opacity, transition_stack_page


class _ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class InlineEditableField(QWidget):
    value_changed = Signal(str)

    def __init__(
        self,
        *,
        display_object_name: str = "movieArchiveEditableValue",
        editor_object_name: str = "movieArchiveInlineEdit",
        word_wrap: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._value = ""
        self._fallback = "—"
        self.stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stack)

        self.display = _ClickableLabel()
        self.display.setObjectName(display_object_name)
        self.display.setWordWrap(word_wrap)
        self.display.setCursor(Qt.CursorShape.IBeamCursor)
        self.display.setToolTip("点击修改")
        self.stack.addWidget(self.display)

        self.editor = QLineEdit()
        self.editor.setObjectName(editor_object_name)
        self.editor.setToolTip("Enter 或移开焦点保存")
        self.stack.addWidget(self.editor)

        self.display.clicked.connect(self.begin_edit)
        self.editor.editingFinished.connect(self.finish_edit)
        self.stack.setCurrentWidget(self.display)

    def set_value(self, value: str | None, *, fallback: str = "—") -> None:
        self._value = str(value or "")
        self._fallback = fallback
        self.display.setText(self._value or self._fallback)
        if self.stack.currentWidget() is not self.editor:
            self.editor.setText(self._value)

    def begin_edit(self) -> None:
        self.editor.setText(self._value)
        transition_stack_page(self.stack, self.editor, duration_ms=110, slide_px=0)
        self.editor.setFocus(Qt.FocusReason.MouseFocusReason)
        self.editor.selectAll()

    def finish_edit(self) -> None:
        if self.stack.currentWidget() is not self.editor:
            return
        value = self.editor.text().strip()
        transition_stack_page(self.stack, self.display, direction=-1, duration_ms=110, slide_px=0)
        if value != self._value:
            self.value_changed.emit(value)


class StarRatingEditor(QWidget):
    rating_changed = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rating = 0
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        self.buttons: list[QPushButton] = []
        for value in range(1, 6):
            button = QPushButton("☆")
            button.setObjectName("movieArchiveStarButton")
            button.setToolTip(f"{value} 星；再次点击当前评分可清零")
            button.clicked.connect(lambda _checked=False, score=value: self._choose(score))
            layout.addWidget(button)
            self.buttons.append(button)
        layout.addStretch(1)

    def set_rating(self, rating: int) -> None:
        self._rating = max(0, min(5, int(rating)))
        for index, button in enumerate(self.buttons, start=1):
            button.setText("★" if index <= self._rating else "☆")

    def _choose(self, score: int) -> None:
        new_rating = 0 if score == self._rating else score
        if new_rating == self._rating:
            return
        self.set_rating(new_rating)
        pulse_opacity(self.buttons[score - 1])
        self.rating_changed.emit(new_rating)


class _NotesEditor(QTextEdit):
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


class MovieArchivePage(QWidget):
    COVER_WIDTH = 280

    back_requested = Signal()
    play_requested = Signal(str)
    metadata_patch_requested = Signal(str, object)
    cover_change_requested = Signal(str)
    open_folder_requested = Signal(str)
    relink_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.record: MovieRecord | None = None
        self.setObjectName("movieArchivePage")
        self._build_ui()
        self._responsive_narrow: bool | None = None
        self._pending_responsive_narrow: bool | None = None
        self._responsive_timer = QTimer(self)
        self._responsive_timer.setSingleShot(True)
        self._responsive_timer.setInterval(90)
        self._responsive_timer.timeout.connect(self._commit_responsive_layout)

    @property
    def movie_uuid(self) -> str | None:
        return self.record.metadata.uuid if self.record is not None else None

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        nav = QHBoxLayout()
        nav.setContentsMargins(0, 0, 0, 0)
        self.back_button = QPushButton("←")
        self.back_button.setObjectName("movieArchiveBackButton")
        self.back_button.setToolTip("返回影片库")
        nav.addWidget(self.back_button)
        nav.addStretch(1)
        root.addLayout(nav)

        scroll = QScrollArea()
        scroll.setObjectName("movieArchiveScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll, 1)
        self.scroll = scroll

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("movieArchiveContent")
        scroll.setWidget(self.scroll_content)
        content = QVBoxLayout(self.scroll_content)
        content.setContentsMargins(2, 2, 8, 16)
        content.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("movieArchiveHero")
        hero_layout = QHBoxLayout(hero)
        self.hero_layout = hero_layout
        hero_layout.setContentsMargins(18, 18, 18, 18)
        hero_layout.setSpacing(22)
        content.addWidget(hero)

        cover_column = QVBoxLayout()
        cover_column.setSpacing(8)
        self.cover_label = QLabel("无封面")
        self.cover_label.setObjectName("movieArchiveCover")
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setFixedSize(self.COVER_WIDTH, 390)
        cover_column.addWidget(self.cover_label, 0, Qt.AlignmentFlag.AlignTop)
        self.change_cover_button = QPushButton("更换封面")
        self.change_cover_button.setObjectName("quietButton")
        cover_column.addWidget(self.change_cover_button)
        hero_layout.addLayout(cover_column)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(10)
        self.title_field = InlineEditableField(
            display_object_name="movieArchiveTitle",
            editor_object_name="movieArchiveTitleEdit",
            word_wrap=True,
        )
        hero_text.addWidget(self.title_field)
        self.code_field = InlineEditableField(
            display_object_name="movieArchiveMeta",
            editor_object_name="movieArchiveInlineEdit",
        )
        hero_text.addWidget(self.code_field)

        self.rating_editor = StarRatingEditor()
        hero_text.addWidget(self.rating_editor)

        self.play_time_label = QLabel()
        self.play_time_label.setObjectName("movieArchiveStat")
        hero_text.addWidget(self.play_time_label)

        self.availability_label = QLabel()
        self.availability_label.setObjectName("movieArchiveMutedText")
        hero_text.addWidget(self.availability_label)
        hero_text.addStretch(1)

        actions = QHBoxLayout()
        self.play_button = QPushButton("▶ 播放影片")
        self.play_button.setObjectName("primaryButton")
        actions.addWidget(self.play_button)
        actions.addStretch(1)
        hero_text.addLayout(actions)
        hero_layout.addLayout(hero_text, 1)

        columns = QHBoxLayout()
        self.columns_layout = columns
        columns.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(16)
        right = QVBoxLayout()
        right.setSpacing(16)
        columns.addLayout(left, 3)
        columns.addLayout(right, 2)
        content.addLayout(columns)

        info_card, info_layout = self._card("影片资料")
        info_form = QFormLayout()
        info_form.setContentsMargins(0, 2, 0, 0)
        info_form.setSpacing(9)
        self.cover_key_field = self._inline_field()
        self.actors_field = self._inline_field(word_wrap=True)
        self.series_field = self._inline_field()
        self.studio_field = self._inline_field()
        self.release_field = self._inline_field()
        self.tags_field = self._inline_field(word_wrap=True)
        self.subtitle_label = self._value_label()
        info_form.addRow("封面键", self.cover_key_field)
        info_form.addRow("演员", self.actors_field)
        info_form.addRow("系列", self.series_field)
        info_form.addRow("厂商", self.studio_field)
        info_form.addRow("发行日期", self.release_field)
        info_form.addRow("标签", self.tags_field)
        info_form.addRow("字幕", self.subtitle_label)
        info_layout.addLayout(info_form)
        left.addWidget(info_card)

        notes_card, notes_layout = self._card("我的记录")
        self.notes_edit = _NotesEditor()
        self.notes_edit.setObjectName("movieArchiveNotesEdit")
        self.notes_edit.setPlaceholderText("点击这里记录观后感、版本信息或其他个人备注…")
        self.notes_edit.setToolTip("移开焦点自动保存")
        self.notes_edit.setMinimumHeight(92)
        notes_layout.addWidget(self.notes_edit)
        left.addWidget(notes_card)

        media_card, media_layout = self._card("本地媒体")
        self.media_summary_label = QLabel()
        self.media_summary_label.setObjectName("movieArchiveBodyText")
        self.media_summary_label.setWordWrap(True)
        self.media_summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        media_layout.addWidget(self.media_summary_label)
        self.path_label = QLabel()
        self.path_label.setObjectName("movieArchivePath")
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        media_layout.addWidget(self.path_label)
        media_actions = QHBoxLayout()
        self.open_folder_button = QPushButton("打开目录")
        self.open_folder_button.setObjectName("quietButton")
        self.relink_button = QPushButton("关联本地文件")
        self.relink_button.setObjectName("quietButton")
        media_actions.addWidget(self.open_folder_button)
        media_actions.addWidget(self.relink_button)
        media_actions.addStretch(1)
        media_layout.addLayout(media_actions)
        right.addWidget(media_card)

        right.addStretch(1)

        destructive = QHBoxLayout()
        destructive.addStretch(1)
        self.delete_button = QPushButton("删除影片档案")
        self.delete_button.setObjectName("dangerButton")
        destructive.addWidget(self.delete_button)
        content.addLayout(destructive)
        content.addStretch(1)

        self.back_button.clicked.connect(self.back_requested.emit)
        self.play_button.clicked.connect(self._request_play)
        self.change_cover_button.clicked.connect(self._request_cover_change)
        self.open_folder_button.clicked.connect(self._request_open_folder)
        self.relink_button.clicked.connect(self._request_relink)
        self.delete_button.clicked.connect(self._request_delete)

        self.title_field.value_changed.connect(lambda value: self._emit_text_patch("title", value))
        self.code_field.value_changed.connect(lambda value: self._emit_text_patch("code", value))
        self.cover_key_field.value_changed.connect(lambda value: self._emit_text_patch("cover_key", value))
        self.actors_field.value_changed.connect(lambda value: self._emit_list_patch("actors", value))
        self.series_field.value_changed.connect(lambda value: self._emit_text_patch("series", value))
        self.studio_field.value_changed.connect(lambda value: self._emit_text_patch("studio", value))
        self.release_field.value_changed.connect(lambda value: self._emit_text_patch("release_date", value))
        self.tags_field.value_changed.connect(lambda value: self._emit_list_patch("tags", value))
        self.rating_editor.rating_changed.connect(lambda value: self._emit_patch(MovieMetadataPatch(rating=value)))
        self.notes_edit.editing_finished.connect(
            lambda value: self._emit_patch(MovieMetadataPatch(notes=value))
        )


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
        # Wait until the resize gesture settles so the breakpoint transition
        # is seen as one deliberate reflow rather than layout thrashing.
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
            self.hero_layout.setDirection(direction)
            self.columns_layout.setDirection(direction)
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
        card.setObjectName("movieArchiveCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        heading = QLabel(title)
        heading.setObjectName("movieArchiveSectionTitle")
        layout.addWidget(heading)
        return card, layout

    @staticmethod
    def _value_label(*, wrap: bool = False) -> QLabel:
        label = QLabel()
        label.setObjectName("movieArchiveValue")
        label.setWordWrap(wrap)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    @staticmethod
    def _inline_field(*, word_wrap: bool = False) -> InlineEditableField:
        return InlineEditableField(word_wrap=word_wrap)

    def set_record(self, record: MovieRecord) -> None:
        self.record = record
        movie = record.metadata
        runtime = record.runtime
        title_fallback = movie.code or movie.cover_key or "未命名影片"
        code_fallback = movie.cover_key or "本地影片档案"
        self.title_field.set_value(movie.title, fallback=title_fallback)
        self.code_field.set_value(movie.code, fallback=code_fallback)
        self.rating_editor.set_rating(movie.rating)
        self.play_time_label.setText(f"累计播放 {_format_hours(movie.total_play_seconds)}")

        available = bool(
            runtime.availability_status == "available"
            and runtime.video_path
            and Path(runtime.video_path).is_file()
        )
        self.play_button.setEnabled(available)
        self.open_folder_button.setEnabled(available)
        self.availability_label.setText("本地可播放" if available else "仅档案 / 当前无本地视频")

        self.cover_key_field.set_value(movie.cover_key, fallback="点击填写")
        self.actors_field.set_value(" / ".join(movie.actors), fallback="点击填写")
        self.series_field.set_value(movie.series, fallback="点击填写")
        self.studio_field.set_value(movie.studio, fallback="点击填写")
        self.release_field.set_value(movie.release_date, fallback="点击填写")
        self.tags_field.set_value(" / ".join(movie.tags), fallback="点击填写")
        self.subtitle_label.setText("有字幕" if runtime.subtitle_status else "无字幕")
        self.notes_edit.set_value(movie.notes)

        self.media_summary_label.setText(_format_media_summary(record))
        self.path_label.setText(runtime.video_path or "当前没有关联的本地影片文件。")
        self._show_cover(runtime.cover_path)

    def _show_cover(self, path: str | None) -> None:
        pixmap = QPixmap(path) if path and Path(path).is_file() else QPixmap()
        if pixmap.isNull():
            self.cover_label.setPixmap(QPixmap())
            self.cover_label.setText("无封面")
            self.cover_label.setFixedSize(self.COVER_WIDTH, 390)
            return
        scaled = pixmap.scaledToWidth(
            self.COVER_WIDTH,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.cover_label.setText("")
        self.cover_label.setFixedSize(scaled.size())
        self.cover_label.setPixmap(scaled)

    def _emit_text_patch(self, field: str, value: str) -> None:
        self._emit_patch(MovieMetadataPatch(**{field: value}))

    def _emit_list_patch(self, field: str, value: str) -> None:
        self._emit_patch(MovieMetadataPatch(**{field: _split_values(value)}))

    def _emit_patch(self, patch: MovieMetadataPatch) -> None:
        if self.record is not None:
            self.metadata_patch_requested.emit(self.record.metadata.uuid, patch)

    def _request_play(self) -> None:
        if self.record is not None:
            self.play_requested.emit(self.record.metadata.uuid)

    def _request_cover_change(self) -> None:
        if self.record is not None:
            self.cover_change_requested.emit(self.record.metadata.uuid)

    def _request_open_folder(self) -> None:
        if self.record is not None:
            self.open_folder_requested.emit(self.record.metadata.uuid)

    def _request_relink(self) -> None:
        if self.record is not None:
            self.relink_requested.emit(self.record.metadata.uuid)

    def _request_delete(self) -> None:
        if self.record is not None:
            self.delete_requested.emit(self.record.metadata.uuid)


def _split_values(text: str) -> list[str]:
    normalized = text.replace(",", "/").replace("，", "/").replace("、", "/")
    return [item.strip() for item in normalized.split("/") if item.strip()]


def _format_media_summary(record: MovieRecord) -> str:
    runtime = record.runtime
    resolution = f"{runtime.width}×{runtime.height}" if runtime.width and runtime.height else "未知分辨率"
    duration = _fmt_duration(runtime.duration)
    codecs = " / ".join(item for item in (runtime.video_codec, runtime.audio_codec) if item) or "未知编码"
    size = _fmt_file_size(runtime.file_size)
    return f"{resolution}  ·  {duration}\n{codecs}  ·  {size}"


def _format_hours(duration_seconds: int) -> str:
    return f"{max(0, int(duration_seconds)) / 3600:.1f} 小时"


def _fmt_duration(seconds: float | None) -> str:
    if seconds is None:
        return "未知时长"
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _fmt_file_size(value: int | None) -> str:
    if value is None or value < 0:
        return "未知大小"
    size = float(value)
    units = ["B", "KB", "MB", "GB", "TB"]
    unit = units[0]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            break
        size /= 1024
    return f"{size:.1f} {unit}"
