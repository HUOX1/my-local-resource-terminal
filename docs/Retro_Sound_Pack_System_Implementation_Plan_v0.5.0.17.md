# Retro Sound Pack System v0.5.0.17 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user-managed, low-latency Retro UI Sound Packs with multi-format import, seven semantic UI events, scene-native mapping controls, persistent settings, and backup support.

**Architecture:** Keep audio data, import/normalization, and playback separate. `SoundPackStore` owns safe pack/mapping persistence under `data_dir/soundpacks`; `AudioImportService` copies originals and normalizes runtime media to PCM WAV transactionally; `UISoundService` preloads mapped WAV files into Qt `QSoundEffect` and exposes only semantic `play(event)` calls. Retro UI binds existing action boundaries to semantic events and renders sound settings inside the existing right-side Settings scene.

**Tech Stack:** Python 3.11+, PySide6 6.x (`QtMultimedia.QSoundEffect`), FFmpeg subprocess integration, JSON/Pathlib/shutil/tempfile, pytest, existing Windows Retro GUI smoke runner.

**Spec:** `docs/Retro_Sound_Pack_System_Design_v0.5.0.17.md`

## Global Constraints

- Version target: `0.5.0.17`.
- Sound Packs live under `<AppSettings.data_dir>/soundpacks` and code-only overwrite patches must never ship user Sound Pack data.
- Imported originals may be WAV, MP3, OGG, FLAC, M4A, or any FFmpeg-readable format.
- Runtime playback uses normalized PCM WAV; source compatibility is handled during import.
- Exactly seven live semantic events in this version: `navigate`, `select`, `focus`, `confirm`, `back`, `open_panel`, `close_panel`.
- Audio failure must never block carousel movement, Focus, MORE/Settings transitions, launch/play, or shutdown.
- Do not alter package geometry, cover polygons, 4-up composition, ambient waves/symbols, search behavior, archive editing, focus text layout, or MORE content except for attaching semantic sound calls at existing action boundaries.
- Retro sound management remains scene-native. The only allowed external UI during mapping is the native file chooser.
- Imported sound files are copied into the selected Sound Pack; external source paths are not retained as runtime dependencies.
- Default migration behavior: sound disabled if no usable pack exists, no active pack, volume `0.70`.

---

### Task 1: Sound Pack persistence core

**Files:**
- Create: `app/services/sound_pack_store.py`
- Create: `tests/test_sound_pack_store_v0517.py`

**Interfaces:**
- Produces: `SOUND_EVENTS: tuple[str, ...]`
- Produces: `SoundPackInfo(id: str, name: str, path: Path)`
- Produces: `SoundPackStore(root: Path)`
- Produces methods: `list_packs()`, `create_pack(name)`, `duplicate_pack(pack_id, new_name)`, `rename_pack(pack_id, new_name)`, `delete_pack(pack_id)`, `load_mappings(pack_id)`, `set_mapping(pack_id, event, runtime_filename, original_filename)`, `clear_mapping(pack_id, event)`, `resolve_audio_path(pack_id, event)`.

- [ ] **Step 1: Write failing persistence and safety tests**

