from __future__ import annotations

from pathlib import Path
from typing import Literal

from app.config.theme_registry import get_theme, resolve_theme_id


ThemeAssetRole = Literal["background", "texture", "brand_mark"]
DEFAULT_THEME_ASSET_ROOT = Path(__file__).with_name("theme_assets_data")


def resolve_theme_asset_path(
    theme_id: str,
    role: ThemeAssetRole,
    *,
    asset_root: Path | None = None,
) -> Path | None:
    """Resolve an optional skin asset without making themes depend on file I/O."""

    spec = get_theme(theme_id)
    relative_name = getattr(spec.assets, role)
    if not relative_name:
        return None
    root = Path(asset_root) if asset_root is not None else DEFAULT_THEME_ASSET_ROOT
    candidate = root / resolve_theme_id(theme_id) / relative_name
    return candidate if candidate.is_file() else None
