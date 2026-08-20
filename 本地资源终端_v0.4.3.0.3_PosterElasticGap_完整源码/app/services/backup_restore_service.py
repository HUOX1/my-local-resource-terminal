from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from app.config.data_dirs import ensure_data_layout
from app.config.settings import AppSettings, SettingsStore
from app.services.cover_service import SUPPORTED_COVER_EXTENSIONS

BACKUP_FORMAT = "local_movie_manager_backup"
BACKUP_VERSION = 4
SUPPORTED_BACKUP_VERSIONS = {1, 2, 3, 4}


class InvalidBackupError(ValueError):
    """Raised when a ZIP is not a supported Local Resource Terminal backup."""


@dataclass(frozen=True, slots=True)
class BackupManifest:
    format: str
    version: int
    created_at: str
    includes_covers: bool
    includes_visual_assets: bool


@dataclass(frozen=True, slots=True)
class BackupSummary:
    path: Path
    metadata_files: int
    cover_files: int
    includes_covers: bool
    game_asset_files: int = 0

    @property
    def includes_visual_assets(self) -> bool:
        return self.includes_covers


@dataclass(frozen=True, slots=True)
class RestoreAssessment:
    data_will_overwrite: bool
    cover_conflicts: int
    cover_files: int

    @property
    def has_existing_content(self) -> bool:
        return self.data_will_overwrite or self.cover_conflicts > 0


@dataclass(frozen=True, slots=True)
class RestoreSummary:
    metadata_files: int
    cover_files: int
    cover_conflicts: int
    game_asset_files: int = 0