```python
from pathlib import Path
import pytest

from app.services.sound_pack_store import SOUND_EVENTS, SoundPackStore


def test_create_map_duplicate_rename_delete_pack(tmp_path: Path):
    store = SoundPackStore(tmp_path / "soundpacks")
    pack = store.create_pack("我的 PS 混搭")
    assert pack.path.exists()
    assert (pack.path / "originals").is_dir()
    assert (pack.path / "audio").is_dir()
    assert store.load_mappings(pack.id) == {}

    store.set_mapping(pack.id, "navigate", "navigate.wav", "RE3_move.mp3")
    assert store.load_mappings(pack.id)["navigate"]["audio"] == "navigate.wav"

    copied = store.duplicate_pack(pack.id, "副本")
    assert store.load_mappings(copied.id)["navigate"]["original"] == "RE3_move.mp3"

    renamed = store.rename_pack(copied.id, "MGS")
    assert renamed.name == "MGS"
    store.delete_pack(renamed.id)
    assert {p.id for p in store.list_packs()} == {pack.id}


def test_pack_names_and_mapping_paths_cannot_escape_root(tmp_path: Path):
    store = SoundPackStore(tmp_path / "soundpacks")
    with pytest.raises(ValueError):
        store.create_pack("../outside")
    pack = store.create_pack("safe")
    with pytest.raises(ValueError):
        store.set_mapping(pack.id, "navigate", "../escape.wav", "source.wav")
    with pytest.raises(ValueError):
        store.set_mapping(pack.id, "unknown", "x.wav", "source.wav")


def test_sound_event_contract_is_exact():
    assert SOUND_EVENTS == (
        "navigate", "select", "focus", "confirm", "back", "open_panel", "close_panel"
    )
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `PYTHONPATH=. pytest -q tests/test_sound_pack_store_v0517.py`

Expected: collection/import failure because `app.services.sound_pack_store` does not exist.

- [ ] **Step 3: Implement atomic JSON persistence and safe path validation**

Use `pack.json.tmp` + `Path.replace()` for writes. Generate stable UUID ids for directory names; keep the display name in JSON. Validate event names against `SOUND_EVENTS` and reject absolute paths, `..`, or nested filenames for mapped runtime/original files.

- [ ] **Step 4: Run Task 1 tests GREEN**

Run: `PYTHONPATH=. pytest -q tests/test_sound_pack_store_v0517.py`

Expected: all Task 1 tests PASS.

---

### Task 2: Transactional multi-format audio import

**Files:**
- Create: `app/services/audio_import_service.py`
- Create: `tests/test_audio_import_service_v0517.py`
- Modify: `app/services/sound_pack_store.py`

**Interfaces:**
- Consumes: `SoundPackStore` from Task 1.
- Produces: `AudioImportError(RuntimeError)`.
- Produces: `ImportedSound(original_path: Path, runtime_path: Path)`.
- Produces: `AudioImportService(store: SoundPackStore, ffmpeg_path: str)`.
- Produces: `import_for_event(pack_id: str, event: str, source: Path) -> ImportedSound`.

- [ ] **Step 1: Write failing WAV/direct-import and rollback tests**

```python
import json
from pathlib import Path
import pytest

from app.services.audio_import_service import AudioImportError, AudioImportService
from app.services.sound_pack_store import SoundPackStore


def test_wav_import_copies_original_and_publishes_mapping_without_ffmpeg(tmp_path: Path):
    source = tmp_path / "click.wav"
    source.write_bytes(b"RIFF" + b"\0" * 128)
    store = SoundPackStore(tmp_path / "soundpacks")
    pack = store.create_pack("mix")
    service = AudioImportService(store, ffmpeg_path="missing-ffmpeg")
    imported = service.import_for_event(pack.id, "focus", source)
    assert imported.original_path.read_bytes() == source.read_bytes()
    assert imported.runtime_path.name == "focus.wav"
    assert store.resolve_audio_path(pack.id, "focus") == imported.runtime_path


def test_non_wav_conversion_failure_preserves_previous_mapping(tmp_path: Path):
    store = SoundPackStore(tmp_path / "soundpacks")
    pack = store.create_pack("mix")
    old = pack.path / "audio" / "navigate.wav"
    old.write_bytes(b"old")
    store.set_mapping(pack.id, "navigate", old.name, "old.wav")
    source = tmp_path / "move.mp3"
    source.write_bytes(b"not-really-mp3")
    service = AudioImportService(store, ffmpeg_path=str(tmp_path / "does-not-exist"))
    with pytest.raises(AudioImportError):
        service.import_for_event(pack.id, "navigate", source)
    assert store.resolve_audio_path(pack.id, "navigate") == old
