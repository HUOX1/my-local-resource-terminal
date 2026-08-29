# Retro Stage 1 A4 — v0.5.0.12

## Scope

Stage 1 A4 is intentionally limited to the remaining dirty/diagonal ambient background artifact reported after v0.5.0.11. It does not change showcase geometry, package drawing, focus layout, MORE, resize behavior, or archive editing.

## Root cause

The radial glow and bottom stage layers had already been removed, but the base fill in `RetroShowcaseOverlay._draw_background()` still used a diagonal `QLinearGradient(rect.topLeft(), rect.bottomRight())`. That made the dark base itself change horizontally at the same vertical position and visually read as a large diagonal haze from the upper-right toward the lower-left.

The v0.5.0.8 background that the user explicitly confirmed as clean used a vertical base gradient instead.

## Change

- Replace the diagonal base gradient with `QLinearGradient(0.0, rect.top(), 0.0, rect.bottom())`.
- Restore the clean vertical dark-base stops from the previously user-validated background.
- Keep `_draw_ambient_waves()` unchanged.
- Keep radial glow/stage overlays absent.

## Regression protection

- Added a source-level regression test that rejects a diagonal base gradient inside `_draw_background()`.
- Added a real Qt GUI smoke check that temporarily hides the ambient waves, renders the production background base, and verifies that pixels at the same Y coordinate are identical across the window width.
- Local Windows smoke target becomes 5/5 checks.

## Explicitly not changed

- Carousel / visible-item layout
- Package/cover geometry, including the known right-top corner defect
- Focus/MORE layout
- Minimum window behavior
- Archive edit dialogs
- Wave shape, amplitude, phase, speed, or animation timing
