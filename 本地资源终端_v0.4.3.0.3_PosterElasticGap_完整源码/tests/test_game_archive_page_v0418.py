from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.config.data_dirs import ensure_data_layout
from app.db.database import Database
from app.models.game import GameMetadata, GameMetadataPatch
from app.repositories.game_repository import GameRepository
from app.services.game_asset_service import GameAssetService
from app.services.game_catalog_service import GameCatalogService
from app.services.game_metadata_service import GameMetadataService


def _build_catalog(tmp_path: Path) -> tuple[GameCatalogService, object]:
    layout = ensure_data_layout(tmp_path / "data")
    db = Database(layout.database_path)
    db.initialize()
    catalog = GameCatalogService(
        GameRepository(db),
        GameMetadataService(layout.game_metadata_dir),
        GameAssetService(layout.game_cover_dir, layout.game_preview_dir, layout.game_archive_media_dir),
        layout.game_screenshot_cache_dir,
    )
    return catalog, layout


def test_v0418_archive_media_column_survives_schema_version_5_upgrade(tmp_path: Path) -> None:
    db = Database(tmp_path / "library.db")
    db.initialize()

    assert db.schema_version() == 6
    with db.connect() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(games)")}
    assert "archive_media_path" in columns


def test_game_metadata_json_roundtrip_preserves_archive_media_path(tmp_path: Path) -> None:
    service = GameMetadataService(tmp_path / "metadata")
    game = GameMetadata.new("Demo")
    game.archive_media_path = str(tmp_path / "hero.gif")

    service.save(game)
    loaded = service.load(game.uuid)

    assert loaded.archive_media_path == str(tmp_path / "hero.gif")


def test_archive_media_import_accepts_images_and_gif_but_rejects_video(tmp_path: Path) -> None:
    covers = tmp_path / "covers"
    previews = tmp_path / "previews"
    archives = tmp_path / "archive"
    image_source = tmp_path / "hero.png"
    gif_source = tmp_path / "hero.gif"
    video_source = tmp_path / "hero.mp4"
    Image.new("RGB", (64, 36), "navy").save(image_source)
    Image.new("RGB", (64, 36), "purple").save(gif_source, format="GIF")
    video_source.write_bytes(b"not-a-video")

    service = GameAssetService(covers, previews, archives)
    image_target = service.import_archive_media("game-1", image_source)
    gif_target = service.import_archive_media("game-1", gif_source)

    assert image_target == archives / "game-1.png"
    assert gif_target == archives / "game-1.gif"
    assert not image_target.exists()  # GIF import replaces the previous owned archive media.
    assert gif_target.exists()
    with pytest.raises(ValueError, match="archive media"):
        service.import_archive_media("game-1", video_source)


def test_catalog_can_set_and_clear_archive_media_without_touching_source(tmp_path: Path) -> None:
    catalog, _layout = _build_catalog(tmp_path)
    exe = tmp_path / "demo.exe"
    exe.write_bytes(b"")
    hero = tmp_path / "hero.png"
    Image.new("RGB", (80, 45), "teal").save(hero)

    record = catalog.create_game(title="Demo", launch_exe=exe, timing_exe=exe)
    updated = catalog.update_archive_media(record.metadata.uuid, source=hero)
    owned = Path(updated.metadata.archive_media_path or "")

    assert owned.is_file()
    assert hero.is_file()

    cleared = catalog.update_archive_media(record.metadata.uuid, remove=True)
    assert cleared.metadata.archive_media_path is None
    assert not owned.exists()
    assert hero.exists()


def test_regular_game_patch_does_not_drop_archive_media_path(tmp_path: Path) -> None:
    catalog, _layout = _build_catalog(tmp_path)
    exe = tmp_path / "demo.exe"
    exe.write_bytes(b"")
    hero = tmp_path / "hero.png"
    Image.new("RGB", (80, 45), "green").save(hero)

    record = catalog.create_game(title="Demo", launch_exe=exe, timing_exe=exe)
    with_hero = catalog.update_archive_media(record.metadata.uuid, source=hero)
    patched = catalog.update_game(with_hero.metadata.uuid, GameMetadataPatch(notes="我的记录"))

    assert patched.metadata.archive_media_path == with_hero.metadata.archive_media_path


def test_archive_media_resolver_prefers_dedicated_then_preview_then_newest_screenshot(tmp_path: Path) -> None:
    from app.services.game_archive_media import resolve_game_archive_media
    from app.services.screenshot_service import ScreenshotService

    game = GameMetadata.new("Demo")
    record = __import__("app.models.game", fromlist=["GameRecord"]).GameRecord.from_metadata(game)
    shots = tmp_path / "shots"
    shots.mkdir()
    older = shots / "older.png"
    newer = shots / "newer.jpg"
    Image.new("RGB", (40, 20), "red").save(older)
    Image.new("RGB", (40, 20), "blue").save(newer)
    older.touch()
    newer.touch()
    import os
    os.utime(older, (100, 100))
    os.utime(newer, (200, 200))
    game.screenshot_directory = str(shots)

    screenshot_service = ScreenshotService(tmp_path / "cache")
    assert resolve_game_archive_media(record, screenshot_service) == newer

    preview = tmp_path / "preview.gif"
    Image.new("RGB", (40, 20), "green").save(preview, format="GIF")
    game.preview_gif_path = str(preview)
    assert resolve_game_archive_media(record, screenshot_service) == preview

    dedicated = tmp_path / "hero.webp"
    Image.new("RGB", (40, 20), "purple").save(dedicated, format="WEBP")
    game.archive_media_path = str(dedicated)
    assert resolve_game_archive_media(record, screenshot_service) == dedicated


