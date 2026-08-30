from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_runtime_directories_are_g3_named():
    assert (ROOT / "g3_core").is_dir()
    assert (ROOT / "g3_launcher").is_dir()
    assert (ROOT / "g3_frontend").is_dir()
    assert (ROOT / "g3_tests").is_dir()
    assert (ROOT / "g3_tools").is_dir()
    assert not (ROOT / "terminal_core").exists()
    assert not (ROOT / "terminal_launcher").exists()
    assert not (ROOT / "godot_frontend").exists()
    assert not (ROOT / "terminal_tests").exists()
    assert not (ROOT / "terminal_tools").exists()


def test_root_launcher_invokes_g3_launcher():
    text = (ROOT / "run_windows.vbs").read_text(encoding="utf-8")
    assert "-m g3_launcher" in text
    assert "terminal_launcher" not in text


def test_python_package_name_and_script_are_g3():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "g3"' in text
    assert 'g3 = "g3_launcher.__main__:main"' in text
    assert 'testpaths = ["g3_tests"]' in text
