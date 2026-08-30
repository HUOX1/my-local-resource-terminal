from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from websockets.asyncio.client import connect

from terminal_core.backend_app import BackendApplication
from terminal_core.paths import TerminalPaths
from terminal_core.websocket_server import HOST, TerminalWebSocketServer


def _paths(base: Path) -> TerminalPaths:
    root = base / "LocalResourceTerminal" / "v0.6"
    return TerminalPaths(
        root=root,
        database=root / "library.db",
        assets=root / "assets",
        cache=root / "cache",
        themes=root / "themes",
        logs=root / "logs",
        settings=root / "settings.json",
    )


async def smoke() -> None:
    with tempfile.TemporaryDirectory(prefix="lrt-v06-smoke-") as directory:
        base = Path(directory)
        builtin = base / "builtin-themes"
        builtin.mkdir()
        app = BackendApplication(_paths(base), builtin_theme_root=builtin)
        app.initialize()
        server = TerminalWebSocketServer(app.handle_command, port=0)
        app.set_event_sink(server.broadcast)
        await server.start()
        try:
            async with connect(f"ws://{HOST}:{server.bound_port}") as websocket:
                await websocket.send(json.dumps(
                    {"id": "hello", "type": "hello", "payload": {"protocol": 1}}
                ))
                hello = json.loads(await websocket.recv())
                if not hello.get("ok") or hello.get("data", {}).get("protocol") != 1:
                    raise RuntimeError(f"handshake failed: {hello}")
                await websocket.send(json.dumps(
                    {"id": "games", "type": "library.games.list", "payload": {}}
                ))
                games = json.loads(await websocket.recv())
                if not games.get("ok") or games.get("data") != []:
                    raise RuntimeError(f"empty game list failed: {games}")
        finally:
            await server.close()


def main() -> int:
    asyncio.run(smoke())
    print("v0.6 protocol smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
