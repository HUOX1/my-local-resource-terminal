import pytest

pytest.importorskip("PySide6")

from pathlib import Path

from app.ui.giga_cover_dialog import GigaCoverDialog


def test_dialog_defaults_output_to_central_cover_directory(qtbot, tmp_path: Path):
    cover_dir = tmp_path / "covers"
    dialog = GigaCoverDialog(cover_dir)
    qtbot.addWidget(dialog)

    assert dialog.output_edit.text() == str(cover_dir)
    assert dialog.margin_spin.value() == 3
    assert dialog.overwrite_check.isChecked() is False
    assert dialog.process_button.isEnabled() is False


def test_dialog_restores_source_directory_and_margin(qtbot, tmp_path: Path):
    cover_dir = tmp_path / "covers"
    source_dir = tmp_path / "raw"
    dialog = GigaCoverDialog(cover_dir, source_dir=source_dir, margin_px=0)
    qtbot.addWidget(dialog)

    assert dialog.windowTitle() == "封面处理"
    assert dialog.source_edit.text() == str(source_dir)
    assert dialog.margin_spin.value() == 0
