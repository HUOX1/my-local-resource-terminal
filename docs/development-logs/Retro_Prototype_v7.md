# Retro Prototype v7 — Carousel Geometry Pass

Version: **v0.5.0.6**

## CLEAN AMBIENT

Retro ambient background now uses only the dark base gradient plus the continuous multi-layer wave bands. The additional radial glow and lower stage glow from v6 were removed because their alpha layers created visible color strata and made the otherwise clean PS-style background look segmented.

## EDGE GAP RAIL

Browse layout no longer spaces packages by fixed center-point percentages. Each settled rail measures the actual rendered width of the visible package objects (including different cover ratios and platform package profiles), anchors the selected object, then derives one shared visible edge gap for neighboring packages. When the row would otherwise overflow, that gap can become a mild, uniform overlap instead of leaving large irregular holes between the outer and inner boxes.

## SEAMLESS WRAP

The carousel no longer modulo-wraps a package position while it is visible. Motion is represented as an unwrapped segment between two integer rail bases. During a wrap, the outgoing instance continues completely past the window edge while a cyclic draw copy enters from the opposite edge. This is especially important for 2–4 item libraries, where the old shortest-distance modulo mapping made the right-most package teleport directly to the left-most slot.

No MORE/detail layout, focus information, box material, or function-recovery behavior was intentionally changed in this pass.
