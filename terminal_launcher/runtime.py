from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import subprocess

from terminal_core.backend_app import BackendApplication
from terminal_core.logging_setup import configure_logging
from terminal_core.paths import TerminalPaths
from terminal_core.websocket_server import HOST, PORT, TerminalWebSocketServer

from .discovery import resolve_godot_executable


logger = logging.getLogger("local_resource_terminal.launcher")


def build_godot_command(executable: Path, project_directory: Path) -> list[str]:
    return [str(Path(executable).resolve()), "--path", str(Path(project_directory).resolve())]


async def run_terminal(
    *,
    repo_root: Path | None = None,
    paths: TerminalPaths | None = None,
) -> int:
    repository_root = (
        Path(repo_root).resolve()
        if repo_root is not None
        else Path(__file__).resolve().parent.parent
    )
    runtime_paths = paths or TerminalPaths.from_environment()
    runtime_paths.ensure()
    configure_logging(runtime_paths.logs)

    builtin_themes = repository_root / "godot_frontend" / "themes"
    frontend = repository_root / "godot_frontend"
    if not (frontend / "project.godot").is_file():
        raise FileNotFoundError(frontend / "project.godot")

    app = BackendApplication(runtime_paths, builtin_theme_root=builtin_themes)
    app.initialize()
    godot_executable = resolve_godot_executable(app.settings)
    app.settings.save(runtime_paths.settings)

    server = TerminalWebSocketServer(app.handle_command, host=HOST, port=PORT)
    app.set_event_sink(server.broadcast)
    await server.start()
    logger.info("Backend listening on ws://%s:%d", HOST, PORT)

    creationflags = 0
    if os.name == "nt":
        creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    process: subprocess.Popen | None = None
    try:
        command = build_godot_command(godot_executable, frontend)
        logger.info("Starting Godot frontend: %s", godot_executable)
        process = subprocess.Popen(
            command,
            cwd=str(repository_root),
            shell=False,
            creationflags=creationflags,
        )
        return int(await asyncio.to_thread(process.wait))
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
        await server.close()
        logger.info("Terminal launcher stopped")
