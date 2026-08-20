from __future__ import annotations

from pathlib import Path

import pytest


def test_identity_round_trip_accepts_unicode_and_manages_assets(tmp_path: Path) -> None:
    from app.services.identity_service import IdentityService

    source_avatar = tmp_path / "source.gif"
    source_avatar.write_bytes(b"GIF89a")
    source_frame = tmp_path / "frame.png"
    source_frame.write_bytes(b"PNG")

    service = IdentityService(tmp_path / "identity")
    identity = service.create_or_update("☁ 夜雨.exe ✨", source_avatar, source_frame)

    assert service.load() == identity
    assert identity.username == "☁ 夜雨.exe ✨"
    assert service.avatar_path(identity) == tmp_path / "identity" / "assets" / "avatar.gif"
    assert service.frame_path(identity) == tmp_path / "identity" / "assets" / "frame.png"
    assert service.avatar_path(identity).read_bytes() == b"GIF89a"
    assert service.frame_path(identity).read_bytes() == b"PNG"
    assert source_avatar.exists()
    assert source_frame.exists()


def test_identity_requires_non_empty_username_but_assets_are_optional(tmp_path: Path) -> None:
    from app.services.identity_service import IdentityService

    service = IdentityService(tmp_path / "identity")
    identity = service.create_or_update("  本地用户  ", None, None)

    assert identity.username == "本地用户"
    assert identity.avatar_filename is None
    assert identity.frame_filename is None
    with pytest.raises(ValueError):
        service.create_or_update("   ", None, None)


def test_identity_rejects_unsupported_asset_extensions(tmp_path: Path) -> None:
    from app.services.identity_service import IdentityService

    bad_avatar = tmp_path / "avatar.webp"
    bad_avatar.write_bytes(b"webp")
    bad_frame = tmp_path / "frame.jpg"
    bad_frame.write_bytes(b"jpg")
    service = IdentityService(tmp_path / "identity")

    with pytest.raises(ValueError):
        service.create_or_update("User", bad_avatar, None)
    with pytest.raises(ValueError):
        service.create_or_update("User", None, bad_frame)


def test_identity_update_preserves_omitted_assets_and_clear_methods_remove_managed_files(tmp_path: Path) -> None:
    from app.services.identity_service import IdentityService

    avatar = tmp_path / "avatar.png"
    avatar.write_bytes(b"avatar")
    frame = tmp_path / "frame.png"
    frame.write_bytes(b"frame")
    service = IdentityService(tmp_path / "identity")
    created = service.create_or_update("User", avatar, frame)

    updated = service.create_or_update("Renamed", None, None)
    assert updated.avatar_filename == created.avatar_filename
    assert updated.frame_filename == created.frame_filename
    assert service.avatar_path(updated).read_bytes() == b"avatar"
    assert service.frame_path(updated).read_bytes() == b"frame"

    cleared_avatar = service.clear_avatar()
    assert cleared_avatar.avatar_filename is None
    assert not (tmp_path / "identity" / "assets" / "avatar.png").exists()

    cleared_frame = service.clear_frame()
    assert cleared_frame.frame_filename is None
    assert not (tmp_path / "identity" / "assets" / "frame.png").exists()
