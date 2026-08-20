from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.models.game import GameMetadata


@dataclass(frozen=True, slots=True)
class GameEditResult:
    title: str
    series: str
    developer: str
    publisher: str
    release_date: str
    tags: list[str]
    rating: int
    favorite: bool
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


class GameEditDialog(QDialog):
    def __init__(self, game: GameMetadata | None = None, parent=None) -> None:
        super().__init__(parent)
        self.game = game
        self._cover_source: Path | None = None
        self._preview_source: Path | None = None
        self._remove_cover = False
        self._remove_preview = False
        self._result: GameEditResult | None = None
        self._hidden_series = game.series if game else ""
        self._hidden_developer = game.developer if game else ""
        self._hidden_publisher = game.publisher if game else ""
        self._hidden_release_date = game.release_date if game else ""
        self._hidden_tags = list(game.tags) if game else []
        self._hidden_favorite = bool(game.favorite) if game else False
        self._hidden_notes = game.notes if game else ""
        self.setWindowTitle("编辑游戏" if game else "添加游戏")
        self.resize(680, 620)
        self._build_ui()
        if game:
            self._load_game(game)

    @property
    def result_data(self) -> GameEditResult:
        if self._result is None:
            raise RuntimeError("dialog has no accepted result")
        return self._result

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        heading = QLabel("编辑游戏" if self.game else "添加游戏")
        heading.setObjectName("dialogHeading")
        root.addWidget(heading)
        subtitle = QLabel("先填写能让游戏启动和计时的必要信息；其他档案内容可之后在游戏档案里补充。")
        subtitle.setObjectName("secondaryLabel")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        card, card_layout = self._section_card(
            "游戏与启动",
            "游戏名称、启动 EXE 和计时 EXE 为必填项。",
        )
        form = QFormLayout()
        form.setSpacing(10)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        self.title_edit = QLineEdit()
        self.launch_edit = QLineEdit()
        self.timing_edit = QLineEdit()
        self.args_edit = QLineEdit()
        self.workdir_edit = QLineEdit()
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(0, 5)

        form.addRow("游戏名称 *", self.title_edit)
        form.addRow("启动 EXE *", self._path_row(self.launch_edit, self._browse_launch))
        form.addRow("计时 EXE *", self._path_row(self.timing_edit, self._browse_timing))
        form.addRow("启动参数", self.args_edit)
        form.addRow("工作目录", self._path_row(self.workdir_edit, self._browse_workdir, directory=True))
        form.addRow("评分", self.rating_spin)

        self.cover_edit = QLineEdit()
        self.cover_edit.setReadOnly(True)
        self.preview_edit = QLineEdit()
        self.preview_edit.setReadOnly(True)
        self.screenshot_edit = QLineEdit()
        form.addRow("静态封面", self._path_row(self.cover_edit, self._browse_cover, clear_callback=self._clear_cover))
        form.addRow(
            "GIF 动态预览",
            self._path_row(self.preview_edit, self._browse_preview, clear_callback=self._clear_preview),
        )
        form.addRow("截图目录", self._path_row(self.screenshot_edit, self._browse_screenshots, directory=True))
        card_layout.addLayout(form)
        root.addWidget(card, 1)

        note = QLabel("游戏 EXE 完全由你手动选择；程序不会扫描目录或自动猜测启动文件。")
        note.setWordWrap(True)
        note.setObjectName("secondaryLabel")
        root.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_button is not None:
            save_button.setText("保存")
            save_button.setObjectName("primaryButton")
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button is not None:
            cancel_button.setText("取消")
            cancel_button.setObjectName("quietButton")
        buttons.accepted.connect(self._accept_validated)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _section_card(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        card = QWidget()
        card.setObjectName("panelCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("dialogSectionTitle")
        layout.addWidget(title_label)
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("secondaryLabel")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)
        return card, layout

    def _path_row(self, edit: QLineEdit, callback, *, directory: bool = False, clear_callback=None) -> QWidget:
        widget = QWidget()
        widget.setMinimumWidth(0)
        edit.setMinimumWidth(0)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(edit, 1)
        button = QPushButton("浏览…")
        button.clicked.connect(callback)
        layout.addWidget(button)
        if clear_callback is not None:
            clear_button = QPushButton("清除")
            clear_button.clicked.connect(clear_callback)
            layout.addWidget(clear_button)
        return widget

    def _load_game(self, game: GameMetadata) -> None:
        self.title_edit.setText(game.title)
        self.rating_spin.setValue(game.rating)
        self.launch_edit.setText(game.launch_exe)
        self.timing_edit.setText(game.timing_exe)
        self.args_edit.setText(game.launch_args)
        self.workdir_edit.setText(game.working_directory)
        self.cover_edit.setText(game.cover_path or "")
        self.preview_edit.setText(game.preview_gif_path or "")
        self.screenshot_edit.setText(game.screenshot_directory or "")

    def _browse_launch(self) -> None:
        previous = self.launch_edit.text().strip()
        path, _ = QFileDialog.getOpenFileName(self, "选择启动 EXE", previous, "程序 (*.exe);;所有文件 (*)")
        if not path:
            return
        self.launch_edit.setText(path)
        if not self.timing_edit.text().strip() or self.timing_edit.text().strip() == previous:
            self.timing_edit.setText(path)
        if not self.workdir_edit.text().strip() or (previous and self.workdir_edit.text().strip() == str(Path(previous).parent)):
            self.workdir_edit.setText(str(Path(path).parent))

    def _browse_timing(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择计时 EXE", self.timing_edit.text(), "程序 (*.exe);;所有文件 (*)")
        if path:
            self.timing_edit.setText(path)

    def _browse_workdir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择工作目录", self.workdir_edit.text())
        if path:
            self.workdir_edit.setText(path)

    def _browse_cover(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择游戏封面", "", "图片 (*.jpg *.jpeg *.png *.webp *.bmp)")
        if path:
            self._cover_source = Path(path)
            self._remove_cover = False
            self.cover_edit.setText(path)

    def _browse_preview(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 GIF 动态预览", "", "GIF 动图 (*.gif)")
        if path:
            self._preview_source = Path(path)
            self._remove_preview = False
            self.preview_edit.setText(path)

    def _clear_cover(self) -> None:
        self._cover_source = None
        self._remove_cover = bool(self.game and self.game.cover_path)
        self.cover_edit.clear()

    def _clear_preview(self) -> None:
        self._preview_source = None
        self._remove_preview = bool(self.game and self.game.preview_gif_path)
        self.preview_edit.clear()

    def _browse_screenshots(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择截图目录", self.screenshot_edit.text())
        if path:
            self.screenshot_edit.setText(path)

    def _accept_validated(self) -> None:
        title = self.title_edit.text().strip()
        launch = self.launch_edit.text().strip()
        timing = self.timing_edit.text().strip()
        if not title or not launch or not timing:
            QMessageBox.information(self, "信息不完整", "游戏名称、启动 EXE 和计时 EXE 为必填项。")
            return
        workdir = self.workdir_edit.text().strip() or str(Path(launch).parent)
        screenshot = self.screenshot_edit.text().strip()
        self._result = GameEditResult(
            title=title,
            series=self._hidden_series,
            developer=self._hidden_developer,
            publisher=self._hidden_publisher,
            release_date=self._hidden_release_date,
            tags=list(self._hidden_tags),
            rating=self.rating_spin.value(),
            favorite=self._hidden_favorite,
            notes=self._hidden_notes,
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
        self.accept()

