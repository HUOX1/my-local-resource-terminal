from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Awaitable, Callable

from .database import Database
from .models import CreateGame, GameRecord, LaunchProfile
from .paths import TerminalPaths
from .repository import LibraryRepository
from .services.game_runtime import GameRuntime, GameExit
from .services.media_assets import MediaAssetService, PreviewManifest
from .services.themes import ThemeManifest, ThemeService
from .settings import TerminalSettings


logger = logging.getLogger("g3.backend")
EventSink = Callable[[str, dict[str, object]], Awaitable[None]]


async def _noop_event_sink(event_type: str, payload: dict[str, object]) -> None:
    return None


class BackendApplication:
    def __init__(self, paths: TerminalPaths, *, builtin_theme_root: Path) -> None:
        self.paths = paths
        self.database = Database(paths.database)
        self.repository = LibraryRepository(self.database)
        self.settings = TerminalSettings.default()
        self.media = MediaAssetService(self.repository, paths.cache)
        self.themes = ThemeService(
            builtin_root=Path(builtin_theme_root),
            user_root=paths.themes,
        )
        self.runtime = GameRuntime(self.repository)
        self._event_sink: EventSink = _noop_event_sink
        self._game_tasks: set[asyncio.Task[None]] = set()

    def initialize(self) -> None:
        self.paths.ensure()
        self.database.initialize()
        self.settings = TerminalSettings.load(self.paths.settings)
        self.settings.save(self.paths.settings)

    def set_event_sink(self, sink: EventSink) -> None:
        self._event_sink = sink

    async def handle_command(self, command_type: str, payload: dict) -> object:
        if command_type == "library.games.list":
            return [self._game_to_dict(item) for item in self.repository.list_games()]
        if command_type == "game.create":
            game = self.repository.create_game(
                CreateGame(
                    title=str(payload.get("title", "")),
                    executable_path=Path(str(payload.get("executable_path", ""))),
                    launch_args=str(payload.get("launch_args", "")),
                    working_directory=str(payload.get("working_directory", "")),
                    platform=str(payload.get("platform", "")),
                )
            )
            await self._event_sink("library.changed", {"media_type": "game"})
            return self._game_to_dict(game)
        if command_type == "game.preview":
            item_id = self._require_id(payload)
            return self._preview_to_dict(self.media.resolve_preview(item_id))
        if command_type == "game.launch_profile.get":
            item_id = self._require_id(payload)
            return self._profile_to_dict(self.repository.get_launch_profile(item_id))
        if command_type == "game.launch_profile.update":
            item_id = self._require_id(payload)
            profile = self._profile_from_payload(payload)
            updated = self.repository.update_launch_profile(item_id, profile)
            await self._event_sink("library.changed", {"media_type": "game", "item_id": item_id})
            return self._profile_to_dict(updated)
        if command_type == "game.launch":
            return await self._launch_game(self._require_id(payload))
        if command_type == "settings.get":
            return self.settings.to_dict()
        if command_type == "settings.update":
            merged = self.settings.to_dict()
            merged.update(payload)
            self.settings = TerminalSettings.from_dict(merged)
            self.settings.save(self.paths.settings)
            return self.settings.to_dict()
        if command_type == "state.get":
            return self.repository.get_state()
        if command_type == "state.update":
            self.repository.update_state(payload)
            return self.repository.get_state()
        if command_type == "theme.current":
            manifest = self.themes.load(self.settings.current_theme)
            return self._theme_to_dict(manifest)
        raise KeyError(f"unknown command: {command_type}")

    async def _launch_game(self, item_id: str) -> dict[str, object]:
        game = self.repository.get_game(item_id)
        if game is None:
            raise KeyError(item_id)
        try:
            running = self.runtime.launch(game)
        except Exception:
            logger.exception("Game launch failed before session watch: item_id=%s", item_id)
            raise
        await self._event_sink(
            "game.started",
            {
                "item_id": item_id,
                "pid": int(running.launch_pid),
                "profile_type": running.profile.profile_type,
            },
        )
        task = asyncio.create_task(self._watch_game(running))
        self._game_tasks.add(task)
        task.add_done_callback(self._game_tasks.discard)
        return {
            "item_id": item_id,
            "pid": int(running.launch_pid),
            "profile_type": running.profile.profile_type,
        }

    async def _watch_game(self, running) -> None:
        try:
            session_started = await self.runtime.wait_for_session_start(running)
            await self._event_sink(
                "game.session_started",
                {
                    "item_id": running.item_id,
                    "monitor_exe": str(running.profile.monitor_exe or ""),
                    "started_at": session_started.isoformat(),
                },
            )
            result: GameExit = await self.runtime.wait_for_exit(running, session_started)
            await self._event_sink(
                "game.exited",
                {
                    "item_id": result.item_id,
                    "elapsed_seconds": result.elapsed_seconds,
                    "exit_code": result.exit_code,
                    "ended_at": result.ended_at.isoformat(),
                },
            )
        except TimeoutError as exc:
            logger.exception("Game session monitor timeout: item_id=%s", running.item_id)
            await self._event_sink(
                "backend.error",
                {
                    "code": "game_session_timeout",
                    "item_id": running.item_id,
                    "message": str(exc),
                },
            )
        except Exception as exc:
            logger.exception("Game session watch failed: item_id=%s", running.item_id)
            await self._event_sink(
                "backend.error",
                {
                    "code": "game_watch_failed",
                    "item_id": running.item_id,
                    "message": str(exc),
                },
            )

    @staticmethod
    def _require_id(payload: dict) -> str:
        item_id = payload.get("id")
        if not isinstance(item_id, str) or not item_id:
            raise ValueError("id must be a non-empty string")
        return item_id

    @staticmethod
    def _profile_from_payload(payload: dict) -> LaunchProfile:
        launch_exe = str(payload.get("launch_exe", "")).strip()
        if not launch_exe:
            raise ValueError("launch_exe is required")
        working_directory = str(payload.get("working_directory", "")).strip()
        content_path = str(payload.get("content_path", "")).strip()
        monitor_exe = str(payload.get("monitor_exe", "")).strip()
        return LaunchProfile(
            profile_type=str(payload.get("profile_type", "direct")),
            launch_exe=Path(launch_exe),
            launch_args=str(payload.get("launch_args", "")),
            working_directory=Path(working_directory) if working_directory else None,
            content_path=Path(content_path) if content_path else None,
            monitor_exe=Path(monitor_exe) if monitor_exe else None,
            wait_timeout_s=int(payload.get("wait_timeout_s", 300)),
            run_as_admin=bool(payload.get("run_as_admin", False)),
        )

    def _game_to_dict(self, game: GameRecord) -> dict[str, object]:
        cover_asset = self.repository.best_media_asset(game.id, "cover")
        profile = game.launch_profile
        return {
            "id": game.id,
            "title": game.title,
            "sort_title": game.sort_title,
            "description": game.description,
            "executable_path": str(game.executable_path),
            "launch_args": game.launch_args,
            "working_directory": game.working_directory,
            "launch_profile": self._profile_to_dict(profile),
            "platform": game.platform,
            "playtime_seconds": game.playtime_seconds,
            "last_played_at": game.last_played_at.isoformat() if game.last_played_at else None,
            "installed_state": game.installed_state,
            "cover": str(cover_asset.path) if cover_asset else "",
        }

    @staticmethod
    def _profile_to_dict(profile: LaunchProfile) -> dict[str, object]:
        return {
            "profile_type": profile.profile_type,
            "launch_exe": str(profile.launch_exe or ""),
            "launch_args": profile.launch_args,
            "working_directory": str(profile.working_directory or ""),
            "content_path": str(profile.content_path or ""),
            "monitor_exe": str(profile.monitor_exe or ""),
            "wait_timeout_s": profile.wait_timeout_s,
            "run_as_admin": profile.run_as_admin,
        }

    @staticmethod
    def _preview_to_dict(manifest: PreviewManifest) -> dict[str, object]:
        return {
            "cover": str(manifest.cover) if manifest.cover else "",
            "background": str(manifest.background) if manifest.background else "",
            "screenshots": [str(path) for path in manifest.screenshots],
            "gif_frames": [str(path) for path in manifest.gif_frames],
            "gif_durations_ms": manifest.gif_durations_ms,
            "video_ogv": str(manifest.video_ogv) if manifest.video_ogv else "",
            "preview_audio": str(manifest.preview_audio) if manifest.preview_audio else "",
            "logo": str(manifest.logo) if manifest.logo else "",
        }

    @staticmethod
    def _theme_to_dict(manifest: ThemeManifest) -> dict[str, object]:
        return {
            "id": manifest.id,
            "name": manifest.name,
            "colors": manifest.colors,
            "ambient": manifest.ambient,
            "audio": manifest.audio,
            "icons": manifest.icons,
            "transitions": manifest.transitions,
            "directory": str(manifest.directory),
        }
