from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_visible_windows_entry_remains_run_windows_vbs():
    text=(ROOT/"run_windows.vbs").read_text(encoding="utf-8"); assert "-m g3_launcher" in text; assert "-m app.main" not in text; assert ".venv\\Scripts\\pythonw.exe" in text
def test_debug_entry_runs_same_v06_launcher():
    assert "-m g3_launcher" in (ROOT/"run_windows_debug.bat").read_text(encoding="utf-8")
def test_g3_dependencies_include_local_websocket():
    text=(ROOT/"pyproject.toml").read_text(encoding="utf-8"); assert 'version = "0.6.1"' in text; assert '"websockets>=15,<16"' in text; assert 'g3 = "g3_launcher.__main__:main"' in text
