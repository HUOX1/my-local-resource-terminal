from __future__ import annotations

import asyncio
from pathlib import Path

from .backend_app import BackendApplication
from .logging_setup import configure_logging
from .paths import TerminalPaths
from .websocket_server import HOST, PORT, TerminalWebSocketServer


async def run_backend() -> None:
    paths = TerminalPaths.from_environment().ensure()
    configure_logging(paths.logs)
    builtin_themes = Path(__file__).resolve().parent.parent / "godot_frontend" / "themes"
    app = BackendApplication(paths, builtin_theme_root=builtin_themes)
    app.initialize()
    server = TerminalWebSocketServer(app.handle_command, host=HOST, port=PORT)
    app.set_event_sink(server.broadcast)
    await server.start()
    try:
        await asyncio.Future()
    finally:
        await server.close()


def main() -> int:
    try:
        asyncio.run(run_backend())
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
