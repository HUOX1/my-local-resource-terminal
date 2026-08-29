from __future__ import annotations

from PySide6.QtWidgets import QCheckBox

from app.services.sound_pack_backup_adapter import SoundPackBackupAdapter


def enhance_settings_dialog_with_soundpacks(dialog) -> None:
    """Inject the Sound Pack backup option into the legacy advanced-settings backup page."""
    if hasattr(dialog, "include_soundpacks_check"):
        return
    checkbox = QCheckBox("包含 Sound Packs")
    checkbox.setChecked(True)
    adapter = SoundPackBackupAdapter(dialog.backup_service, include_soundpacks=True)
    dialog.backup_service = adapter
    dialog.include_soundpacks_check = checkbox
    checkbox.toggled.connect(lambda checked: setattr(adapter, "include_soundpacks", bool(checked)))

    covers = getattr(dialog, "include_covers_check", None)
    parent = covers.parentWidget() if covers is not None else None
    layout = parent.layout() if parent is not None else None
    if layout is not None:
        index = layout.indexOf(covers)
        layout.insertWidget(max(0, index + 1), checkbox)
