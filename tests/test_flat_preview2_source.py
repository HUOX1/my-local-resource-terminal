from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_flat_theme_defines_visual_roles_for_preview2():
    source = read('app/ui/flat_theme.py')
    for role in (
        'QLabel#sectionLabel',
        'QPushButton#primaryButton',
        'QPushButton#dangerButton',
        'QPushButton#quietButton',
        'QWidget#panelCard',
        'QLabel#previewFrame',
        'QLabel#dialogHeading',
    ):
        assert role in source


def test_main_window_uses_sidebar_sections_and_compact_game_action():
    source = read('app/ui/main_window.py')
    assert '媒体库' in source
    assert '系统' in source
    assert 'sectionLabel' in source
    assert 'self.add_game_button.setObjectName("statusActionButton")' in source


def test_settings_dialog_marks_notes_and_save_as_flat_roles():
    source = read('app/ui/settings_dialog.py')
    assert 'setObjectName("sectionLabel")' in source
    assert 'setObjectName("secondaryLabel")' in source
    assert 'StandardButton.Save' in source
    assert 'setObjectName("primaryButton")' in source


def test_detail_dialogs_mark_primary_and_danger_actions():
    movie = read('app/ui/movie_detail.py')
    game = read('app/ui/game_detail.py')
    assert 'self.play_button.setObjectName("primaryButton")' in movie
    assert 'self.delete_button.setObjectName("dangerButton")' in movie
    assert 'self.launch_button.setObjectName("primaryButton")' in game
    assert 'self.save_button.setObjectName("primaryButton")' in game
    assert 'self.media_preview_label.setObjectName("previewFrame")' in game
