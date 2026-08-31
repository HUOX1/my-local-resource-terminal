from __future__ import annotations

from pathlib import Path
import sys

import pytest

from g3_core.backend_app import BackendApplication
from g3_core.database import Database
from g3_core.models import CreateGame
from g3_core.paths import TerminalPaths
from g3_core.repository import LibraryRepository
from g3_core.services.game_runtime import GameRuntime
from g3_core.services.process_monitor import ProcessMonitor

ROOT = Path(__file__).parents[1]
CASE = ROOT / "g3_frontend/scripts/game_case_3d.gd"
CAROUSEL = ROOT / "g3_frontend/scripts/game_carousel.gd"
MAIN = ROOT / "g3_frontend/scripts/main.gd"
PREVIEW = ROOT / "g3_frontend/scripts/preview_panel.gd"
METADATA_DIALOG = ROOT / "g3_frontend/scripts/game_metadata_dialog.gd"


def _paths(tmp_path: Path) -> TerminalPaths:
    root = tmp_path / "G3"
    return TerminalPaths(
        root=root,
        database=root / "library.db",
        assets=root / "assets",
        cache=root / "cache",
        themes=root / "themes",
        logs=root / "logs",
        settings=root / "settings.json",
    )


def _repo(tmp_path: Path) -> LibraryRepository:
    db = Database(tmp_path / "library.db")
    db.initialize()
    return LibraryRepository(db)


def test_focus_case_is_large_front_facing_and_hover_only_tilts():
    case_text = CASE.read_text(encoding="utf-8")
    carousel_text = CAROUSEL.read_text(encoding="utf-8")
    assert "const BASE_YAW_DEGREES: float = 0.0" in case_text
    assert "const HOVER_YAW_DEGREES: float = 12.0" in case_text
    assert "hover_vector.x * HOVER_YAW_DEGREES" in case_text
    assert "const PREVIEW_SELECTED_SCALE: float = 2.18" in carousel_text
    assert "PREVIEW_SELECTED_SCALE" in carousel_text


def test_cover_is_unshaded_and_slightly_dimmed_for_print_clarity():
    text = CASE.read_text(encoding="utf-8")
    assert "BaseMaterial3D.SHADING_MODE_UNSHADED" in text
    assert "const COVER_PRINT_BRIGHTNESS: float = 0.90" in text
    assert "Color(COVER_PRINT_BRIGHTNESS" in text


def test_product_lighting_adds_subtle_ssao_for_case_recesses():
    text = MAIN.read_text(encoding="utf-8")
    assert "environment.ssao_enabled = true" in text
    assert "environment.ssao_radius = 0.18" in text
    assert "environment.ssao_intensity = 1.10" in text


def test_main_minimizes_instead_of_hiding_main_window_for_gameplay():
    text = MAIN.read_text(encoding="utf-8")
    assert "get_window().mode = Window.MODE_MINIMIZED" not in text
    assert "window.mode = Window.MODE_MINIMIZED" in text
    assert "get_window().hide()" not in text
    assert "get_window().show()" not in text


def test_existing_v0614_database_gains_metadata_table_on_initialize(tmp_path):
    import sqlite3

    db_path = tmp_path / "library.db"
    schema = (ROOT / "g3_core/schema.sql").read_text(encoding="utf-8")
    start = schema.index("CREATE TABLE IF NOT EXISTS game_metadata")
    end = schema.index("CREATE TABLE IF NOT EXISTS media_assets", start)
    old_schema = schema[:start] + schema[end:]
    with sqlite3.connect(db_path) as conn:
        conn.executescript(old_schema)
    db = Database(db_path)
    assert "game_metadata" not in db.table_names()
    db.initialize()
    assert "game_metadata" in db.table_names()


