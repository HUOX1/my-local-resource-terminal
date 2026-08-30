from __future__ import annotations

import asyncio
from pathlib import Path
import sys

import pytest

from g3_core.backend_app import BackendApplication
from g3_core.paths import TerminalPaths


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


@pytest.mark.asyncio
async def test_backend_can_create_list_and_restore_state(tmp_path):
    app = BackendApplication(_paths(tmp_path), builtin_theme_root=tmp_path / "builtin")
    app.initialize()
    exe = tmp_path / "demo.exe"
    exe.write_bytes(b"")

    created = await app.handle_command(
        "game.create",
        {"title": "Demo", "executable_path": str(exe)},
    )
    games = await app.handle_command("library.games.list", {})
    assert games[0]["id"] == created["id"]
    assert games[0]["title"] == "Demo"

    await app.handle_command(
        "state.update",
        {"last_section": "games", "last_item_id": created["id"]},
    )
    state = await app.handle_command("state.get", {})
    assert state == {"last_section": "games", "last_item_id": created["id"]}


@pytest.mark.asyncio
async def test_game_launch_emits_started_and_exited(tmp_path):
    app = BackendApplication(_paths(tmp_path), builtin_theme_root=tmp_path / "builtin")
    app.initialize()
    game = await app.handle_command(
        "game.create",
        {
            "title": "Sleeper",
            "executable_path": sys.executable,
            "launch_args": '-c "import time; time.sleep(0.05)"',
            "working_directory": str(tmp_path),
        },
    )

    events: list[dict] = []

    async def capture(event_type: str, payload: dict) -> None:
        events.append({"type": event_type, "payload": payload})

    app.set_event_sink(capture)
    result = await app.handle_command("game.launch", {"id": game["id"]})
    assert result["item_id"] == game["id"]
    assert result["pid"] > 0

    for _ in range(100):
        if any(event["type"] == "game.exited" for event in events):
            break
        await asyncio.sleep(0.02)

    assert [event["type"] for event in events][:3] == ["game.started", "game.session_started", "game.exited"]
    assert events[1]["payload"]["item_id"] == game["id"]
