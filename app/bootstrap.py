from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QStandardPaths, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from app.config.data_dirs import (
    DataDirectoryMigrator,
    DataLayout,
    MovieMetadataMigrator,
    ensure_data_layout,
)
from app.config.settings import AppSettings, SettingsStore
from app.db.database import Database
from app.repositories.game_repository import GameRepository
from app.repositories.movie_repository import MovieRepository
from app.services.catalog_service import CatalogService
from app.services.cover_service import CoverService
from app.services.collection_folder_service import CollectionFolderService
from app.services.discovery_service import DiscoveryService
from app.services.game_asset_service import GameAssetService
from app.services.game_catalog_service import GameCatalogService
from app.services.game_launcher import GameLauncher
from app.services.game_metadata_service import GameMetadataService
from app.services.game_session_service import GameSessionService
from app.services.identity_service import IdentityService
from app.services.media_probe import MediaProbe
from app.services.metadata_service import MetadataService
from app.services.player_service import PlayerService
from app.services.scanner import Scanner
from app.services.screenshot_service import ScreenshotService
from app.services.viewing_service import ViewingService
from app.single_instance import SingleInstanceGate
from app.ui.flat_theme import apply_theme
from app.ui.main_window import MainWindow
from app.ui.settings_dialog import SettingsDialog
from app.utils.logging import configure_logging

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ServiceBundle:
    layout: DataLayout
    database: Database
    repository: MovieRepository
    metadata: MetadataService
    media_probe: MediaProbe
    cover_service: CoverService
    catalog: CatalogService
    scanner: Scanner
    player: PlayerService
    viewing: ViewingService
    collection_folders: CollectionFolderService
    game_repository: GameRepository
    game_metadata: GameMetadataService
    game_assets: GameAssetService
    screenshot_service: ScreenshotService
    game_catalog: GameCatalogService
    game_launcher: GameLauncher
    game_session_service: GameSessionService


def default_settings() -> AppSettings:
    base = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    return AppSettings(
        data_dir=base / "data",
        cover_dir=base / "covers",
        libraries=[],
        player_mode="system",
        player_path=None,
        ffprobe_path="ffprobe",
        ffmpeg_path="ffmpeg",
        auto_scan=True,
        ui_theme="flat_pro",
        poster_display_mode="natural",
        sidebar_visible=False,
        sidebar_width=196,
        cover_tool_source_dir=None,
        cover_tool_margin_px=0,
        sort_key="code",
        sort_desc=False,
        startup_library="movies",
        game_sort_key="last_played_at",
        game_sort_desc=True,
        movie_filter="all",
        game_filter="all",
    )


def default_settings_path() -> Path:
    config = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation))
    return config / "settings.json"


