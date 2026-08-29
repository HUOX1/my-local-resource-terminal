from __future__ import annotations

import math

SCROLL_STEP_PX = 132.0
SCROLL_RESPONSE_SECONDS = 0.060


def accumulate_scroll_target(
    current_value: float,
    target_value: float,
    angle_delta: int,
    minimum: float,
    maximum: float,
    *,
    step_px: float = SCROLL_STEP_PX,
) -> float:
    """Return an accumulated wheel target for traditional 120-unit mouse wheels.

    New wheel input extends the existing destination instead of restarting a
    per-event animation.  The current value is used only when the previous
    target is already settled or invalidated by the caller.
    """
    del current_value
    steps = float(angle_delta) / 120.0
    candidate = float(target_value) - steps * float(step_px)
    return max(float(minimum), min(float(maximum), candidate))


def smooth_scroll_value(
    current_value: float,
    target_value: float,
    dt_seconds: float,
    *,
    response_seconds: float = SCROLL_RESPONSE_SECONDS,
) -> float:
    """Ease current_value toward target_value with frame-rate-independent decay."""
    current = float(current_value)
    target = float(target_value)
    dt = max(0.0, float(dt_seconds))
    response = max(0.001, float(response_seconds))
    if dt <= 0.0 or current == target:
        return current
    alpha = 1.0 - math.exp(-dt / response)
    return current + (target - current) * alpha
