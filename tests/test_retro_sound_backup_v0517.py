from pathlib import Path
from types import SimpleNamespace
import zipfile

from app.services.sound_pack_backup_adapter import SoundPackBackupAdapter


class FakeBackupService:
    def create_backup(self, settings, settings_path, output_zip, **kwargs):
        with zipfile.ZipFile(output_zip, "w") as archive:
            archive.writestr("manifest.json", "{}")
        return SimpleNamespace(path=Path(output_zip))

    def restore_backup(self, settings, settings_path, backup_zip):
        return "restored"


def test_backup_adapter_includes_complete_soundpack_tree_by_default(tmp_path: Path):
    data_dir = tmp_path / "data"
    pack_file = data_dir / "soundpacks" / "abc" / "audio" / "navigate.wav"
    pack_file.parent.mkdir(parents=True)
    pack_file.write_bytes(b"wave")
    (data_dir / "soundpacks" / "abc" / "pack.json").write_text('{"name":"mix"}', encoding="utf-8")
    output = tmp_path / "backup.zip"
    adapter = SoundPackBackupAdapter(FakeBackupService())
    adapter.create_backup(SimpleNamespace(data_dir=data_dir), tmp_path / "settings.json", output)
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
    assert "soundpacks/abc/pack.json" in names
    assert "soundpacks/abc/audio/navigate.wav" in names


def test_restore_adapter_merges_soundpacks_after_base_restore(tmp_path: Path):
    data_dir = tmp_path / "data"
    backup = tmp_path / "backup.zip"
    with zipfile.ZipFile(backup, "w") as archive:
        archive.writestr("soundpacks/abc/pack.json", '{"name":"mix"}')
        archive.writestr("soundpacks/abc/originals/click.mp3", b"mp3")
    adapter = SoundPackBackupAdapter(FakeBackupService())
    result = adapter.restore_backup(SimpleNamespace(data_dir=data_dir), tmp_path / "settings.json", backup)
    assert result == "restored"
    assert (data_dir / "soundpacks" / "abc" / "pack.json").is_file()
    assert (data_dir / "soundpacks" / "abc" / "originals" / "click.mp3").read_bytes() == b"mp3"


def test_soundpack_backup_ui_contract_is_default_on_and_scene_agnostic():
    root = Path(__file__).resolve().parents[1]
    source = (root / "app/ui/sound_backup_ui.py").read_text(encoding="utf-8")
    bootstrap = (root / "app/bootstrap.py").read_text(encoding="utf-8")
    assert 'QCheckBox("包含 Sound Packs")' in source
    assert "setChecked(True)" in source
    assert "enhance_settings_dialog_with_soundpacks(dialog)" in bootstrap
