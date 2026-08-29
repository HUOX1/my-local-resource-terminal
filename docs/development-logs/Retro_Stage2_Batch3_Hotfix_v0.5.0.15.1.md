# Retro Stage 2 Batch 3 Hotfix · v0.5.0.15.1

## Scope

Tight visual hotfix for the ambient scene only.

Goals:
- move more ambient activity into the upper and lower thirds of the screen;
- keep the central hero package visually dominant;
- brighten the cyan/blue ambient palette;
- preserve the existing showcase composition and interaction logic.

## Changes

### Ambient redistribution

The ambient wave field and `△ ○ □ ×` symbols are redistributed so the top and
bottom parts of the frame carry more motion.  The center lane still has some
movement, but it is intentionally weaker so the package remains the main visual
subject.

### Foreground waves around the hero box

Foreground waves are now biased toward upper and lower lanes instead of running
mainly across the center of the package.  This keeps the scene alive without
placing heavy overlay content directly over the box art.

### Brighter palette

All ambient layers were shifted to a brighter cyan/blue range.  The goal is to
make the scene feel more luminous without turning it into neon.

## Unchanged

- showcase geometry and 4-up composition;
- click / focus / hover behavior;
- search and settings;
- archive editing;
- MORE and system panels.
