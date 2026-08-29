# Retro Prototype v3 — Wide Arc / Suspended Showcase

**Version:** v0.5.0.2  
**Date:** 2026-08-29  
**Status:** Retro Preview iteration; Flat Pro remains the baseline/fallback.

## Why this iteration exists

The v0.5.0.1 continuous Arc solved the most obvious movement snap, but the settled browse composition remained left-heavy: the selected collectible and its two neighbours occupied the left side while the right side stayed empty until focus information appeared. User feedback also confirmed that the thin ambient waves felt too flat and their short repeating rhythm read like a looping GIF.

This iteration keeps the clean Retro scene and changes the browse presentation rather than adding more permanent UI.

## WIDE ARC

The default browse state is now a console-like horizontal content rail. Around five logical positions remain visible at once:

- current selection is enlarged at the centre;
- one and two positions on each side progressively reduce in scale and opacity;
- objects enter and leave through off-screen continuation anchors;
- all settled and animated poses still come from the same continuous `arc_pose()` function.

Focus is a separate state. Clicking the current object moves the hero left and enlarges it so the concise text information can appear on the right. The browse state itself therefore no longer reserves an empty right-hand information area.

## HANGER / SUSPENSION RAIL

A restrained metal suspension rail is introduced near the top of the scene. The browse focus sits beneath a fixed hanger: during a wheel transition the collection moves along the rail and the newly selected item arrives beneath that hanger.

The rail is deliberately subtle. It is a spatial/display cue, not a vending-machine illustration or a dominant HUD element.

## CONTINUOUS AMBIENT

The background no longer relies on a finite phase that resets after one cycle. The ambient phase is monotonic for the lifetime of the scene.

The previous thin wave lines are replaced by several broad translucent bands with different:

- speeds;
- amplitudes;
- thicknesses;
- secondary frequencies;
- cyan/blue-green values.

The intent remains PS3/XMB-like: the background supplies slow atmosphere while the collectible objects carry the interaction and depth.

## Existing behaviour retained

- single click: focus current item;
- double click: launch/play;
- right click: content management menu;
- wheel/arrow keys: continuous rail selection;
- MORE: compact right-side detail drawer;
- Settings: compact right-side system drawer;
- Movie cover tools remain accessible from Retro context menus;
- F12 returns to the Flat Pro baseline.

## Next evaluation

This is still a preview. The next decisions should be based on actual screenshots and use, especially:

1. whether five visible objects create the desired PS3-like balance;
2. whether the suspension rail feels like a useful physical metaphor or is still too explicit;
3. box/poster scale and spacing at common window sizes;
4. whether the multi-layer ambient bands have enough depth without distracting from covers.
