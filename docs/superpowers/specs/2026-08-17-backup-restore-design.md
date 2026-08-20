# Local Backup and Restore Design

## Goal
Add offline ZIP backup and restore to Settings without adding any main-window controls.

## Backup contents
- `library.db` as a consistent SQLite snapshot.
- `metadata/*.json` permanent movie archives and viewing history.
- `settings/settings.json` as a settings snapshot.
- `covers/` when “包含封面” is checked (checked by default).
- `manifest.json` describing backup format/version and whether covers are included.

Never include movie video files, cache, logs, generated covers, thumbnails, or temporary files.

## Restore semantics
- Restore into the paths configured on the current machine.
- Never restore old absolute location fields from the backup: `data_dir`, `cover_dir`, library paths, player executable, ffprobe/ffmpeg paths, or cover-tool source path stay as currently configured.
- Restore non-location UI/preferences from the settings snapshot where compatible.
- Application data is restored as a backup state: replace `library.db` and replace current `metadata/*.json` with the backup metadata set.
- Covers use merge semantics: backup covers overwrite same-name current covers, while current covers not present in the backup are retained.
- If target application data or matching cover files already exist, require explicit “覆盖并恢复” confirmation; otherwise cancel with no changes.
- Validate the ZIP structure before touching current files.
- Restore runs transactionally at the filesystem level: snapshot the files that will change to a temporary rollback directory; if any step fails, restore the snapshot and remove newly-created cover files.
- After successful restore, prompt for application restart. Do not attempt a partial hot reload of service state.

## UI
Settings gains a compact “备份与恢复” section:
- checkbox: `包含封面` (default checked)
- button: `创建备份…`
- button: `从备份恢复…`

Backup proposes filename `LocalMovieManager_Backup_YYYY-MM-DD_HHMM.zip`.

## Safety
- Only backups with a valid `manifest.json` and supported format version are accepted.
- ZIP path traversal entries are rejected.
- Restore never deletes videos, cache, logs, or unrelated files in the cover directory.
