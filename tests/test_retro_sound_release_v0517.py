from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_v0517_version_docs_and_sound_services_are_present():
    assert 'version = "0.5.0.17.1"' in read("pyproject.toml")
    assert 'RETRO_VERSION = "0.5.0.17.1"' in read("app/ui/retro_showcase.py")
    assert 'QLabel("v0.5.0.17.1")' in read("app/ui/app_chrome.py")
    assert "v0.5.0.17.1 · Retro Performance Hotfix" in read("app/bootstrap.py")
    assert (ROOT / "app/services/sound_pack_store.py").is_file()
    assert (ROOT / "app/services/audio_import_service.py").is_file()
    assert (ROOT / "app/services/ui_sound_service.py").is_file()
    assert (ROOT / "docs/Retro_Sound_Pack_System_Design_v0.5.0.17.md").is_file()
    assert (ROOT / "docs/Retro_Sound_Pack_System_Implementation_Plan_v0.5.0.17.md").is_file()
    assert (ROOT / "docs/development-logs/Retro_Sound_Pack_System_v0.5.0.17.md").is_file()
