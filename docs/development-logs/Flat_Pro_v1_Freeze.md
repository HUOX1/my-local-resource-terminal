# Flat Pro v1 Freeze

Date: 2026-08-29
Status: FROZEN BASELINE

## Decision

Flat Pro stops active visual development from v0.5.0.0 onward.

Flat Pro was introduced after the first skeuomorphic/glass experiment became unstable and difficult to diagnose. Its purpose was to give the project a predictable PySide6 Widgets baseline so movie/game business flows, persistence, scanning, archive data, episode modeling, backup/restore and launch/play flows could mature without being blocked by visual experimentation.

That job is now considered complete.

## What “frozen” means

Flat Pro remains in the repository and remains usable as a baseline/debug presentation. Future changes should be limited to:

- real functional bugs;
- data/persistence correctness;
- compatibility fixes;
- severe usability regressions;
- changes required to keep shared business functions reachable.

Flat Pro should no longer receive large visual redesigns, new showcase concepts, or theme-specific animation systems.

## Why it is not deleted

Retro is intentionally more experimental. Keeping Flat Pro gives the project a known-good comparison surface:

- if data works in Flat Pro but not Retro, the problem is presentation;
- if both fail, investigate shared business/data layers;
- unfinished Retro management operations may temporarily fall back to Flat Pro while they are migrated.

F12 toggles between the Retro preview and the Flat Pro baseline in v0.5.0.0.

## Identity

The Identity entry flow is removed from the Retro startup path. Retro starts directly in Game Scene.

Identity code/data is not physically deleted in this freeze because Flat Pro still references it. It is considered legacy presentation infrastructure and may be removed later after Retro no longer depends on Flat Pro fallback UI.

## Next visual direction

Active visual development moves to the temporary working name **Retro Theme**: a retro-future personal media showcase built around spatial depth, physical/digital collection objects, hidden controls and scene-local detail panels.

## v0.5.0.3 addendum — fallback retired

The original freeze kept Flat Pro reachable as a temporary debug/fallback presentation. Real use exposed a serious transition defect: entering Flat Pro from Retro could reveal the old shell while Retro-hidden navigation/title/window controls remained hidden. Because active development has now committed to Retro, this fallback is retired instead of repaired.

From v0.5.0.3 onward:

- F12 no longer switches presentation;
- Retro record menus no longer expose `更多管理（Flat Pro）`;
- Retro system/scene menus no longer expose a Flat Pro switch;
- Flat Pro source remains in the repository as historical implementation/reference only.

Any management feature still missing in Retro must be migrated into Retro rather than depending on a user-visible fallback.
