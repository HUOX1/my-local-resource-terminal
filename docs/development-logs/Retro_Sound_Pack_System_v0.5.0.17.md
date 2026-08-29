# Retro Sound Pack System · v0.5.0.17

## Scope

This release adds the first full Retro UI sound subsystem without changing box
geometry, cover polygons, 4-up composition, ambient waves/symbols, Focus text,
search, archive editing, or MORE content.

## Sound Pack architecture

The subsystem is split into three focused services:

- `SoundPackStore` owns `<data_dir>/soundpacks`, pack metadata, safe path rules,
  atomic `pack.json` writes, mapping CRUD, and pack create/copy/rename/delete.
- `AudioImportService` copies user-selected originals into `originals/`, keeps
  the original filename for identification, and publishes event-named runtime
  WAV files under `audio/`. Non-WAV input is normalized with FFmpeg to 44.1 kHz,
  stereo, signed 16-bit PCM WAV.
- `UISoundService` preloads mapped runtime WAV files through Qt `QSoundEffect`,
  keeps preview audition separate from live UI playback, and isolates audio
  failures from navigation and launch/play behavior.

## Semantic events

Version 0.5.0.17 introduces exactly seven live UI events:

- `navigate` — valid wheel/keyboard box movement;
- `select` — click a non-current visible box into the primary position;
- `focus` — click the current box into short-info Focus;
- `confirm` — double-click the current box to launch/play;
- `back` — leave Focus or return from the Sound mapping child scene;
- `open_panel` — MORE/Settings begins opening;
- `close_panel` — MORE/Settings begins closing.

`navigate` uses stop/restart semantics for rapid scrolling. Important events stop
an active navigation sound before playing. No sound is attached to animation
frames or paint callbacks.

## Retro Settings integration

The existing right-side Settings scene now includes a SOUND section with:

- UI sound enable/disable;
- current Sound Pack cycling;
- volume control;
- entry to a scene-native Sound Mapping page.

The mapping page exposes all seven events with audition, replace/import, and
clear actions. Pack management supports create, duplicate, rename, delete, and
switching. Pack-name entry stays inside the Retro scene. Selecting an audio file
uses only the native file chooser.

## Import transaction behavior

Imports stage source/runtime files first and update `pack.json` last. Conversion
failure leaves the old mapping intact. Mapping-persistence failure restores the
previous runtime/original files, so a failed replacement cannot silently change
an existing event sound.

WAV input can be copied directly when FFmpeg is unavailable. MP3, OGG, FLAC,
M4A, AAC, WMA, and other FFmpeg-readable formats use the configured FFmpeg path.

## Backup integration

To avoid overwriting legacy backup/settings files, Sound Pack backup is added
through a small adapter around the existing backup service. Advanced Settings →
Backup gains `包含 Sound Packs`, enabled by default. When enabled, the complete
`soundpacks/` tree is appended to the existing backup ZIP; restore merges those
files back into the current `data_dir/soundpacks` after the base restore.

## Validation

Pure tests cover pack CRUD/path safety, direct WAV import, FFmpeg failure
rollback, persistence-failure rollback, playback-service contract, scene-native
sound controls/event attachment, and backup/restore behavior.

The Windows local GUI smoke runner gains a ninth check:

`[RUN ] sound packs / mapping / semantic events`

Final audible acceptance remains manual because automated smoke cannot prove
speaker output, latency, subjective volume, or rapid-wheel rhythm.
