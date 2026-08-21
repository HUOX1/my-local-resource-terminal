from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PosterDisplayMode = Literal["natural", "fit", "fill"]


@dataclass(frozen=True)
class PosterWallMetrics:
    columns: int
    spacing: int
    card_width: int


PosterWallAlignment = Literal["centered", "fixed_left"]


@dataclass(frozen=True)
class PosterTarget:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class PosterWallLayout:
    columns: int
    spacing: int
    card_width: int
    content_height: int
    targets: tuple[PosterTarget, ...]


def _minimum_width_for_columns(columns: int, *, card_width: int, spacing: int) -> int:
    columns = max(1, int(columns))
    return columns * card_width + (columns + 1) * spacing


def poster_wall_targets(
    viewport_width: int,
    item_heights: list[int] | tuple[int, ...],
    *,
    card_width: int,
    min_spacing: int,
    previous_columns: int | None = None,
    hysteresis: int = 24,
    alignment: PosterWallAlignment = "centered",
) -> PosterWallLayout:
    """Compute deterministic poster target geometry for a viewport.

    QListView remains the model/view host, but this function owns the actual
    row/column decision.  Cards keep a fixed width and natural per-item height.
    Growth uses a small hysteresis margin, while shrinking drops a column as
    soon as the current count no longer fits at the minimum gap so cards never
    overlap.
    """
    width = max(0, int(viewport_width))
    card = max(1, int(card_width))
    gap = max(0, int(min_spacing))
    deadband = max(0, int(hysteresis))
    heights = tuple(max(1, int(height)) for height in item_heights)

    ideal_columns = max(1, (width - gap) // (card + gap)) if width > gap else 1
    columns = ideal_columns

    if previous_columns is not None:
        previous = max(1, int(previous_columns))
        if width < _minimum_width_for_columns(previous, card_width=card, spacing=gap):
            columns = min(previous, ideal_columns)
        elif ideal_columns > previous:
            columns = previous
            for candidate in range(previous + 1, ideal_columns + 1):
                threshold = _minimum_width_for_columns(candidate, card_width=card, spacing=gap)
                if width >= threshold + deadband:
                    columns = candidate
                else:
                    break
        else:
            columns = previous

    columns = max(1, columns)
    if alignment == "fixed_left":
        left = gap
        vertical_spacing = gap
        if columns > 1 and len(heights) >= columns:
            # Keep the left/right wall margins anchored while distributing the
            # remaining width only between columns.  Sparse walls stay compact
            # at the minimum gap so a few posters do not spread across the
            # entire viewport.
            between_width = max(0, width - 2 * gap - columns * card)
            spacing = max(gap, between_width // (columns - 1))
        else:
            spacing = gap
    else:
        alignment = "centered"
        spacing = max(0, (width - columns * card) // (columns + 1))
        left = spacing
        vertical_spacing = spacing

    if not heights:
        return PosterWallLayout(
            columns=columns,
            spacing=spacing,
            card_width=card,
            content_height=0,
            targets=(),
        )

    targets: list[PosterTarget] = []
    y = vertical_spacing
    for row_start in range(0, len(heights), columns):
        row_heights = heights[row_start : row_start + columns]
        row_height = max(row_heights)
        for offset, item_height in enumerate(row_heights):
            x = left + offset * (card + spacing)
            targets.append(PosterTarget(x=x, y=y, width=card, height=item_height))
        y += row_height + vertical_spacing

    return PosterWallLayout(
        columns=columns,
        spacing=spacing,
        card_width=card,
        content_height=y,
        targets=tuple(targets),
    )


def poster_height_for_width(
    source_width: int,
    source_height: int,
    target_width: int,
    *,
    fallback_height: int = 260,
) -> int:
    """Scale a poster to a fixed width while preserving its original ratio."""
    if source_width <= 0 or source_height <= 0 or target_width <= 0:
        return fallback_height
    return max(1, round(target_width * source_height / source_width))


def scaled_poster_size(
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
    mode: PosterDisplayMode,
) -> tuple[int, int]:
    """Return an aspect-preserving scaled size for legacy fit/fill callers."""
    if min(source_width, source_height, target_width, target_height) <= 0:
        return 0, 0
    if mode not in {"fit", "fill"}:
        mode = "fit"
    width_scale = target_width / source_width
    height_scale = target_height / source_height
    scale = min(width_scale, height_scale) if mode == "fit" else max(width_scale, height_scale)
    return max(1, round(source_width * scale)), max(1, round(source_height * scale))


def adaptive_poster_wall_metrics(
    viewport_width: int,
    *,
    card_width: int,
    min_spacing: int,
) -> PosterWallMetrics:
    """Return fixed-card wall metrics for the current viewport.

    The poster card itself never changes size.  Extra width is absorbed only by
    spacing, and a new column appears only when a complete fixed-width card plus
    the minimum edge/gap spacing fits.  That keeps resize motion continuous
    inside a column count and makes column changes discrete, predictable events.
    """
    width = max(0, int(viewport_width))
    card = max(1, int(card_width))
    gap = max(0, int(min_spacing))

    if width <= card + gap * 2:
        return PosterWallMetrics(columns=1, spacing=max(0, (width - card) // 2), card_width=card)

    # QListView icon mode uses spacing on the two outer row edges as well as
    # between items: n*card + (n+1)*gap <= viewport width.
    columns = max(1, (width - gap) // (card + gap))
    spacing = max(0, (width - columns * card) // (columns + 1))
    return PosterWallMetrics(columns=columns, spacing=spacing, card_width=card)


def justified_poster_cell_width(viewport_width: int, *, card_width: int, spacing: int) -> int:
    """Legacy helper retained for compatibility with older tests/callers.

    v0.4.2.1 no longer stretches poster cells to fill the row; the wall now
    keeps fixed-width cards and adapts spacing instead.
    """
    width = max(0, int(viewport_width))
    card = max(1, int(card_width))
    gap = max(0, int(spacing))
    if width <= card + gap * 2:
        return card
    columns = max(1, (width - gap) // (card + gap))
    usable = width - gap * (columns + 1)
    return max(card, usable // columns)
