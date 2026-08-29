# Retro Prototype v4 — Package Profile / Retro Primary

**Version:** v0.5.0.3  
**Date:** 2026-08-29  
**Status:** Retro primary presentation; Flat Pro no longer exposed as a user fallback.

## Why this pass exists

Real screenshots from v0.5.0.2 exposed two presentation problems that could not be fixed by merely tuning colors. First, the five-item Wide Arc was still visually composed as a three-item center group plus two added edge items; with fewer than five games, the missing slot remained visible and the rail looked unbalanced. Second, the collectible itself still read as a thick framed picture rather than a retail game/movie package. The front artwork was cropped, console platform strips could be eaten, the spine was weak, and PS1-style square artwork was forced into the same tall case proportions as PS3/PS4 artwork.

## UNIFORM RAIL

The browse scene now uses one horizontal rail model. Five or more records keep the wide five-item window. Collections with one to four records are re-spaced across the available scene width instead of reserving an empty fifth slot. The selected item remains larger, but the layout no longer depends on a fan shape.

The literal suspension rail/hanger introduced in v0.5.0.2 is removed. The original user request described the *feeling* of guided vending-machine/console motion, not a request for a visible metal hook. Movement keeps the fast console-style guided character without drawing a physical mechanism.

## PACKAGE PROFILE

Game packaging now resolves a visual profile from existing data without introducing a database migration. Existing tags and cover filenames may provide explicit hints such as PS1, PS2, PS3, PS4, PSP, Vita, Switch, Xbox 360 or Xbox One/Series. When no hint is available, the original cover aspect ratio is used as the fallback.

The initial profiles include:

- PS1 / square artwork -> jewel-case family;
- PS2 / Xbox 360 -> tall keepcase family;
- PS3 / PS4 / PS5 / modern Xbox -> Blu-ray-like tall family;
- PSP / Vita / Switch -> slimmer handheld families;
- unknown artwork -> ratio-based generic profile.

This deliberately avoids adding a `platform` column or changing game JSON/schema during a visual prototype pass. A formal platform field can be added later if manual platform assignment becomes necessary.

## FULL COVER

The front artwork no longer uses `KeepAspectRatioByExpanding`. It now uses full-cover fit: the entire source image is preserved inside the package face. This is especially important for real cover scans where the top PlayStation/Xbox/Nintendo platform band is part of the artwork. Small letterboxing is preferred over destroying packaging information.

Classic cases are thinner, have a real side/spine plane, a restrained clear-plastic film cue, and family-specific seams. Neo cases use the same package proportions but retain the smoked acrylic / very-low-intensity cyan edge language. The spine synthesizes a title/platform read when enough space exists.

Movie presentation is no longer just a poster with a thick side rectangle. It now uses a thinner media-case construction with a side/spine, top surface, full poster fit, and a restrained translucent blue case lip.

## RETRO PRIMARY

The user discovered that `更多管理（Flat Pro）` could reveal the frozen Flat Pro shell while its title/navigation/window controls remained hidden by Retro state. Rather than spend new work repairing a presentation that has already been frozen, v0.5.0.3 removes the user-facing fallback path:

- `更多管理（Flat Pro）` is removed from record menus;
- `切换到 Flat Pro 基线` is removed from Retro scene/system menus;
- F12 no longer hides Retro or exposes Flat Pro.

Flat Pro source remains in the repository as historical baseline/reference. Missing management abilities must now be migrated into Retro instead of using Flat Pro as an escape hatch.

## No data migration

This pass changes presentation logic only. Movie/game database schemas and archive JSON formats are unchanged.
