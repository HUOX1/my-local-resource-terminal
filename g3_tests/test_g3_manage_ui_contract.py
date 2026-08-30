from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / "g3_frontend/scripts/main.gd").read_text(encoding="utf-8")
MENU = (ROOT / "g3_frontend/scripts/manage_menu.gd").read_text(encoding="utf-8")
DIALOG = (ROOT / "g3_frontend/scripts/launch_profile_dialog.gd").read_text(encoding="utf-8")


def test_right_click_manage_menu_exposes_game_actions():
    for label in ("启动", "预览", "编辑资料", "媒体素材", "启动设置", "移除收藏"):
        assert label in MENU
    assert "main_case_right_clicked" in (ROOT / "g3_frontend/scripts/game_carousel.gd").read_text(encoding="utf-8")
    assert "_on_manage_action_requested" in MAIN


def test_launch_profile_dialog_exposes_all_profile_fields():
    for token in (
        "profile_type", "_launch_exe", "_launch_args", "_working_directory",
        "_content_path", "_monitor_exe", "_wait_timeout", "_run_as_admin",
    ):
        assert token in DIALOG
    assert "{content}" in DIALOG
    assert 'game.launch_profile.get' in MAIN
    assert 'game.launch_profile.update' in MAIN


def test_preview_is_discoverable_by_click_and_manage_menu():
    assert "_on_main_case_clicked" in MAIN
    assert '"preview"' in MENU
    assert '"preview":' in MAIN
