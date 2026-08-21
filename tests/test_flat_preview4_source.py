from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_settings_dialog_localizes_save_and_cancel_buttons():
    source = read("app/ui/settings_dialog.py")
    assert 'save_button.setText("保存")' in source
    assert 'cancel_button.setText("取消")' in source
    assert 'cancel_button.setObjectName("quietButton")' in source


def test_game_edit_dialog_uses_flat_heading_sections_and_localized_actions():
    source = read("app/ui/game_edit_dialog.py")
    assert 'setObjectName("dialogHeading")' in source
    assert '"游戏与启动"' in source
    assert 'setObjectName("panelCard")' in source
    assert 'setObjectName("secondaryLabel")' in source
    assert 'save_button.setText("保存")' in source
    assert 'cancel_button.setText("取消")' in source


def test_movie_detail_uses_flat_cards_and_dialog_heading():
    source = read("app/ui/movie_detail.py")
    assert 'setObjectName("panelCard")' in source
    assert 'setObjectName("dialogHeading")' in source
    assert 'setObjectName("secondaryLabel")' in source


def test_flat_theme_has_dialog_section_title_role():
    source = read("app/ui/flat_theme.py")
    assert 'QLabel#dialogSectionTitle' in source
