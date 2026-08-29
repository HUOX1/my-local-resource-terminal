from __future__ import annotations

from dataclasses import dataclass
import math
import re

RETRO_MIN_WINDOW_WIDTH = 1100
RETRO_MIN_WINDOW_HEIGHT = 700
RETRO_MAX_VISIBLE_ITEMS = 4

AMBIENT_IDLE_INTERVAL_MS = 66
AMBIENT_ACTIVE_INTERVAL_MS = 33
_AMBIENT_PHASE_PER_MS = 0.0105 / 33.0


def ambient_phase_step(elapsed_ms: float) -> float:
    """Advance ambient motion by real elapsed time at the legacy visual speed."""
    elapsed = max(0.0, float(elapsed_ms))
    return elapsed * _AMBIENT_PHASE_PER_MS


def ambient_refresh_interval_ms(
    hover_sequence: int | None, hover_strengths: dict[int, float]
) -> int:
    """Use 30fps only while hover easing is actually moving; idle stays at 15fps."""
    sequences = set(hover_strengths)
    if hover_sequence is not None:
        sequences.add(hover_sequence)
    for sequence in sequences:
        current = float(hover_strengths.get(sequence, 0.0))
        target = 1.0 if sequence == hover_sequence else 0.0
        if abs(target - current) > 0.02:
            return AMBIENT_ACTIVE_INTERVAL_MS
    return AMBIENT_IDLE_INTERVAL_MS


@dataclass(frozen=True, slots=True)
class FocusInfoLayout:
    left: float
    top: float
    width: float
    title_height: float
    title_max_lines: int
    title_min_point_size: int

    @property
    def right(self) -> float:
        return self.left + self.width


def focus_info_layout(
    viewport_width: float, viewport_height: float, *, hero_right: float
) -> FocusInfoLayout:
    """Return the short-info text area for a focused Retro item.

    At the supported minimum viewport the title receives more horizontal room
    by starting just after the real hero edge instead of a fixed 59.5% column.
    Compact windows may use a third title line and a smaller minimum font, while
    the normal 1320px composition keeps the established two-line treatment.
    """

    width = max(float(RETRO_MIN_WINDOW_WIDTH), float(viewport_width))
    height = max(float(RETRO_MIN_WINDOW_HEIGHT), float(viewport_height))
    compact_progress = max(
        0.0, min(1.0, (width - RETRO_MIN_WINDOW_WIDTH) / 220.0)
    )
    right_ratio = 0.790 + 0.015 * compact_progress
    right = width * right_ratio
    gap = max(22.0, width * 0.020)
    left = max(width * 0.50, float(hero_right) + gap)
    minimum_width = 280.0 if width <= 1180.0 else 240.0
    if right - left < minimum_width:
        left = max(float(hero_right) + gap, right - minimum_width)
    available = max(160.0, right - left)
    compact = width <= 1180.0
    return FocusInfoLayout(
        left=left,
        top=height * 0.31,
        width=available,
        title_height=height * (0.155 if compact else 0.125),
        title_max_lines=3 if compact else 2,
        title_min_point_size=12 if compact else 15,
    )


@dataclass(frozen=True, slots=True)
class HoverPose:
    scale_multiplier: float
    lift_px: float
    angle_delta: float
    emphasis_boost: float


def hover_pose(progress: float, *, x_bias: float = 0.0, y_bias: float = 0.0) -> HoverPose:
    """Return a restrained pointer-response pose for one visible package.

    This intentionally stays subtle in the QPainter generation: a small scale,
    a short upward lift, a tiny directional roll, and a little extra edge
    emphasis.  The future Qt Quick/3D renderer can replace the roll with true
    perspective tilt without changing the interaction contract.
    """

    p = max(0.0, min(1.0, float(progress)))
    x = max(-1.0, min(1.0, float(x_bias)))
    y = max(-1.0, min(1.0, float(y_bias)))
    return HoverPose(
        scale_multiplier=1.0 + 0.035 * p,
        lift_px=-(5.0 + 1.5 * (1.0 - y) * 0.5) * p,
        angle_delta=1.15 * x * p,
        emphasis_boost=0.22 * p,
    )


