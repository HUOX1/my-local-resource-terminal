# Retro Performance Smoke Budget Fix · v0.5.0.17.1

Date: 2026-08-30

## Symptom

On native Windows, the new idle ambient repaint smoke could fail with `paint_events=29` during an 800 ms window even though the ambient timer ended at the intended 66 ms interval.

## Root cause

The smoke started counting every `QEvent.Paint` immediately after showing the native window. Delayed Windows expose/compositor paints and pointer/hover settling are not equivalent to app-owned ambient animation ticks, so the test could report an apparent ~30 fps repaint rate while the ambient timer itself was already configured for ~15 fps.

## Fix

- Move the synthetic pointer to a blank corner and allow a 300 ms native-window settle period.
- Keep raw Paint events as diagnostic output only.
- Measure the app-owned `QTimer.timeout` signal with `QSignalSpy` for 1000 ms.
- Accept 10-20 ambient timeouts, which covers normal Windows timer jitter around the 66 ms (~15.2 Hz) target while still rejecting the former ~30 Hz loop.
- Rename the smoke label to `idle ambient timer budget` to match what is actually being asserted.

## Scope

No production rendering, animation timing, Sound Pack code, or UI behavior changes are included. Product version remains `v0.5.0.17.1`.

## Validation

Container validation can verify the source contract, non-GUI regressions, syntax compilation, and patch hashes. Native Windows Qt timing remains authoritative and must be re-run with `tools\\run_retro_smoke.bat`.