```

- [ ] **Step 2: Verify RED**

Run: `PYTHONPATH=. pytest -q tests/test_audio_import_service_v0517.py`

Expected: import failure because `audio_import_service.py` does not exist.

- [ ] **Step 3: Implement staging, copying, FFmpeg normalization, and commit-last mapping update**

For non-WAV sources run FFmpeg with arguments equivalent to:

```text
ffmpeg -y -i <source> -vn -ac 2 -ar 44100 -c:a pcm_s16le <temporary-output.wav>
```

Do not use `shell=True`. Publish original/runtime files only after successful conversion/output validation; update `pack.json` last. On failure, remove temporary files and leave the previous event mapping untouched.

- [ ] **Step 4: Run Task 2 tests GREEN**

Run: `PYTHONPATH=. pytest -q tests/test_audio_import_service_v0517.py`

Expected: Task 2 tests PASS.

---

### Task 3: Low-latency semantic playback service

**Files:**
- Create: `app/services/ui_sound_service.py`
- Create: `tests/test_ui_sound_service_v0517.py`

**Interfaces:**
- Consumes: `SoundPackStore`, `SOUND_EVENTS`.
- Produces: `UISoundService(store, parent=None)`.
- Produces: `configure(enabled: bool, active_pack_id: str | None, volume: float) -> None`.
- Produces: `reload_pack() -> None`, `play(event: str) -> None`, `preview(path: Path) -> None`, `stop_preview() -> None`.

- [ ] **Step 1: Write a failing source-contract test for channel and restart policy**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ui_sound_service_uses_qsoundeffect_and_separate_preview_channel():
    source = (ROOT / "app/services/ui_sound_service.py").read_text(encoding="utf-8")
    assert "QSoundEffect" in source
    assert "self._effects" in source
    assert "self._preview_effect" in source
    assert 'if event == "navigate"' in source
    assert ".stop()" in source and ".play()" in source
```

- [ ] **Step 2: Verify RED**

Run: `PYTHONPATH=. pytest -q tests/test_ui_sound_service_v0517.py`

Expected: file-not-found failure.

- [ ] **Step 3: Implement QSoundEffect preload and failure isolation**

Create one cached `QSoundEffect` per mapped live event and one dedicated preview effect. Clamp volume to `0.0..1.0`. `play("navigate")` stops/restarts the navigation effect; important events stop an active navigation effect before playing. Invalid/missing mappings return silently. Wrap public playback operations so audio exceptions do not escape into UI handlers.

- [ ] **Step 4: Run Task 3 tests GREEN**

Run: `PYTHONPATH=. pytest -q tests/test_ui_sound_service_v0517.py`

Expected: Task 3 tests PASS.

---

### Task 4: Persist Retro sound preferences and integrate scene-native Sound Settings

**Files:**
- Modify: `app/ui/retro_showcase.py`
- Create: `tests/test_retro_sound_scene_v0517.py`

**Interfaces:**
- Consumes: `host.settings.data_dir`, `host.settings.ffmpeg_path`, `SoundPackStore`, `AudioImportService`, `UISoundService`.
- Uses existing `QSettings("LocalMovieManager", "LocalMovieManager")` for global Retro sound preferences with keys:
  - `retro/sound_enabled`
  - `retro/sound_pack_id`
  - `retro/sound_volume`
- Adds overlay state `_system_page: Literal["settings", "sound"]` and scene-native hit/action rectangles for sound controls.

- [ ] **Step 1: Write failing source and state tests**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_retro_sound_settings_are_scene_native_and_persisted():
    source = (ROOT / "app/ui/retro_showcase.py").read_text(encoding="utf-8")
    assert '"retro/sound_enabled"' in source
    assert '"retro/sound_pack_id"' in source
    assert '"retro/sound_volume"' in source
    assert 'self._system_page = "settings"' in source
    assert 'self._system_action_rects["sound_manage"]' in source
    assert "QFileDialog.getOpenFileName" in source
    assert "SoundPackStore" in source
    assert "AudioImportService" in source
    assert "UISoundService" in source
