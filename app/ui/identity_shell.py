from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMovie, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.models.identity import LocalIdentity
from app.services.identity_service import IdentityService
from app.ui.sidebar_motion import sidebar_text_progress
from app.ui.flat_theme import FlatTokens


class IdentityAvatarWidget(QWidget):
    clicked = Signal()

    def __init__(self, size: int = 160, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._identity: LocalIdentity | None = None
        self._username = ""
        self._avatar = QPixmap()
        self._frame = QPixmap()
        self._movie: QMovie | None = None

    def set_identity(self, identity: LocalIdentity | None, service: IdentityService) -> None:
        self._identity = identity
        self._username = identity.username if identity else ""
        avatar_path = service.avatar_path(identity) if identity else None
        frame_path = service.frame_path(identity) if identity else None
        self._set_paths(avatar_path, frame_path)

    def set_preview(self, username: str, avatar_path: Path | None, frame_path: Path | None) -> None:
        self._identity = None
        self._username = username.strip()
        self._set_paths(avatar_path, frame_path)

    def _set_paths(self, avatar_path: Path | None, frame_path: Path | None) -> None:
        if self._movie is not None:
            self._movie.stop()
            self._movie.deleteLater()
            self._movie = None
        self._avatar = QPixmap()
        self._frame = QPixmap()
        if avatar_path and avatar_path.is_file():
            if avatar_path.suffix.casefold() == ".gif":
                movie = QMovie(str(avatar_path))
                movie.frameChanged.connect(lambda _frame: self.update())
                movie.start()
                self._movie = movie
            else:
                self._avatar = QPixmap(str(avatar_path))
        if frame_path and frame_path.is_file():
            self._frame = QPixmap(str(frame_path))
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        clip = QPainterPath()
        clip.addEllipse(rect)

        painter.save()
        painter.setClipPath(clip)
        painter.fillRect(rect, QColor(FlatTokens.SURFACE_RAISED))
        pixmap = self._movie.currentPixmap() if self._movie is not None else self._avatar
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                int(rect.width()),
                int(rect.height()),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = int(rect.x() + (rect.width() - scaled.width()) / 2)
            y = int(rect.y() + (rect.height() - scaled.height()) / 2)
            painter.drawPixmap(x, y, scaled)
        else:
            painter.setPen(QColor(FlatTokens.ACCENT_SOFT_TEXT))
            font = painter.font()
            font.setBold(True)
            font.setPointSize(max(14, int(rect.width() / 4.5)))
            painter.setFont(font)
            fallback = self._username[:1].upper() if self._username else "●"
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, fallback)
        painter.restore()

        painter.setPen(QPen(QColor(FlatTokens.BORDER_STRONG), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect)
        if not self._frame.isNull():
            painter.drawPixmap(self.rect(), self._frame)


class IdentityShellWidget(QWidget):
    identity_created = Signal(object)
    enter_requested = Signal()
    identity_changed = Signal(object)

    def __init__(self, identity_service: IdentityService, parent=None) -> None:
        super().__init__(parent)
        self.identity_service = identity_service
        self.setObjectName("identityShell")
        self._avatar_source: Path | None = None
        self._frame_source: Path | None = None
        self._build_ui()
        identity = self.identity_service.load()
        if identity is None:
            self.show_setup_state()
        else:
            self.show_entry_state(identity)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(48, 40, 48, 40)
        outer.addStretch(1)

        self.stack = QStackedWidget()
        self.stack.setMaximumWidth(520)
        self.stack.setObjectName("identityShellStack")
        outer.addWidget(self.stack, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)

        setup = QWidget()
        setup.setObjectName("identityShellCard")
        setup_layout = QVBoxLayout(setup)
        setup_layout.setContentsMargins(38, 34, 38, 34)
        setup_layout.setSpacing(14)
        setup_title = QLabel("建立本地身份")
        setup_title.setObjectName("identityShellTitle")
        setup_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        setup_layout.addWidget(setup_title)
        setup_note = QLabel("这是进入你本地收藏终端的身份标记，不是在线账号。")
        setup_note.setObjectName("secondaryLabel")
        setup_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        setup_note.setWordWrap(True)
        setup_layout.addWidget(setup_note)

        self.setup_avatar = IdentityAvatarWidget(150)
        setup_layout.addWidget(self.setup_avatar, 0, Qt.AlignmentFlag.AlignHCenter)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("用户名")
        self.username_edit.textChanged.connect(self._refresh_setup_preview)
        setup_layout.addWidget(self.username_edit)

        asset_row = QHBoxLayout()
        self.choose_avatar_button = QPushButton("选择头像")
        self.choose_frame_button = QPushButton("选择头像框")
        asset_row.addWidget(self.choose_avatar_button)
        asset_row.addWidget(self.choose_frame_button)
        setup_layout.addLayout(asset_row)
        self.create_button = QPushButton("建立身份")
        self.create_button.setObjectName("primaryButton")
        setup_layout.addWidget(self.create_button)
        self.stack.addWidget(setup)

        entry = QWidget()
        entry.setObjectName("identityShellCard")
        entry_layout = QVBoxLayout(entry)
        entry_layout.setContentsMargins(44, 42, 44, 42)
        entry_layout.setSpacing(10)
        self.entry_avatar = IdentityAvatarWidget(184)
        entry_layout.addWidget(self.entry_avatar, 0, Qt.AlignmentFlag.AlignHCenter)
        self.entry_username = QLabel()
        self.entry_username.setObjectName("identityEntryName")
        self.entry_username.setAlignment(Qt.AlignmentFlag.AlignCenter)
        entry_layout.addWidget(self.entry_username)
        self.enter_hint = QLabel("点击头像进入")
        self.enter_hint.setObjectName("secondaryLabel")
        self.enter_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        entry_layout.addWidget(self.enter_hint)
        self.stack.addWidget(entry)

        self.choose_avatar_button.clicked.connect(self._choose_avatar)
        self.choose_frame_button.clicked.connect(self._choose_frame)
        self.create_button.clicked.connect(self._create_identity)
        self.entry_avatar.clicked.connect(self.enter_requested.emit)

    def show_setup_state(self) -> None:
        self._avatar_source = None
        self._frame_source = None
        self.username_edit.clear()
        self.setup_avatar.set_preview("", None, None)
        self.stack.setCurrentIndex(0)

    def show_entry_state(self, identity: LocalIdentity) -> None:
        self.entry_avatar.set_identity(identity, self.identity_service)
        self.entry_username.setText(identity.username)
        self.stack.setCurrentIndex(1)

    def refresh_identity(self, identity: LocalIdentity) -> None:
        self.show_entry_state(identity)
        self.identity_changed.emit(identity)

    def _refresh_setup_preview(self) -> None:
        self.setup_avatar.set_preview(self.username_edit.text(), self._avatar_source, self._frame_source)

    def _choose_avatar(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "选择头像", "", "头像 (*.png *.jpg *.jpeg *.gif)")
        if filename:
            self._avatar_source = Path(filename)
            self._refresh_setup_preview()

    def _choose_frame(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "选择头像框", "", "PNG 头像框 (*.png)")
        if filename:
            self._frame_source = Path(filename)
            self._refresh_setup_preview()

    def _create_identity(self) -> None:
        try:
            identity = self.identity_service.create_or_update(
                self.username_edit.text(),
                self._avatar_source,
                self._frame_source,
            )
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "无法建立身份", str(exc))
            return
        self.identity_created.emit(identity)
        self.show_entry_state(identity)


