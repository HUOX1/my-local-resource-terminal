from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_retro_record_menu_exposes_archive_edit_for_both_domains():
    source = read("app/ui/retro_showcase.py")
    record_menu = source.split("def _show_record_menu", 1)[1].split("def _set_box_style", 1)[0]
    assert 'menu.addAction("编辑游戏档案…")' in record_menu
    assert 'menu.addAction("编辑影片档案…")' in record_menu
    assert "def _edit_current_game" in record_menu
    assert "def _edit_current_movie" in record_menu
    assert "game_catalog.update_game" in record_menu
    assert "catalog.update_metadata" in record_menu


def test_archive_editor_is_scrollable_and_does_not_restore_favorite_field():
    source = read("app/ui/retro_edit_dialogs.py")
    assert "QScrollArea" in source
    assert "setWidgetResizable(True)" in source
    assert "RetroGameArchiveEditDialog" in source
    assert "RetroMovieArchiveEditDialog" in source
    assert "favorite=" not in source
    assert "收藏" not in source


def test_local_gui_smoke_covers_archive_edit_dialogs():
    smoke = read("tests/test_retro_gui_smoke.py")
    runner = read("tools/retro_smoke_runner.py")
    assert "test_archive_edit_dialogs_build_scroll_and_metadata_patches" in smoke
    assert '"archive edit dialogs"' in runner
    assert "test_archive_edit_dialogs_build_scroll_and_metadata_patches" in runner


def test_stage1_a2_version_is_0510():
    assert 'version = "0.5.0.17.1"' in read("pyproject.toml")
    assert "v0.5.0.17" in read("app/bootstrap.py")
    assert "v0.5.0.17" in read("app/ui/app_chrome.py")
    assert 'RETRO_VERSION = "0.5.0.17.1"' in read("app/ui/retro_showcase.py")
