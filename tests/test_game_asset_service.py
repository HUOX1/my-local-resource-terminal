from pathlib import Path

from PIL import Image

from app.services.game_asset_service import GameAssetService


def test_import_cover_and_preview_copy_into_terminal_owned_assets(tmp_path):
    covers = tmp_path / "covers"
    previews = tmp_path / "previews"
    source_cover = tmp_path / "source.png"
    source_preview = tmp_path / "preview.gif"
    Image.new("RGB", (20, 30)).save(source_cover)
    Image.new("RGB", (20, 30)).save(source_preview, format="GIF")
    original_cover = source_cover.read_bytes()
    original_preview = source_preview.read_bytes()
    service = GameAssetService(covers, previews)

    cover = service.import_cover("game-1", source_cover)
    preview = service.import_preview("game-1", source_preview)

    assert cover == covers / "game-1.png"
    assert preview == previews / "game-1.gif"
    assert cover.exists() and preview.exists()
    assert source_cover.read_bytes() == original_cover
    assert source_preview.read_bytes() == original_preview


def test_remove_game_assets_never_touches_sources(tmp_path):
    covers = tmp_path / "covers"
    previews = tmp_path / "previews"
    source = tmp_path / "source.jpg"
    Image.new("RGB", (10, 10)).save(source)
    service = GameAssetService(covers, previews)
    imported = service.import_cover("game-1", source)

    service.remove_game_assets("game-1")

    assert not imported.exists()
    assert source.exists()


def test_remove_individual_owned_assets_never_touch_sources(tmp_path):
    covers = tmp_path / "covers"
    previews = tmp_path / "previews"
    source_cover = tmp_path / "source-cover.png"
    source_preview = tmp_path / "source-preview.gif"
    Image.new("RGB", (10, 10)).save(source_cover)
    Image.new("RGB", (10, 10)).save(source_preview, format="GIF")
    service = GameAssetService(covers, previews)
    owned_cover = service.import_cover("game-1", source_cover)
    owned_preview = service.import_preview("game-1", source_preview)

    service.remove_cover("game-1")
    assert not owned_cover.exists()
    assert owned_preview.exists()
    assert source_cover.exists()
    assert source_preview.exists()

    service.remove_preview("game-1")
    assert not owned_preview.exists()
    assert source_cover.exists()
    assert source_preview.exists()
