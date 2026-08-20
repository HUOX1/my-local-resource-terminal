from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_silent_windows_launcher_uses_pythonw() -> None:
    launcher = ROOT / "run_windows.vbs"
    assert launcher.is_file()
    source = launcher.read_text(encoding="utf-8-sig").lower()
    assert "pythonw.exe" in source
    assert "windowstyle" not in source


def test_debug_batch_launcher_is_retained() -> None:
    debug = ROOT / "run_windows_debug.bat"
    assert debug.is_file()
    source = debug.read_text(encoding="utf-8").lower()
    assert "python.exe" in source
    assert "-m app.main" in source