def test_metadata_schema_and_repository_round_trip(tmp_path):
    repo = _repo(tmp_path)
    assert "game_metadata" in repo.database.table_names()
    exe = tmp_path / "demo.exe"
    exe.write_bytes(b"")
    game = repo.create_game(CreateGame(title="Demo", executable_path=exe))

    updated = repo.update_game_metadata(
        game.id,
        title="Rain World",
        platform="PC",
        description="一场关于蛞蝓猫、雨与循环的旅程。",
        developer="Videocult",
        publisher="Akupara Games",
        release_year=2017,
        tags="生存, 平台, 探索",
        notes="这是我写给 G3 聚焦页看的收藏备注。",
    )

    assert updated.title == "Rain World"
    assert updated.platform == "PC"
    assert updated.description.startswith("一场关于")
    assert updated.developer == "Videocult"
    assert updated.publisher == "Akupara Games"
    assert updated.release_year == 2017
    assert updated.tags == "生存, 平台, 探索"
    assert updated.notes.startswith("这是我写给")


@pytest.mark.asyncio
async def test_backend_metadata_update_refreshes_library_payload(tmp_path):
    app = BackendApplication(_paths(tmp_path), builtin_theme_root=tmp_path / "builtin")
    app.initialize()
    exe = tmp_path / "demo.exe"
    exe.write_bytes(b"")
    created = await app.handle_command("game.create", {"title": "Demo", "executable_path": str(exe)})

    events: list[tuple[str, dict]] = []

    async def capture(event_type: str, payload: dict) -> None:
        events.append((event_type, payload))

    app.set_event_sink(capture)
    saved = await app.handle_command(
        "game.metadata.update",
        {
            "id": created["id"],
            "title": "Rain World",
            "platform": "PC",
            "description": "聚焦页面测试简介",
            "developer": "Videocult",
            "publisher": "Akupara Games",
            "release_year": 2017,
            "tags": "生存,探索",
            "notes": "右侧布局测试备注",
        },
    )
    assert saved["title"] == "Rain World"
    assert saved["developer"] == "Videocult"
    assert events[-1][0] == "library.changed"

    listed = await app.handle_command("library.games.list", {})
    assert listed[0]["description"] == "聚焦页面测试简介"
    assert listed[0]["release_year"] == 2017
    assert listed[0]["notes"] == "右侧布局测试备注"


def test_edit_metadata_dialog_and_preview_layout_are_real_ui():
    assert METADATA_DIALOG.exists()
    dialog = METADATA_DIALOG.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    preview = PREVIEW.read_text(encoding="utf-8")
    assert 'title = "编辑资料"' in dialog
    for label in ["标题", "平台", "开发商", "发行商", "发行年份", "标签", "简介", "收藏备注"]:
        assert label in dialog
    assert 'backend.request("game.metadata.get"' in main
    assert 'backend.request("game.metadata.update"' in main
    assert "game_metadata_dialog.show_metadata" in main
    assert 'game.get("developer"' in preview
    assert 'game.get("publisher"' in preview
    assert 'game.get("release_year"' in preview
    assert 'game.get("tags"' in preview
    assert 'game.get("notes"' in preview


def test_winerror_740_promotes_to_uac_and_waits_for_real_monitor(tmp_path):
    repo = _repo(tmp_path)
    exe = tmp_path / "RainWorld.exe"
    exe.write_bytes(b"")
    game = repo.create_game(CreateGame(title="RainWorld", executable_path=exe))

    calls: list[tuple[Path, list[str], Path]] = []

    def needs_elevation(*args, **kwargs):
        exc = OSError(740, "请求的操作需要提升")
        exc.winerror = 740
        raise exc

    def elevated(executable: Path, arguments: list[str], cwd: Path) -> None:
        calls.append((executable, arguments, cwd))

    snapshots = iter([set(), {str(exe.resolve())}])
    last: set[str] = set()

    def process_paths():
        nonlocal last
        try:
            last = next(snapshots)
        except StopIteration:
            pass
        return last

    monitor = ProcessMonitor(process_paths=process_paths, sleep=lambda _: None, poll_interval_s=0.0)
    runtime = GameRuntime(repo, monitor=monitor, popen=needs_elevation, elevated_launch=elevated)
    running = runtime.launch(game)
    assert running.process is None
    assert running.launch_pid == 0
    assert calls and calls[0][0] == exe.resolve()
    started = runtime.wait_for_session_start_blocking(running)
    assert started is not None
