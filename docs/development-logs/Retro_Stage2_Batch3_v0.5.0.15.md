# Retro Stage 2 Batch 3 · v0.5.0.15

## Scope

This batch upgrades the ambient scene only:

- keep the existing PS/XMB-style dynamic background;
- add drifting `△ ○ □ ×` symbol layers;
- add a second, lighter wave layer that is rendered in front of the showcase;
- increase the wave amplitude so the environment remains visible even when the
  hero package is large.

Showcase geometry, click behavior, hover response, search, settings, archive
editing, and panel layouts are intentionally unchanged.

## Key changes

### AMBIENT SYMBOLS

Added multiple translucent symbol fields using `△ ○ □ ×` with deterministic
placement, slow right-to-left drift, slight rotation, and subtle vertical float.
The symbols are split into depth layers so the background feels more like a live
console environment than a flat wallpaper.

### FOREGROUND WAVES

Added a second wave pass after showcase rendering. These lighter wave bands are
rendered in front of the boxes but behind focus text, MORE, Settings, and other
scene UI. This keeps the ambient motion visible across the whole screen and
prevents the wave field from being completely hidden by the hero package.

### NOT BLOCKED

The original back-layer waves still drive the main ambience, but the new front
pass means the wave motion is no longer fully blocked by the boxes. Amplitudes
were increased so the bands travel through more of the frame.

## Runtime protection

Extended the local Windows smoke suite with a new ambient check that verifies:

- symbol specs are generated and move over time;
- foreground wave rendering changes the composed image;
- the extra ambient layers do not interrupt the Qt drawing pipeline.
