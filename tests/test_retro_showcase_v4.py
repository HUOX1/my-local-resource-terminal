from pathlib import Path

from app.ui.retro_showcase_state import (
    rail_center_x,
    resolve_game_package_profile,
)

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_platform_profiles_match_console_package_proportions():
    ps1 = resolve_game_package_profile("PS1 PlayStation", 0.70)
    ps2 = resolve_game_package_profile("ps2", 0.70)
    ps3 = resolve_game_package_profile("PlayStation 3", 0.70)
    switch = resolve_game_package_profile("Nintendo Switch", 0.70)

    assert ps1.family == "jewel"
    assert 0.94 <= ps1.face_ratio <= 1.04
    assert ps2.family == "keepcase"
    assert 0.66 <= ps2.face_ratio <= 0.73
    assert ps3.family == "bluray"
    assert 0.68 <= ps3.face_ratio <= 0.75
    assert switch.family == "switch"
    assert switch.face_ratio < ps2.face_ratio


def test_cover_ratio_can_select_square_package_without_platform_metadata():
    square = resolve_game_package_profile("", 0.98)
    portrait = resolve_game_package_profile("", 0.69)
    assert square.family == "jewel"
    assert square.face_ratio > 0.9
    assert portrait.family in {"keepcase", "bluray"}
    assert portrait.face_ratio < 0.78


def test_small_collections_use_the_full_horizontal_rail_without_blank_slot():
    four = [rail_center_x(position, 4) for position in (-2.0, -1.0, 0.0, 1.0)]
    three = [rail_center_x(position, 3) for position in (-1.0, 0.0, 1.0)]
    two = [rail_center_x(position, 2) for position in (-1.0, 0.0)]

    assert four == sorted(four)
    assert four[0] <= 0.12 and four[-1] >= 0.78
    assert three[0] < 0.3 < three[1] < 0.7 < three[2]
    assert two[0] < 0.4 and two[1] > 0.6


def test_v4_preserves_full_cover_art_and_removes_flat_fallback_ui():
    source = read("app/ui/retro_showcase.py")
    cover_block = source.split("def _draw_cover", 1)[1].split("def _cover_aspect", 1)[0]
    assert "KeepAspectRatioByExpanding" not in cover_block
    assert "Qt.AspectRatioMode.KeepAspectRatio" in cover_block
    assert "更多管理（Flat Pro）" not in source
    assert "切换到 Flat Pro" not in source
    assert 'QShortcut(QKeySequence("F12")' not in source
    assert "Key_F12" not in source
    assert "def _draw_suspension_rail" not in source


def test_v4_log_remains_packaged_as_history():
    log = read("docs/development-logs/Retro_Prototype_v4.md")
    assert "PACKAGE PROFILE" in log
    assert "FULL COVER" in log
    assert "RETRO PRIMARY" in log
