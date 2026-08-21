from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QImageReader, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.services.giga_cover_cropper import GigaCoverCandidate, GigaCoverCropper


class CropSourcePreview(QWidget):
    cropPositionChanged = Signal(int)

    def __init__(self, image: QImage, crop_x: int, parent=None) -> None:
        super().__init__(parent)
        self.image = image
        self.crop_x = max(0, min(int(crop_x), max(0, image.width() - 1)))
        self.margin_px = 0
        self.setMinimumSize(480, 320)
        self.setMouseTracking(True)

    def set_crop_x(self, value: int) -> None:
        value = max(0, min(int(value), max(0, self.image.width() - 1)))
        if value == self.crop_x:
            return
        self.crop_x = value
        self.update()

    def set_margin(self, value: int) -> None:
        self.margin_px = max(0, int(value))
        self.update()

    def _target_rect(self) -> QRectF:
        if self.image.isNull() or self.width() <= 16 or self.height() <= 16:
            return QRectF()
        available = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        scale = min(available.width() / self.image.width(), available.height() / self.image.height())
        width = self.image.width() * scale
        height = self.image.height() * scale
        return QRectF(
            available.center().x() - width / 2,
            available.center().y() - height / 2,
            width,
            height,
        )

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(28, 28, 30))
        target = self._target_rect()
        if target.isEmpty():
            return
        painter.drawImage(target, self.image)
        boundary_x = target.left() + (self.crop_x / max(1, self.image.width())) * target.width()
        final_x = min(self.image.width() - 1, self.crop_x + self.margin_px)
        final_line_x = target.left() + (final_x / max(1, self.image.width())) * target.width()
        painter.setPen(QPen(QColor(255, 70, 70), 2))
        painter.drawLine(QPointF(boundary_x, target.top()), QPointF(boundary_x, target.bottom()))
        if final_x != self.crop_x:
            painter.setPen(QPen(QColor(255, 210, 70), 1, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(final_line_x, target.top()), QPointF(final_line_x, target.bottom()))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._set_from_mouse(event.position().x())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._set_from_mouse(event.position().x())

    def _set_from_mouse(self, mouse_x: float) -> None:
        target = self._target_rect()
        if target.isEmpty():
            return
        clamped = min(max(mouse_x, target.left()), target.right())
        ratio = (clamped - target.left()) / max(1.0, target.width())
        value = max(0, min(self.image.width() - 1, int(round(ratio * self.image.width()))))
        if value != self.crop_x:
            self.crop_x = value
            self.update()
            self.cropPositionChanged.emit(value)


class CropResultPreview(QWidget):
    def __init__(self, image: QImage, crop_left: int, parent=None) -> None:
        super().__init__(parent)
        self.image = image
        self.crop_left = crop_left
        self.setMinimumSize(260, 320)

    def set_crop_left(self, value: int) -> None:
        self.crop_left = max(0, min(int(value), max(0, self.image.width() - 1)))
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(28, 28, 30))
        if self.image.isNull():
            return
        left = max(0, min(self.crop_left, self.image.width() - 1))
        source = QRectF(left, 0, self.image.width() - left, self.image.height())
        available = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        scale = min(available.width() / source.width(), available.height() / source.height())
        width = source.width() * scale
        height = source.height() * scale
        target = QRectF(
            available.center().x() - width / 2,
            available.center().y() - height / 2,
            width,
            height,
        )
        painter.drawImage(target, self.image, source)


