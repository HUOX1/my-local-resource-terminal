from __future__ import annotations

import json
from dataclasses import dataclass, asdict, replace
from statistics import median
from pathlib import Path
from typing import Callable, Iterable, Literal

from PIL import Image, ImageOps

SUPPORTED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
CropStatus = Literal["ready", "single", "review", "unreadable", "exists", "processed", "failed"]
ProgressCallback = Callable[[int, int], None]


@dataclass(slots=True, frozen=True)
class GigaCoverCandidate:
    source_path: Path
    output_path: Path
    status: CropStatus
    message: str = ""
    width: int | None = None
    height: int | None = None
    spine_left: int | None = None
    spine_right: int | None = None
    crop_box: tuple[int, int, int, int] | None = None


@dataclass(slots=True, frozen=True)
class _StructureAnalysis:
    status: Literal["ready", "single", "review", "unreadable"]
    message: str = ""
    width: int | None = None
    height: int | None = None
    spine_left: int | None = None
    spine_right: int | None = None


class GigaCoverCropper:
    """Extract the right-side Front cover from full DVD wrap images.

    Detection is based on structural vertical boundaries around the physical
    center of the wrap. Spine color is deliberately ignored.
    """

    CACHE_FILENAME = '.giga_cover_scan_cache.json'
    CACHE_VERSION = 1

    def __init__(
        self,
        *,
        wide_ratio_threshold: float = 1.30,
        center_start: float = 0.36,
        center_end: float = 0.64,
        default_front_ratio: float = 0.70,
    ) -> None:
        self.wide_ratio_threshold = wide_ratio_threshold
        self.center_start = center_start
        self.center_end = center_end
        self.default_front_ratio = default_front_ratio

    def reference_front_ratio(self, output_dir: Path) -> float:
        """Return the median aspect ratio of existing portrait Front covers."""
        ratios: list[float] = []
        output_dir = Path(output_dir)
        if output_dir.is_dir():
            for path in sorted(output_dir.iterdir(), key=lambda p: p.name.casefold())[:300]:
                if not path.is_file() or path.suffix.casefold() not in SUPPORTED_IMAGE_EXTENSIONS:
                    continue
                try:
                    with Image.open(path) as opened:
                        width, height = ImageOps.exif_transpose(opened).size
                except (OSError, ValueError):
                    continue
                if height <= 0 or width >= height:
                    continue
                ratio = width / height
                if 0.45 <= ratio <= 0.95:
                    ratios.append(ratio)
        return float(median(ratios)) if ratios else self.default_front_ratio

    def iter_source_files(self, source_dir: Path) -> list[Path]:
        source_dir = Path(source_dir)
        if not source_dir.is_dir():
            return []
        return [
            path
            for path in sorted(source_dir.iterdir(), key=lambda p: p.name.casefold())
            if path.is_file() and path.suffix.casefold() in SUPPORTED_IMAGE_EXTENSIONS
        ]

    def scan_directory(
        self,
        source_dir: Path,
        output_dir: Path,
        *,
        margin_px: int = 0,
        overwrite: bool = False,
        source_paths: Iterable[Path] | None = None,
        progress_callback: ProgressCallback | None = None,
        use_cache: bool = True,
    ) -> list[GigaCoverCandidate]:
        source_dir = Path(source_dir)
        output_dir = Path(output_dir)
        paths = list(source_paths) if source_paths is not None else self.iter_source_files(source_dir)
        results: list[GigaCoverCandidate] = []
        if not paths:
            return results
        reference_ratio = self.reference_front_ratio(output_dir)
        cache = self._load_scan_cache(output_dir) if use_cache else {}
        dirty = False
        total = len(paths)
        for index, path in enumerate(paths, start=1):
            results.append(
                self.inspect_file(
                    path,
                    output_dir,
                    margin_px=margin_px,
                    overwrite=overwrite,
                    reference_ratio=reference_ratio,
                    cache=cache,
                    cache_dirty=lambda: self._mark_dirty(),
                )
            )
            if use_cache and getattr(self, '_cache_dirty_flag', False):
                dirty = True
                self._cache_dirty_flag = False
            if progress_callback is not None:
                progress_callback(index, total)
        if use_cache and dirty:
            self._save_scan_cache(output_dir, cache)
        return results

    def inspect_file(
        self,
        source_path: Path,
        output_dir: Path,
        *,
        margin_px: int = 0,
        overwrite: bool = False,
        reference_ratio: float | None = None,
        cache: dict[str, dict] | None = None,
        cache_dirty: Callable[[], None] | None = None,
    ) -> GigaCoverCandidate:
        source_path = Path(source_path)
        output_dir = Path(output_dir)
        existing = self._existing_output(output_dir, source_path.stem)
        default_output = output_dir / source_path.name
        try:
            same_location = default_output.resolve() == source_path.resolve()
        except OSError:
            same_location = default_output.absolute() == source_path.absolute()
        if same_location:
            return GigaCoverCandidate(
                source_path=source_path,
                output_path=default_output,
                status="failed",
                message="原始封面目录与输出目录不能相同，以免覆盖原图",
            )
        if existing is not None and not overwrite:
            return GigaCoverCandidate(
                source_path=source_path,
                output_path=existing,
                status="exists",
                message="正式封面已存在，默认跳过",
            )

        expected_ratio = reference_ratio if reference_ratio is not None else self.reference_front_ratio(output_dir)
        analysis = self._load_or_analyze_structure(source_path, expected_ratio, cache)
        if cache is not None and cache_dirty is not None and self._last_cache_write:
            cache_dirty()
            self._last_cache_write = False

        if analysis.status == "unreadable":
            return GigaCoverCandidate(
                source_path=source_path,
                output_path=default_output,
                status="unreadable",
                message=analysis.message,
            )

        if analysis.status == "single":
            return GigaCoverCandidate(
                source_path=source_path,
                output_path=default_output,
                status="single",
                message=analysis.message,
                width=analysis.width,
                height=analysis.height,
            )

        if analysis.status == "review":
            return GigaCoverCandidate(
                source_path=source_path,
                output_path=default_output,
                status="review",
                message=analysis.message,
                width=analysis.width,
                height=analysis.height,
                spine_left=analysis.spine_left,
                spine_right=analysis.spine_right,
            )

        width = analysis.width or 0
        height = analysis.height or 0
        spine_left = analysis.spine_left
        spine_right = analysis.spine_right
        if spine_right is None or spine_left is None:
            return GigaCoverCandidate(
                source_path=source_path,
                output_path=default_output,
                status="review",
                message="缺少 Spine 分界信息，请人工复核",
                width=analysis.width,
                height=analysis.height,
            )
        crop_left = min(width - 1, spine_right + max(0, int(margin_px)))
        front_width = width - crop_left
        front_ratio = front_width / max(1, height)
        if front_width <= 0 or not 0.45 <= front_ratio <= 0.95:
            return GigaCoverCandidate(
                source_path=source_path,
                output_path=default_output,
                status="review",
                message="检测到结构分界，但右侧 Front 比例异常，请人工复核",
                width=width,
                height=height,
                spine_left=spine_left,
                spine_right=spine_right,
            )

        return GigaCoverCandidate(
            source_path=source_path,
            output_path=default_output,
            status="ready",
            message="已识别 Spine / Front 分界，可自动提取右侧 Front",
            width=width,
            height=height,
            spine_left=spine_left,
            spine_right=spine_right,
            crop_box=(crop_left, 0, width, height),
        )

    def manual_candidate(
        self,
        source_path: Path,
        output_dir: Path,
        *,
        crop_x: int,
        margin_px: int = 0,
        overwrite: bool = False,
    ) -> GigaCoverCandidate:
        """Create a crop candidate from a user-selected Front start position."""
        source_path = Path(source_path)
        output_dir = Path(output_dir)
        existing = self._existing_output(output_dir, source_path.stem)
        default_output = output_dir / source_path.name
        try:
            same_location = default_output.resolve() == source_path.resolve()
        except OSError:
            same_location = default_output.absolute() == source_path.absolute()
        if same_location:
            return GigaCoverCandidate(
                source_path=source_path,
                output_path=default_output,
                status="failed",
                message="原始封面目录与输出目录不能相同，以免覆盖原图",
            )
        if existing is not None and not overwrite:
            return GigaCoverCandidate(
                source_path=source_path,
                output_path=existing,
                status="exists",
                message="正式封面已存在，需要确认覆盖",
            )

        try:
            with Image.open(source_path) as opened:
                width, height = ImageOps.exif_transpose(opened).size
        except (OSError, ValueError) as exc:
            return GigaCoverCandidate(
                source_path=source_path,
                output_path=default_output,
                status="unreadable",
                message=f"无法读取图片：{exc}",
            )

        left = int(crop_x) + max(0, int(margin_px))
        if height <= 0 or left < 0 or left >= width:
            return GigaCoverCandidate(
                source_path=source_path,
                output_path=default_output,
                status="failed",
                message="手动裁剪起点超出图片范围",
                width=width,
                height=height,
            )

        return GigaCoverCandidate(
            source_path=source_path,
            output_path=default_output,
            status="ready",
            message="已设置手动 Front 起点",
            width=width,
            height=height,
            crop_box=(left, 0, width, height),
        )

    def _load_or_analyze_structure(
        self,
        source_path: Path,
        reference_ratio: float,
        cache: dict[str, dict] | None,
    ) -> _StructureAnalysis:
        self._last_cache_write = False
        signature = self._path_signature(source_path)
        key = self._cache_key(source_path)
        if cache is not None:
            entry = cache.get(key)
            if entry and entry.get('signature') == signature and abs(float(entry.get('reference_ratio', 0.0)) - reference_ratio) < 0.0005:
                return self._structure_from_payload(entry['analysis'])

        try:
            with Image.open(source_path) as opened:
                image = ImageOps.exif_transpose(opened).convert('RGB')
        except (OSError, ValueError) as exc:
            analysis = _StructureAnalysis(status='unreadable', message=f'无法读取图片：{exc}')
        else:
            width, height = image.size
            if height <= 0 or width / height < self.wide_ratio_threshold:
                analysis = _StructureAnalysis(
                    status='single',
                    message='看起来已经是单张 Front，跳过',
                    width=width,
                    height=height,
                )
            else:
                spine = self._detect_spine(image, reference_ratio)
                if spine is None:
                    analysis = _StructureAnalysis(
                        status='review',
                        message='未检测到可靠的 Spine / Front 结构分界，请人工复核',
                        width=width,
                        height=height,
                    )
                else:
                    analysis = _StructureAnalysis(
                        status='ready',
                        message='已识别 Spine / Front 分界，可自动提取右侧 Front',
                        width=width,
                        height=height,
                        spine_left=spine[0],
                        spine_right=spine[1],
                    )
        if cache is not None:
            cache[key] = {
                'signature': signature,
                'reference_ratio': round(reference_ratio, 6),
                'analysis': self._structure_to_payload(analysis),
            }
            self._last_cache_write = True
        return analysis

    def _cache_key(self, source_path: Path) -> str:
        try:
            return str(source_path.resolve())
        except OSError:
            return str(source_path.absolute())

    def _path_signature(self, source_path: Path) -> dict[str, int | str]:
        stat = source_path.stat()
        return {
            'mtime_ns': int(stat.st_mtime_ns),
            'size': int(stat.st_size),
            'suffix': source_path.suffix.casefold(),
        }

    def _scan_cache_path(self, output_dir: Path) -> Path:
        return Path(output_dir) / self.CACHE_FILENAME

    def _load_scan_cache(self, output_dir: Path) -> dict[str, dict]:
        path = self._scan_cache_path(output_dir)
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict) or payload.get('version') != self.CACHE_VERSION:
            return {}
        items = payload.get('items')
        return items if isinstance(items, dict) else {}

    def _save_scan_cache(self, output_dir: Path, cache: dict[str, dict]) -> None:
        path = self._scan_cache_path(output_dir)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({'version': self.CACHE_VERSION, 'items': cache}, ensure_ascii=False, separators=(',', ':')),
                encoding='utf-8',
            )
        except OSError:
            return

    def _structure_to_payload(self, analysis: _StructureAnalysis) -> dict:
        return {
            'status': analysis.status,
            'message': analysis.message,
            'width': analysis.width,
            'height': analysis.height,
            'spine_left': analysis.spine_left,
            'spine_right': analysis.spine_right,
        }

    def _structure_from_payload(self, payload: dict) -> _StructureAnalysis:
        return _StructureAnalysis(
            status=payload.get('status', 'review'),
            message=payload.get('message', ''),
            width=payload.get('width'),
            height=payload.get('height'),
            spine_left=payload.get('spine_left'),
            spine_right=payload.get('spine_right'),
        )

    def _mark_dirty(self) -> None:
        self._cache_dirty_flag = True

    def _detect_spine(self, image: Image.Image, reference_ratio: float) -> tuple[int, int] | None:
        width, height = image.size
        scores = self._vertical_edge_scores(image)
        x_start = max(2, int(width * self.center_start))
        x_end = min(width - 2, int(width * self.center_end))
        center = width / 2.0

        region_scores = scores[x_start:x_end]
        if not region_scores:
            return None
        sorted_scores = sorted(region_scores)
        typical = sorted_scores[len(sorted_scores) // 2]
        strong_threshold = max(5.0, typical * 2.2)

        peaks = self._local_peaks(scores, x_start, x_end, strong_threshold)
        if len(peaks) < 2:
            return self._ratio_guided_boundary(scores, width, height, reference_ratio, strong_threshold)

        max_spine_width = max(8, int(width * 0.12))
        min_spine_width = max(6, int(width * 0.015))
        best: tuple[float, int, int] | None = None
        left_peaks = [x for x in peaks if x < center]
        right_peaks = [x for x in peaks if x > center]
        for right in right_peaks:
            mirror = width - right
            plausible_left = [
                left
                for left in left_peaks
                if min_spine_width <= right - left <= max_spine_width
                and abs(left - mirror) / width <= 0.10
            ]
            if not plausible_left:
                continue
            left = min(plausible_left, key=lambda x: (abs(x - mirror), -scores[x]))
            back_width = left
            front_width = width - right
            symmetry_error = abs(back_width - front_width) / width
            front_ratio = front_width / max(1, height)
            ratio_error = abs(front_ratio - reference_ratio)
            center_error = abs(((left + right) / 2.0) - center) / width
            score = scores[right] + scores[left] * 0.35 - symmetry_error * 300.0 - center_error * 80.0 - ratio_error * 20.0
            candidate = (score, left, right)
            if best is None or candidate[0] > best[0]:
                best = candidate

        if best is not None:
            return best[1], best[2]
        return self._ratio_guided_boundary(scores, width, height, reference_ratio, strong_threshold)

    def _ratio_guided_boundary(
        self,
        scores: list[float],
        width: int,
        height: int,
        reference_ratio: float,
        threshold: float,
    ) -> tuple[int, int] | None:
        predicted_right = int(round(width - reference_ratio * height))
        radius = max(10, int(width * 0.06))
        lo = max(2, predicted_right - radius)
        hi = min(width - 2, predicted_right + radius)
        if lo >= hi:
            return None
        right = max(range(lo, hi + 1), key=lambda x: scores[x])
        if scores[right] < threshold * 0.45:
            return None
        predicted_spine_width = max(6, int(width * 0.03))
        left_lo = max(2, right - int(width * 0.12))
        left_hi = max(left_lo, right - max(4, int(width * 0.01)))
        left = max(range(left_lo, left_hi + 1), key=lambda x: scores[x])
        if right - left < max(4, predicted_spine_width // 2):
            left = max(2, right - predicted_spine_width)
        return left, right

    def _vertical_edge_scores(self, image: Image.Image) -> list[float]:
        gray = image.convert('L')
        width, height = gray.size
        if width <= 2 or height <= 0:
            return [0.0] * max(1, width)
        pixels = gray.load()
        y_step = max(1, height // 240)
        scores = [0.0] * width
        for x in range(1, width - 1):
            total = 0.0
            count = 0
            for y in range(0, height, y_step):
                left = pixels[x - 1, y]
                right = pixels[x + 1, y]
                total += abs(int(right) - int(left))
                count += 1
            scores[x] = total / max(1, count)
        return scores

    def _local_peaks(self, scores: list[float], start: int, end: int, threshold: float) -> list[int]:
        peaks: list[int] = []
        end = min(end, len(scores) - 1)
        for x in range(max(1, start), end):
            value = scores[x]
            if value < threshold:
                continue
            if value >= scores[x - 1] and value >= scores[x + 1]:
                peaks.append(x)
        return peaks

    def _existing_output(self, output_dir: Path, stem: str) -> Path | None:
        for suffix in SUPPORTED_IMAGE_EXTENSIONS:
            candidate = output_dir / f'{stem}{suffix}'
            if candidate.exists():
                return candidate
        return None

    def process_single(self, candidate: GigaCoverCandidate, *, overwrite: bool = False) -> GigaCoverCandidate:
        """Copy an existing Front cover without changing the original file."""
        output = Path(candidate.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists() and not overwrite:
            return replace(candidate, status="exists", message="正式封面已存在，跳过复制")
        try:
            import shutil
            shutil.copy2(candidate.source_path, output)
        except OSError as exc:
            return replace(candidate, status="failed", message=f"复制失败：{exc}")
        return replace(candidate, status="processed", message="已复制单张 Front 封面")

    def process(self, candidate: GigaCoverCandidate, *, overwrite: bool = False) -> GigaCoverCandidate:
        if candidate.status != 'ready' or candidate.crop_box is None:
            return candidate
        output = Path(candidate.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists() and not overwrite:
            return replace(candidate, status='exists', message='正式封面已存在，跳过')
        try:
            with Image.open(candidate.source_path) as opened:
                image = ImageOps.exif_transpose(opened).convert('RGB')
                cropped = image.crop(candidate.crop_box)
                cropped.save(output)
        except (OSError, ValueError) as exc:
            return replace(candidate, status='failed', message=f'保存失败：{exc}')
        return replace(candidate, status='processed', message='已提取 Front 封面')
