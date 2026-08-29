# Retro Stage 2 Batch 1 · v0.5.0.13

## Scope

This batch moves the first group of everyday controls into the Retro scene while keeping the Showcase rendering architecture frozen.

## Changes

- Replaced the modal search prompt with a centered scene-native capsule search field.
- Search is live with a short debounce, keeps separate game/movie queries, closes with Escape or a click on the scene, and keeps the active query until cleared.
- Gear now opens the settings drawer directly; the intermediate Settings/About tabs were removed.
- About/version information now lives inline inside the settings drawer.
- Added a scene-native installed-font selector for Retro text UI. The selection is persisted via `QSettings` under `retro/ui_font_family`, intentionally avoiding an AppSettings schema migration in this batch.
- Kept one temporary `高级设置…` bridge to the legacy SettingsDialog for data paths/player/ffmpeg and other complex controls that are not yet scene-native.
- Extended the local Windows GUI smoke suite with search/settings/font runtime coverage.

## Frozen areas

No Carousel geometry, package/cover geometry, ambient wave algorithm, resize architecture, MORE content structure, or archive edit logic was changed in this batch.