class ManualCoverCropDialog(QDialog):
    def __init__(
        self,
        source_path: Path,
        output_dir: Path,
        cropper: GigaCoverCropper,
        *,
        margin_px: int = 0,
        initial_crop_x: int | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.source_path = Path(source_path)
        self.output_dir = Path(output_dir)
        self.cropper = cropper
        self.saved_candidate: GigaCoverCandidate | None = None
        self.image = self._load_image(self.source_path)
        self.setWindowTitle(f"手动裁剪封面 - {self.source_path.name}")
        self.resize(1120, 720)

        if initial_crop_x is None:
            if self.image.width() < self.image.height():
                initial_crop_x = 0
            else:
                ratio = self.cropper.reference_front_ratio(self.output_dir)
                initial_crop_x = int(round(self.image.width() - ratio * self.image.height()))
        initial_crop_x = max(0, min(int(initial_crop_x), max(0, self.image.width() - 1)))
        self._build_ui(initial_crop_x, margin_px)
        self._update_preview()

    @staticmethod
    def _load_image(path: Path) -> QImage:
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            raise ValueError(reader.errorString() or f"无法读取图片：{path}")
        return image

    def _build_ui(self, initial_crop_x: int, margin_px: int) -> None:
        root = QVBoxLayout(self)
        tip = QLabel("拖动左侧预览中的红色竖线确定 Front 起点；黄色虚线表示加上安全边距后的实际裁剪位置。")
        tip.setWordWrap(True)
        root.addWidget(tip)

        previews = QHBoxLayout()
        left_box = QVBoxLayout()
        left_box.addWidget(QLabel("完整原图"))
        self.source_preview = CropSourcePreview(self.image, initial_crop_x)
        left_box.addWidget(self.source_preview, 1)
        previews.addLayout(left_box, 2)

        right_box = QVBoxLayout()
        right_box.addWidget(QLabel("最终 Front 预览"))
        self.result_preview = CropResultPreview(self.image, initial_crop_x + margin_px)
        right_box.addWidget(self.result_preview, 1)
        previews.addLayout(right_box, 1)
        root.addLayout(previews, 1)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Front 起点"))
        self.crop_spin = QSpinBox()
        self.crop_spin.setRange(0, max(0, self.image.width() - 1))
        self.crop_spin.setValue(initial_crop_x)
        self.crop_spin.setSuffix(" px")
        controls.addWidget(self.crop_spin)
        controls.addSpacing(18)
        controls.addWidget(QLabel("安全边距"))
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 50)
        self.margin_spin.setValue(max(0, min(int(margin_px), 50)))
        self.margin_spin.setSuffix(" px")
        controls.addWidget(self.margin_spin)
        controls.addStretch(1)
        self.size_label = QLabel()
        controls.addWidget(self.size_label)
        root.addLayout(controls)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("取消")
        save = QPushButton("保存封面")
        save.setDefault(True)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        root.addLayout(buttons)

        self.source_preview.cropPositionChanged.connect(self.crop_spin.setValue)
        self.crop_spin.valueChanged.connect(self.source_preview.set_crop_x)
        self.crop_spin.valueChanged.connect(self._update_preview)
        self.margin_spin.valueChanged.connect(self._update_preview)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)

    def _update_preview(self, *_args) -> None:
        crop_x = self.crop_spin.value()
        margin = self.margin_spin.value()
        final_left = min(self.image.width() - 1, crop_x + margin)
        self.source_preview.set_margin(margin)
        self.result_preview.set_crop_left(final_left)
        front_width = self.image.width() - final_left
        self.size_label.setText(
            f"实际裁剪：x={final_left} · 输出 {front_width}×{self.image.height()}"
        )

    def _save(self) -> None:
        overwrite = False
        candidate = self.cropper.manual_candidate(
            self.source_path,
            self.output_dir,
            crop_x=self.crop_spin.value(),
            margin_px=self.margin_spin.value(),
            overwrite=False,
        )
        if candidate.status == "exists":
            answer = QMessageBox.question(
                self,
                "正式封面已存在",
                f"{candidate.output_path.name} 已存在。\n\n是否覆盖这个影片现有的正式封面？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            overwrite = True
            candidate = self.cropper.manual_candidate(
                self.source_path,
                self.output_dir,
                crop_x=self.crop_spin.value(),
                margin_px=self.margin_spin.value(),
                overwrite=True,
            )
        if candidate.status != "ready":
            QMessageBox.warning(self, "无法裁剪", candidate.message or "当前裁剪参数无效。")
            return

        result = self.cropper.process(candidate, overwrite=overwrite)
        if result.status != "processed":
            QMessageBox.warning(self, "保存失败", result.message or "无法写出封面。")
            return
        self.saved_candidate = result
        self.accept()
