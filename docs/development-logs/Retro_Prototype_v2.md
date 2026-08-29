# Retro Prototype v2 — Polish Pass

Date: 2026-08-29  
Version: v0.5.0.1  
Status: RETRO PREVIEW POLISH / CONTINUOUS ARC

## Why this pass exists

The first runnable Retro prototype proved that the clean scene-first direction is worth keeping, but the first visual implementation exposed several problems in real use: Arc switching felt segmented, the moving pose did not meet the settled pose cleanly, the MORE and Settings surfaces were too large, a mouse-parallax quadrilateral looked like a debug layer instead of atmosphere, and some Flat Pro tools were no longer directly reachable.

This pass does not expand the product scope. It polishes the existing prototype around those concrete observations.

## CONTINUOUS ARC

Arc Showcase no longer treats left / center / right as separate static presets with a different animation preset in between. Every visible object is evaluated from one continuous logical rail position. Settled rendering and in-flight rendering use the same `arc_pose()` function.

Repeated mouse-wheel input retargets from the exact current rail position instead of committing an unfinished transition and jumping to a new static pose. The intended feel remains console-style: fast response, smooth travel, and a clear snap to an item without a pose discontinuity at the end.

The hero collectible is larger than v1. Rear neighbors remain partially hidden and visually weaker.

## PS3-inspired ambient background

The large mouse-following four-sided acrylic wall from v1 is removed.

The background is now deliberately simpler: a dark cyan/blue ambient field with slow flowing wave/light bands inspired by the calm motion language of the PS3 system interface. The background supplies atmosphere rather than pretending to be a physical foreground object. Mouse movement no longer drags a large background polygon around the scene.

## Focus vs MORE

The short information shown after clicking the current collectible remains a lightweight focus state and is intentionally kept separate from the complete detail surface.

`MORE` now opens a compact right-side smoked-acrylic drawer rather than a near-full-width page. The drawer is approximately 42% of the window width and 78% of its height, with an upper width cap. The large collectible remains visible on the left at comparable visual weight and is not reduced to a small thumbnail.

The detail tabs remain:

- Game: 概览 / 截图 / 记录 / 本地
- Movie: 概览 / 剧集 (or 截图) / 记录 / 本地

## Settings drawer

Settings/control mode is also reduced. Its Retro system drawer is approximately 34% of the window width and 78% of its height, aligned near the right edge. The Showcase retreats and dims but remains part of the scene.

## Feature reachability

Retro is allowed to hide management UI, but it must not remove useful capabilities.

Movie cover tools are restored to Retro through both the movie scene context menu and the movie record context menu. Flat Pro remains available through F12 / fallback management while Retro-specific management surfaces continue to mature.

## Box material pass

The Neo box keeps its smoked-acrylic identity but reduces cyan wireframe emphasis. Box depth is stronger so the object reads more as a collectible volume and less as a transformed poster with a glowing outline. Classic and Neo still share the same Arc motion system.

## Boundaries

This is still a preview, not the final Retro theme. No database/movie/game schema changes are introduced. Flat Pro remains the frozen baseline and fallback presentation.