def showcase_click_intent(
    *, clicked_sequence: int, current_sequence: int, focused: bool
) -> str:
    """Separate carousel selection from opening the focused info state.

    Clicking another visible package only moves it into the primary slot.  A
    second click on the settled primary package enters the short-info state.
    """

    if int(clicked_sequence) != int(current_sequence):
        return "select"
    return "stay" if bool(focused) else "focus"


def cycle_index(current: int, count: int, delta: int) -> int:
    """Wrap an index by delta. Empty collections always resolve to 0."""
    if count <= 0:
        return 0
    return (int(current) + int(delta)) % int(count)


def neighbor_indices(current: int, count: int) -> tuple[int | None, int | None, int | None]:
    """Return previous/current/next indices for the showcase."""
    if count <= 0:
        return None, None, None
    center = int(current) % count
    if count == 1:
        return None, center, None
    if count == 2:
        other = (center + 1) % 2
        return other, center, other
    return (center - 1) % count, center, (center + 1) % count


def format_duration(seconds: int | float | None) -> str:
    total = max(0, int(seconds or 0))
    hours, remainder = divmod(total, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}.{minutes // 6} h" if minutes else f"{hours} h"
    if minutes:
        return f"{minutes} min"
    return "0 min"


def library_filter_options(domain: str) -> tuple[tuple[str, str, dict], ...]:
    """Stable Retro filter options shared by menus and persistence tests."""
    if domain == "games":
        return (
            ("全部", "all", {}),
            ("已安装", "installed", {"installed": True}),
            ("未安装", "uninstalled", {"installed": False}),
            ("最近游玩", "recent", {"recently_played": True}),
        )
    return (
        ("全部", "all", {}),
        ("未观看", "unwatched", {"watched": False}),
        ("已观看", "watched", {"watched": True}),
        ("本地可播放", "available", {"availability_status": "available"}),
        ("仅档案", "offline", {"availability_status": "offline"}),
        ("有字幕", "subtitle", {"subtitle_status": True}),
        ("无字幕", "no_subtitle", {"subtitle_status": False}),
    )


def library_sort_options(domain: str) -> tuple[tuple[str, str], ...]:
    if domain == "games":
        return (
            ("最近添加", "added_at"),
            ("游戏名称", "title"),
            ("发行日期", "release_date"),
            ("评分", "rating"),
            ("累计游玩时间", "total_play_seconds"),
            ("最近游玩", "last_played_at"),
            ("游玩次数", "play_count"),
        )
    return (
        ("最近添加", "added_at"),
        ("编号", "code"),
        ("标题", "title"),
        ("发行日期", "release_date"),
        ("评分", "rating"),
        ("最后观看", "last_watched_at"),
        ("观看次数", "play_count"),
    )


def persistent_filter_key(domain: str, key: str) -> str:
    """Only fixed filters are safe to restore from settings.

    Tag/library filters carry dynamic payloads and intentionally remain
    session-only until their identity is encoded explicitly.
    """
    allowed = {item[1] for item in library_filter_options(domain)}
    return key if key in allowed else "all"


@dataclass(frozen=True, slots=True)
class PackageProfile:
    """Visual package geometry for one game cover.

    ``face_ratio`` is front-face width / height.  The first Retro packaging
    pass intentionally avoids a database migration: explicit platform hints
    come from existing tags/asset names, while cover aspect ratio provides a
    safe fallback for square jewel cases and tall keepcases.
    """

    key: str
    family: str
    face_ratio: float
    depth_ratio: float
    spine_ratio: float
    label: str = ""


def _normalized_hint(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def resolve_game_package_profile(
    platform_hint: str = "", cover_aspect: float | None = None
) -> PackageProfile:
    """Resolve a console-like package profile without changing metadata schema."""

    hint = f" {_normalized_hint(platform_hint)} "

    # More specific names must win before broad Playstation/Xbox tokens.
    candidates: tuple[tuple[tuple[str, ...], PackageProfile], ...] = (
        ((" ps1 ", " psx ", " playstation 1 "), PackageProfile("ps1", "jewel", 1.00, 0.036, 0.052, "PS1")),
        ((" ps2 ", " playstation 2 "), PackageProfile("ps2", "keepcase", 0.695, 0.044, 0.050, "PS2")),
        ((" ps3 ", " playstation 3 "), PackageProfile("ps3", "bluray", 0.715, 0.040, 0.046, "PS3")),
        ((" ps4 ", " playstation 4 "), PackageProfile("ps4", "bluray", 0.715, 0.038, 0.044, "PS4")),
        ((" ps5 ", " playstation 5 "), PackageProfile("ps5", "bluray", 0.715, 0.038, 0.044, "PS5")),
        ((" psp ",), PackageProfile("psp", "handheld", 0.590, 0.033, 0.038, "PSP")),
        ((" vita ", " psvita ", " ps vita "), PackageProfile("vita", "handheld", 0.635, 0.032, 0.036, "PS VITA")),
        ((" switch ", " nintendo switch "), PackageProfile("switch", "switch", 0.615, 0.030, 0.035, "SWITCH")),
        ((" xbox 360 ", " x360 "), PackageProfile("xbox360", "keepcase", 0.695, 0.044, 0.050, "XBOX 360")),
        ((" xbox one ", " xbox series ", " series x ", " series s "), PackageProfile("xboxmodern", "bluray", 0.715, 0.039, 0.045, "XBOX")),
    )
    for tokens, profile in candidates:
        if any(token in hint for token in tokens):
            return profile

    ratio = float(cover_aspect or 0.0)
    if ratio >= 0.88:
        return PackageProfile(
            "aspect-jewel",
            "jewel",
            max(0.94, min(1.04, ratio)),
            0.036,
            0.052,
            "",
        )
    if 0.0 < ratio <= 0.635:
        return PackageProfile(
            "aspect-slim",
            "handheld",
            max(0.56, min(0.635, ratio)),
            0.032,
            0.038,
            "",
        )
    if 0.0 < ratio <= 0.75:
        return PackageProfile(
            "aspect-keepcase",
            "keepcase",
            max(0.66, min(0.735, ratio)),
            0.042,
            0.048,
            "",
        )
    return PackageProfile("generic", "bluray", 0.705, 0.040, 0.046, "")


def effective_package_face_ratio(
    profile_face_ratio: float, cover_aspect: float | None
) -> float:
    """Use real cover geometry for the package front whenever it is available.

    Platform profiles still define material/depth/spine behavior, but a scanned
    retail sleeve should not be letterboxed just to satisfy a nominal console
    template.  Only clearly invalid/extreme ratios are bounded for scene safety.
    """

    ratio = float(cover_aspect or 0.0)
    if ratio > 0.0:
        return max(0.40, min(1.30, ratio))
    return max(0.40, min(1.30, float(profile_face_ratio)))


@dataclass(frozen=True, slots=True)
class ArcPose:
    """Normalized pose for one item on the continuous showcase rail."""

    center_x: float
    center_y: float
    scale: float
    angle: float
    opacity: float


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_pose(a: ArcPose, b: ArcPose, t: float) -> ArcPose:
    return ArcPose(
        center_x=_lerp(a.center_x, b.center_x, t),
        center_y=_lerp(a.center_y, b.center_y, t),
        scale=_lerp(a.scale, b.scale, t),
        angle=_lerp(a.angle, b.angle, t),
        opacity=_lerp(a.opacity, b.opacity, t),
    )


def arc_pose(position: float, *, focus: float = 0.0) -> ArcPose:
    """Return the continuous scale/depth pose for a logical rail position."""

    # FOUR-UP RAIL: the primary package is deliberately larger and the settled
    # four-item composition is asymmetric (one item left, two right).  Rotation
    # stays restrained; the package construction itself supplies the 3D read.
    anchors = (
        (-2.6, ArcPose(-0.055, 0.486, 0.34, -4.3, 0.00)),
        (-2.0, ArcPose(0.080, 0.470, 0.44, -2.8, 0.22)),
        (-1.0, ArcPose(0.278, 0.454, 0.64, -1.4, 0.48)),
        (0.0, ArcPose(0.500, 0.428, 1.10, 0.5, 1.00)),
        (1.0, ArcPose(0.724, 0.452, 0.66, 1.4, 0.50)),
        (2.0, ArcPose(0.916, 0.470, 0.45, 2.8, 0.23)),
        (2.6, ArcPose(1.055, 0.486, 0.34, 4.3, 0.00)),
    )
    pos = max(-2.6, min(2.6, float(position)))
    for index in range(len(anchors) - 1):
        left_pos, left_pose = anchors[index]
        right_pos, right_pose = anchors[index + 1]
        if left_pos <= pos <= right_pos:
            span = right_pos - left_pos
            pose = _lerp_pose(left_pose, right_pose, (pos - left_pos) / span)
            break
    else:
        pose = anchors[-1][1]

    f = max(0.0, min(1.0, float(focus)))
    if not f:
        return pose

    center_weight = max(0.0, 1.0 - abs(pos))
    side_weight = min(1.0, abs(pos))
    target_center_x = pose.center_x
    if pos < 0:
        target_center_x -= 0.080 * side_weight
    elif pos > 0:
        # Focus text owns the right-middle safe zone. Push the next package
        # toward the edge instead of letting long titles paint through it.
        target_center_x += 0.160 * side_weight
    else:
        target_center_x = 0.345
    return ArcPose(
        center_x=_lerp(pose.center_x, target_center_x, f),
        # FOCUS COMPOSITION: the light-focus hero settles closer to the visual
        # center instead of climbing toward the title-bar edge.
        center_y=pose.center_y + 0.052 * f * center_weight,
        # Focus uses an independent hero target instead of compounding the
        # enlarged browse scale.  This preserves the v0.5.0.14 four-up impact
        # while returning horizontal room to the short-info block.
        scale=_lerp(
            pose.scale,
            _lerp(pose.scale * (1.0 - 0.08 * side_weight), 1.12, center_weight),
            f,
        ),
        angle=pose.angle * (1.0 - 0.78 * f * center_weight),
        opacity=pose.opacity * (1.0 - 0.62 * f * side_weight),
    )


def _interpolate_x(position: float, anchors: tuple[tuple[float, float], ...]) -> float:
    pos = float(position)
    if pos <= anchors[0][0]:
        return anchors[0][1]
    if pos >= anchors[-1][0]:
        return anchors[-1][1]
    for (left_p, left_x), (right_p, right_x) in zip(anchors, anchors[1:]):
        if left_p <= pos <= right_p:
            return _lerp(left_x, right_x, (pos - left_p) / (right_p - left_p))
    return anchors[-1][1]


def rail_center_x(position: float, count: int, *, focus: float = 0.0) -> float:
    """Horizontal center for the current collection size.

    Collections below five items are re-spaced across the usable width rather
    than pretending that an empty fifth slot exists.  Scale/opacity still come
    from :func:`arc_pose`, keeping the selected item visually dominant.
    """

    count = max(0, int(count))
    if count >= 5:
        return arc_pose(position, focus=focus).center_x
    if count <= 1:
        base = 0.50
    elif count == 2:
        # Qt's wrapped relative offsets settle at -1 and 0 for a two-item rail.
        base = _interpolate_x(position, ((-1.0, 0.34), (0.0, 0.66), (1.0, 0.86)))
    elif count == 3:
        base = _interpolate_x(position, ((-1.5, 0.08), (-1.0, 0.22), (0.0, 0.50), (1.0, 0.78), (1.5, 0.92)))
    else:  # count == 4; settled wrapped offsets are -2, -1, 0, +1.
        base = _interpolate_x(position, ((-2.0, 0.10), (-1.0, 0.32), (0.0, 0.54), (1.0, 0.80), (2.0, 0.94)))

    f = max(0.0, min(1.0, float(focus)))
    if not f:
        return base
    center_weight = max(0.0, 1.0 - abs(float(position)))
    if center_weight > 0.0:
        return _lerp(base, 0.345, f * center_weight)
    return base


def carousel_slots(count: int, max_visible: int = 5) -> tuple[int, ...]:
    """Logical settled slots for one carousel segment.

    Odd collections center the selected item.  Even collections keep the
    selected item just left of center so the full group remains balanced.
    """
    visible = max(0, min(int(count), int(max_visible)))
    if visible <= 0:
        return ()
    start = -((visible - 1) // 2)
    return tuple(range(start, start + visible))


def carousel_segment(arc_position: float, direction: int) -> tuple[int, int, float]:
    """Return start/end integer bases plus progress for one continuous segment.

    The unwrapped arc coordinate is never modulo-wrapped while it is moving.
    That lets the outgoing instance travel fully off-screen while a new cyclic
    copy enters from the opposite edge.
    """
    pos = float(arc_position)
    if int(direction) < 0:
        start = math.ceil(pos - 1e-9)
        progress = max(0.0, min(1.0, start - pos))
        return start, start - 1, progress
    start = math.floor(pos + 1e-9)
    progress = max(0.0, min(1.0, pos - start))
    return start, start + 1, progress


def anchored_equal_gap_centers(
    widths: list[float] | tuple[float, ...],
    *,
    anchor_index: int,
    viewport_width: float,
    desired_gap: float = 24.0,
    padding: float = 18.0,
    anchor_x: float = 0.50,
) -> tuple[float, ...]:
    """Place items with one equal *visible edge* gap around an anchor.

    Center-point spacing looks uneven when package widths differ.  This helper
    computes one gap from the actual rendered widths, reducing it (even into a
    mild overlap) only when needed to keep the rail inside the viewport.
    """
    values = tuple(max(1.0, float(value)) for value in widths)
    count = len(values)
    if count == 0:
        return ()
    anchor = max(0, min(int(anchor_index), count - 1))
    width = max(1.0, float(viewport_width))
    pad = max(0.0, float(padding))
    anchor_center = max(pad, min(width - pad, width * float(anchor_x)))

    left_count = anchor
    right_count = count - anchor - 1
    selected_half = values[anchor] / 2.0

    limits = [float(desired_gap)]
    if left_count:
        room = anchor_center - pad - selected_half - sum(values[:anchor])
        limits.append(room / left_count)
    if right_count:
        room = width - pad - anchor_center - selected_half - sum(values[anchor + 1 :])
        limits.append(room / right_count)
    gap = min(limits)

    centers = [0.0] * count
    centers[anchor] = anchor_center
    for index in range(anchor - 1, -1, -1):
        centers[index] = (
            centers[index + 1]
            - values[index + 1] / 2.0
            - gap
            - values[index] / 2.0
        )
    for index in range(anchor + 1, count):
        centers[index] = (
            centers[index - 1]
            + values[index - 1] / 2.0
            + gap
            + values[index] / 2.0
        )
    return tuple(centers)


@dataclass(frozen=True, slots=True)
class NormalizedRect:
    x: float
    y: float
    width: float
    height: float

    def pixels(self, width: int, height: int) -> tuple[int, int, int, int]:
        return (
            round(self.x * width),
            round(self.y * height),
            round(self.width * width),
            round(self.height * height),
        )


BOTTOM_RIGHT_HOT_ZONE = NormalizedRect(0.91, 0.88, 0.09, 0.12)
BOTTOM_LEFT_HOT_ZONE = NormalizedRect(0.0, 0.88, 0.09, 0.12)
