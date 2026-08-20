import os
from pathlib import Path

from PIL import Image

from app.services.screenshot_service import ScreenshotService


def test_list_images_reads_external_folder_newest_first(tmp_path):
    source = tmp_path / "shots"
    source.mkdir()
    older = source / "a.png"
    newer = source / "b.jpg"
    ignored = source / "x.txt"
    Image.new("RGB", (50, 40)).save(older)
    Image.new("RGB", (50, 40)).save(newer)
    ignored.write_text("x")
    os.utime(older, (10, 10))
    os.utime(newer, (20, 20))
    service = ScreenshotService(tmp_path / "cache")

    result = service.list_images(source)

    assert result.available is True
    assert [item.path.name for item in result.items] == ["b.jpg", "a.png"]


def test_missing_screenshot_directory_is_nonfatal(tmp_path):
    service = ScreenshotService(tmp_path / "cache")
    result = service.list_images(tmp_path / "missing")
    assert result.available is False
    assert result.items == []


def test_thumbnail_is_cached_below_game_uuid(tmp_path):
    source = tmp_path / "shot.png"
    Image.new("RGB", (800, 600)).save(source)
    service = ScreenshotService(tmp_path / "cache")

    thumb = service.thumbnail_for("game-1", source)

    assert thumb.exists()
    assert thumb.parent == tmp_path / "cache" / "game-1"
    with Image.open(thumb) as image:
        assert image.width <= 320
        assert image.height <= 200