def build_services(settings: AppSettings) -> ServiceBundle:
    layout = ensure_data_layout(settings.data_dir)
    settings.cover_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(layout.logs_dir)

    migration = MovieMetadataMigrator().migrate(layout)
    for error in migration.errors:
        logger.warning("movie metadata migration error %s: %s", error.path, error.message)

    database = Database(layout.database_path)
    database.initialize()

    metadata = MetadataService(layout.movie_metadata_dir)
    repository = MovieRepository(database)
    archived_movies, errors = metadata.load_all()
    for error in errors:
        logger.warning("metadata load error %s: %s", error.path, error.message)
    if database.is_empty() and archived_movies:
        repository.rebuild_from_archives(archived_movies)
    elif archived_movies:
        for archived_movie in archived_movies:
            repository.upsert_metadata(archived_movie)

    media_probe = MediaProbe(settings.ffprobe_path)
    cover_service = CoverService(settings.cover_dir, layout.cache_dir, settings.ffmpeg_path)
    catalog = CatalogService(repository, metadata, media_probe, cover_service, settings)
    scanner = Scanner(DiscoveryService(), metadata, repository, media_probe, cover_service)
    player = PlayerService()
    viewing = ViewingService(repository, metadata)
    collection_folders = CollectionFolderService(layout.collection_folders_path)

    game_metadata = GameMetadataService(layout.game_metadata_dir)
    game_repository = GameRepository(database)
    archived_games, game_errors = game_metadata.load_all()
    for error in game_errors:
        logger.warning("game metadata load error %s: %s", error.path, error.message)
    if game_repository.is_empty() and archived_games:
        game_repository.rebuild_from_archives(archived_games)
    elif archived_games:
        for archived_game in archived_games:
            game_repository.upsert_game(archived_game)

    game_assets = GameAssetService(layout.game_cover_dir, layout.game_preview_dir, layout.game_archive_media_dir)
    screenshot_service = ScreenshotService(layout.game_screenshot_cache_dir)
    game_catalog = GameCatalogService(
        game_repository,
        game_metadata,
        game_assets,
        layout.game_screenshot_cache_dir,
    )
    game_launcher = GameLauncher()
    game_session_service = GameSessionService(
        game_repository,
        game_metadata,
        layout.active_game_session_path,
    )
    try:
        game_session_service.recover()
    except Exception as exc:
        logger.warning("game session recovery failed: %s", exc)

    return ServiceBundle(
        layout=layout,
        database=database,
        repository=repository,
        metadata=metadata,
        media_probe=media_probe,
        cover_service=cover_service,
        catalog=catalog,
        scanner=scanner,
        player=player,
        viewing=viewing,
        collection_folders=collection_folders,
        game_repository=game_repository,
        game_metadata=game_metadata,
        game_assets=game_assets,
        screenshot_service=screenshot_service,
        game_catalog=game_catalog,
        game_launcher=game_launcher,
        game_session_service=game_session_service,
    )


