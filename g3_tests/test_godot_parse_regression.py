from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'g3_frontend' / 'scripts'


def test_entry_scripts_do_not_require_global_custom_class_cache():
    main = (ROOT / 'main.gd').read_text(encoding='utf-8')
    carousel = (ROOT / 'game_carousel.gd').read_text(encoding='utf-8')
    forbidden = ('TerminalBackendClient','GameCarousel3D','PreviewPanel','GameCase3D')
    for name in forbidden:
        assert f': {name}' not in main
        assert f' as {name}' not in main
        assert f': {name}' not in carousel
        assert f' as {name}' not in carousel
    assert 'Array[GameCase3D]' not in carousel


def test_gdscript_does_not_use_python_casefold():
    for path in ROOT.glob('*.gd'):
        assert '.casefold()' not in path.read_text(encoding='utf-8')
