# Retro Stage 1 A3 — v0.5.0.11

## Scope

This stage is intentionally narrow. It adds a minimum Retro window size and makes the focused short-title block adapt at that minimum size. It does not change the background, carousel/package geometry, MORE content, archive editing, or package artwork clipping.

## Changes

- Retro main window minimum is now `1100 × 700` when the Retro presentation is installed.
- Focus short-info positioning is anchored to the actual selected package right edge instead of a fixed `59.5%` screen column.
- At widths up to `1180px`, the title area may use up to three lines and shrink to 12pt when needed.
- At normal/wide layouts the existing two-line treatment and 15pt minimum are retained.
- The local Windows GUI smoke suite adds a fourth check covering minimum-size clamping and a deliberately long focused title.

## Regression boundary

No changes were made to `_draw_showcase()` package/carousel geometry, background rendering, MORE panel content, archive edit dialogs, or resize animation code.

## Validation

Container-side validation can cover pure layout math, source contracts, compilation, and patch checksums. The final GUI acceptance for this stage remains the local Windows smoke test because the container does not have the user's native PySide6/Qt runtime.
