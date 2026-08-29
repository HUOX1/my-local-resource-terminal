from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

SOUND_EVENTS: tuple[str, ...] = (
    "navigate",
    "select",
    "focus",
    "confirm",
    "back",
    "open_panel",
    "close_panel",
)


@dataclass(frozen=True, slots=True)
class SoundPackInfo:
    id: str
    name: str
    path: Path


class SoundPackStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def list_packs(self) -> list[SoundPackInfo]:
        packs: list[SoundPackInfo] = []
        for directory in sorted((p for p in self.root.iterdir() if p.is_dir()), key=lambda p: p.name.casefold()):
            pack_file = directory / "pack.json"
            if not pack_file.is_file():
                continue
            try:
                payload = json.loads(pack_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            name = str(payload.get("name", "")).strip() or directory.name
            packs.append(SoundPackInfo(directory.name, name, directory))
        return sorted(packs, key=lambda item: item.name.casefold())

    def create_pack(self, name: str) -> SoundPackInfo:
        display_name = self._validate_pack_name(name)
        pack_id = uuid4().hex
        path = self.root / pack_id
        path.mkdir(parents=True, exist_ok=False)
        (path / "originals").mkdir()
        (path / "audio").mkdir()
        self._write_payload(path, {"id": pack_id, "name": display_name, "mappings": {}})
        return SoundPackInfo(pack_id, display_name, path)

    def duplicate_pack(self, pack_id: str, new_name: str) -> SoundPackInfo:
        source = self._pack_path(pack_id)
        if not source.is_dir():
            raise FileNotFoundError(pack_id)
        display_name = self._validate_pack_name(new_name)
        new_id = uuid4().hex
        target = self.root / new_id
        shutil.copytree(source, target)
        payload = self._read_payload(target)
        payload["id"] = new_id
        payload["name"] = display_name
        self._write_payload(target, payload)
        return SoundPackInfo(new_id, display_name, target)

    def rename_pack(self, pack_id: str, new_name: str) -> SoundPackInfo:
        path = self._require_pack(pack_id)
        display_name = self._validate_pack_name(new_name)
        payload = self._read_payload(path)
        payload["name"] = display_name
        self._write_payload(path, payload)
        return SoundPackInfo(path.name, display_name, path)

    def delete_pack(self, pack_id: str) -> None:
        path = self._require_pack(pack_id)
        shutil.rmtree(path)

    def load_mappings(self, pack_id: str) -> dict[str, dict[str, str]]:
        path = self._require_pack(pack_id)
        raw = self._read_payload(path).get("mappings", {})
        if not isinstance(raw, dict):
            return {}
        result: dict[str, dict[str, str]] = {}
        for event, mapping in raw.items():
            if event not in SOUND_EVENTS or not isinstance(mapping, dict):
                continue
            audio = str(mapping.get("audio", ""))
            original = str(mapping.get("original", ""))
            try:
                audio = self._validate_leaf_filename(audio)
                original = self._validate_leaf_filename(original)
            except ValueError:
                continue
            result[event] = {"audio": audio, "original": original}
        return result

    def set_mapping(self, pack_id: str, event: str, runtime_filename: str, original_filename: str) -> None:
        self._validate_event(event)
        runtime = self._validate_leaf_filename(runtime_filename)
        original = self._validate_leaf_filename(original_filename)
        path = self._require_pack(pack_id)
        payload = self._read_payload(path)
        mappings = payload.setdefault("mappings", {})
        if not isinstance(mappings, dict):
            mappings = {}
            payload["mappings"] = mappings
        mappings[event] = {"audio": runtime, "original": original}
        self._write_payload(path, payload)

    def clear_mapping(self, pack_id: str, event: str) -> None:
        self._validate_event(event)
        path = self._require_pack(pack_id)
        payload = self._read_payload(path)
        mappings = payload.get("mappings", {})
        if isinstance(mappings, dict):
            mappings.pop(event, None)
        self._write_payload(path, payload)

    def resolve_audio_path(self, pack_id: str, event: str) -> Path | None:
        self._validate_event(event)
        mapping = self.load_mappings(pack_id).get(event)
        if not mapping:
            return None
        path = self._require_pack(pack_id) / "audio" / mapping["audio"]
        return path if path.is_file() else None

    def pack_info(self, pack_id: str) -> SoundPackInfo:
        path = self._require_pack(pack_id)
        payload = self._read_payload(path)
        return SoundPackInfo(path.name, str(payload.get("name", path.name)), path)

    def _pack_path(self, pack_id: str) -> Path:
        if not pack_id or any(ch not in "0123456789abcdefABCDEF" for ch in pack_id) or len(pack_id) != 32:
            raise ValueError("Invalid Sound Pack id")
        return self.root / pack_id.lower()

    def _require_pack(self, pack_id: str) -> Path:
        path = self._pack_path(pack_id)
        if not path.is_dir() or not (path / "pack.json").is_file():
            raise FileNotFoundError(pack_id)
        return path

    @staticmethod
    def _validate_pack_name(name: str) -> str:
        value = str(name).strip()
        if not value or value in {".", ".."} or "/" in value or "\\" in value or ".." in value:
            raise ValueError("Invalid Sound Pack name")
        if any(ch in value for ch in '<>:"|?*'):
            raise ValueError("Invalid Sound Pack name")
        return value[:80]

    @staticmethod
    def _validate_leaf_filename(filename: str) -> str:
        value = str(filename).strip()
        path = Path(value)
        if not value or path.is_absolute() or path.name != value or value in {".", ".."} or ".." in path.parts:
            raise ValueError("Invalid mapped filename")
        return value

    @staticmethod
    def _validate_event(event: str) -> None:
        if event not in SOUND_EVENTS:
            raise ValueError(f"Unknown sound event: {event}")

    @staticmethod
    def _read_payload(path: Path) -> dict:
        return json.loads((path / "pack.json").read_text(encoding="utf-8"))

    @staticmethod
    def _write_payload(path: Path, payload: dict) -> None:
        target = path / "pack.json"
        temporary = path / "pack.json.tmp"
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)
