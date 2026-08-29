# Retro Sound Pack System Design · v0.5.0.17

## Status

Approved design for the Retro UI sound subsystem. This document defines scope,
architecture, data layout, user interaction, failure behavior, and test coverage
before implementation begins.

## Product goals

The sound system should make Retro navigation feel like a console shell while
remaining fully user-controlled. Users can keep multiple Sound Packs, switch the
active pack, and map each UI event to any imported sound. Imported source files
may be WAV, MP3, OGG, FLAC, M4A, or other FFmpeg-readable formats.

The system must never make box animation, browsing, Focus, MORE, Settings, or
launch/play behavior dependent on audio success. Audio is enhancement only.

## Non-goals

This version does not implement preview-video audio, background music, per-game
sound themes, audio visualization, or automatic online sound acquisition. It also
does not bundle copyrighted game audio with the application.

## Architecture

The subsystem is split into three independently testable units.

### SoundPackStore

Responsibilities:

- own the `soundpacks/` directory inside the configured application `data_dir`;
- create, copy, rename, delete, and enumerate Sound Packs;
- load and save each `pack.json` atomically;
- resolve the active pack and event mappings;
- enforce safe pack names and paths so mappings cannot escape the pack folder;
- keep old mappings valid when unrelated imports fail.

It does not decode audio and does not play sound.

### AudioImportService

Responsibilities:

- accept an external user-selected source file;
- copy the original file into the target pack's `originals/` directory;
- normalize playback media into PCM WAV inside `audio/`;
- use the application's existing FFmpeg configuration for non-WAV sources;
- stage work through temporary files and publish files/mappings only after
  successful validation;
- leave the previous mapping unchanged on any failure.

WAV input may be used directly when FFmpeg is unavailable. Other formats that
require conversion report a clear FFmpeg error instead of silently failing.

### UISoundService

Responsibilities:

- preload the active Sound Pack's mapped WAV files;
- expose semantic events such as `play("navigate")` rather than file paths;
- apply the current UI sound volume and enabled state;
- provide a dedicated preview channel for Settings audition buttons;
- isolate playback exceptions so UI interaction always continues.

The recommended runtime backend is Qt `QSoundEffect` for short, low-latency PCM
WAV playback. Source-format compatibility belongs to import time, not playback
time.

## Storage layout

Sound Packs live under the application's configured `data_dir`:

```text
data/
└─ soundpacks/
   ├─ 我的PS混搭/
   │  ├─ pack.json
   │  ├─ originals/
   │  │  ├─ RE3_move.mp3
   │  │  ├─ MGS_confirm.ogg
   │  │  └─ HL_back.wav
   │  └─ audio/
   │     ├─ navigate.wav
   │     ├─ focus.wav
   │     └─ back.wav
   └─ 生化3/
      └─ ...
```

`originals/` preserves the user's imported source material. `audio/` contains
normalized runtime WAV files. `pack.json` owns the semantic event mapping.

Example:

```json
{
  "name": "我的PS混搭",
  "mappings": {
    "navigate": "navigate.wav",
    "select": "select.wav",
    "focus": "focus.wav",
    "confirm": "confirm.wav",
    "back": "back.wav",
    "open_panel": "open_panel.wav",
    "close_panel": "close_panel.wav"
  }
}
```

The global application settings store only:

- UI sound enabled/disabled;
- active Sound Pack id/name;
- UI sound volume.

Per-event file mappings remain inside each Sound Pack.

## Supported UI events

Version 0.5.0.17 introduces exactly seven semantic events:

| Event | Trigger |
| --- | --- |
| `navigate` | Valid mouse-wheel move to previous/next box |
| `select` | Click a non-selected visible box and start moving it to primary position |
| `focus` | Click the already selected primary box to enter short-info Focus |
| `confirm` | Double-click primary game/movie to launch/play |
| `back` | Escape/blank action that actually leaves Focus or returns from a child scene |
| `open_panel` | MORE or Settings begins opening |
| `close_panel` | MORE or Settings begins closing |

