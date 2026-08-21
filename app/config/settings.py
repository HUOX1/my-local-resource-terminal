from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.config.theme_registry import DEFAULT_THEME_ID, resolve_theme_id


@dataclass(frozen=True, slots=True)
class LibraryConfig:
    id: str
    name: str
    path: Path
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class AppSettings:
    data_dir: Path
    cover_dir: Path
    libraries: list[LibraryConfig]
    player_mode: Literal["system", "custom"] = "system"
    player_path: Path | None = None
    ffprobe_path: str = "ffprobe"
    ffmpeg_path: str = "ffmpeg"
    auto_scan: bool = True
    ui_theme: str = DEFAULT_THEME_ID
    # Retained for backward-compatible settings files. The poster wall now
    # always uses the source image's natural aspect ratio.
    poster_display_mode: Literal["natural", "fit", "fill"] = "natural"
    sidebar_visible: bool = False
    sidebar_width: int = 196
    cover_tool_source_dir: Path | None = None
    cover_tool_margin_px: int = 0
    sort_key: Literal["added_at", "code", "title", "release_date", "rating", "last_watched_at", "play_count"] = "code"
    sort_desc: bool = False
    startup_library: Literal["movies", "games"] = "movies"
    game_sort_key: Literal["added_at", "title", "release_date", "rating", "total_play_seconds", "last_played_at", "play_count"] = "last_played_at"
    game_sort_desc: bool = True
    movie_filter: Literal["all", "favorite", "watched", "unwatched"] = "all"
    game_filter: Literal["all", "favorite", "installed", "uninstalled", "recent"] = "all"


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> AppSettings:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        # v0.2.1 used fit/fill in a fixed poster box. v0.2.2 replaces that
        # layout with natural-aspect posters, so old values migrate once.
        poster_display_mode = payload.get("poster_display_mode", "natural")
        if poster_display_mode != "natural":
            poster_display_mode = "natural"
        sidebar_width = payload.get("sidebar_width", 196)
        try:
            sidebar_width = int(sidebar_width)
        except (TypeError, ValueError):
            sidebar_width = 196
        sidebar_width = 72 if sidebar_width <= 104 else 196
        cover_tool_margin_px = payload.get("cover_tool_margin_px", 0)
        try:
            cover_tool_margin_px = int(cover_tool_margin_px)
        except (TypeError, ValueError):
            cover_tool_margin_px = 0
        cover_tool_margin_px = max(0, min(cover_tool_margin_px, 50))
        sort_key = str(payload.get("sort_key", "code"))
        valid_sort_keys = {"added_at", "code", "title", "release_date", "rating", "last_watched_at", "play_count"}
        if sort_key not in valid_sort_keys:
            sort_key = "code"
        startup_library = str(payload.get("startup_library", "movies"))
        if startup_library not in {"movies", "games"}:
            startup_library = "movies"
        game_sort_key = str(payload.get("game_sort_key", "last_played_at"))
        valid_game_sort_keys = {"added_at", "title", "release_date", "rating", "total_play_seconds", "last_played_at", "play_count"}
        if game_sort_key not in valid_game_sort_keys:
            game_sort_key = "last_played_at"
        movie_filter = str(payload.get("movie_filter", "all"))
        if movie_filter not in {"all", "favorite", "watched", "unwatched"}:
            movie_filter = "all"
        ui_theme = resolve_theme_id(str(payload.get("ui_theme", DEFAULT_THEME_ID)))
        game_filter = str(payload.get("game_filter", "all"))
        if game_filter not in {"all", "favorite", "installed", "uninstalled", "recent"}:
            game_filter = "all"
        return AppSettings(
            data_dir=Path(payload["data_dir"]),
            cover_dir=Path(payload["cover_dir"]),
            libraries=[
                LibraryConfig(
                    id=item["id"],
                    name=item["name"],
                    path=Path(item["path"]),
                    enabled=bool(item.get("enabled", True)),
                )
                for item in payload.get("libraries", [])
            ],
            player_mode=payload.get("player_mode", "system"),
            player_path=Path(payload["player_path"]) if payload.get("player_path") else None,
            ffprobe_path=payload.get("ffprobe_path", "ffprobe"),
            ffmpeg_path=payload.get("ffmpeg_path", "ffmpeg"),
            auto_scan=bool(payload.get("auto_scan", True)),
            ui_theme=ui_theme,
            poster_display_mode=poster_display_mode,
            sidebar_visible=bool(payload.get("sidebar_visible", False)),
            sidebar_width=sidebar_width,
            cover_tool_source_dir=Path(payload["cover_tool_source_dir"]) if payload.get("cover_tool_source_dir") else None,
            cover_tool_margin_px=cover_tool_margin_px,
            sort_key=sort_key,
            sort_desc=bool(payload.get("sort_desc", False)),
            startup_library=startup_library,
            game_sort_key=game_sort_key,
            game_sort_desc=bool(payload.get("game_sort_desc", True)),
            movie_filter=movie_filter,
            game_filter=game_filter,
        )

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "data_dir": str(settings.data_dir),
            "cover_dir": str(settings.cover_dir),
            "libraries": [
                {
                    "id": item.id,
                    "name": item.name,
                    "path": str(item.path),
                    "enabled": item.enabled,
                }
                for item in settings.libraries
            ],
            "player_mode": settings.player_mode,
            "player_path": str(settings.player_path) if settings.player_path else None,
            "ffprobe_path": settings.ffprobe_path,
            "ffmpeg_path": settings.ffmpeg_path,
            "auto_scan": settings.auto_scan,
            "ui_theme": settings.ui_theme,
            "poster_display_mode": "natural",
            "sidebar_visible": settings.sidebar_visible,
            "sidebar_width": settings.sidebar_width,
            "cover_tool_source_dir": str(settings.cover_tool_source_dir) if settings.cover_tool_source_dir else None,
            "cover_tool_margin_px": settings.cover_tool_margin_px,
            "sort_key": settings.sort_key,
            "sort_desc": settings.sort_desc,
            "startup_library": settings.startup_library,
            "game_sort_key": settings.game_sort_key,
            "game_sort_desc": settings.game_sort_desc,
            "movie_filter": settings.movie_filter,
            "game_filter": settings.game_filter,
        }
        temporary = self.path.with_name(f"{self.path.name}.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
