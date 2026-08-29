from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.services.sound_pack_store import SOUND_EVENTS, SoundPackStore


class AudioImportError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ImportedSound:
    original_path: Path
    runtime_path: Path


class AudioImportService:
    def __init__(self, store: SoundPackStore, ffmpeg_path: str = "ffmpeg") -> None:
        self.store = store
        self.ffmpeg_path = str(ffmpeg_path or "ffmpeg")

    def import_for_event(self, pack_id: str, event: str, source: Path) -> ImportedSound:
        if event not in SOUND_EVENTS:
            raise AudioImportError(f"未知音效事件：{event}")
        source = Path(source)
        if not source.is_file():
            raise AudioImportError(f"音效文件不存在：{source}")
        pack = self.store.pack_info(pack_id)
        suffix = source.suffix.casefold()
        original_name = source.name
        runtime_name = f"{event}.wav"
        original_target = pack.path / "originals" / original_name
        runtime_target = pack.path / "audio" / runtime_name

        staged_original: Path | None = None
        staged_runtime: Path | None = None
        try:
            with tempfile.TemporaryDirectory(prefix="sound-import-", dir=pack.path) as temp_dir_text:
                temp_dir = Path(temp_dir_text)
                staged_original = temp_dir / "original" / original_name
                staged_runtime = temp_dir / runtime_name
                staged_original.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, staged_original)

                if suffix == ".wav":
                    shutil.copy2(staged_original, staged_runtime)
                else:
                    self._normalize_with_ffmpeg(staged_original, staged_runtime)

                self._validate_runtime(staged_runtime)

                original_target.parent.mkdir(parents=True, exist_ok=True)
                runtime_target.parent.mkdir(parents=True, exist_ok=True)
                previous_original = temp_dir / "previous-original"
                previous_runtime = temp_dir / "previous-runtime"
                had_original = original_target.is_file()
                had_runtime = runtime_target.is_file()
                if had_original:
                    shutil.copy2(original_target, previous_original)
                if had_runtime:
                    shutil.copy2(runtime_target, previous_runtime)

                published_original = original_target.with_name(original_target.name + ".new")
                published_runtime = runtime_target.with_name(runtime_target.name + ".new")
                shutil.copy2(staged_original, published_original)
                shutil.copy2(staged_runtime, published_runtime)
                published_original.replace(original_target)
                published_runtime.replace(runtime_target)
                try:
                    self.store.set_mapping(pack_id, event, runtime_name, original_name)
                except Exception:
                    if had_original:
                        shutil.copy2(previous_original, original_target)
                    else:
                        original_target.unlink(missing_ok=True)
                    if had_runtime:
                        shutil.copy2(previous_runtime, runtime_target)
                    else:
                        runtime_target.unlink(missing_ok=True)
                    raise
        except AudioImportError:
            raise
        except (OSError, subprocess.SubprocessError) as exc:
            raise AudioImportError(str(exc)) from exc

        return ImportedSound(original_target, runtime_target)

    def _normalize_with_ffmpeg(self, source: Path, output: Path) -> None:
        try:
            result = subprocess.run(
                [
                    self.ffmpeg_path,
                    "-y",
                    "-i",
                    str(source),
                    "-vn",
                    "-ac",
                    "2",
                    "-ar",
                    "44100",
                    "-c:a",
                    "pcm_s16le",
                    str(output),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
            raise AudioImportError(f"FFmpeg 不可用：{self.ffmpeg_path}") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "FFmpeg 转码失败").strip().splitlines()
            message = detail[-1] if detail else "FFmpeg 转码失败"
            raise AudioImportError(message)

    @staticmethod
    def _validate_runtime(path: Path) -> None:
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise AudioImportError("没有生成可播放的 WAV 文件") from exc
        if size <= 4:
            raise AudioImportError("生成的 WAV 文件为空或无效")
