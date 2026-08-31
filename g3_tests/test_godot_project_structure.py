from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "g3_frontend"


def test_g3_frontend_has_phase1_shell_files():
    required = [
        FRONTEND / "project.godot",
        FRONTEND / "main.tscn",
        FRONTEND / "scripts" / "main.gd",
        FRONTEND / "scripts" / "backend_client.gd",
        FRONTEND / "scripts" / "game_case_3d.gd",
        FRONTEND / "scripts" / "game_carousel.gd",
        FRONTEND / "scripts" / "preview_panel.gd",
        FRONTEND / "shaders" / "ambient.gdshader",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    assert missing == []


def test_project_targets_godot_47_and_borderless_window():
    text = (FRONTEND / "project.godot").read_text(encoding="utf-8")
    assert 'config/features=PackedStringArray("4.7")' in text
    assert "window/size/mode=2" in text
    assert "window/size/borderless=true" in text
    assert "run/max_fps=60" in text
    assert "anti_aliasing/quality/msaa_3d=1" in text


def test_backend_client_is_localhost_websocket_protocol_1():
    text = (FRONTEND / "scripts" / "backend_client.gd").read_text(encoding="utf-8")
    assert 'BACKEND_URL: String = "ws://127.0.0.1:8765"' in text
    assert "PROTOCOL_VERSION: int = 1" in text
    assert "WebSocketPeer" in text
    assert "send_text" in text


def test_game_case_is_real_3d_box_not_control_card():
    text = (FRONTEND / "scripts" / "game_case_3d.gd").read_text(encoding="utf-8")
    assert "extends Node3D" in text
    assert "standard_tall.glb" in text
    assert "GLTFDocument.new()" in text
    assert "append_from_file" in text
    assert "BoxMesh.new()" not in text
    assert "MeshInstance3D" in text


def test_ambient_keeps_lightweight_procedural_symbols_in_one_shader():
    text = (FRONTEND / "shaders" / "ambient.gdshader").read_text(encoding="utf-8")
    assert "for (int i = 0; i < 24; i++)" in text
    assert "TIME" in text
    assert "glow" not in text


def test_phase1_input_and_lifecycle_rules_are_encoded():
    main = (FRONTEND / "scripts" / "main.gd").read_text(encoding="utf-8")
    carousel = (FRONTEND / "scripts" / "game_carousel.gd").read_text(encoding="utf-8")
    assert "PREVIEW_SETTLE_SECONDS: float = 0.40" in main
    assert 'backend.request("state.get"' in main
    assert 'backend.request("theme.current"' in main
    assert "RenderingServer.render_loop_enabled = false" in main
    assert "window.mode = Window.MODE_MINIMIZED" in main
    assert "get_window().hide()" not in main
    assert "添加游戏" in main
    assert "_emit_single_click_after_delay" in carousel


def test_preview_audio_and_theme_music_hooks_exist():
    preview = (FRONTEND / "scripts" / "preview_panel.gd").read_text(encoding="utf-8")
    main = (FRONTEND / "scripts" / "main.gd").read_text(encoding="utf-8")
    loader = FRONTEND / "scripts" / "audio_file_loader.gd"
    assert loader.is_file()
    loader_text = loader.read_text(encoding="utf-8")
    assert "AudioStreamMP3.load_from_file" in loader_text
    assert "AudioStreamOggVorbis.load_from_file" in loader_text
    assert "AudioStreamWAV.load_from_file" in loader_text
    assert "preview_audio" in preview
    assert "media_audio_activity_changed" in preview
    assert 'backend.request("settings.get"' in main
    assert "theme_music_player" in main
    assert "_on_preview_audio_activity_changed" in main
