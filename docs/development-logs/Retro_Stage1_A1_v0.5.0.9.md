# Retro Stage 1 A1 — v0.5.0.9

## Scope

This is the first re-run of Stage 1 after the failed v0.5.0.8 experiment. The failed v0.5.0.8 release remains abandoned; this release skips directly from v0.5.0.7 to v0.5.0.9.

A1 is intentionally limited to low-risk navigation cleanup:

- add an in-scene **About** tab that reports the current version;
- reduce the gear/system drawer to **Settings / About** only;
- remove duplicated Settings, search, add-game, scan, box-style, and corner-placement entries from that drawer;
- keep those existing scene/context-menu entry points unchanged where they already belong;
- remove **Favorite** from Retro record context menus and Retro filters while preserving the underlying data field for compatibility;
- reset any persisted legacy `favorite` Retro filter to `all`.

## Safety boundary

A1 does **not** change:

- showcase layout or carousel geometry;
- `paintEvent()` ordering;
- game/movie box geometry or cover clipping;
- background rendering;
- frameless-window resize behavior;
- focus/MORE panel geometry;
- archive-edit dialogs.

The system drawer continues to use the existing Retro panel rendering path; only its tabs and content are simplified.

## Verification

- TDD red state confirmed before implementation for About/system-drawer/favorite/version behavior.
- Focused Retro regression suite: 57 tests passed in the build workspace.
- Modified Python sources compile successfully.
- Real Windows GUI acceptance remains the local `tools\\run_retro_smoke.bat` run on the user's PySide6 6.11.2 environment.
