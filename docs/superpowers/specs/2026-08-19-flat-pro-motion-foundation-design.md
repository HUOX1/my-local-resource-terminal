# Flat Pro Motion Foundation Design

## Goal

Give Flat Pro a restrained motion language without changing Stage 1 business behavior or poster-wall cache rules.

## Scope

- Flat Pro only: motion enabled by a theme-level motion profile; Flat Dark/Light stay static.
- Poster wall reflow: when a settled resize changes poster cell layout, visible posters move from their old visual position toward the new one instead of snapping.
- Poster hover: subtle scale/lift only; no layout displacement.
- Wheel scrolling: one continuous velocity timer with short decay; new wheel input adds impulse without stop/restart stutter. Pixel-delta touchpad input keeps Qt-native handling.
- Archive enter/back: short fade + horizontal offset when switching between library and Movie/Game archive pages; refreshes of the already-visible page do not replay the transition.
- Remove obsolete Movie right-click and batch actions for 收藏/已观看.
- No sidebar animation in this release.
- No database, backup, metadata schema, scan, playback, launch, timing, or cache changes.

## Motion character

Flat Pro motion is short and restrained: reflow ~170 ms, hover ~110 ms, archive ~150 ms, wheel inertia ~200 ms tail. Motion never blocks input and is disabled outside Flat Pro.