class BackupRestoreService:
    def create_backup(
        self,
        settings: AppSettings,
        settings_path: Path,
        output_zip: Path,
        *,
        include_visual_assets: bool | None = None,
        include_covers: bool | None = None,
    ) -> BackupSummary:
        if include_visual_assets is None:
            include_visual_assets = True if include_covers is None else bool(include_covers)
        output = Path(output_zip)
        if output.suffix.casefold() != ".zip":
            output = output.with_suffix(".zip")
        output.parent.mkdir(parents=True, exist_ok=True)

        layout = ensure_data_layout(settings.data_dir)
        if not layout.database_path.is_file():
            raise FileNotFoundError(f"找不到数据库：{layout.database_path}")

        movie_metadata = sorted(path for path in layout.movie_metadata_dir.glob("*.json") if path.is_file())
        game_metadata = sorted(path for path in layout.game_metadata_dir.glob("*.json") if path.is_file())
        # Backward-compatible safety: if an upgrade has not migrated legacy movie JSON yet,
        # include it under the v2 movie archive tree rather than silently omitting it.
        legacy_movie_metadata = sorted(path for path in layout.metadata_dir.glob("*.json") if path.is_file())
        collection_folders = layout.collection_folders_path if layout.collection_folders_path.is_file() else None
        identity_root = Path(settings_path).parent / "identity"
        identity_files = (
            sorted(path for path in identity_root.rglob("*") if path.is_file())
            if (identity_root / "profile.json").is_file()
            else []
        )
        movie_covers: list[Path] = []
        game_covers: list[Path] = []
        game_previews: list[Path] = []
        game_archive_media: list[Path] = []
        if include_visual_assets:
            if settings.cover_dir.is_dir():
                movie_covers = sorted(
                    path
                    for path in settings.cover_dir.iterdir()
                    if path.is_file() and path.suffix.casefold() in SUPPORTED_COVER_EXTENSIONS
                )
            game_covers = sorted(path for path in layout.game_cover_dir.iterdir() if path.is_file())
            game_previews = sorted(path for path in layout.game_preview_dir.iterdir() if path.is_file())
            game_archive_media = sorted(path for path in layout.game_archive_media_dir.iterdir() if path.is_file())

        manifest = {
            "format": BACKUP_FORMAT,
            "version": BACKUP_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "includes_covers": bool(include_visual_assets),
            "includes_visual_assets": bool(include_visual_assets),
        }

        temp_output = output.with_name(f".{output.name}.tmp")
        temp_output.unlink(missing_ok=True)
        try:
            with tempfile.TemporaryDirectory(prefix="lrt-backup-") as temp_dir_text:
                temp_dir = Path(temp_dir_text)
                db_snapshot = temp_dir / "library.db"
                self._snapshot_sqlite(layout.database_path, db_snapshot)
                settings_snapshot = temp_dir / "settings.json"
                SettingsStore(settings_snapshot).save(settings)

                with zipfile.ZipFile(temp_output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                    archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
                    archive.write(db_snapshot, "data/library.db")
                    seen_movie_names: set[str] = set()
                    for source in [*movie_metadata, *legacy_movie_metadata]:
                        if source.name in seen_movie_names:
                            continue
                        seen_movie_names.add(source.name)
                        archive.write(source, f"data/metadata/movies/{source.name}")
                    for source in game_metadata:
                        archive.write(source, f"data/metadata/games/{source.name}")
                    if collection_folders is not None:
                        archive.write(collection_folders, "data/collections/folders.json")
                    archive.write(settings_snapshot, "settings/settings.json")
                    for source in identity_files:
                        relative = source.relative_to(identity_root).as_posix()
                        archive.write(source, f"identity/{relative}")
                    for source in movie_covers:
                        archive.write(source, f"covers/{source.name}")
                    for source in game_covers:
                        archive.write(source, f"game_assets/covers/{source.name}")
                    for source in game_previews:
                        archive.write(source, f"game_assets/previews/{source.name}")
                    for source in game_archive_media:
                        archive.write(source, f"game_assets/archive/{source.name}")
            temp_output.replace(output)
        except Exception:
            temp_output.unlink(missing_ok=True)
            raise

        metadata_count = len({path.name for path in [*movie_metadata, *legacy_movie_metadata]}) + len(game_metadata)
        return BackupSummary(
            path=output,
            metadata_files=metadata_count,
            cover_files=len(movie_covers),
            includes_covers=bool(include_visual_assets),
            game_asset_files=len(game_covers) + len(game_previews) + len(game_archive_media),
        )

    def inspect_backup(self, backup_zip: Path) -> BackupManifest:
        backup = Path(backup_zip)
        if not backup.is_file():
            raise InvalidBackupError(f"找不到备份文件：{backup}")
        try:
            with zipfile.ZipFile(backup) as archive:
                names = archive.namelist()
                for name in names:
                    self._validate_member_name(name)
                for required in ("manifest.json", "data/library.db", "settings/settings.json"):
                    if required not in names:
                        raise InvalidBackupError(f"备份缺少 {PurePosixPath(required).name}")
                try:
                    payload = json.loads(archive.read("manifest.json").decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError, KeyError) as exc:
                    raise InvalidBackupError("manifest.json 无法读取") from exc
        except zipfile.BadZipFile as exc:
            raise InvalidBackupError("不是有效的 ZIP 备份") from exc

        if payload.get("format") != BACKUP_FORMAT:
            raise InvalidBackupError("不是本地资源终端生成的备份")
        try:
            version = int(payload.get("version"))
        except (TypeError, ValueError) as exc:
            raise InvalidBackupError("备份版本信息无效") from exc
        if version not in SUPPORTED_BACKUP_VERSIONS:
            raise InvalidBackupError(f"不支持的备份版本：{version}")
        includes_visual = bool(payload.get("includes_visual_assets", payload.get("includes_covers", False)))
        return BackupManifest(
            format=BACKUP_FORMAT,
            version=version,
            created_at=str(payload.get("created_at", "")),
            includes_covers=includes_visual,
            includes_visual_assets=includes_visual,
        )

    def assess_restore(self, settings: AppSettings, backup_zip: Path) -> RestoreAssessment:
        manifest = self.inspect_backup(backup_zip)
        layout = ensure_data_layout(settings.data_dir)
        data_will_overwrite = (
            layout.database_path.exists()
            or any(layout.metadata_dir.rglob("*.json"))
            or layout.collection_folders_path.exists()
        )
        movie_cover_names, game_cover_names, game_preview_names, game_archive_names = self._backup_visual_names(backup_zip, manifest)
        conflicts = sum(1 for name in movie_cover_names if (settings.cover_dir / name).exists())
        conflicts += sum(1 for name in game_cover_names if (layout.game_cover_dir / name).exists())
        conflicts += sum(1 for name in game_preview_names if (layout.game_preview_dir / name).exists())
        conflicts += sum(1 for name in game_archive_names if (layout.game_archive_media_dir / name).exists())
        return RestoreAssessment(
            data_will_overwrite=data_will_overwrite,
            cover_conflicts=conflicts,
            cover_files=len(movie_cover_names) + len(game_cover_names) + len(game_preview_names) + len(game_archive_names),
        )

    def restore_backup(self, settings: AppSettings, settings_path: Path, backup_zip: Path) -> RestoreSummary:
        manifest = self.inspect_backup(backup_zip)
        layout = ensure_data_layout(settings.data_dir)
        settings.cover_dir.mkdir(parents=True, exist_ok=True)
        settings_path = Path(settings_path)

        with tempfile.TemporaryDirectory(prefix="lrt-restore-") as temp_dir_text:
            temp_dir = Path(temp_dir_text)
            staged = temp_dir / "staged"
            rollback = temp_dir / "rollback"
            self._stage_backup(Path(backup_zip), staged)
            staged_settings = SettingsStore(staged / "settings" / "settings.json").load()
            restored_settings = self._merge_restored_settings(settings, staged_settings)

            movie_metadata, game_metadata = self._staged_metadata(staged, manifest)
            staged_collection_folders = staged / "data" / "collections" / "folders.json"
            if manifest.version < 4 or not staged_collection_folders.is_file():
                staged_collection_folders = None
            staged_movie_covers = self._files_in(staged / "covers") if manifest.includes_visual_assets else []
            staged_game_covers = self._files_in(staged / "game_assets" / "covers") if manifest.includes_visual_assets else []
            staged_game_previews = self._files_in(staged / "game_assets" / "previews") if manifest.includes_visual_assets else []
            staged_game_archive = self._files_in(staged / "game_assets" / "archive") if manifest.includes_visual_assets else []
            staged_identity = staged / "identity"
            restore_identity = manifest.version >= 3 and (staged_identity / "profile.json").is_file()

            cover_conflicts = sum(1 for source in staged_movie_covers if (settings.cover_dir / source.name).exists())
            cover_conflicts += sum(1 for source in staged_game_covers if (layout.game_cover_dir / source.name).exists())
            cover_conflicts += sum(1 for source in staged_game_previews if (layout.game_preview_dir / source.name).exists())
            cover_conflicts += sum(1 for source in staged_game_archive if (layout.game_archive_media_dir / source.name).exists())

            rollback_state = self._snapshot_for_rollback(
                layout=layout,
                settings=settings,
                settings_path=settings_path,
                staged_covers=staged_movie_covers,
                staged_game_covers=staged_game_covers,
                staged_game_previews=staged_game_previews,
                staged_game_archive=staged_game_archive,
                rollback=rollback,
                restore_identity=restore_identity,
            )
            try:
                self._apply_database_and_metadata(
                    layout,
                    staged / "data" / "library.db",
                    movie_metadata,
                    game_metadata,
                    staged_collection_folders,
                )
                self._apply_covers(settings.cover_dir, staged_movie_covers)
                self._apply_covers(layout.game_cover_dir, staged_game_covers)
                self._apply_covers(layout.game_preview_dir, staged_game_previews)
                self._apply_covers(layout.game_archive_media_dir, staged_game_archive)
                if restore_identity:
                    self._apply_identity(settings_path.parent / "identity", staged_identity)
                SettingsStore(settings_path).save(restored_settings)
            except Exception:
                self._rollback_restore(
                    layout=layout,
                    settings=settings,
                    settings_path=settings_path,
                    rollback=rollback,
                    state=rollback_state,
                )
                raise

        return RestoreSummary(
            metadata_files=len(movie_metadata) + len(game_metadata),
            cover_files=len(staged_movie_covers),
            cover_conflicts=cover_conflicts,
            game_asset_files=len(staged_game_covers) + len(staged_game_previews) + len(staged_game_archive),
        )

    def suggested_backup_name(self) -> str:
        return f"LocalResourceTerminal_Backup_{datetime.now().strftime('%Y-%m-%d_%H%M')}.zip"

    def _snapshot_sqlite(self, source_path: Path, destination_path: Path) -> None:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(source_path)
        destination = sqlite3.connect(destination_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()

    def _validate_member_name(self, name: str) -> None:
        normalized = name.replace("\\", "/")
        path = PurePosixPath(normalized)
        if not normalized or normalized.startswith("/") or path.is_absolute() or ".." in path.parts:
            raise InvalidBackupError(f"备份包含不安全路径：{name}")
        if path.parts and ":" in path.parts[0]:
            raise InvalidBackupError(f"备份包含不安全路径：{name}")

    def _stage_backup(self, backup_zip: Path, staged: Path) -> None:
        staged.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(backup_zip) as archive:
            for info in archive.infolist():
                self._validate_member_name(info.filename)
                if info.is_dir():
                    continue
                relative = PurePosixPath(info.filename.replace("\\", "/"))
                target = staged.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)

    def _backup_visual_names(
        self, backup_zip: Path, manifest: BackupManifest
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        if not manifest.includes_visual_assets:
            return [], [], [], []
        movie: list[str] = []
        game_covers: list[str] = []
        game_previews: list[str] = []
        game_archive: list[str] = []
        with zipfile.ZipFile(backup_zip) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                parts = PurePosixPath(info.filename.replace("\\", "/")).parts
                if len(parts) == 2 and parts[0] == "covers":
                    movie.append(parts[1])
                elif len(parts) == 3 and parts[:2] == ("game_assets", "covers"):
                    game_covers.append(parts[2])
                elif len(parts) == 3 and parts[:2] == ("game_assets", "previews"):
                    game_previews.append(parts[2])
                elif len(parts) == 3 and parts[:2] == ("game_assets", "archive"):
                    game_archive.append(parts[2])
        return movie, game_covers, game_previews, game_archive

    def _staged_metadata(self, staged: Path, manifest: BackupManifest) -> tuple[list[Path], list[Path]]:
        if manifest.version == 1:
            legacy = self._files_in(staged / "data" / "metadata")
            return legacy, []
        return (
            self._files_in(staged / "data" / "metadata" / "movies"),
            self._files_in(staged / "data" / "metadata" / "games"),
        )

    @staticmethod
    def _files_in(directory: Path) -> list[Path]:
        if not directory.exists():
            return []
        return sorted(path for path in directory.iterdir() if path.is_file())

    def _merge_restored_settings(self, current: AppSettings, backup: AppSettings) -> AppSettings:
        return replace(
            backup,
            data_dir=current.data_dir,
            cover_dir=current.cover_dir,
            libraries=current.libraries,
            player_mode=current.player_mode,
            player_path=current.player_path,
            ffprobe_path=current.ffprobe_path,
            ffmpeg_path=current.ffmpeg_path,
            cover_tool_source_dir=current.cover_tool_source_dir,
        )

    def _snapshot_for_rollback(
        self,
        *,
        layout,
        settings: AppSettings,
        settings_path: Path,
        staged_covers: list[Path],
        staged_game_covers: list[Path],
        staged_game_previews: list[Path],
        staged_game_archive: list[Path],
        rollback: Path,
        restore_identity: bool,
    ) -> dict[str, object]:
        rollback.mkdir(parents=True, exist_ok=True)
        state: dict[str, object] = {
            "had_database": layout.database_path.exists(),
            "had_settings": settings_path.exists(),
            "new_movie_covers": [],
            "new_game_covers": [],
            "new_game_previews": [],
            "new_game_archive": [],
            "restore_identity": restore_identity,
            "had_identity": (settings_path.parent / "identity").exists(),
        }
        if layout.database_path.exists():
            shutil.copy2(layout.database_path, rollback / "library.db")
        self._copy_tree(layout.metadata_dir, rollback / "metadata")
        self._copy_tree(layout.collections_dir, rollback / "collections")
        if settings_path.exists():
            shutil.copy2(settings_path, rollback / "settings.json")
        if restore_identity:
            self._copy_tree(settings_path.parent / "identity", rollback / "identity")
        state["new_movie_covers"] = self._snapshot_named_assets(settings.cover_dir, staged_covers, rollback / "movie_covers")
        state["new_game_covers"] = self._snapshot_named_assets(layout.game_cover_dir, staged_game_covers, rollback / "game_covers")
        state["new_game_previews"] = self._snapshot_named_assets(layout.game_preview_dir, staged_game_previews, rollback / "game_previews")
        state["new_game_archive"] = self._snapshot_named_assets(
            layout.game_archive_media_dir, staged_game_archive, rollback / "game_archive"
        )
        return state

    @staticmethod
    def _snapshot_named_assets(target_dir: Path, staged: list[Path], backup_dir: Path) -> list[str]:
        backup_dir.mkdir(parents=True, exist_ok=True)
        new_names: list[str] = []
        for source in staged:
            target = target_dir / source.name
            if target.exists():
                shutil.copy2(target, backup_dir / source.name)
            else:
                new_names.append(source.name)
        return new_names

    def _apply_database_and_metadata(
        self,
        layout,
        staged_database: Path,
        movie_metadata: list[Path],
        game_metadata: list[Path],
        collection_folders: Path | None,
    ) -> None:
        temporary_db = layout.database_path.with_name(f".{layout.database_path.name}.restore.tmp")
        shutil.copy2(staged_database, temporary_db)
        temporary_db.replace(layout.database_path)
        # Backup state is authoritative for permanent archive trees.
        for directory in (layout.movie_metadata_dir, layout.game_metadata_dir):
            for existing in directory.glob("*.json"):
                existing.unlink()
        for legacy in layout.metadata_dir.glob("*.json"):
            legacy.unlink()
        for source in movie_metadata:
            shutil.copy2(source, layout.movie_metadata_dir / source.name)
        for source in game_metadata:
            shutil.copy2(source, layout.game_metadata_dir / source.name)
        if layout.collections_dir.exists():
            for existing in layout.collections_dir.rglob("*"):
                if existing.is_file():
                    existing.unlink(missing_ok=True)
        if collection_folders is not None:
            layout.collections_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(collection_folders, layout.collection_folders_path)

    def _apply_covers(self, cover_dir: Path, staged_covers: list[Path]) -> None:
        cover_dir.mkdir(parents=True, exist_ok=True)
        for source in staged_covers:
            target = cover_dir / source.name
            temporary = target.with_name(f".{target.name}.restore.tmp")
            shutil.copy2(source, temporary)
            temporary.replace(target)

    def _apply_identity(self, identity_root: Path, staged_identity: Path) -> None:
        temporary = identity_root.with_name(f".{identity_root.name}.restore.tmp")
        if temporary.exists():
            shutil.rmtree(temporary)
        self._copy_tree(staged_identity, temporary)
        if identity_root.exists():
            shutil.rmtree(identity_root)
        temporary.replace(identity_root)

    def _rollback_restore(self, *, layout, settings: AppSettings, settings_path: Path, rollback: Path, state: dict[str, object]) -> None:
        if bool(state["had_database"]):
            shutil.copy2(rollback / "library.db", layout.database_path)
        else:
            layout.database_path.unlink(missing_ok=True)

        if layout.metadata_dir.exists():
            for path in sorted(layout.metadata_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink(missing_ok=True)
        self._copy_tree(rollback / "metadata", layout.metadata_dir)
        if layout.collections_dir.exists():
            for path in sorted(layout.collections_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink(missing_ok=True)
        self._copy_tree(rollback / "collections", layout.collections_dir)

        self._restore_named_assets(
            settings.cover_dir,
            rollback / "movie_covers",
            list(state.get("new_movie_covers", [])),
        )
        self._restore_named_assets(
            layout.game_cover_dir,
            rollback / "game_covers",
            list(state.get("new_game_covers", [])),
        )
        self._restore_named_assets(
            layout.game_preview_dir,
            rollback / "game_previews",
            list(state.get("new_game_previews", [])),
        )
        self._restore_named_assets(
            layout.game_archive_media_dir,
            rollback / "game_archive",
            list(state.get("new_game_archive", [])),
        )

        if bool(state.get("restore_identity")):
            identity_root = settings_path.parent / "identity"
            if identity_root.exists():
                shutil.rmtree(identity_root)
            if bool(state.get("had_identity")):
                self._copy_tree(rollback / "identity", identity_root)

        if bool(state["had_settings"]):
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(rollback / "settings.json", settings_path)
        else:
            settings_path.unlink(missing_ok=True)

    @staticmethod
    def _restore_named_assets(target_dir: Path, backup_dir: Path, new_names: list[str]) -> None:
        for name in new_names:
            (target_dir / str(name)).unlink(missing_ok=True)
        if backup_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            for source in backup_dir.iterdir():
                if source.is_file():
                    shutil.copy2(source, target_dir / source.name)

    @staticmethod
    def _copy_tree(source_dir: Path, destination_dir: Path) -> None:
        if not source_dir.exists():
            return
        for source in source_dir.rglob("*"):
            if source.is_file():
                relative = source.relative_to(source_dir)
                target = destination_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
