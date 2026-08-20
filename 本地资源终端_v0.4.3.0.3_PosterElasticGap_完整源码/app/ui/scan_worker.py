from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot


class ScanWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, scanner, settings) -> None:
        super().__init__()
        self.scanner = scanner
        self.settings = settings

    @Slot()
    def run(self) -> None:
        try:
            summary = self.scanner.scan(self.settings)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(summary)