def test_archive_media_resolver_never_uses_cover_as_hero(tmp_path: Path) -> None:
    from app.services.game_archive_media import resolve_game_archive_media
    from app.services.screenshot_service import ScreenshotService
    from app.models.game import GameRecord

    cover = tmp_path / "cover.png"
    Image.new("RGB", (40, 60), "orange").save(cover)
    game = GameMetadata.new("Demo")
    game.cover_path = str(cover)
    record = GameRecord.from_metadata(game)

    assert resolve_game_archive_media(record, ScreenshotService(tmp_path / "cache")) is None


def test_archive_media_resolver_ignores_missing_or_unsupported_dedicated_media(tmp_path: Path) -> None:
    from app.services.game_archive_media import resolve_game_archive_media
    from app.services.screenshot_service import ScreenshotService
    from app.models.game import GameRecord

    preview = tmp_path / "preview.gif"
    Image.new("RGB", (40, 20), "green").save(preview, format="GIF")
    game = GameMetadata.new("Demo")
    game.archive_media_path = str(tmp_path / "missing.mp4")
    game.preview_gif_path = str(preview)
    record = GameRecord.from_metadata(game)

    assert resolve_game_archive_media(record, ScreenshotService(tmp_path / "cache")) == preview


def test_game_archive_page_source_has_full_content_page_structure() -> None:
    source = Path("app/ui/game_archive_page.py").read_text(encoding="utf-8")
    assert "class GameArchivePage(QWidget)" in source
    assert "back_requested = Signal()" in source
    assert 'setObjectName("gameArchivePage")' in source
    assert 'setObjectName("gameArchiveHero")' in source
    assert 'setObjectName("gameArchiveBackButton")' in source
    assert 'self._card("作品介绍")' in source
    assert 'self._card("我的记录")' in source
    assert 'self._card("媒体")' in source
    assert 'self._card("档案资料")' in source
    assert 'self._card("游玩")' in source
    assert 'QPushButton("启动游戏")' in source
    assert 'QPushButton("编辑档案")' not in source
    assert 'metadata_patch_requested = Signal(str, object)' in source
    assert 'QPushButton("更换展示图")' in source
    assert 'QPushButton("清除展示图")' in source
    assert "QScrollArea" in source
    assert "QMovie" in source
    assert "video" not in source.lower()


def test_main_window_opens_game_archive_inside_content_area_not_as_modal_dialog() -> None:
    source = Path("app/ui/main_window.py").read_text(encoding="utf-8")
    assert "from app.ui.game_archive_page import GameArchivePage" in source
    assert "self.content_page_stack = QStackedWidget()" in source
    assert "self.library_page = QWidget()" in source
    assert "self.game_archive_page = GameArchivePage" in source
    start = source.index("    def _open_game_detail")
    end = source.index("    def _close_game_archive", start)
    block = source[start:end]
    assert "self.game_archive_page.set_record(record)" in block
    assert "transition_stack_page(self.content_page_stack, self.game_archive_page" in block
    assert ".exec()" not in block
    assert "def _close_game_archive" in source
    assert "self.content_page_stack.setCurrentWidget(self.library_page)" in source


def test_main_window_game_archive_edits_inline_without_legacy_modal_editor() -> None:
    source = Path("app/ui/main_window.py").read_text(encoding="utf-8")
    assert "def _edit_game_archive" not in source
    assert "GameDetailDialog" not in source
    assert "game_archive_page.metadata_patch_requested.connect(self._update_game_archive_metadata)" in source


def test_game_archive_media_resolver_does_not_reference_cover_or_motion_formats() -> None:
    source = Path("app/services/game_archive_media.py").read_text(encoding="utf-8")
    resolver_start = source.index("def resolve_game_archive_media")
    resolver = source[resolver_start:]
    assert "cover_path" not in resolver
    assert ".mp4" not in source.lower()
    assert ".webm" not in source.lower()


def test_v0418_version_is_visible_in_project_and_window_chrome() -> None:
    assert 'version = "0.4.3.0.3"' in Path("pyproject.toml").read_text(encoding="utf-8")
    assert "v0.4.3.0.3" in Path("app/ui/main_window.py").read_text(encoding="utf-8")
    assert "v0.4.3.0.3" in Path("app/ui/app_chrome.py").read_text(encoding="utf-8")


def test_v0418_hero_picker_accepts_only_image_and_gif_extensions() -> None:
    source = Path("app/ui/main_window.py").read_text(encoding="utf-8")
    assert '"图片 / GIF (*.jpg *.jpeg *.png *.webp *.bmp *.gif)"' in source
    assert "archive_media_change_requested" in source
    assert "archive_media_clear_requested" in source


def test_refresh_games_refreshes_open_archive_record_after_session_changes() -> None:
    source = Path("app/ui/main_window.py").read_text(encoding="utf-8")
    start = source.index("    def _refresh_games")
    end = source.index("    def _filter_changed", start)
    block = source[start:end]
    assert "self.content_page_stack.currentWidget() is self.game_archive_page" in block
    assert "self.game_archive_page.game_uuid" in block
    assert "self.game_catalog.get(self.game_archive_page.game_uuid)" in block
    assert "self.game_archive_page.set_record" in block
