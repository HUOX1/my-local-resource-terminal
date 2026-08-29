# Retro Stage 1 A2 — v0.5.0.10

## Scope

Stage 1 A2 restores archive editing only. The v0.5.0.9 Retro rendering, resize behavior, background, showcase geometry, focus composition, MORE panel, and package drawing are intentionally frozen for this pass.

## Changes

- Restored `编辑游戏档案…` in the Retro game record context menu.
- Restored `编辑影片档案…` in the Retro movie record context menu.
- Game edits save through the existing `GameCatalogService.update_game()` path.
- Movie edits save through the existing `CatalogService.update_metadata()` path.
- Added temporary compatibility editors for Stage 1. They are deliberately conventional Qt dialogs; Stage 2 will migrate editing into the Retro scene.
- Both compatibility editors use a `QScrollArea`, keep Save/Cancel outside the scroll area, and bound their initial size to the available desktop so a long form does not extend past the display.
- The Retro favorite concept removed in A1 is not reintroduced by the editors.

## Windows GUI smoke extension

The local smoke suite now includes `archive edit dialogs` in addition to the existing drawing and native resize/repaint checks. It creates both real PySide6 dialogs, verifies their scrollable form container, and builds real `GameMetadataPatch` / `MovieMetadataPatch` results.

Expected local result after applying this patch:

```text
[PASS] draw pipeline: browse/focus/MORE/system/chrome
[PASS] native widget resize/repaint
[PASS] archive edit dialogs
PASS (3/3 checks passed)
```

## Regression guard

The `retro_showcase.py` diff from v0.5.0.9 is constrained to imports/version, two context-menu actions, and the two edit handlers. No drawing method or resize path is changed in A2.
