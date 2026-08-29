# Retro Prototype v8 — v0.5.0.7

## Scope

This pass keeps the v7 carousel geometry and focuses on three visible defects from real use: selected-item separation, the top-right cover/case seam, and the short focus information block.

## FOCUS CONTRAST

The selected package must read as the current item through more than scale alone. Near/far rail items now use lower opacity, while the selected package receives a restrained outer emphasis edge. In focus mode the right neighbor is pushed farther toward the edge and dimmed so it cannot visually compete with the title block.

## FRONT FACE CLIP

The previous box renderer used a rectangular front artwork surface while the 3D side plane began on a slanted top-right edge. This allowed one artwork corner to protrude beyond the package. The front shell and artwork are now clipped to the same slanted front-face polygon used by the case geometry.

## SHORT INFO

The focus label is intentionally not a mini archive page. Game focus information now contains:

- title (bounded to two lines and reduced in size when necessary)
- detected original package/platform label when available
- `PLAY TIME`
- `MORE +`

The old runtime-environment `PC/ARCHIVE` row and `LAST PLAYED` row were removed. Full history remains in MORE → 记录.

## Deferred

GIF/video preview inside the short-information area remains planned, but is not part of this pass. MORE panel structure and package material work are unchanged.
