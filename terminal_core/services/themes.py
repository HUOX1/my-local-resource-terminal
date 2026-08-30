from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


class ThemeError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ThemeManifest:
    id: str
    name: str
    colors: dict[str, Any]
    ambient: dict[str, Any]
    audio: dict[str, Any]
    icons: dict[str, Any]
    transitions: dict[str, Any]
    directory: Path


class ThemeService:
    def __init__(self, *, builtin_root: Path, user_root: Path) -> None:
        self.builtin_root = Path(builtin_root)
        self.user_root = Path(user_root)

    def list_themes(self) -> list[ThemeManifest]:
        merged: dict[str, ThemeManifest] = {}
        for root in (self.builtin_root, self.user_root):
            if not root.is_dir():
                continue
            for path in sorted(root.iterdir()):
                manifest_path = path / "theme.json"
                if not manifest_path.is_file():
                    continue
                manifest = self._load_manifest(manifest_path)
                merged[manifest.id] = manifest
        return sorted(merged.values(), key=lambda item: (item.name.casefold(), item.id))

    def load(self, theme_id: str) -> ThemeManifest:
        for root in (self.user_root, self.builtin_root):
            manifest_path = root / theme_id / "theme.json"
            if manifest_path.is_file():
                return self._load_manifest(manifest_path)
        raise FileNotFoundError(theme_id)

    def _load_manifest(self, path: Path) -> ThemeManifest:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ThemeError(str(exc)) from exc
        if not isinstance(payload, dict):
            raise ThemeError("theme manifest root must be an object")

        required = ("id", "name", "colors", "ambient")
        missing = [key for key in required if key not in payload]
        if missing:
            raise ThemeError(f"missing theme field(s): {', '.join(missing)}")

        theme_id = payload["id"]
        name = payload["name"]
        colors = payload["colors"]
        ambient = payload["ambient"]
        if not isinstance(theme_id, str) or not theme_id:
            raise ThemeError("theme id must be a non-empty string")
        if not isinstance(name, str) or not name:
            raise ThemeError("theme name must be a non-empty string")
        if not isinstance(colors, dict) or not isinstance(ambient, dict):
            raise ThemeError("colors and ambient must be objects")

        audio = payload.get("audio", {})
        icons = payload.get("icons", {})
        transitions = payload.get("transitions", {})
        if not isinstance(audio, dict) or not isinstance(icons, dict) or not isinstance(transitions, dict):
            raise ThemeError("audio/icons/transitions must be objects")

        return ThemeManifest(
            id=theme_id,
            name=name,
            colors=colors,
            ambient=ambient,
            audio=audio,
            icons=icons,
            transitions=transitions,
            directory=path.parent.resolve(),
        )

    def resolve_resource(self, theme_directory: Path, relative_path: str) -> Path | None:
        if not relative_path:
            return None
        base = Path(theme_directory).resolve()
        candidate = (base / relative_path).resolve()
        try:
            candidate.relative_to(base)
        except ValueError as exc:
            raise ThemeError(f"theme resource escapes theme directory: {relative_path}") from exc
        return candidate
