from pathlib import Path
import pytest

from app.services.audio_import_service import AudioImportError, AudioImportService
from app.services.sound_pack_store import SoundPackStore


def test_wav_import_copies_original_and_publishes_mapping_without_ffmpeg(tmp_path: Path):
    source = tmp_path / "click.wav"
    source.write_bytes(b"RIFF" + b"\0" * 128)
    store = SoundPackStore(tmp_path / "soundpacks")
    pack = store.create_pack("mix")
    service = AudioImportService(store, ffmpeg_path="missing-ffmpeg")
    imported = service.import_for_event(pack.id, "focus", source)
    assert imported.original_path.read_bytes() == source.read_bytes()
    assert imported.original_path.name == "click.wav"
    assert store.load_mappings(pack.id)["focus"]["original"] == "click.wav"
    assert imported.runtime_path.name == "focus.wav"
    assert store.resolve_audio_path(pack.id, "focus") == imported.runtime_path


def test_non_wav_conversion_failure_preserves_previous_mapping(tmp_path: Path):
    store = SoundPackStore(tmp_path / "soundpacks")
    pack = store.create_pack("mix")
    old = pack.path / "audio" / "navigate.wav"
    old.write_bytes(b"old")
    store.set_mapping(pack.id, "navigate", old.name, "old.wav")
    source = tmp_path / "move.mp3"
    source.write_bytes(b"not-really-mp3")
    service = AudioImportService(store, ffmpeg_path=str(tmp_path / "does-not-exist"))
    with pytest.raises(AudioImportError):
        service.import_for_event(pack.id, "navigate", source)
    assert store.resolve_audio_path(pack.id, "navigate") == old
    assert store.load_mappings(pack.id)["navigate"]["original"] == "old.wav"


def test_mapping_persistence_failure_restores_previous_runtime_file(tmp_path: Path):
    class FailingStore(SoundPackStore):
        def __init__(self, root: Path):
            super().__init__(root)
            self.fail = False

        def set_mapping(self, pack_id: str, event: str, runtime_filename: str, original_filename: str) -> None:
            if self.fail:
                raise OSError("pack.json write failed")
            super().set_mapping(pack_id, event, runtime_filename, original_filename)

    store = FailingStore(tmp_path / "soundpacks")
    pack = store.create_pack("mix")
    old_runtime = pack.path / "audio" / "focus.wav"
    old_runtime.write_bytes(b"old-wave")
    old_original = pack.path / "originals" / "old.wav"
    old_original.write_bytes(b"old-source")
    store.set_mapping(pack.id, "focus", "focus.wav", "old.wav")
    store.fail = True

    source = tmp_path / "new.wav"
    source.write_bytes(b"RIFF" + b"n" * 128)
    service = AudioImportService(store, ffmpeg_path="missing")
    with pytest.raises(AudioImportError):
        service.import_for_event(pack.id, "focus", source)

    assert old_runtime.read_bytes() == b"old-wave"
    assert old_original.read_bytes() == b"old-source"
