from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_game_add_dialog_remains_resizable_and_wraps_long_rows():
    source = read("app/ui/game_edit_dialog.py")
    assert "QFormLayout.RowWrapPolicy.WrapLongRows" in source
    assert "setFixedSize" not in source
    assert "setFixedWidth" not in source


def test_flat_preview_displays_exact_four_part_version():
    source = read("app/ui/main_window.py")
    assert 'self.setWindowTitle("本地资源终端 · v0.4.3.1.1")' in source

    pyproject = read("pyproject.toml")
    assert 'version = "0.4.3.1.1"' in pyproject
