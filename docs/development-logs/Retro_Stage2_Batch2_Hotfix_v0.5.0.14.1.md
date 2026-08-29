# Retro Stage 2 Batch 2 Hotfix · v0.5.0.14.1

## Trigger

The Windows local GUI smoke suite caught a regression in the existing
`minimum window / long focus title` check after v0.5.0.14 enlarged the primary
browse package.

At the supported 1100×700 minimum viewport, the short-info area fell below the
280 px safety width.

## Root cause

v0.5.0.14 raised the settled browse hero scale from `1.00` to `1.10`.  The old
focus formula then multiplied that already enlarged value by another `1.12`,
producing a final focus scale of `1.232`.

The intended interaction was different: browse should keep the stronger 1.10
hero, while focus should rebalance package and text around an independent
1.12 target.

## Fix

- Keep the four-up browse hero scale at `1.10`.
- Interpolate the center package toward an independent focus target of `1.12`.
- Preserve the established side-item focus attenuation.
- Do not change four-up positions, hover response, click behavior, wrap logic,
  cover drawing, background, settings, search, archive editing, or MORE.

## Regression coverage

Added a pure-state regression test proving:

- browse center scale = `1.10`;
- focused center scale = `1.12`;
- focus no longer compounds `1.10 × 1.12`.

The existing Windows local smoke check remains the final runtime gate for the
1100×700 long-title layout.
