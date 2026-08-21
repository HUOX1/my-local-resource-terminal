from pathlib import Path


def test_build_services_loads_both_archive_domains_and_recovers_session_last() -> None:
    source = Path("app/bootstrap.py").read_text(encoding="utf-8")
    movie_migration = source.index("MovieMetadataMigrator().migrate(layout)")
    movie_service = source.index("MetadataService(layout.movie_metadata_dir)")
    game_service = source.index("GameMetadataService(layout.game_metadata_dir)")
    game_load = source.index("game_metadata.load_all()")
    session_service = source.index("game_session_service = GameSessionService(")
    recovery = source.index("game_session_service.recover()")
    assert movie_migration < movie_service
    assert game_service < game_load < session_service < recovery
    assert "game_repository.rebuild_from_archives(archived_games)" in source
    assert "game_repository.upsert_game(archived_game)" in source


def test_startup_library_is_owned_by_settings_and_main_window() -> None:
    settings_source = Path("app/config/settings.py").read_text(encoding="utf-8")
    window_source = Path("app/ui/main_window.py").read_text(encoding="utf-8")
    assert 'startup_library: Literal["movies", "games"] = "movies"' in settings_source
    assert 'self.switch_library(getattr(settings, "startup_library", "movies"), clear_search=False)' in window_source
