from pathlib import Path

from app.config.data_dirs import ensure_data_layout
from app.config.settings import AppSettings, LibraryConfig, SettingsStore


def test_settings_round_trip(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    settings = AppSettings(
        data_dir=tmp_path / "data",
        cover_dir=tmp_path / "covers",
        libraries=[LibraryConfig("main", "主收藏", tmp_path / "movies", True)],
        player_mode="system",
        player_path=None,
        ffprobe_path="ffprobe",
        ffmpeg_path="ffmpeg",
        auto_scan=True,
        poster_display_mode="natural",
    )

    store.save(settings)

    assert store.load() == settings


def test_old_settings_default_to_natural_poster_mode(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    store.path.write_text(
        """{
  \"data_dir\": \"D:/data\",
  \"cover_dir\": \"D:/covers\",
  \"libraries\": []
}""",
        encoding="utf-8",
    )

    loaded = store.load()

    assert loaded.poster_display_mode == "natural"


def test_ensure_data_layout_creates_expected_directories(tmp_path: Path) -> None:
    layout = ensure_data_layout(tmp_path / "data")

    assert layout.database_path == tmp_path / "data" / "library.db"
    assert layout.metadata_dir.is_dir()
    assert layout.thumbnail_cache_dir.is_dir()
    assert layout.generated_cover_dir.is_dir()
    assert layout.logs_dir.is_dir()


def test_data_directory_migration_copies_db_and_metadata_but_not_cache(tmp_path: Path) -> None:
    from app.config.data_dirs import DataDirectoryMigrator

    old = ensure_data_layout(tmp_path / "old")
    old.database_path.write_bytes(b"db")
    (old.metadata_dir / "a.json").write_text("{}", encoding="utf-8")
    (old.thumbnail_cache_dir / "temp.jpg").write_bytes(b"cache")

    new = DataDirectoryMigrator().migrate(old, tmp_path / "new")

    assert new.database_path.read_bytes() == b"db"
    assert (new.metadata_dir / "a.json").exists()
    assert not (new.thumbnail_cache_dir / "temp.jpg").exists()


def test_ui_sidebar_width_migrates_to_two_state_expanded_width(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    settings = AppSettings(
        data_dir=tmp_path / "data",
        cover_dir=tmp_path / "covers",
        libraries=[],
        sidebar_visible=True,
        sidebar_width=205,
    )

    store.save(settings)
    loaded = store.load()

    assert loaded.sidebar_visible is True
    assert loaded.sidebar_width == 196


def test_old_settings_default_sidebar_uses_pro_expanded_width(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    store.path.write_text(
        '{"data_dir":"D:/data","cover_dir":"D:/covers","libraries":[]}',
        encoding="utf-8",
    )

    loaded = store.load()

    assert loaded.sidebar_visible is False
    assert loaded.sidebar_width == 196


def test_cover_tool_preferences_round_trip(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    settings = AppSettings(
        data_dir=tmp_path / "data",
        cover_dir=tmp_path / "covers",
        libraries=[],
        cover_tool_source_dir=tmp_path / "raw-covers",
        cover_tool_margin_px=7,
    )

    store.save(settings)
    loaded = store.load()

    assert loaded.cover_tool_source_dir == tmp_path / "raw-covers"
    assert loaded.cover_tool_margin_px == 7


def test_old_settings_default_cover_tool_preferences(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    store.path.write_text(
        '{"data_dir":"D:/data","cover_dir":"D:/covers","libraries":[]}',
        encoding="utf-8",
    )

    loaded = store.load()

    assert loaded.cover_tool_source_dir is None
    assert loaded.cover_tool_margin_px == 0


def test_sort_preferences_round_trip_and_old_defaults(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    settings = AppSettings(
        data_dir=tmp_path / "data",
        cover_dir=tmp_path / "covers",
        libraries=[],
        sort_key="rating",
        sort_desc=True,
    )
    store.save(settings)
    loaded = store.load()
    assert loaded.sort_key == "rating"
    assert loaded.sort_desc is True

    store.path.write_text(
        '{"data_dir":"D:/data","cover_dir":"D:/covers","libraries":[]}',
        encoding="utf-8",
    )
    legacy = store.load()
    assert legacy.sort_key == "code"
    assert legacy.sort_desc is False