Events bind to user actions, never animation frames. A 250 ms carousel motion
must therefore emit one sound, not one sound per `_arc_position` update.

## Playback policy

`navigate` uses restart behavior: repeated valid wheel steps stop/restart the same
navigation effect so rapid browsing produces a clean rhythmic sequence instead of
many overlapping voices.

Important events (`select`, `focus`, `confirm`, `back`, `open_panel`,
`close_panel`) may interrupt the current navigation effect. They are not queued
behind it.

Settings audition uses a separate preview channel and does not invoke the live UI
event pipeline.

## Retro Settings UX

Sound configuration remains inside the existing scene-native Retro Settings area.
No new custom top-level dialog is introduced.

The main Sound section contains:

```text
SOUND

UI 音效          [ ON ]
当前音效包        [ 我的 PS 混搭 ▼ ]
音量              ━━━━━●━━ 70%

[ 管理音效映射 > ]
```

The mapping page replaces the same right-side Settings content and includes one
row per event:

```text
盒子切换
RE3_menu_move.mp3             [▶] [更换] [×]
```

`更换` opens only the native Windows file chooser. After selection the import
pipeline copies and converts the file, then returns to the scene-native mapping
page. `▶` auditions the mapped sound. `×` removes only that event mapping.

Sound Pack management in the first release supports:

- create;
- duplicate current pack;
- rename;
- delete;
- switch active pack.

Deleting the active pack requires switching to another available pack first. If
no packs exist, the sound service becomes silently disabled rather than treating
absence as an error.

## Import transaction and error handling

Imports are transactional:

```text
choose external source
→ copy/stage temporary source
→ convert to temporary PCM WAV when needed
→ validate output exists and is readable
→ publish originals/audio files
→ atomically update pack.json
```

If conversion, copying, validation, or JSON persistence fails, the old event
mapping remains unchanged. Temporary partial files are cleaned when possible.

Runtime audio failures are logged/ignored by the audio subsystem and never block
carousel movement, focus changes, panel transitions, launch/play, or application
shutdown.

## Backup integration

Backup settings gain a separate option:

```text
☑ 包含 Sound Packs
```

It defaults to enabled. When selected, backup includes the whole `soundpacks/`
tree including `pack.json`, `originals/`, and normalized `audio/` files. Restored
packs should therefore be immediately playable without re-running FFmpeg.

## Compatibility and migration

Existing settings files that do not contain sound fields load with safe defaults:

- UI sound enabled: false until a usable pack exists;
- active pack: none;
- volume: 70%.

Existing movie/game databases and metadata require no migration.

Sound Packs are data assets and are not overwritten by future code-only overwrite
patches.

## Testing strategy

### Pure/service tests

Cover:

- pack create / duplicate / rename / delete;
- atomic mapping persistence;
- safe path validation;
- source copying into `originals/`;
- WAV direct import when FFmpeg is absent;
- non-WAV FFmpeg failure keeps the previous mapping;
- successful normalization publishes the new mapping only at the end;
- old settings load with safe sound defaults;
- active-pack switching and missing-pack behavior.

### GUI smoke

Extend the local Windows Retro smoke suite to verify:

- Sound section can be opened inside Retro Settings;
- mapping-management view is scene-native;
- Sound Pack switching does not raise Qt exceptions;
- semantic event calls can be exercised during carousel/focus/panel interaction;
- disabling sound leaves every existing interaction unchanged.

Automated smoke cannot reliably prove audible speaker output. Final acceptance
therefore includes a manual local check for latency, volume, event correctness,
and rapid-wheel restart behavior.

## Scope guard

Implementation must not modify package geometry, cover polygons, 4-up carousel
composition, ambient waves/symbols, search behavior, archive editing, focus text
layout, or MORE content except where a semantic sound event is attached to an
existing action boundary.
