from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from app.models.collection_folder import CollectionFolder, _normalize_domain, _normalize_name

FOLDER_SCHEMA_VERSION = 1


class CollectionFolderService:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list(self, domain: str) -> list[CollectionFolder]:
        domain = _normalize_domain(domain)
        return sorted(
            (item for item in self._load_all() if item.domain == domain),
            key=lambda item: (item.name.casefold(), item.created_at, item.id),
        )

    def get(self, folder_id: str | None) -> CollectionFolder | None:
        if not folder_id:
            return None
        needle = str(folder_id)
        return next((item for item in self._load_all() if item.id == needle), None)

    def create(self, domain: str, name: str) -> CollectionFolder:
        domain = _normalize_domain(domain)
        name = _normalize_name(name)
        folders = self._load_all()
        self._ensure_unique(folders, domain, name)
        folder = CollectionFolder.new(domain, name)
        folders.append(folder)
        self._save_all(folders)
        return folder

    def rename(self, folder_id: str, name: str) -> CollectionFolder:
        name = _normalize_name(name)
        folders = self._load_all()
        existing = next((item for item in folders if item.id == str(folder_id)), None)
        if existing is None:
            raise KeyError(folder_id)
        self._ensure_unique(folders, existing.domain, name, exclude_id=existing.id)
        renamed = replace(existing, name=name)
        self._save_all([renamed if item.id == existing.id else item for item in folders])
        return renamed

    def delete(self, folder_id: str) -> None:
        folders = self._load_all()
        remaining = [item for item in folders if item.id != str(folder_id)]
        if len(remaining) == len(folders):
            raise KeyError(folder_id)
        self._save_all(remaining)

    @staticmethod
    def _ensure_unique(
        folders: list[CollectionFolder],
        domain: str,
        name: str,
        *,
        exclude_id: str | None = None,
    ) -> None:
        folded = name.casefold()
        if any(
            item.domain == domain and item.id != exclude_id and item.name.casefold() == folded
            for item in folders
        ):
            raise ValueError(f"folder already exists: {name}")

    def _load_all(self) -> list[CollectionFolder]:
        if not self.path.is_file():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        version = int(payload.get("schema_version", 1))
        if version != FOLDER_SCHEMA_VERSION:
            raise ValueError(f"unsupported collection folder schema_version: {version}")
        raw = payload.get("folders", [])
        if not isinstance(raw, list):
            raise ValueError("collection folders must be a list")
        return [self._decode(item) for item in raw]

    def _save_all(self, folders: list[CollectionFolder]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.tmp")
        payload = {
            "schema_version": FOLDER_SCHEMA_VERSION,
            "folders": [self._encode(item) for item in folders],
        }
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        # Verify the temporary representation before replacing the archive.
        verified = json.loads(temporary.read_text(encoding="utf-8"))
        for item in verified.get("folders", []):
            self._decode(item)
        temporary.replace(self.path)

    @staticmethod
    def _encode(folder: CollectionFolder) -> dict[str, Any]:
        return {
            "id": folder.id,
            "domain": folder.domain,
            "name": folder.name,
            "created_at": folder.created_at.isoformat(),
        }

    @staticmethod
    def _decode(payload: dict[str, Any]) -> CollectionFolder:
        if not isinstance(payload, dict):
            raise ValueError("collection folder must be an object")
        created_at = datetime.fromisoformat(str(payload["created_at"]))
        return CollectionFolder(
            id=str(payload["id"]),
            domain=_normalize_domain(str(payload["domain"])),
            name=_normalize_name(str(payload["name"])),
            created_at=created_at,
        )
