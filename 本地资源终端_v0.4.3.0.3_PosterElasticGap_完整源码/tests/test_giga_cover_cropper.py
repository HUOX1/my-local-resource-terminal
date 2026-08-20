from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from app.services.giga_cover_cropper import GigaCoverCropper


def make_giga_cover(path: Path) -> None:
    image = Image.new("RGB", (1000, 600), (180, 170, 160))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 479, 599), fill=(120, 90, 80))
    draw.rectangle((480, 0, 519, 599), fill=(5, 5, 5))
    # Simulate bright spine text without destroying the dark-band signal.
    draw.rectangle((495, 80, 503, 520), fill=(220, 220, 220))
    draw.rectangle((520, 0, 999, 599), fill=(220, 160, 170))
    image.save(path, quality=95)


def test_inspect_detects_center_spine_and_right_front(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "TBW-35.jpg"
    output = tmp_path / "covers"
    source.parent.mkdir()
    make_giga_cover(source)

    result = GigaCoverCropper().inspect_file(source, output, margin_px=3)

    assert result.status == "ready"
    assert result.spine_left is not None and 470 <= result.spine_left <= 490
    assert result.spine_right is not None and 510 <= result.spine_right <= 530
    assert result.crop_box is not None
    assert result.crop_box[0] == result.spine_right + 3
    assert result.crop_box[2:] == (1000, 600)


def test_process_writes_only_right_front_and_preserves_source(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "TBW-35.jpg"
    output = tmp_path / "covers"
    source.parent.mkdir()
    make_giga_cover(source)
    original_bytes = source.read_bytes()
    cropper = GigaCoverCropper()
    candidate = cropper.inspect_file(source, output, margin_px=3)

    processed = cropper.process(candidate)

    assert processed.status == "processed"
    assert source.read_bytes() == original_bytes
    assert processed.output_path.exists()
    with Image.open(processed.output_path) as image:
        assert image.height == 600
        assert 465 <= image.width <= 485
        # The extracted cover should be dominated by the pink front color.
        pixel = image.convert("RGB").getpixel((image.width // 2, image.height // 2))
        assert pixel[0] > 190 and pixel[1] > 120


def test_vertical_single_cover_is_skipped(tmp_path: Path) -> None:
    source = tmp_path / "single.jpg"
    Image.new("RGB", (400, 600), (100, 120, 140)).save(source)

    result = GigaCoverCropper().inspect_file(source, tmp_path / "out")

    assert result.status == "single"
    assert result.crop_box is None


def test_wide_cover_without_reliable_spine_requires_review(tmp_path: Path) -> None:
    source = tmp_path / "wide.jpg"
    Image.new("RGB", (1000, 600), (180, 180, 180)).save(source)

    result = GigaCoverCropper().inspect_file(source, tmp_path / "out")

    assert result.status == "review"
    assert result.crop_box is None


def test_existing_cover_is_skipped_by_default_even_with_different_extension(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "TBW-35.jpg"
    output = tmp_path / "covers"
    source.parent.mkdir()
    output.mkdir()
    make_giga_cover(source)
    Image.new("RGB", (300, 450), (1, 2, 3)).save(output / "TBW-35.png")

    result = GigaCoverCropper().inspect_file(source, output, overwrite=False)

    assert result.status == "exists"
    assert result.output_path == output / "TBW-35.png"


def test_scan_directory_only_returns_supported_images(tmp_path: Path) -> None:
    source_dir = tmp_path / "raw"
    source_dir.mkdir()
    make_giga_cover(source_dir / "A.jpg")
    make_giga_cover(source_dir / "B.png")
    (source_dir / "notes.txt").write_text("x")

    results = GigaCoverCropper().scan_directory(source_dir, tmp_path / "out")

    assert [item.source_path.name for item in results] == ["A.jpg", "B.png"]


def test_source_and_output_directory_cannot_be_the_same(tmp_path: Path) -> None:
    source = tmp_path / "TBW-35.jpg"
    make_giga_cover(source)

    result = GigaCoverCropper().inspect_file(source, tmp_path, overwrite=True)

    assert result.status == "failed"
    assert "不能相同" in result.message


def test_overwrite_removes_stale_same_stem_cover_extension(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "TBW-35.jpg"
    output = tmp_path / "covers"
    source.parent.mkdir()
    output.mkdir()
    make_giga_cover(source)
    stale = output / "TBW-35.png"
    Image.new("RGB", (300, 450), (1, 2, 3)).save(stale)
    cropper = GigaCoverCropper()

    candidate = cropper.inspect_file(source, output, overwrite=True)
    result = cropper.process(candidate, overwrite=True)

    assert result.status == "processed"
    assert (output / "TBW-35.jpg").exists()
    assert not stale.exists()


def make_colored_spine_cover(path: Path, spine_color: tuple[int, int, int], *, patterned: bool = False) -> None:
    image = Image.new("RGB", (1000, 600), (130, 95, 75))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 474, 599), fill=(125, 85, 70))
    draw.rectangle((475, 0, 524, 599), fill=spine_color)
    if patterned:
        for y in range(20, 580, 60):
            draw.rectangle((482, y, 517, min(599, y + 24)), fill=(240, 210, 60))
    draw.rectangle((525, 0, 999, 599), fill=(218, 155, 170))
    # Strong internal artwork edge that must not be mistaken for the spine boundary.
    draw.rectangle((635, 0, 650, 599), fill=(20, 25, 30))
    image.save(path, quality=95)


def test_detects_green_spine_without_dark_color_assumption(tmp_path: Path) -> None:
    source = tmp_path / "green.jpg"
    make_colored_spine_cover(source, (25, 190, 65))

    result = GigaCoverCropper().inspect_file(source, tmp_path / "out", margin_px=0)

    assert result.status == "ready"
    assert result.spine_left is not None and 465 <= result.spine_left <= 485
    assert result.spine_right is not None and 515 <= result.spine_right <= 535
    assert result.crop_box is not None and 515 <= result.crop_box[0] <= 535


def test_detects_red_spine_without_dark_color_assumption(tmp_path: Path) -> None:
    source = tmp_path / "red.jpg"
    make_colored_spine_cover(source, (220, 40, 45))

    result = GigaCoverCropper().inspect_file(source, tmp_path / "out", margin_px=0)

    assert result.status == "ready"
    assert result.spine_right is not None and 515 <= result.spine_right <= 535


def test_detects_patterned_spine_by_structure(tmp_path: Path) -> None:
    source = tmp_path / "patterned.jpg"
    make_colored_spine_cover(source, (30, 150, 210), patterned=True)

    result = GigaCoverCropper().inspect_file(source, tmp_path / "out", margin_px=0)

    assert result.status == "ready"
    assert result.spine_right is not None and 515 <= result.spine_right <= 535


def test_existing_fronts_provide_reference_aspect_ratio(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "sample.jpg"
    output = tmp_path / "covers"
    source.parent.mkdir()
    output.mkdir()
    make_colored_spine_cover(source, (25, 190, 65))
    # Existing single Front samples: 420 / 600 == 0.70.
    Image.new("RGB", (420, 600), (1, 2, 3)).save(output / "A.jpg")
    Image.new("RGB", (700, 1000), (4, 5, 6)).save(output / "B.jpg")

    cropper = GigaCoverCropper()
    ratio = cropper.reference_front_ratio(output)

    assert 0.695 <= ratio <= 0.705


def test_manual_candidate_uses_selected_front_start_and_margin(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "TBW-35.jpg"
    output = tmp_path / "covers"
    source.parent.mkdir()
    make_giga_cover(source)

    candidate = GigaCoverCropper().manual_candidate(source, output, crop_x=520, margin_px=3)

    assert candidate.status == "ready"
    assert candidate.crop_box == (523, 0, 1000, 600)
    assert candidate.width == 1000
    assert candidate.height == 600


def test_manual_crop_preserves_source_and_writes_right_side(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "TBW-35.jpg"
    output = tmp_path / "covers"
    source.parent.mkdir()
    make_giga_cover(source)
    original = source.read_bytes()
    cropper = GigaCoverCropper()
    candidate = cropper.manual_candidate(source, output, crop_x=520, margin_px=0)

    result = cropper.process(candidate)

    assert result.status == "processed"
    assert source.read_bytes() == original
    with Image.open(output / "TBW-35.jpg") as image:
        assert image.size == (480, 600)


def test_manual_candidate_does_not_overwrite_existing_cover_without_permission(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "TBW-35.jpg"
    output = tmp_path / "covers"
    source.parent.mkdir()
    output.mkdir()
    make_giga_cover(source)
    Image.new("RGB", (300, 450), (1, 2, 3)).save(output / "TBW-35.png")

    candidate = GigaCoverCropper().manual_candidate(source, output, crop_x=520, overwrite=False)

    assert candidate.status == "exists"
    assert candidate.output_path == output / "TBW-35.png"


def test_manual_candidate_rejects_crop_start_outside_image(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "TBW-35.jpg"
    source.parent.mkdir()
    make_giga_cover(source)

    candidate = GigaCoverCropper().manual_candidate(source, tmp_path / "covers", crop_x=1000)

    assert candidate.status == "failed"
    assert candidate.crop_box is None
