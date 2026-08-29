# Retro Prototype v6 — FUNCTION RECOVERY

Version: **v0.5.0.5**

## FUNCTION RECOVERY

Retro is now the primary presentation, so missing management entry points are
recovered directly inside Retro instead of falling back to Flat Pro. This pass
restores the first daily-use browsing set without adding permanent toolbar UI.

## ADD GAME

- Game scene context menu now exposes **添加游戏…**.
- System → 资源库 also exposes **添加游戏…**.
- The existing `GameEditDialog` / `GameCatalogService.create_game()` flow remains
  the single business implementation; Retro only restores the entry point.

## SEARCH / FILTER / SORT / FOLDER

Scene context menus now provide:

- search / clear search;
- the stable Flat Pro filter set plus dynamic tags and movie-library filters;
- the existing game/movie sort keys and ascending/descending direction;
- collection-folder browsing;
- moving the focused record to a collection folder.

Retro queries the existing catalog services directly using its own view state.
Stable filter/sort/folder choices are persisted through dedicated Retro signals,
without driving hidden Flat Pro widgets. Dynamic tag/library filters remain
session-only, matching the previous persistence rule.

## SCOPE

This pass intentionally does **not** restore full game/movie metadata editing,
episode management, batch movie editing, or a traditional list view. Those are
separate migration passes.