class IdentitySidebarRoom(QWidget):
    edit_requested = Signal()

    def __init__(self, identity_service: IdentityService, parent=None) -> None:
        super().__init__(parent)
        self.identity_service = identity_service
        self.setObjectName("identitySidebarRoom")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(66)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(9)
        self.avatar = IdentityAvatarWidget(48)
        layout.addWidget(self.avatar)
        self.text_container = QWidget()
        self._text_opacity_effect = QGraphicsOpacityEffect(self.text_container)
        self._text_opacity_effect.setOpacity(1.0)
        self.text_container.setGraphicsEffect(self._text_opacity_effect)
        self._motion_progress = 1.0
        texts = QVBoxLayout(self.text_container)
        texts.setContentsMargins(0, 0, 0, 0)
        texts.setSpacing(1)
        self.name_label = QLabel("本地身份")
        self.name_label.setObjectName("identitySidebarName")
        self.kind_label = QLabel("LOCAL IDENTITY")
        self.kind_label.setObjectName("identitySidebarKind")
        texts.addWidget(self.name_label)
        texts.addWidget(self.kind_label)
        layout.addWidget(self.text_container, 1)
        self._layout = layout
        identity = self.identity_service.load()
        if identity is not None:
            self.set_identity(identity)

    def set_identity(self, identity: LocalIdentity) -> None:
        self.name_label.setText(identity.username)
        self.avatar.set_identity(identity, self.identity_service)

    def set_compact(self, compact: bool) -> None:
        self._motion_progress = 0.0 if compact else 1.0
        self._text_opacity_effect.setOpacity(0.0 if compact else 1.0)
        self.text_container.setVisible(not compact)
        self.text_container.setMaximumWidth(0 if compact else 16777215)
        self._layout.setContentsMargins(4 if compact else 8, 8, 4 if compact else 8, 8)
        self._layout.setAlignment(
            self.avatar,
            Qt.AlignmentFlag.AlignHCenter if compact else Qt.AlignmentFlag.AlignVCenter,
        )

    def set_motion_progress(self, progress: float) -> None:
        self._motion_progress = max(0.0, min(1.0, float(progress)))
        self._apply_motion_progress()

    def _apply_motion_progress(self) -> None:
        progress = self._motion_progress
        text_progress = sidebar_text_progress(progress)
        effect = self._text_opacity_effect
        self.text_container.setVisible(progress > 0.0)
        effect.setOpacity(text_progress)

        compact_left = max(4, round((self.width() - self.avatar.width()) / 2.0))
        left = round(compact_left + (8 - compact_left) * progress)
        right = round(4 + 4 * progress)
        self._layout.setContentsMargins(left, 8, right, 8)
        self._layout.setAlignment(self.avatar, Qt.AlignmentFlag.AlignVCenter)

        spacing = self._layout.spacing()
        available = max(0, self.width() - left - right - self.avatar.width() - spacing)
        self.text_container.setMaximumWidth(available)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        if 0.0 < self._motion_progress < 1.0:
            self._apply_motion_progress()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.edit_requested.emit()
        super().mouseReleaseEvent(event)


