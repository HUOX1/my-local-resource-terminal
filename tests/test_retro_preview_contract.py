from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_retro_preview_is_installed_and_identity_is_bypassed():
    source = read("app/bootstrap.py")
    assert "install_retro_showcase(window)" in source
    assert 'window.switch_library("games", clear_search=False)' in source
    assert 'window.identity_entered.connect(start_scan_after_identity)' not in source


def test_retro_showcase_contains_agreed_interaction_states():
    source = read("app/ui/retro_showcase.py")
    for token in (
        'self.domain = "games"',
        'self.box_style = "neo"',
        'self.menu_corner = "bottom_right"',
        'def wheelEvent',
        'def mouseDoubleClickEvent',
        'def _draw_detail_panel',
        'def _draw_system_panel',
        'Classic Box',
        'Neo Box',
    ):
        assert token in source


def test_flat_pro_freeze_and_retro_logs_are_packaged():
    freeze = read("docs/development-logs/Flat_Pro_v1_Freeze.md")
    retro = read("docs/development-logs/Retro_Prototype_v1.md")
    assert "FROZEN BASELINE" in freeze
    assert "FIRST RUNNABLE PROTOTYPE" in retro
    assert "Arc Showcase" in retro
