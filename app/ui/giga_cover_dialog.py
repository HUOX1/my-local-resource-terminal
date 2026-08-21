from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QMenu,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.cover_matching import movie_cover_keys, normalize_cover_match_text
from app.services.giga_cover_cropper import GigaCoverCandidate, GigaCoverCropper
from app.ui.manual_cover_crop_dialog import ManualCoverCropDialog


STATUS_LABELS = {
    "ready": "可自动处理",
    "single": "单张封面 / 跳过",
    "review": "需人工复核",
    "unreadable": "无法读取",
    "exists": "已有正式封面",
    "processed": "已处理",
    "failed": "失败",
}

STATUS_COLORS = {
    "ready": QColor(35, 120, 55),
    "processed": QColor(35, 120, 55),
    "review": QColor(170, 110, 20),
    "single": QColor(100, 100, 100),
    "exists": QColor(100, 100, 100),
    "unreadable": QColor(170, 45, 45),
    "failed": QColor(170, 45, 45),
}


class _CoverScanWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(list, int, int)
    failed = Signal(str)

    def __init__(
        self,
        cropper: GigaCoverCropper,
        source_dir: Path,
        output_dir: Path,
        *,
        margin_px: int,
        overwrite: bool,
        match_only: bool,
        movie_keys: list[str],
    ) -> None:
        super().__init__()
        self.cropper = cropper
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.margin_px = margin_px
        self.overwrite = overwrite
        self.match_only = match_only
        self.movie_keys = movie_keys
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            all_paths = self.cropper.iter_source_files(self.source_dir)
            if self.match_only:
                selected = [path for path in all_paths if _matches_movie_library(path.stem, self.movie_keys)]
            else:
                selected = list(all_paths)

            def on_progress(current: int, total: int) -> None:
                if self._cancelled:
                    raise RuntimeError("扫描已取消")
                current_name = selected[current - 1].name if 0 < current <= len(selected) else ""
                self.progress.emit(current, total, current_name)

            results = self.cropper.scan_directory(
                self.source_dir,
                self.output_dir,
                margin_px=self.margin_px,
                overwrite=self.overwrite,
                source_paths=selected,
                progress_callback=on_progress,
                use_cache=True,
            )
            self.finished.emit(results, len(all_paths), len(selected))
        except Exception as exc:
            self.failed.emit(str(exc))


