from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ui_sound_service_uses_qsoundeffect_and_separate_preview_channel():
    source = (ROOT / "app/services/ui_sound_service.py").read_text(encoding="utf-8")
    assert "QSoundEffect" in source
    assert "self._effects" in source
    assert "self._preview_effect" in source
    assert 'if event == "navigate"' in source
    assert ".stop()" in source and ".play()" in source


def test_public_playback_methods_are_failure_isolated():
    source = (ROOT / "app/services/ui_sound_service.py").read_text(encoding="utf-8")
    assert "def play(" in source
    assert "def preview(" in source
    assert "except Exception" in source
