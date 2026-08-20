from pathlib import Path


def test_manual_crop_dialog_has_draggable_crop_line_and_live_preview() -> None:
    source = Path("app/ui/manual_cover_crop_dialog.py")
    assert source.exists(), "manual crop dialog module must exist"
    text = source.read_text(encoding="utf-8")
    assert "cropPositionChanged = Signal(int)" in text
    assert "mouseMoveEvent" in text
    assert "Front 起点" in text
    assert "安全边距" in text
    assert "保存封面" in text
    assert "_update_preview" in text


def test_cover_processing_dialog_opens_manual_crop_from_double_click_and_context_menu() -> None:
    text = Path("app/ui/giga_cover_dialog.py").read_text(encoding="utf-8")
    assert "ManualCoverCropDialog" in text
    assert "doubleClicked.connect" in text
    assert "customContextMenuRequested.connect" in text
    assert "手动裁剪" in text
    assert "_open_manual_crop" in text
