from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_flat_theme_is_centralized_and_applied_at_application_level() -> None:
    theme = (ROOT / "app" / "ui" / "flat_theme.py").read_text(encoding="utf-8")
    bootstrap = (ROOT / "app" / "bootstrap.py").read_text(encoding="utf-8")
    assert "class FlatTokens" in theme
    for token in (
        "BACKGROUND",
        "SURFACE",
        "SURFACE_HOVER",
        "BORDER",
        "TEXT_PRIMARY",
        "TEXT_SECONDARY",
        "ACCENT",
        "RADIUS_SMALL",
        "RADIUS_MEDIUM",
        "SIDEBAR_WIDTH",
        "CONTROL_HEIGHT",
    ):
        assert token in theme
    assert "def build_flat_stylesheet" in theme
    assert "def apply_flat_theme" in theme
    assert "apply_theme(app, settings.ui_theme)" in bootstrap


def test_main_window_uses_flat_sidebar_content_shell() -> None:
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "FlatTokens" in source
    assert 'setObjectName("sidebar")' in source
    assert 'setObjectName("contentSurface")' in source
    assert 'setObjectName("navButton")' in source
    assert 'setObjectName("libraryToolsPopup")' in source
    assert "self.library_title_label" not in source
    assert "self.library_count_label" not in source
    assert "self.main_splitter.addWidget(self.sidebar)" in source
    assert "self.main_splitter.addWidget(content)" in source


def test_sidebar_contains_only_existing_primary_domains_and_settings() -> None:
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert 'NavigationButton("影片")' in source
    assert 'NavigationButton("游戏")' in source
    assert 'NavigationButton("设置")' in source
    assert 'QPushButton("电视剧")' not in source
    assert 'QPushButton("动漫")' not in source
    assert 'QPushButton("音乐")' not in source


def test_poster_delegates_use_rounded_clip_without_adding_text() -> None:
    movie = (ROOT / "app" / "ui" / "movie_delegate.py").read_text(encoding="utf-8")
    game = (ROOT / "app" / "ui" / "game_delegate.py").read_text(encoding="utf-8")
    for source in (movie, game):
        assert "FlatTokens" in source
        assert "QPainterPath" in source
        assert "addRoundedRect" in source
        assert "drawText" not in source


def test_game_delegate_imports_every_qt_symbol_used_by_flat_painter() -> None:
    import ast

    source = (ROOT / "app" / "ui" / "game_delegate.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    for name in ("QColor", "QPainterPath", "QRectF"):
        assert name in imported, f"{name} is used by GameCardDelegate.paint() but not imported"
