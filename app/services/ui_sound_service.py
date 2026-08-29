from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect

from app.services.sound_pack_store import SOUND_EVENTS, SoundPackStore


class UISoundService(QObject):
    def __init__(self, store: SoundPackStore, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.enabled = False
        self.active_pack_id: str | None = None
        self.volume = 0.70
        self._effects: dict[str, QSoundEffect] = {}
        self._preview_effect = QSoundEffect(self)
        self._preview_effect.setLoopCount(1)
        self._preview_effect.setVolume(self.volume)

    def configure(self, enabled: bool, active_pack_id: str | None, volume: float) -> None:
        self.enabled = bool(enabled)
        self.active_pack_id = str(active_pack_id).strip() if active_pack_id else None
        self.volume = max(0.0, min(float(volume), 1.0))
        self._preview_effect.setVolume(self.volume)
        self.reload_pack()

    def reload_pack(self) -> None:
        try:
            for effect in self._effects.values():
                effect.stop()
                effect.deleteLater()
            self._effects.clear()
            if not self.active_pack_id:
                return
            for event in SOUND_EVENTS:
                path = self.store.resolve_audio_path(self.active_pack_id, event)
                if path is None:
                    continue
                effect = QSoundEffect(self)
                effect.setLoopCount(1)
                effect.setVolume(self.volume)
                effect.setSource(QUrl.fromLocalFile(str(path.resolve())))
                self._effects[event] = effect
        except Exception:
            self._effects.clear()

    def play(self, event: str) -> None:
        if not self.enabled or event not in SOUND_EVENTS:
            return
        try:
            effect = self._effects.get(event)
            if effect is None:
                return
            navigate = self._effects.get("navigate")
            if event == "navigate":
                effect.stop()
                effect.play()
                return
            if navigate is not None:
                navigate.stop()
            effect.stop()
            effect.play()
        except Exception:
            return

    def preview(self, path: Path) -> None:
        try:
            candidate = Path(path)
            if not candidate.is_file():
                return
            self._preview_effect.stop()
            self._preview_effect.setVolume(self.volume)
            self._preview_effect.setSource(QUrl.fromLocalFile(str(candidate.resolve())))
            self._preview_effect.play()
        except Exception:
            return

    def stop_preview(self) -> None:
        try:
            self._preview_effect.stop()
        except Exception:
            return
