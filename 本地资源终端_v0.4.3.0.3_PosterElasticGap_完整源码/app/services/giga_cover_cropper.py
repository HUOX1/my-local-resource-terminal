from __future__ import annotations

from dataclasses import dataclass, replace
from statistics import median
from pathlib import Path
from typing import Literal

from PIL import Image, ImageOps

SUPPORTED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
CropStatus = Literal["ready", "single", "review", "unreadable", "exists", "processed", "failed"]


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


class GigaCoverCropper:
    """Extract the right-side Front cover from full DVD wrap images.

    Detection is based on structural vertical boundaries around the physical
    center of the wrap. Spine color is deliberately ignored.
    """

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

    def scan_directory(
        self,
        source_dir: Path,
        output_dir: Path,
        *,
        margin_px: int = 0,
        overwrite: bool = False,
    ) -> list[GigaCoverCandidate]:
        source_dir = Path(source_dir)
        output_dir = Path(output_dir)
        results: list[GigaCoverCandidate] = []
        if not source_dir.is_dir():
            return results
        reference_ratio = self.reference_front_ratio(output_dir)
        for path in sorted(source_dir.iterdir(), key=lambda p: p.name.casefold()):
            if path.is_file() and path.suffix.casefold() in SUPPORTED_IMAGE_EXTENSIONS:
                results.append(
                    self.inspect_file(
                        path,
                        output_dir,
                        margin_px=margin_px,
                        overwrite=overwrite,
                        reference_ratio=reference_ratio,
                    )
                )
        return results

    def inspect_file(
        self,
        source_path: Path,
        output_dir: Path,
        *,
        margin_px: int = 0,
        overwrite: bool = False,
        reference_ratio: float | None = None,
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

        try:
            with Image.open(source_path) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
        except (OSError, ValueError) as exc:
            return GigaCoverCandidate(
                source_path=source_path,
                output_path=default_output,
                status="unreadable",
                message=f"无法读取图片：{exc}",
            )

        width, height = image.size
        if height <= 0 or width / height < self.wide_ratio_threshold:
            return GigaCoverCandidate(
                source_path=source_path,
                output_path=default_output,
                status="single",
                message="看起来已经是单张 Front，跳过",
                width=width,
                height=height,
            )

        expected_ratio = reference_ratio if reference_ratio is not None else self.reference_front_ratio(output_dir)
        spine = self._detect_spine(image, expected_ratio)
        if spine is None:
            return GigaCoverCandidate(
                source_path=source_path,
                output_path=default_output,
                status="review",
                message="未检测到可靠的 Spine / Front 结构分界，请人工复核",
                width=width,
                height=height,
            )

        spine_left, spine_right = spine
        crop_left = min(width - 1, spine_right + max(0, int(margin_px)))
        front_width = width - crop_left
        front_ratio = front_width / height
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
            # The physical Back and Front panels are almost the same width.
            # Pick the left boundary closest to the mirror of the right edge;
            # this prevents lettering/graphics inside the Spine from becoming
            # a false left boundary.
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
        if scores[right] < threshold:
            return None
        mirror = width - right
        left_lo = max(2, mirror - radius)
        left_hi = min(width - 2, mirror + radius)
        left = max(range(left_lo, left_hi + 1), key=lambda x: scores[x])
        if scores[left] < threshold * 0.65 or left >= right:
            return None
        if abs(left - (width - right)) / width > 0.10:
            return None
        return left, right

    @staticmethod
    def _vertical_edge_scores(image: Image.Image) -> list[float]:
        width, height = image.size
        sample_height = min(height, 240)
        sampled = image.resize((width, sample_height)).convert("RGB")
        pixels = sampled.load()
        y_start = max(0, int(sample_height * 0.04))
        y_end = min(sample_height, int(sample_height * 0.96))
        count = max(1, y_end - y_start)
        scores = [0.0] * width
        for x in range(1, width):
            total = 0.0
            for y in range(y_start, y_end):
                a = pixels[x - 1, y]
                b = pixels[x, y]
                total += (abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])) / 3.0
            scores[x] = total / count
        # JPEG edges are often spread over a few columns. A small max filter
        # keeps the physical boundary location while making detection stable.
        raw = scores[:]
        for x in range(2, width - 2):
            scores[x] = max(raw[x - 2 : x + 3])
        return scores

    @staticmethod
    def _local_peaks(scores: list[float], start: int, end: int, threshold: float) -> list[int]:
        candidates: list[int] = []
        for x in range(max(start, 2), min(end, len(scores) - 2)):
            if scores[x] < threshold:
                continue
            if scores[x] >= scores[x - 1] and scores[x] >= scores[x + 1]:
                candidates.append(x)
        # Collapse adjacent columns from one physical boundary to one peak.
        peaks: list[int] = []
        for x in candidates:
            if peaks and x - peaks[-1] <= 5:
                if scores[x] > scores[peaks[-1]]:
                    peaks[-1] = x
            else:
                peaks.append(x)
        return peaks

    def process(self, candidate: GigaCoverCandidate, *, overwrite: bool = False) -> GigaCoverCandidate:
        if candidate.status != "ready" or candidate.crop_box is None:
            return candidate
        output = candidate.output_path
        if output.exists() and not overwrite:
            return replace(candidate, status="exists", message="正式封面已存在，跳过")
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            with Image.open(candidate.source_path) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
                front = image.crop(candidate.crop_box)
                temporary = output.with_name(f".{output.stem}.tmp{output.suffix}")
                self._save_image(front, temporary, output.suffix.casefold())
                temporary.replace(output)
                if overwrite:
                    for extension in SUPPORTED_IMAGE_EXTENSIONS:
                        stale = output.parent / f"{output.stem}{extension}"
                        if stale != output:
                            stale.unlink(missing_ok=True)
        except (OSError, ValueError) as exc:
            return replace(candidate, status="failed", message=f"写出失败：{exc}")
        return replace(candidate, status="processed", message="已提取右侧 Front")

    def process_many(
        self,
        candidates: list[GigaCoverCandidate],
        *,
        overwrite: bool = False,
    ) -> list[GigaCoverCandidate]:
        return [self.process(item, overwrite=overwrite) for item in candidates]

    @staticmethod
    def _existing_output(output_dir: Path, stem: str) -> Path | None:
        output_dir = Path(output_dir)
        for extension in SUPPORTED_IMAGE_EXTENSIONS:
            candidate = output_dir / f"{stem}{extension}"
            if candidate.is_file():
                return candidate
        return None

    @staticmethod
    def _save_image(image: Image.Image, path: Path, extension: str) -> None:
        if extension in (".jpg", ".jpeg"):
            image.save(path, format="JPEG", quality=95, optimize=True)
        elif extension == ".png":
            image.save(path, format="PNG", optimize=True)
        elif extension == ".webp":
            image.save(path, format="WEBP", quality=95, method=6)
        else:
            raise ValueError(f"unsupported image format: {extension}")
