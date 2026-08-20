from pathlib import Path


def test_settings_dialog_uses_category_navigation_and_stacked_pages():
    source = Path('app/ui/settings_dialog.py').read_text(encoding='utf-8')

    assert 'QStackedWidget' in source
    assert 'settingsCategoryButton' in source
    assert 'self.settings_stack' in source
    assert '_set_settings_page' in source
    assert '常规' in source
    assert '影片库' in source
    assert '播放' in source
    assert '备份' in source


def test_flat_theme_styles_settings_category_buttons():
    source = Path('app/ui/flat_theme.py').read_text(encoding='utf-8')

    assert 'QPushButton#settingsCategoryButton' in source
    assert 'QWidget#settingsNav' in source
    assert 'QWidget#settingsPage' in source