def build_application(settings_path: Path | None = None) -> QApplication:
    # Keep the existing application identity so upgrades continue using the same
    # per-user settings location on Windows.
    QCoreApplication.setOrganizationName("LocalMovieManager")
    QCoreApplication.setApplicationName("LocalMovieManager")
    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app, "flat_pro")

    single_instance_gate = SingleInstanceGate("LocalMovieManager.SingleInstance.v1")
    if not single_instance_gate.acquire():
        app._local_movie_manager_secondary_instance = True  # type: ignore[attr-defined]
        app._local_movie_manager_single_instance_gate = single_instance_gate  # type: ignore[attr-defined]
        return app
    app._local_movie_manager_secondary_instance = False  # type: ignore[attr-defined]
    app._local_movie_manager_single_instance_gate = single_instance_gate  # type: ignore[attr-defined]

    path = Path(settings_path) if settings_path else default_settings_path()
    store = SettingsStore(path)
    if path.exists():
        try:
            settings = store.load()
        except Exception as exc:
            QMessageBox.warning(None, "设置文件损坏", f"无法读取设置，将使用默认值。\n\n{exc}")
            settings = default_settings()
            store.save(settings)
    else:
        settings = default_settings()
        store.save(settings)

    apply_theme(app, settings.ui_theme)

    identity_service = IdentityService(path.parent / "identity")

    bundle = build_services(settings)
    window = MainWindow(
        bundle.catalog,
        bundle.scanner,
        settings,
        bundle.cover_service,
        bundle.player,
        bundle.viewing,
        collection_folder_service=bundle.collection_folders,
        game_catalog=bundle.game_catalog,
        game_launcher=bundle.game_launcher,
        game_session_service=bundle.game_session_service,
        screenshot_service=bundle.screenshot_service,
        identity_service=identity_service,
    )

    state = {"settings": settings, "bundle": bundle}

    def activate_existing_window() -> None:
        if window.isMinimized():
            window.showNormal()
        else:
            window.show()
        window.raise_()
        window.activateWindow()

    single_instance_gate.set_activation_handler(activate_existing_window)

    def save_runtime_settings(updated: AppSettings, *, warning_name: str) -> bool:
        try:
            store.save(updated)
        except OSError as exc:
            logger.warning("failed to save %s: %s", warning_name, exc)
            return False
        state["settings"] = updated
        window.settings = updated
        return True

    def open_settings() -> None:
        current_bundle: ServiceBundle = state["bundle"]
        if current_bundle.game_session_service.active_session is not None:
            QMessageBox.information(window, "游戏正在计时", "请先结束当前游戏，再修改设置。")
            return
        current = state["settings"]
        dialog = SettingsDialog(current, window, settings_path=path)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dialog.result_settings
        if updated.data_dir != current.data_dir:
            try:
                DataDirectoryMigrator().migrate(current_bundle.layout, updated.data_dir)
            except FileExistsError:
                use_existing = QMessageBox.question(
                    window,
                    "使用现有数据目录",
                    "目标目录已经包含 library.db。是否直接切换到这个现有数据目录，而不覆盖其中内容？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if use_existing != QMessageBox.StandardButton.Yes:
                    return
            except OSError as exc:
                QMessageBox.warning(window, "数据目录迁移失败", str(exc))
                return
        try:
            store.save(updated)
            if updated.ui_theme != current.ui_theme:
                app._local_movie_manager_restart_requested = True  # type: ignore[attr-defined]
                app.quit()
                return
            new_bundle = build_services(updated)
        except Exception as exc:
            QMessageBox.critical(window, "应用设置失败", str(exc))
            return
        state["settings"] = updated
        state["bundle"] = new_bundle
        window.catalog = new_bundle.catalog
        window.scanner = new_bundle.scanner
        window.cover_service = new_bundle.cover_service
        window.player_service = new_bundle.player
        window.viewing_service = new_bundle.viewing
        window.collection_folders = new_bundle.collection_folders
        window.game_catalog = new_bundle.game_catalog
        window.game_launcher = new_bundle.game_launcher
        window.game_session_service = new_bundle.game_session_service
        window.screenshot_service = new_bundle.screenshot_service
        window.apply_settings(updated)
        window.statusBar().showMessage("设置已应用", 5000)

    def persist_cover_tool_state(source_dir: str, margin_px: int) -> None:
        current = state["settings"]
        source = Path(source_dir) if source_dir else None
        updated = replace(
            current,
            cover_tool_source_dir=source,
            cover_tool_margin_px=max(0, min(int(margin_px), 50)),
        )
        save_runtime_settings(updated, warning_name="cover tool state")

    def persist_movie_view_state(sort_key: str, sort_desc: bool, filter_key: str) -> None:
        current = state["settings"]
        updated = replace(
            current,
            sort_key=sort_key,
            sort_desc=bool(sort_desc),
            movie_filter=filter_key,
        )
        save_runtime_settings(updated, warning_name="movie view state")

    def persist_game_view_state(sort_key: str, sort_desc: bool, filter_key: str) -> None:
        current = state["settings"]
        updated = replace(
            current,
            game_sort_key=sort_key,
            game_sort_desc=bool(sort_desc),
            game_filter=filter_key,
        )
        save_runtime_settings(updated, warning_name="game view state")

    window.settings_requested.connect(open_settings)
    window.cover_tool_state_changed.connect(persist_cover_tool_state)
    window.movie_view_state_changed.connect(persist_movie_view_state)
    window.game_view_state_changed.connect(persist_game_view_state)
    def start_scan_after_identity() -> None:
        settings = state["settings"]
        if settings.auto_scan and settings.libraries:
            QTimer.singleShot(250, window.start_scan)

    window.identity_entered.connect(start_scan_after_identity)
    window.show()

    # Retain the old attribute names so any local launch integrations remain stable.
    app._local_movie_manager_window = window  # type: ignore[attr-defined]
    app._local_movie_manager_state = state  # type: ignore[attr-defined]
    return app
