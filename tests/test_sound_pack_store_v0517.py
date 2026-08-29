from pathlib import Path
import pytest

from app.services.sound_pack_store import SOUND_EVENTS, SoundPackStore


def test_create_map_duplicate_rename_delete_pack(tmp_path: Path):
    store = SoundPackStore(tmp_path / "soundpacks")
    pack = store.create_pack("我的 PS 混搭")
    assert pack.path.exists()
    assert (pack.path / "originals").is_dir()
    assert (pack.path / "audio").is_dir()
    assert store.load_mappings(pack.id) == {}

    store.set_mapping(pack.id, "navigate", "navigate.wav", "RE3_move.mp3")
    assert store.load_mappings(pack.id)["navigate"]["audio"] == "navigate.wav"

    copied = store.duplicate_pack(pack.id, "副本")
    assert store.load_mappings(copied.id)["navigate"]["original"] == "RE3_move.mp3"

    renamed = store.rename_pack(copied.id, "MGS")
    assert renamed.name == "MGS"
    store.delete_pack(renamed.id)
    assert {p.id for p in store.list_packs()} == {pack.id}


def test_pack_names_and_mapping_paths_cannot_escape_root(tmp_path: Path):
    store = SoundPackStore(tmp_path / "soundpacks")
    with pytest.raises(ValueError):
        store.create_pack("../outside")
    pack = store.create_pack("safe")
    with pytest.raises(ValueError):
        store.set_mapping(pack.id, "navigate", "../escape.wav", "source.wav")
    with pytest.raises(ValueError):
        store.set_mapping(pack.id, "unknown", "x.wav", "source.wav")


def test_sound_event_contract_is_exact():
    assert SOUND_EVENTS == (
        "navigate", "select", "focus", "confirm", "back", "open_panel", "close_panel"
    )
