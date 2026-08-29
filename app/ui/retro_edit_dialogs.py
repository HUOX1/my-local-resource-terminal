from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.game import GameMetadata, GameMetadataPatch
from app.models.movie import MovieMetadata, MovieMetadataPatch


def _split_terms(text: str) -> list[str]:
    normalized = text.replace("，", ",").replace("、", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


class _ArchiveEditDialog(QDialog):
    """Temporary Stage-1 archive editor shell.

    Stage 2 will move archive editing into the Retro scene. For Stage 1 this
    dialog is intentionally conventional, but its form is scrollable so it
    cannot grow beyond the user's available desktop height.
    """

    def _fit_initial_size(self, preferred_width: int, preferred_height: int) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(preferred_width, preferred_height)
            return
        available = screen.availableGeometry()
        width = min(preferred_width, max(520, available.width() - 120))
        height = min(preferred_height, max(440, available.height() - 120))
        self.resize(width, height)

    def _scroll_form(self, form: QFormLayout) -> QScrollArea:
        body = QWidget(self)
        body.setLayout(form)
        scroll = QScrollArea(self)
        scroll.setObjectName("archiveEditScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(body)
        return scroll

    def _path_row(self, edit: QLineEdit, callback) -> QWidget:
        widget = QWidget(self)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(edit, 1)
        button = QPushButton("浏览…", widget)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return widget

    def _buttons(self) -> QDialogButtonBox:
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        save = buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if save is not None:
            save.setText("保存")
            save.setObjectName("primaryButton")
        if cancel is not None:
            cancel.setText("取消")
            cancel.setObjectName("quietButton")
        buttons.rejected.connect(self.reject)
        return buttons


class RetroGameArchiveEditDialog(_ArchiveEditDialog):
    """Compatibility editor for the complete game archive metadata."""

    def __init__(self, game: GameMetadata, parent=None) -> None:
        super().__init__(parent)
        self.game = game
        self._result_patch: GameMetadataPatch | None = None
        self.setWindowTitle("编辑游戏档案")
        self.setMinimumSize(520, 440)
        self._fit_initial_size(720, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)
        heading = QLabel("编辑游戏档案", self)
        heading.setObjectName("dialogHeading")
        root.addWidget(heading)

        form = QFormLayout()
        form.setSpacing(10)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.title_edit = QLineEdit(game.title)
        self.series_edit = QLineEdit(game.series)
        self.developer_edit = QLineEdit(game.developer)
        self.publisher_edit = QLineEdit(game.publisher)
        self.release_edit = QLineEdit(game.release_date)
        self.tags_edit = QLineEdit(", ".join(game.tags))
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(0, 5)
        self.rating_spin.setValue(game.rating)
        self.description_edit = QTextEdit(game.description)
        self.description_edit.setMinimumHeight(92)
        self.notes_edit = QTextEdit(game.notes)
        self.notes_edit.setMinimumHeight(82)
        self.launch_edit = QLineEdit(game.launch_exe or "")
        self.timing_edit = QLineEdit(game.timing_exe or "")
        self.args_edit = QLineEdit(game.launch_args or "")
        self.workdir_edit = QLineEdit(game.working_directory or "")
        self.screenshot_edit = QLineEdit(game.screenshot_directory or "")

        form.addRow("游戏名称 *", self.title_edit)
        form.addRow("系列", self.series_edit)
        form.addRow("开发商", self.developer_edit)
        form.addRow("发行商", self.publisher_edit)
        form.addRow("发行日期", self.release_edit)
        form.addRow("标签", self.tags_edit)
        form.addRow("评分", self.rating_spin)
        form.addRow("作品介绍", self.description_edit)
        form.addRow("我的记录", self.notes_edit)
        form.addRow("启动 EXE", self._path_row(self.launch_edit, self._browse_launch))
        form.addRow("计时 EXE", self._path_row(self.timing_edit, self._browse_timing))
        form.addRow("启动参数", self.args_edit)
        form.addRow("工作目录", self._path_row(self.workdir_edit, self._browse_workdir))
        form.addRow("截图目录", self._path_row(self.screenshot_edit, self._browse_screenshots))
        root.addWidget(self._scroll_form(form), 1)

        buttons = self._buttons()
        buttons.accepted.connect(self._accept)
        root.addWidget(buttons)

    @property
    def result_patch(self) -> GameMetadataPatch:
        if self._result_patch is None:
            raise RuntimeError("dialog has no accepted result")
        return self._result_patch

    def _accept(self) -> None:
        title = self.title_edit.text().strip()
        if not title:
            self.title_edit.setFocus()
            return
        self._result_patch = GameMetadataPatch(
            title=title,
            series=self.series_edit.text().strip(),
            developer=self.developer_edit.text().strip(),
            publisher=self.publisher_edit.text().strip(),
            release_date=self.release_edit.text().strip(),
            tags=_split_terms(self.tags_edit.text()),
            rating=self.rating_spin.value(),
            description=self.description_edit.toPlainText().strip(),
            notes=self.notes_edit.toPlainText().strip(),
            launch_exe=self.launch_edit.text().strip(),
            timing_exe=self.timing_edit.text().strip(),
            launch_args=self.args_edit.text().strip(),
            working_directory=self.workdir_edit.text().strip(),
            screenshot_directory=self.screenshot_edit.text().strip(),
        )
        self.accept()

    def _browse_launch(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择启动 EXE",
            self.launch_edit.text(),
            "程序 (*.exe);;所有文件 (*)",
        )
        if not path:
            return
        previous = self.launch_edit.text().strip()
        self.launch_edit.setText(path)
        if not self.timing_edit.text().strip() or self.timing_edit.text().strip() == previous:
            self.timing_edit.setText(path)
        if not self.workdir_edit.text().strip():
            self.workdir_edit.setText(str(Path(path).parent))

    def _browse_timing(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择计时 EXE",
            self.timing_edit.text(),
            "程序 (*.exe);;所有文件 (*)",
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


class RetroMovieArchiveEditDialog(_ArchiveEditDialog):
    """Compatibility editor for movie archive metadata."""

    def __init__(self, movie: MovieMetadata, parent=None) -> None:
        super().__init__(parent)
        self.movie = movie
        self._result_patch: MovieMetadataPatch | None = None
        self.setWindowTitle("编辑影片档案")
        self.setMinimumSize(520, 440)
        self._fit_initial_size(700, 620)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)
        heading = QLabel("编辑影片档案", self)
        heading.setObjectName("dialogHeading")
        root.addWidget(heading)

        form = QFormLayout()
        form.setSpacing(10)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.code_edit = QLineEdit(movie.code)
        self.title_edit = QLineEdit(movie.title)
        self.cover_key_edit = QLineEdit(movie.cover_key)
        self.actors_edit = QLineEdit(", ".join(movie.actors))
        self.series_edit = QLineEdit(movie.series)
        self.studio_edit = QLineEdit(movie.studio)
        self.release_edit = QLineEdit(movie.release_date)
        self.tags_edit = QLineEdit(", ".join(movie.tags))
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(0, 5)
        self.rating_spin.setValue(movie.rating)
        self.watched_check = QCheckBox("已观看")
        self.watched_check.setChecked(movie.watched)
        self.notes_edit = QTextEdit(movie.notes)
        self.notes_edit.setMinimumHeight(110)

        form.addRow("编号", self.code_edit)
        form.addRow("标题", self.title_edit)
        form.addRow("封面键", self.cover_key_edit)
        form.addRow("演员", self.actors_edit)
        form.addRow("系列", self.series_edit)
        form.addRow("厂商", self.studio_edit)
        form.addRow("发行日期", self.release_edit)
        form.addRow("标签", self.tags_edit)
        form.addRow("评分", self.rating_spin)
        form.addRow("观看状态", self.watched_check)
        form.addRow("备注", self.notes_edit)
        root.addWidget(self._scroll_form(form), 1)

        buttons = self._buttons()
        buttons.accepted.connect(self._accept)
        root.addWidget(buttons)

    @property
    def result_patch(self) -> MovieMetadataPatch:
        if self._result_patch is None:
            raise RuntimeError("dialog has no accepted result")
        return self._result_patch

    def _accept(self) -> None:
        self._result_patch = MovieMetadataPatch(
            code=self.code_edit.text().strip(),
            title=self.title_edit.text().strip(),
            cover_key=self.cover_key_edit.text().strip(),
            actors=_split_terms(self.actors_edit.text()),
            series=self.series_edit.text().strip(),
            studio=self.studio_edit.text().strip(),
            release_date=self.release_edit.text().strip(),
            tags=_split_terms(self.tags_edit.text()),
            rating=self.rating_spin.value(),
            watched=self.watched_check.isChecked(),
            notes=self.notes_edit.toPlainText().strip(),
        )
        self.accept()
