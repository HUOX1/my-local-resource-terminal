from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_retro_sound_settings_are_scene_native_and_persisted():
    source = read("app/ui/retro_showcase.py")
    assert '"retro/sound_enabled"' in source
    assert '"retro/sound_pack_id"' in source
    assert '"retro/sound_volume"' in source
    assert 'self._system_page = "settings"' in source
    assert 'self._system_action_rects["sound_manage"]' in source
    assert "QFileDialog.getOpenFileName" in source
    assert "SoundPackStore" in source
    assert "AudioImportService" in source
    assert "UISoundService" in source


def test_sound_mapping_page_has_seven_semantic_rows_and_pack_management():
    source = read("app/ui/retro_showcase.py")
    assert "SOUND_EVENT_LABELS" in source
    for event in ("navigate", "select", "focus", "confirm", "back", "open_panel", "close_panel"):
        assert f'"{event}"' in source
    assert 'sound_pack_create' in source
    assert 'sound_pack_duplicate' in source
    assert 'sound_pack_rename' in source
    assert 'sound_pack_delete' in source
    assert 'sound_import:' in source
    assert 'sound_preview:' in source
    assert 'sound_clear:' in source


def test_semantic_sounds_attach_to_actions_not_animation_frames():
    source = read("app/ui/retro_showcase.py")
    assert 'self._play_ui_sound("navigate")' in source
    assert 'self._play_ui_sound("select")' in source
    assert 'self._play_ui_sound("focus")' in source
    assert 'self._play_ui_sound("confirm")' in source
    assert 'self._play_ui_sound("back")' in source
    assert 'self._play_ui_sound("open_panel")' in source
    assert 'self._play_ui_sound("close_panel")' in source
    arc_setter = source.split("def _set_arc_position", 1)[1].split("arcPosition = Property", 1)[0]
    assert "_play_ui_sound" not in arc_setter


def test_sound_environment_rebinds_after_advanced_settings_change():
    source = read("app/ui/retro_showcase.py")
    bootstrap = read("app/bootstrap.py")
    assert "def refresh_sound_environment(self)" in source
    assert "retro.refresh_sound_environment()" in bootstrap
