from __future__ import annotations

from dataclasses import dataclass


DEFAULT_THEME_ID = "flat_pro"
LEGACY_THEME_ALIASES = {
    "flat_dark": "flat_pro",
    "flat_light": "flat_pro_light",
}


@dataclass(frozen=True, slots=True)
class ThemeMetrics:
    radius_small: int = 6
    radius_medium: int = 9
    radius_large: int = 12
    space_1: int = 4
    space_2: int = 8
    space_3: int = 12
    space_4: int = 16
    space_5: int = 24
    control_height: int = 34
    sidebar_width: int = 190
    titlebar_height: int = 38
    nav_height: int = 44


@dataclass(frozen=True, slots=True)
class ThemeAssets:
    """Optional skin-owned visual resources, relative to that skin's asset folder."""

    background: str | None = None
    texture: str | None = None
    brand_mark: str | None = None
    icon_set: str = "flat"


@dataclass(frozen=True, slots=True)
class ThemeSpec:
    display_name: str
    background: str
    surface: str
    surface_raised: str
    surface_hover: str
    border: str
    border_strong: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_pressed: str
    accent_soft: str
    accent_soft_text: str
    accent_foreground: str
    success: str
    danger: str
    danger_border: str
    danger_text: str
    danger_hover_bg: str
    danger_hover_text: str
    chrome_surface: str
    chrome_border: str
    chrome_text: str
    chrome_button_hover: str
    nav_selected_bg: str
    nav_selected_text: str
    nav_inset_dark: str
    nav_inset_light: str
    nav_style: str = "sunken_card"
    motion_level: str = "full"
    metrics: ThemeMetrics = ThemeMetrics()
    assets: ThemeAssets = ThemeAssets()
    selectable: bool = True


_PRO_METRICS = ThemeMetrics(
    radius_small=5,
    radius_medium=7,
    radius_large=9,
    space_1=4,
    space_2=8,
    space_3=12,
    space_4=16,
    space_5=24,
    control_height=34,
    sidebar_width=196,
    titlebar_height=38,
    nav_height=44,
)

THEMES: dict[str, ThemeSpec] = {
    "flat_pro": ThemeSpec(
        display_name="Flat Pro",
        background="#0F1115",
        surface="#171A1F",
        surface_raised="#1C2026",
        surface_hover="#222730",
        border="#252B33",
        border_strong="#353D48",
        text_primary="#EEF2F7",
        text_secondary="#A2ACB9",
        text_muted="#6F7B89",
        accent="#4F7FD8",
        accent_hover="#5E8CE4",
        accent_pressed="#4069B7",
        accent_soft="#192640",
        accent_soft_text="#A9C5FF",
        accent_foreground="#FFFFFF",
        success="#4CC38A",
        danger="#E9606C",
        danger_border="#67333A",
        danger_text="#FF929B",
        danger_hover_bg="#342025",
        danger_hover_text="#FFD8DC",
        chrome_surface="#13161A",
        chrome_border="#222831",
        chrome_text="#DCE3EC",
        chrome_button_hover="#20252C",
        nav_selected_bg="#12161B",
        nav_selected_text="#E8EEF8",
        nav_inset_dark="#080B0E",
        nav_inset_light="#414B58",
        metrics=_PRO_METRICS,
    ),
    "flat_pro_light": ThemeSpec(
        display_name="Flat Pro Light",
        background="#F3F5F8",
        surface="#FFFFFF",
        surface_raised="#EEF1F5",
        surface_hover="#E7EBF0",
        border="#D8DEE7",
        border_strong="#BCC6D2",
        text_primary="#17202A",
        text_secondary="#5E6976",
        text_muted="#8A95A2",
        accent="#4F7FD8",
        accent_hover="#416FC6",
        accent_pressed="#365EA9",
        accent_soft="#E7EEF9",
        accent_soft_text="#315FAF",
        accent_foreground="#FFFFFF",
        success="#2D9968",
        danger="#D9515C",
        danger_border="#E6A7AD",
        danger_text="#B63640",
        danger_hover_bg="#FAEAEC",
        danger_hover_text="#8A2932",
        chrome_surface="#EDF1F5",
        chrome_border="#D4DBE4",
        chrome_text="#1B2530",
        chrome_button_hover="#E2E7ED",
        nav_selected_bg="#E7EBF1",
        nav_selected_text="#1A2633",
        nav_inset_dark="#C6CFDA",
        nav_inset_light="#FFFFFF",
        metrics=_PRO_METRICS,
    ),
}


def resolve_theme_id(theme_id: str | None) -> str:
    candidate = str(theme_id or DEFAULT_THEME_ID)
    candidate = LEGACY_THEME_ALIASES.get(candidate, candidate)
    return candidate if candidate in THEMES else DEFAULT_THEME_ID


def get_theme(theme_id: str | None) -> ThemeSpec:
    return THEMES[resolve_theme_id(theme_id)]


def theme_options() -> list[tuple[str, str]]:
    return [
        (theme_id, spec.display_name)
        for theme_id, spec in THEMES.items()
        if spec.selectable
    ]
