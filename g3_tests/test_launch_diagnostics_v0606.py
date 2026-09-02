from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import sys

import pytest
from websockets.asyncio.client import connect

from g3_core.database import Database
from g3_core.models import CreateGame
from g3_core.repository import LibraryRepository
from g3_core.services.game_runtime import GameRuntime
from g3_core.settings import TerminalSettings
from g3_core.websocket_server import TerminalWebSocketServer


def _repo(tmp_path: Path) -> LibraryRepository:
    db = Database(tmp_path / "library.db")
    db.initialize()
    return LibraryRepository(db)


def test_missing_game_launch_is_logged_with_exe_cwd_and_args(tmp_path, caplog):
    repo = _repo(tmp_path)
    game = repo.create_game(CreateGame(title="Demo", executable_path=Path(sys.executable)))
    game.executable_path = tmp_path / "missing.exe"
    game.working_directory = str(tmp_path)
    game.launch_args = "--demo"
    runtime = GameRuntime(repo)
    with caplog.at_level(logging.INFO, logger="g3.game_runtime"):
        with pytest.raises(FileNotFoundError):
            runtime.launch(game)
    joined = "\n".join(record.getMessage() for record in caplog.records)
    assert "missing.exe" in joined
    assert str(tmp_path) in joined
    assert "--demo" in joined
    assert "Game launch failed" in joined


@pytest.mark.asyncio
async def test_websocket_logs_command_exception_and_returns_message(caplog):
    async def handler(command_type: str, payload: dict):
        if command_type == "explode":
            raise OSError("synthetic launch error")
        return {}

    server = TerminalWebSocketServer(handler, port=0)
    await server.start()
    try:
        with caplog.at_level(logging.ERROR, logger="g3.websocket"):
            async with connect(f"ws://127.0.0.1:{server.bound_port}") as ws:
                await ws.send(json.dumps({"id":"h","type":"hello","payload":{"protocol":1}}))
                await ws.recv()
                await ws.send(json.dumps({"id":"x","type":"explode","payload":{"id":"g1"}}))
                response = json.loads(await ws.recv())
        assert response["ok"] is False
        assert "synthetic launch error" in response["error"]["message"]
        assert any("explode" in rec.getMessage() for rec in caplog.records)
    finally:
        await server.close()


def test_old_violet_settings_migrate_once_to_cyan(tmp_path):
    path = tmp_path / "settings.json"
    old = TerminalSettings.default().to_dict()
    old.pop("settings_schema", None)
    old["current_theme"] = "classic_violet"
    path.write_text(json.dumps(old), encoding="utf-8")
    migrated = TerminalSettings.load(path)
    assert migrated.current_theme == "classic_cyan"
    assert migrated.settings_schema == 2


def test_debug_launcher_enables_console_logging():
    batch = (Path(__file__).parents[1] / "run_windows_debug.bat").read_text(encoding="utf-8")
    logging_source = (Path(__file__).parents[1] / "g3_core/logging_setup.py").read_text(encoding="utf-8")
    assert 'set "G3_DEBUG_CONSOLE=1"' in batch
    assert 'os.environ.get("G3_DEBUG_CONSOLE") == "1"' in logging_source
    assert 'logging.StreamHandler()' in logging_source


def test_windows_shell_fallback_command_preserves_exe_and_args(tmp_path):
    from g3_core.services.game_runtime import build_windows_shell_command

    exe = tmp_path / "My Game.exe"
    command = build_windows_shell_command(exe, ["--profile", "A B"])
    assert command[:7] == ["cmd.exe", "/d", "/s", "/c", "start", "", "/wait"]
    assert command[7] == str(exe)
    assert command[8:] == ["--profile", "A B"]
