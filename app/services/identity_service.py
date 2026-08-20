from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.models.identity import LocalIdentity

_AVATAR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif"}
_FRAME_EXTENSIONS = {".png"}


class IdentityService:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.assets_dir = self.root / "assets"
        self.profile_path = self.root / "profile.json"

    def load(self) -> LocalIdentity | None:
        if not self.profile_path.is_file():
            return None
        payload = json.loads(self.profile_path.read_text(encoding="utf-8"))
        username = str(payload.get("username", "")).strip()
        if not username:
            return None
        avatar = payload.get("avatar_filename")
        frame = payload.get("frame_filename")
        return LocalIdentity(
            username=username,
            avatar_filename=str(avatar) if avatar else None,
            frame_filename=str(frame) if frame else None,
        )

    def create_or_update(
        self,
        username: str,
        avatar_source: Path | None,
        frame_source: Path | None,
    ) -> LocalIdentity:
        normalized = str(username).strip()
        if not normalized:
            raise ValueError("用户名不能为空")

        current = self.load()
        avatar_filename = current.avatar_filename if current else None
        frame_filename = current.frame_filename if current else None

        if avatar_source is not None:
            avatar_filename = self._install_asset(Path(avatar_source), "avatar", _AVATAR_EXTENSIONS)
        if frame_source is not None:
            frame_filename = self._install_asset(Path(frame_source), "frame", _FRAME_EXTENSIONS)

        identity = LocalIdentity(normalized, avatar_filename, frame_filename)
        self._write_profile(identity)
        self._remove_stale_managed_assets(identity)
        return identity

    def clear_avatar(self) -> LocalIdentity:
        current = self._require_identity()
        old_filename = current.avatar_filename
        updated = LocalIdentity(current.username, None, current.frame_filename)
        self._write_profile(updated)
        if old_filename:
            (self.assets_dir / old_filename).unlink(missing_ok=True)
        return updated

    def clear_frame(self) -> LocalIdentity:
        current = self._require_identity()
        old_filename = current.frame_filename
        updated = LocalIdentity(current.username, current.avatar_filename, None)
        self._write_profile(updated)
        if old_filename:
            (self.assets_dir / old_filename).unlink(missing_ok=True)
        return updated

    def avatar_path(self, identity: LocalIdentity | None = None) -> Path | None:
        item = identity or self.load()
        if item is None or not item.avatar_filename:
            return None
        return self.assets_dir / item.avatar_filename

    def frame_path(self, identity: LocalIdentity | None = None) -> Path | None:
        item = identity or self.load()
        if item is None or not item.frame_filename:
            return None
        return self.assets_dir / item.frame_filename

    def _install_asset(self, source: Path, stem: str, allowed_extensions: set[str]) -> str:
        extension = source.suffix.casefold()
        if extension not in allowed_extensions:
            raise ValueError(f"不支持的素材格式：{source.suffix or '无扩展名'}")
        if not source.is_file():
            raise FileNotFoundError(source)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        target = self.assets_dir / f"{stem}{extension}"
        temporary = self.assets_dir / f".{target.name}.tmp"
        shutil.copy2(source, temporary)
        temporary.replace(target)
        return target.name

    def _write_profile(self, identity: LocalIdentity) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        payload = {
            "username": identity.username,
            "avatar_filename": identity.avatar_filename,
            "frame_filename": identity.frame_filename,
        }
        temporary = self.profile_path.with_name(f".{self.profile_path.name}.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        # Re-read before replacement so a malformed write cannot become authoritative.
        json.loads(temporary.read_text(encoding="utf-8"))
        temporary.replace(self.profile_path)

    def _remove_stale_managed_assets(self, identity: LocalIdentity) -> None:
        if not self.assets_dir.exists():
            return
        keep = {name for name in (identity.avatar_filename, identity.frame_filename) if name}
        for path in self.assets_dir.iterdir():
            if not path.is_file() or path.name.startswith("."):
                continue
            if path.name.startswith("avatar.") or path.name.startswith("frame."):
                if path.name not in keep:
                    path.unlink(missing_ok=True)

    def _require_identity(self) -> LocalIdentity:
        identity = self.load()
        if identity is None:
            raise ValueError("尚未建立本地身份")
        return identity
