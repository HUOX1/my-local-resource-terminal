from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.config.data_dirs import ensure_data_layout
from app.db.database import Database
from app.models.game import GameMetadataPatch
from app.repositories.game_repository import GameRepository
from app.services.game_asset_service import GameAssetService
from app.services.game_catalog_service import GameCatalogService
from app.services.game_metadata_service import GameMetadataService


def build_catalog(tmp_path):
    layout = ensure_data_layout(tmp_path / "data")
    db = Database(layout.database_path)
    db.initialize()
    return GameCatalogService(
        GameRepository(db),
        GameMetadataService(layout.game_metadata_dir),
        GameAssetService(layout.game_cover_dir, layout.game_preview_dir),
        layout.game_screenshot_cache_dir,
    )


def test_create_update_and_delete_game_archive(tmp_path):
    catalog = build_catalog(tmp_path)
    exe = tmp_path / "demo.exe"
    exe.write_bytes(b"")
    cover = tmp_path / "cover.png"
    Image.new("RGB", (20, 30)).save(cover)

    record = catalog.create_game(
        title="Demo",
        launch_exe=exe,
        timing_exe=exe,
        cover_source=cover,
    )
    assert record.metadata.title == "Demo"
    assert Path(record.metadata.cover_path).is_file()

    updated = catalog.update_game(record.metadata.uuid, GameMetadataPatch(favorite=True, tags=["RPG"]))
    assert updated.metadata.favorite is True
    assert updated.metadata.tags == ["RPG"]

    owned_cover = Path(updated.metadata.cover_path)
    catalog.delete_game(updated.metadata.uuid)
    assert catalog.get(updated.metadata.uuid) is None
    assert not owned_cover.exists()
    assert exe.exists()


def test_update_game_can_clear_cover_and_preview_without_touching_sources(tmp_path):
    catalog = build_catalog(tmp_path)
    exe = tmp_path / "demo.exe"
    exe.write_bytes(b"")
    source_cover = tmp_path / "cover.png"
    source_preview = tmp_path / "preview.gif"
    Image.new("RGB", (20, 30)).save(source_cover)
    Image.new("RGB", (20, 30)).save(source_preview, format="GIF")

    record = catalog.create_game(
        title="Demo",
        launch_exe=exe,
        timing_exe=exe,
        cover_source=source_cover,
        preview_source=source_preview,
    )
    owned_cover = Path(record.metadata.cover_path)
    owned_preview = Path(record.metadata.preview_gif_path)

    updated = catalog.update_game(
        record.metadata.uuid,
        GameMetadataPatch(),
        remove_cover=True,
        remove_preview=True,
    )

    assert updated.metadata.cover_path is None
    assert updated.metadata.preview_gif_path is None
    assert not owned_cover.exists()
    assert not owned_preview.exists()
    assert source_cover.exists()
    assert source_preview.exists()


def test_update_game_description_does_not_overwrite_notes(tmp_path):
    catalog = build_catalog(tmp_path)
    exe = tmp_path / "demo.exe"
    exe.write_bytes(b"")
    record = catalog.create_game(
        title="Demo",
        launch_exe=exe,
        timing_exe=exe,
        notes="我的旧记录",
    )

    updated = catalog.update_game(
        record.metadata.uuid,
        GameMetadataPatch(description="作品介绍"),
    )

    assert updated.metadata.description == "作品介绍"
    assert updated.metadata.notes == "我的旧记录"


def test_game_folder_assignment_filter_and_clear_round_trip(tmp_path):
    catalog = build_catalog(tmp_path)
    first_exe = tmp_path / "first.exe"
    second_exe = tmp_path / "second.exe"
    first_exe.write_bytes(b"")
    second_exe.write_bytes(b"")
    first = catalog.create_game(title="First", launch_exe=first_exe, timing_exe=first_exe)
    second = catalog.create_game(title="Second", launch_exe=second_exe, timing_exe=second_exe)

    catalog.set_folder([first.metadata.uuid], "folder-games-1")

    filtered = catalog.list_games(folder_id="folder-games-1", sort="title", descending=False)
    assert [item.metadata.uuid for item in filtered] == [first.metadata.uuid]
    assert catalog.get(first.metadata.uuid).metadata.folder_id == "folder-games-1"
    assert catalog.get(second.metadata.uuid).metadata.folder_id is None

    catalog.set_folder([first.metadata.uuid], None)
    assert catalog.get(first.metadata.uuid).metadata.folder_id is None
    assert catalog.list_games(folder_id="folder-games-1") == []


def test_game_folder_members_can_be_listed_for_delete_cleanup(tmp_path):
    catalog = build_catalog(tmp_path)
    exe = tmp_path / "demo.exe"
    exe.write_bytes(b"")
    record = catalog.create_game(title="Demo", launch_exe=exe, timing_exe=exe)
    catalog.set_folder([record.metadata.uuid], "folder-delete")

    assert catalog.folder_member_uuids("folder-delete") == [record.metadata.uuid]
