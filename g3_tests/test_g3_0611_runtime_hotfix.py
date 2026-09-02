from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_launch_profile_window_starts_hidden():
    text = (ROOT / 'g3_frontend/scripts/launch_profile_dialog.gd').read_text(encoding='utf-8')
    ready = text.split('func _ready() -> void:', 1)[1].split('\nfunc ', 1)[0]
    assert 'hide()' in ready or 'visible = false' in ready


def test_game_case_uses_runtime_gltf_loader_not_resourceloader_for_glb():
    text = (ROOT / 'g3_frontend/scripts/game_case_3d.gd').read_text(encoding='utf-8')
    assert 'GLTFDocument.new()' in text
    assert 'GLTFState.new()' in text
    assert 'append_from_file' in text
    assert 'ProjectSettings.globalize_path(model_path)' in text
    assert 'load(model_path)' not in text


def test_preview_blank_area_click_is_not_blocked_by_whole_preview_rect():
    text = (ROOT / 'g3_frontend/scripts/main.gd').read_text(encoding='utf-8')
    block = text.split('func _unhandled_input(event: InputEvent) -> void:', 1)[1].split('\nfunc _unhandled_key_input', 1)[0]
    assert 'preview.get_global_rect().has_point' not in block
    assert '_close_preview()' in block
