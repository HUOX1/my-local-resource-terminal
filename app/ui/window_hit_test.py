from __future__ import annotations


def edge_zone(width: int, height: int, x: int, y: int, border: int) -> str | None:
    """Return the rectangular resize zone for a point in window pixel coordinates."""
    width = max(0, int(width))
    height = max(0, int(height))
    border = max(1, int(border))
    x = int(x)
    y = int(y)

    left = 0 <= x < border
    right = width - border <= x < width
    top = 0 <= y < border
    bottom = height - border <= y < height

    if top and left:
        return "top_left"
    if top and right:
        return "top_right"
    if bottom and left:
        return "bottom_left"
    if bottom and right:
        return "bottom_right"
    if left:
        return "left"
    if right:
        return "right"
    if top:
        return "top"
    if bottom:
        return "bottom"
    return None