class GigaCoverDialog(QDialog):
    covers_changed = Signal()

    def __init__(
        self,
        cover_dir: Path,
        cover_service=None,
        parent=None,
        *,
        source_dir: Path | None = None,
        margin_px: int = 0,
        catalog_service=None,
    ) -> None:
        super().__init__(parent)
        self.cover_dir = Path(cover_dir)
        self.cover_service = cover_service
        self.catalog_service = catalog_service
        self.source_dir = Path(source_dir) if source_dir else None
        self.initial_margin_px = max(0, min(int(margin_px), 50))
        self.cropper = GigaCoverCropper()
        self._results: list[GigaCoverCandidate] = []
        self._scan_thread: QThread | None = None
        self._scan_worker: _CoverScanWorker | None = None
        self.setWindowTitle("封面处理")
        self.resize(980, 650)
        self._build_ui()

    def closeEvent(self, event) -> None:
        if self._scan_worker is not None and self._scan_thread is not None and self._scan_thread.isRunning():
            self._scan_worker.cancel()
            self._scan_thread.quit()
            self._scan_thread.wait(3000)
        event.accept()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        intro = QLabel(
            "适用于左侧 Back / 中间 Spine / 右侧 Front 的完整 DVD 封面。"
            "Spine 可以是任意颜色或图案；程序根据结构分界提取右侧 Front，"
            "不会强制二次裁成固定比例。"
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.source_edit = QLineEdit(str(self.source_dir) if self.source_dir else "")
        self.output_edit = QLineEdit(str(self.cover_dir))
        form.addRow("原始封面目录", self._path_row(self.source_edit, self._browse_source))
        form.addRow("输出目录", self._path_row(self.output_edit, self._browse_output))
        root.addLayout(form)

        options = QHBoxLayout()
        options.addWidget(QLabel("Spine 右侧安全边距"))
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 50)
        self.margin_spin.setValue(self.initial_margin_px)
        self.margin_spin.setSuffix(" px")
        options.addWidget(self.margin_spin)
        self.overwrite_check = QCheckBox("覆盖已有正式封面")
        options.addWidget(self.overwrite_check)
        options.addStretch(1)
        root.addLayout(options)


        safety = QLabel(
            "安全规则：原图永不修改；源目录和输出目录不能相同；默认遇到已有正式封面会跳过。"
            "匹配模式下会先按电影标题 / 封面键 / 编号筛选文件名，再进入封面结构识别。"
        )
        safety.setWordWrap(True)
        root.addWidget(safety)

        actions = QHBoxLayout()
        self.scan_button = QPushButton("扫描预览")
        self.process_button = QPushButton("开始批量处理")
        self.process_button.setEnabled(False)
        close_button = QPushButton("关闭")
        actions.addWidget(self.scan_button)
        actions.addWidget(self.process_button)
        actions.addStretch(1)
        actions.addWidget(close_button)
        root.addLayout(actions)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["文件", "状态", "尺寸", "Spine", "Front 裁剪", "说明"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.doubleClicked.connect(lambda index: self._open_manual_crop(index.row()))
        self.table.customContextMenuRequested.connect(self._show_table_context_menu)
        root.addWidget(self.table, 1)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        root.addWidget(self.progress)
        self.summary_label = QLabel("尚未扫描")
        root.addWidget(self.summary_label)

        self.scan_button.clicked.connect(self._scan)
        self.process_button.clicked.connect(self._process)
        close_button.clicked.connect(self.accept)
        self.source_edit.textChanged.connect(self._invalidate_preview)
        self.output_edit.textChanged.connect(self._invalidate_preview)
        self.margin_spin.valueChanged.connect(self._invalidate_preview)
        self.overwrite_check.toggled.connect(self._invalidate_preview)

    def _path_row(self, edit: QLineEdit, callback) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(edit, 1)
        button = QPushButton("浏览…")
        button.clicked.connect(callback)
        layout.addWidget(button)
        return widget

    def _browse_source(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择原始完整封面目录", self.source_edit.text())
        if path:
            self.source_edit.setText(path)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择裁剪后封面输出目录", self.output_edit.text())
        if path:
            self.output_edit.setText(path)

    def _invalidate_preview(self, *_args) -> None:
        if self._results:
            self._results = []
            self.table.setRowCount(0)
            self.process_button.setEnabled(False)
            self.summary_label.setText("设置已改变，请重新“扫描预览”")

    def _validate_directories(self) -> tuple[Path, Path] | None:
        source_text = self.source_edit.text().strip()
        output_text = self.output_edit.text().strip()
        if not source_text or not output_text:
            QMessageBox.warning(self, "目录未设置", "请选择原始封面目录和输出目录。")
            return None
        source = Path(source_text)
        output = Path(output_text)
        if not source.is_dir():
            QMessageBox.warning(self, "原始目录无效", f"目录不存在：\n{source}")
            return None
        try:
            same = source.resolve() == output.resolve()
        except OSError:
            same = source.absolute() == output.absolute()
        if same:
            QMessageBox.warning(self, "目录不能相同", "原始封面目录和输出目录不能相同，以免覆盖原图。")
            return None
        output.mkdir(parents=True, exist_ok=True)
        return source, output

    def _scan(self) -> None:
        if self._scan_thread and self._scan_thread.isRunning():
            return
        directories = self._validate_directories()
        if directories is None:
            return
        source, output = directories
        movie_keys = self._movie_keys()
        self.scan_button.setEnabled(False)
        self.process_button.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.summary_label.setText("正在扫描封面目录，请稍候…")
        thread = QThread(self)
        worker = _CoverScanWorker(
            self.cropper,
            source,
            output,
            margin_px=self.margin_spin.value(),
            overwrite=self.overwrite_check.isChecked(),
            match_only=True,
            movie_keys=movie_keys,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._scan_progress)
        worker.finished.connect(self._scan_finished)
        worker.failed.connect(self._scan_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_scan_thread)
        self._scan_thread = thread
        self._scan_worker = worker
        thread.start()

    def _scan_progress(self, current: int, total: int, name: str) -> None:
        self.progress.setRange(0, max(1, total))
        self.progress.setValue(current)
        self.summary_label.setText(f"正在扫描 {current}/{total} · {name}")

    def _scan_finished(self, results: list, total_files: int, selected_files: int) -> None:
        self._results = list(results)
        self._render_results()
        ready = sum(item.status == "ready" for item in self._results)
        review = sum(item.status == "review" for item in self._results)
        skipped = sum(item.status in {"single", "exists"} for item in self._results)
        errors = sum(item.status in {"failed", "unreadable"} for item in self._results)
        prefix = f"目录共 {total_files} 张 · 匹配到库存候选 {selected_files} 张"
        self.summary_label.setText(
            f"{prefix} · 可自动处理 {ready} · 需复核 {review} · 跳过 {skipped} · 错误 {errors}"
        )
        self.progress.setVisible(False)
        self.scan_button.setEnabled(True)
        self.process_button.setEnabled(ready > 0)

    def _scan_failed(self, message: str) -> None:
        self.progress.setVisible(False)
        self.scan_button.setEnabled(True)
        self.process_button.setEnabled(False)
        self.summary_label.setText("扫描失败")
        QMessageBox.warning(self, "扫描失败", message or "封面扫描失败。")

    def _clear_scan_thread(self) -> None:
        self._scan_thread = None
        self._scan_worker = None

    def _movie_keys(self) -> list[str]:
        if self.catalog_service is None:
            return []
        try:
            records = self.catalog_service.list_movies(sort="title", descending=False)
        except Exception:
            return []
        return movie_cover_keys(records)

    def _process(self) -> None:
        ready_indexes = [i for i, item in enumerate(self._results) if item.status == "ready"]
        if not ready_indexes:
            return
        self.scan_button.setEnabled(False)
        self.process_button.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, len(ready_indexes))
        processed_count = 0
        failed_count = 0
        overwrite = self.overwrite_check.isChecked()
        try:
            for position, index in enumerate(ready_indexes, start=1):
                updated = self.cropper.process(self._results[index], overwrite=overwrite)
                self._results[index] = updated
                if updated.status == "processed":
                    processed_count += 1
                elif updated.status == "failed":
                    failed_count += 1
                self.progress.setValue(position)
                QApplication.processEvents()
        finally:
            self.scan_button.setEnabled(True)
            self.progress.setVisible(False)
        self._render_results()
        if processed_count:
            if self.cover_service is not None:
                self.cover_service.invalidate_index()
            self.covers_changed.emit()
        self.summary_label.setText(f"处理完成：成功 {processed_count} · 失败 {failed_count}")
        QMessageBox.information(
            self,
            "批量处理完成",
            f"成功提取 {processed_count} 张 Front 封面。\n"
            f"失败 {failed_count} 张。\n\n"
            "需人工复核和已跳过的图片没有被修改。",
        )

    def _show_table_context_menu(self, pos) -> None:
        item = self.table.itemAt(pos)
        if item is None:
            return
        row = item.row()
        if not self._manual_crop_allowed(row):
            return
        menu = QMenu(self)
        action = menu.addAction("手动裁剪…")
        selected = menu.exec(self.table.viewport().mapToGlobal(pos))
        if selected == action:
            self._open_manual_crop(row)

    def _manual_crop_allowed(self, row: int) -> bool:
        if not 0 <= row < len(self._results):
            return False
        result = self._results[row]
        return result.status != "unreadable" and result.source_path.is_file()

    def _open_manual_crop(self, row: int) -> None:
        if not self._manual_crop_allowed(row):
            return
        result = self._results[row]
        margin = self.margin_spin.value()
        initial_crop_x = None
        if result.crop_box is not None:
            initial_crop_x = max(0, result.crop_box[0] - margin)
        try:
            dialog = ManualCoverCropDialog(
                result.source_path,
                Path(self.output_edit.text().strip()),
                self.cropper,
                margin_px=margin,
                initial_crop_x=initial_crop_x,
                parent=self,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "无法打开图片", str(exc))
            return
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.saved_candidate is None:
            return
        self._results[row] = dialog.saved_candidate
        self._render_results()
        if self.cover_service is not None:
            self.cover_service.invalidate_index()
        self.covers_changed.emit()
        self.summary_label.setText(f"已手动裁剪：{result.source_path.name}")

    def _render_results(self) -> None:
        self.table.setRowCount(len(self._results))
        for row, result in enumerate(self._results):
            size = f"{result.width}×{result.height}" if result.width and result.height else "—"
            spine = (
                f"{result.spine_left}–{result.spine_right}px"
                if result.spine_left is not None and result.spine_right is not None
                else "—"
            )
            if result.crop_box and result.width and result.height:
                front_width = result.crop_box[2] - result.crop_box[0]
                crop = f"{front_width}×{result.height}"
            else:
                crop = "—"
            values = [
                result.source_path.name,
                STATUS_LABELS.get(result.status, result.status),
                size,
                spine,
                crop,
                result.message,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 1:
                    color = STATUS_COLORS.get(result.status)
                    if color:
                        item.setForeground(QBrush(color))
                self.table.setItem(row, column, item)


def _normalize_match_text(value: str) -> str:
    return normalize_cover_match_text(value)


def _matches_movie_library(file_stem: str, movie_keys: list[str]) -> bool:
    normalized_stem = _normalize_match_text(file_stem)
    if not normalized_stem:
        return False
    variants = {normalized_stem}
    # 支持 GIGA 这类 SPSA-01_01 / SPSA-01_02 分段命名。
    for separator in ("_", "-01", "-02", "-03"):
        if separator in file_stem:
            variants.add(_normalize_match_text(file_stem.split(separator)[0]))
    for key in movie_keys:
        normalized_key = _normalize_match_text(key)
        if not normalized_key:
            continue
        for variant in variants:
            if normalized_key in variant or variant in normalized_key:
                return True
    return False
