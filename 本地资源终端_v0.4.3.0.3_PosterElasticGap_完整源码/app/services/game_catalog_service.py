from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil

from app.models.game import GameMetadata, GameMetadataPatch, GameRecord
from app.repositories.game_repository import GameRepository
from app.services.game_asset_service import GameAssetService
from app.services.game_metadata_service import GameMetadataService


class GameCatalogService:
    def __init__(
        self,
        repository: GameRepository,
        metadata_service: GameMetadataService,
        asset_service: GameAssetService,
        screenshot_cache_root: Path,
    ) -> None:
        self.repository = repository
        self.metadata_service = metadata_service
        self.asset_service = asset_service
        self.screenshot_cache_root = Path(screenshot_cache_root)
        self.screenshot_cache_root.mkdir(parents=True, exist_ok=True)

    def list_games(
        self,
        search: str = "",
        *,
        favorite: bool | None = None,
        installed: bool | None = None,
        recently_played: bool | None = None,
        tag: str | None = None,
        folder_id: str | None = None,
        sort: str = "last_played_at",
        descending: bool = True,
    ) -> list[GameRecord]:
        return self.repository.search(
            search,
            favorite=favorite,
            installed=installed,
            recently_played=recently_played,
            tag=tag,
            folder_id=folder_id,
            sort=sort,
            descending=descending,
        )

    def common_tags(self, limit: int = 30) -> list[str]:
        return self.repository.list_tags(limit)

    def get(self, uuid: str) -> GameRecord | None:
        return self.repository.get(uuid)

    def create_game(
        self,
        *,
        title: str,
        launch_exe: Path,
        timing_exe: Path | None = None,
        launch_args: str = "",
        working_directory: Path | None = None,
        series: str = "",
        developer: str = "",
        publisher: str = "",
        release_date: str = "",
        tags: list[str] | None = None,
        rating: int = 0,
        favorite: bool = False,
        description: str = "",
        notes: str = "",
        screenshot_directory: Path | None = None,
        cover_source: Path | None = None,
        preview_source: Path | None = None,
    ) -> GameRecord:
        launch = Path(launch_exe)
        if not launch.is_file():
            raise FileNotFoundError(launch)
        timing = Path(timing_exe) if timing_exe else launch
        if not timing.is_file():
            raise FileNotFoundError(timing)
        game = GameMetadata.new(title, rating=rating)
        game.series = series
        game.developer = developer
        game.publisher = publisher
        game.release_date = release_date
        game.tags = list(tags or [])
        game.favorite = bool(favorite)
        game.description = description
        game.notes = notes
        game.launch_exe = str(launch)
        game.launch_args = launch_args
        game.working_directory = str(working_directory or launch.parent)
        game.timing_exe = str(timing)
        game.screenshot_directory = str(screenshot_directory) if screenshot_directory else None
        if cover_source:
            game.cover_path = str(self.asset_service.import_cover(game.uuid, cover_source))
        if preview_source:
            game.preview_gif_path = str(self.asset_service.import_preview(game.uuid, preview_source))
        game.normalize()
        try:
            self.metadata_service.save(game)
            self.repository.upsert_game(game)
        except Exception:
            self.asset_service.remove_game_assets(game.uuid)
            self.metadata_service.delete(game.uuid)
            raise
        record = self.repository.get(game.uuid)
        if record is None:
            raise RuntimeError("game disappeared after create")
        return record

    def update_game(
        self,
        uuid: str,
        patch: GameMetadataPatch,
        *,
        cover_source: Path | None = None,
        preview_source: Path | None = None,
        remove_cover: bool = False,
        remove_preview: bool = False,
    ) -> GameRecord:
        original = self.metadata_service.load(uuid)
        game = deepcopy(original)
        for field_name in (
            "title",
            "series",
            "developer",
            "publisher",
            "release_date",
            "tags",
            "rating",
            "favorite",
            "description",
            "notes",
            "launch_exe",
            "launch_args",
            "working_directory",
            "timing_exe",
            "screenshot_directory",
        ):
            value = getattr(patch, field_name)
            if value is not None:
                setattr(game, field_name, value)
        if game.launch_exe and not Path(game.launch_exe).is_file():
            # Editing an archived/uninstalled game must remain possible. Only newly selected
            # executable paths are required to exist at the moment they are chosen by the UI.
            pass
        if remove_cover:
            self.asset_service.remove_cover(uuid)
            game.cover_path = None
        if remove_preview:
            self.asset_service.remove_preview(uuid)
            game.preview_gif_path = None
        if cover_source:
            game.cover_path = str(self.asset_service.import_cover(uuid, cover_source))
        if preview_source:
            game.preview_gif_path = str(self.asset_service.import_preview(uuid, preview_source))
        game.normalize()
        self.metadata_service.save(game)
        self.repository.upsert_game(game)
        record = self.repository.get(uuid)
        if record is None:
            raise RuntimeError("game disappeared after update")
        return record


    def set_folder(self, uuids: list[str], folder_id: str | None) -> list[GameRecord]:
        game_ids = list(dict.fromkeys(str(item) for item in uuids if str(item)))
        normalized_folder = str(folder_id).strip() if folder_id else None
        originals = {game_uuid: self.metadata_service.load(game_uuid) for game_uuid in game_ids}
        try:
            results: list[GameRecord] = []
            for game_uuid in game_ids:
                game = deepcopy(originals[game_uuid])
                game.folder_id = normalized_folder
                game.normalize()
                self.metadata_service.save(game)
                self.repository.upsert_game(game)
                record = self.repository.get(game_uuid)
                if record is None:
                    raise RuntimeError("game disappeared after folder update")
                results.append(record)
            return results
        except Exception as exc:
            rollback_errors: list[str] = []
            for original in originals.values():
                try:
                    self.metadata_service.save(original)
                    self.repository.upsert_game(original)
                except Exception as rollback_exc:
                    rollback_errors.append(f"{original.uuid}: {rollback_exc}")
            if rollback_errors:
                raise RuntimeError(
                    f"folder update failed: {exc}; rollback also failed: {'; '.join(rollback_errors)}"
                ) from exc
            raise

    def folder_member_uuids(self, folder_id: str) -> list[str]:
        return self.repository.list_uuids_by_folder(folder_id)


    def update_archive_media(
        self,
        uuid: str,
        *,
        source: Path | None = None,
        remove: bool = False,
    ) -> GameRecord:
        original = self.metadata_service.load(uuid)
        game = deepcopy(original)
        if remove:
            self.asset_service.remove_archive_media(uuid)
            game.archive_media_path = None
        if source is not None:
            game.archive_media_path = str(self.asset_service.import_archive_media(uuid, source))
        game.normalize()
        self.metadata_service.save(game)
        self.repository.upsert_game(game)
        record = self.repository.get(uuid)
        if record is None:
            raise RuntimeError("game disappeared after archive media update")
        return record

    def delete_game(self, uuid: str) -> None:
        record = self.repository.get(uuid)
        if record is None:
            raise KeyError(uuid)
        self.metadata_service.delete(uuid)
        self.repository.delete(uuid)
        self.asset_service.remove_game_assets(uuid)
        shutil.rmtree(self.screenshot_cache_root / uuid, ignore_errors=True)
