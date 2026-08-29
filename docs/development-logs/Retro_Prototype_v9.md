# Retro Prototype v9 — Stage 1 Stabilization

**Version:** v0.5.0.8  
**Status:** STAGE 1 stabilization / usability recovery

This pass follows the first-stage plan recorded after the v0.5.0.7 review. It deliberately does **not** start the Qt Quick / 3D showcase migration yet. The goal is to make the current Retro shell safer to use while preserving the visual direction.

## ARCHIVE EDIT

Retro regains direct archive editing entry points for both games and movies. The record context menu now exposes `编辑游戏档案…` / `编辑影片档案…`. For this stabilization stage these use compatibility dialogs; a later Retro UI-unification stage will move editing into the scene drawer instead of keeping independent windows.

The game editor restores title, series, developer, publisher, release date, tags, rating, description, notes, launch/timing paths, args, work directory, and screenshot directory. The movie editor restores code, title, cover key, actors, series, studio, release date, tags, rating, watched state, and notes.

## FAVORITE REMOVAL

Retro no longer presents Favorite/收藏 as a browsing or record-management concept. The terminal itself is the collection. The backend field remains untouched for archive compatibility, but Retro filters and context menus no longer expose it.

## MINIMUM WINDOW

Retro now enforces a minimum window size of **1100 × 700**. The showcase is intentionally a large-screen presentation surface; supporting arbitrarily tiny windows caused box geometry, title layout, and drawer composition to collapse.

Long focus titles continue to use a bounded two-line layout with adaptive font size.

## ABOUT

The Retro system panel now has a dedicated `关于` page showing the current application version. v0.5.0.8 is the first version to expose this inside the Retro shell.

## SETTINGS ENTRY CLEANUP

The system drawer is simplified to `设置 / 关于`. Repeated `打开完整设置…` entries, duplicated search, add-game, and appearance controls are removed from the system drawer. Search/add-game remain reachable from the scene context menu for now. The later UI-unification stage will replace the remaining independent Settings dialog with a native Retro drawer.

## AMBIENT CLEANUP

The diagonal base gradient is removed. The background now uses a restrained vertical dark base under the PS-style wave bands, eliminating the remaining diagonal glow read.

## PACKAGE FRONT FIT

The game artwork now receives its own inset polygon derived from the same slanted front-face geometry as the case. Artwork is clipped to that inner polygon rather than merely to a rectangular image region, closing the persistent top-right corner protrusion and adding a thin visible plastic lip around the sleeve.
