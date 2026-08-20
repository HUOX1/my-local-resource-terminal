from pathlib import Path


def test_bootstrap_migrates_movie_metadata_before_building_movie_service() -> None:
    source = Path("app/bootstrap.py").read_text(encoding="utf-8")
    migrate_at = source.index("MovieMetadataMigrator().migrate(layout)")
    metadata_at = source.index("MetadataService(layout.movie_metadata_dir)")
    assert migrate_at < metadata_at


def test_bootstrap_builds_parallel_game_services_and_passes_them_to_main_window() -> None:
    source = Path("app/bootstrap.py").read_text(encoding="utf-8")
    for token in (
        "GameRepository(database)",
        "GameMetadataService(layout.game_metadata_dir)",
        "GameAssetService(layout.game_cover_dir, layout.game_preview_dir, layout.game_archive_media_dir)",
        "ScreenshotService(layout.game_screenshot_cache_dir)",
        "GameCatalogService(",
        "GameLauncher()",
        "GameSessionService(",
        "game_catalog=bundle.game_catalog",
        "game_launcher=bundle.game_launcher",
        "game_session_service=bundle.game_session_service",
        "screenshot_service=bundle.screenshot_service",
    ):
        assert token in source


def test_bootstrap_persists_movie_and_game_view_state_without_sidebar_signal() -> None:
    source = Path("app/bootstrap.py").read_text(encoding="utf-8")
    assert "movie_view_state_changed.connect" in source
    assert "game_view_state_changed.connect" in source
    assert "ui_state_changed.connect" not in source
    assert "movie_filter=filter_key" in source
    assert "game_filter=filter_key" in source