class IdentityEditDialog(QDialog):
    identity_changed = Signal(object)

    def __init__(self, identity_service: IdentityService, parent=None) -> None:
        super().__init__(parent)
        self.identity_service = identity_service
        self.identity = self.identity_service.load()
        self._avatar_source: Path | None = None
        self._frame_source: Path | None = None
        self._clear_avatar_requested = False
        self._clear_frame_requested = False
        self.setWindowTitle("我的身份")
        self.resize(500, 560)
        self._build_ui()
        self._load_identity()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        title = QLabel("我的身份")
        title.setObjectName("dialogHeading")
        layout.addWidget(title)
        self.avatar = IdentityAvatarWidget(140)
        layout.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignHCenter)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("用户名")
        self.username_edit.textChanged.connect(self._refresh_preview)
        layout.addWidget(self.username_edit)

        row = QHBoxLayout()
        choose_avatar = QPushButton("选择头像")
        clear_avatar = QPushButton("清除头像")
        choose_frame = QPushButton("选择头像框")
        clear_frame = QPushButton("清除头像框")
        row.addWidget(choose_avatar)
        row.addWidget(clear_avatar)
        row.addWidget(choose_frame)
        row.addWidget(clear_frame)
        layout.addLayout(row)
        layout.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        layout.addWidget(buttons)

        choose_avatar.clicked.connect(self._choose_avatar)
        choose_frame.clicked.connect(self._choose_frame)
        clear_avatar.clicked.connect(self._clear_avatar)
        clear_frame.clicked.connect(self._clear_frame)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

    def _load_identity(self) -> None:
        self.identity = self.identity_service.load()
        if self.identity is None:
            return
        self.username_edit.setText(self.identity.username)
        self.avatar.set_identity(self.identity, self.identity_service)

    def _refresh_preview(self) -> None:
        if self.identity is None:
            self.avatar.set_preview(self.username_edit.text(), self._avatar_source, self._frame_source)
            return
        avatar_path = None if self._clear_avatar_requested else (self._avatar_source or self.identity_service.avatar_path(self.identity))
        frame_path = None if self._clear_frame_requested else (self._frame_source or self.identity_service.frame_path(self.identity))
        self.avatar.set_preview(self.username_edit.text(), avatar_path, frame_path)

    def _choose_avatar(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "选择头像", "", "头像 (*.png *.jpg *.jpeg *.gif)")
        if filename:
            self._avatar_source = Path(filename)
            self._clear_avatar_requested = False
            self._refresh_preview()

    def _choose_frame(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "选择头像框", "", "PNG 头像框 (*.png)")
        if filename:
            self._frame_source = Path(filename)
            self._clear_frame_requested = False
            self._refresh_preview()

    def _clear_avatar(self) -> None:
        if self.identity_service.load() is None:
            return
        self._avatar_source = None
        self._clear_avatar_requested = True
        self._refresh_preview()

    def _clear_frame(self) -> None:
        if self.identity_service.load() is None:
            return
        self._frame_source = None
        self._clear_frame_requested = True
        self._refresh_preview()

    def _save(self) -> None:
        try:
            identity = self.identity_service.create_or_update(
                self.username_edit.text(),
                self._avatar_source,
                self._frame_source,
            )
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "无法保存身份", str(exc))
            return
        if self._clear_avatar_requested:
            identity = self.identity_service.clear_avatar()
        if self._clear_frame_requested:
            identity = self.identity_service.clear_frame()
        self.identity_changed.emit(identity)
        self.accept()
