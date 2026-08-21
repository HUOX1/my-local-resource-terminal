from __future__ import annotations


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def sidebar_motion_progress(width: int, *, minimum: int = 72, expanded: int = 196) -> float:
    """Return the rail expansion fraction directly from the live splitter width."""
    span = max(1, int(expanded) - int(minimum))
    return _clamp01((int(width) - int(minimum)) / span)


def sidebar_text_progress(progress: float) -> float:
    """Keep labels quiet near the icon-only state, then fade them in smoothly."""
    value = _clamp01((float(progress) - 0.18) / 0.58)
    return value * value * (3.0 - 2.0 * value)
