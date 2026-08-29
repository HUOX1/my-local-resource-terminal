from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


class SoundPackBackupAdapter:
    """Add Sound Pack assets around the existing backup service without replacing it."""

    def __init__(self, base_service, *, include_soundpacks: bool = True) -> None:
        self.base_service = base_service
        self.include_soundpacks = bool(include_soundpacks)

    def __getattr__(self, name: str):
        return getattr(self.base_service, name)

    def create_backup(self, settings, settings_path: Path, output_zip: Path, **kwargs):
        summary = self.base_service.create_backup(settings, settings_path, output_zip, **kwargs)
        if not self.include_soundpacks:
            return summary
        soundpacks = Path(settings.data_dir) / "soundpacks"
        if not soundpacks.is_dir():
            return summary
        backup_path = Path(getattr(summary, "path", output_zip))
        with zipfile.ZipFile(backup_path, "a", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for source in sorted(path for path in soundpacks.rglob("*") if path.is_file()):
                relative = source.relative_to(soundpacks).as_posix()
                archive.write(source, f"soundpacks/{relative}")
        return summary

    def restore_backup(self, settings, settings_path: Path, backup_zip: Path):
        summary = self.base_service.restore_backup(settings, settings_path, backup_zip)
        self._restore_soundpacks(Path(settings.data_dir), Path(backup_zip))
        return summary

    def _restore_soundpacks(self, data_dir: Path, backup_zip: Path) -> None:
        with zipfile.ZipFile(backup_zip) as archive:
            members = []
            for info in archive.infolist():
                if info.is_dir():
                    continue
                parts = PurePosixPath(info.filename.replace("\\", "/")).parts
                if not parts or parts[0] != "soundpacks":
                    continue
                if len(parts) < 2 or any(part in {"", ".", ".."} for part in parts):
                    continue
                if PurePosixPath(*parts).is_absolute() or ":" in parts[0]:
                    continue
                members.append((info, parts[1:]))
            if not members:
                return

            target_root = Path(data_dir) / "soundpacks"
            with tempfile.TemporaryDirectory(prefix="lrt-soundpacks-restore-") as temp_text:
                staged_root = Path(temp_text) / "soundpacks"
                for info, relative_parts in members:
                    target = staged_root.joinpath(*relative_parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info, "r") as source, target.open("wb") as destination:
                        shutil.copyfileobj(source, destination)
                for source in sorted(path for path in staged_root.rglob("*") if path.is_file()):
                    destination = target_root / source.relative_to(staged_root)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    temporary = destination.with_name(destination.name + ".restore")
                    shutil.copy2(source, temporary)
                    temporary.replace(destination)