```

- [ ] **Step 2: Verify RED**

Run: `PYTHONPATH=. pytest -q tests/test_retro_sound_scene_v0517.py`

Expected: assertions fail because no sound scene exists.

- [ ] **Step 3: Add Sound summary controls to current Retro Settings body**

Keep `RETRO UI FONT` and `ABOUT`, but add a compact SOUND section showing enabled state, current pack name, volume, and `管理音效映射 >`. Handle toggling/enabling and pack cycling through scene hit rectangles rather than a new custom dialog.

- [ ] **Step 4: Add scene-native mapping page and native import chooser**

Render seven rows from `SOUND_EVENTS`, each with mapped source name and hit rectangles for audition, replace/import, and clear. Add pack actions for create, duplicate, rename, delete, and active-pack cycling using compact in-scene controls; where text input is required, reuse existing scene-native line-edit/capsule patterns rather than introducing a new application-owned top-level dialog. `更换` may open only `QFileDialog.getOpenFileName(...)` with audio extensions and then call `AudioImportService.import_for_event(...)`.

- [ ] **Step 5: Bind exactly one semantic sound to each existing action boundary**

Attach calls at these boundaries only:

```text
_start_arc(valid step)              -> navigate
non-current click before animation  -> select
focus transition false -> true      -> focus
double-click current launch/play    -> confirm
action that actually leaves focus   -> back
MORE/Settings false -> true         -> open_panel
MORE/Settings true -> false         -> close_panel
```

Do not emit from animation property setters or paint methods.

- [ ] **Step 6: Run Task 4 source tests GREEN**

Run: `PYTHONPATH=. pytest -q tests/test_retro_sound_scene_v0517.py`

Expected: PASS.

---

### Task 5: Backup support, local smoke, versioning, and overwrite package

**Files:**
- Modify/Create latest project versions of: `app/services/backup_restore_service.py`, `app/ui/settings_dialog.py` only if the local source contract exposes them; otherwise implement pack backup through the existing backup service extension point without replacing unrelated settings code.
- Modify: `tests/test_retro_gui_smoke.py`
- Modify: `tools/retro_smoke_runner.py`
- Modify: `app/bootstrap.py`
- Modify: `app/ui/app_chrome.py`
- Modify: `app/ui/retro_showcase.py`
- Modify: `pyproject.toml`
- Create: `docs/development-logs/Retro_Sound_Pack_System_v0.5.0.17.md`
- Test: `tests/test_retro_sound_backup_v0517.py`

**Interfaces:**
- Backup option label: `包含 Sound Packs`, default enabled.
- Backup source: `<settings.data_dir>/soundpacks/**`.
- Restore destination: current `<settings.data_dir>/soundpacks/`.
- Local smoke target after integration: existing 8 checks plus one Sound Settings / semantic-event check.

- [ ] **Step 1: Write failing backup contract test**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_backup_contract_mentions_soundpacks_and_default_enabled_option():
    service = (ROOT / "app/services/backup_restore_service.py").read_text(encoding="utf-8")
    dialog = (ROOT / "app/ui/settings_dialog.py").read_text(encoding="utf-8")
    assert "soundpacks" in service.casefold()
    assert "包含 Sound Packs" in dialog
    assert "setChecked(True)" in dialog
```

- [ ] **Step 2: Verify RED, then implement backup inclusion/restore**

Run: `PYTHONPATH=. pytest -q tests/test_retro_sound_backup_v0517.py`

Expected: FAIL before implementation; PASS after adding opt-in flag plumbing and safe tree copy/restore.

- [ ] **Step 3: Extend GUI smoke with Sound Settings check**

Add a ninth smoke check that creates a temporary `data_dir/soundpacks`, opens Retro Settings, enters the Sound page, switches/loads a pack, calls all seven semantic events with sound disabled, and confirms no Python exception is routed through Qt.

- [ ] **Step 4: Update versions and development log**

Set all visible/package versions to `0.5.0.17` and document storage layout, import behavior, event map, backup behavior, and manual audible-acceptance requirement.

- [ ] **Step 5: Run verification suite**

Run at minimum:

```text
PYTHONPATH=. pytest -q tests/test_sound_pack_store_v0517.py tests/test_audio_import_service_v0517.py tests/test_ui_sound_service_v0517.py tests/test_retro_sound_scene_v0517.py tests/test_retro_sound_backup_v0517.py
python -m compileall app tests tools
```

On the user's Windows environment, final acceptance remains:

```text
tools\run_retro_smoke.bat
PASS (9/9 checks passed)
```

Automated tests do not claim audible-output success; the user performs the final latency/event/volume ear check.

- [ ] **Step 6: Build and verify overwrite ZIP**

Package only repo-relative changed/new files plus `PATCH_NOTES.txt` and `SHA256SUMS.txt`. Extract to a clean verification directory, run `sha256sum -c SHA256SUMS.txt`, and never include any actual `data/soundpacks` user content in the patch.
