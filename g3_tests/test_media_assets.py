
from pathlib import Path
import subprocess

from PIL import Image

from g3_core.database import Database
from g3_core.models import CreateGame
from g3_core.repository import LibraryRepository
from g3_core.services.media_assets import MediaAssetService


def _repo(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()
    return LibraryRepository(db)


def test_manual_preview_video_overrides_auto_discovery(tmp_path):
    repo = _repo(tmp_path)
    exe = tmp_path / "demo.exe"
    exe.write_bytes(b"")
    auto_video = tmp_path / "preview.ogv"
    manual_video = tmp_path / "chosen.ogv"
    auto_video.write_bytes(b"a")
    manual_video.write_bytes(b"m")
    game = repo.create_game(CreateGame(title="Demo", executable_path=exe))
    repo.add_media_asset(game.id, "preview_video", manual_video, source="manual")

    service = MediaAssetService(repo, tmp_path / "cache", ffmpeg_path="ffmpeg")
    manifest = service.resolve_preview(game.id)
    assert manifest.video_ogv == manual_video.resolve()


def test_gif_is_expanded_to_cached_png_frames_with_durations(tmp_path):
    repo = _repo(tmp_path)
    exe = tmp_path / "demo.exe"
    exe.write_bytes(b"")
    gif_path = tmp_path / "preview.gif"
    images = [Image.new("RGB", (4, 4), c) for c in ("red", "blue")]
    images[0].save(gif_path, save_all=True, append_images=images[1:], duration=[80, 120], loop=0)
    game = repo.create_game(CreateGame(title="Demo", executable_path=exe))
    repo.add_media_asset(game.id, "preview_gif", gif_path, source="manual")

    service = MediaAssetService(repo, tmp_path / "cache", ffmpeg_path="ffmpeg")
    manifest = service.resolve_preview(game.id)
    assert len(manifest.gif_frames) == 2
    assert all(path.suffix == ".png" and path.exists() for path in manifest.gif_frames)
    assert manifest.gif_durations_ms == [80, 120]


def test_mp4_requests_ogv_transcode_command(tmp_path):
    repo = _repo(tmp_path)
    exe = tmp_path / "demo.exe"
    exe.write_bytes(b"")
    video = tmp_path / "preview.mp4"
    video.write_bytes(b"fake")
    game = repo.create_game(CreateGame(title="Demo", executable_path=exe))
    repo.add_media_asset(game.id, "preview_video", video, source="manual")

    calls = []
    def runner(command, **kwargs):
        calls.append(command)
        Path(command[-1]).write_bytes(b"ogv")
        return subprocess.CompletedProcess(command, 0, "", "")

    service = MediaAssetService(
        repo, tmp_path / "cache", ffmpeg_path="ffmpeg", runner=runner
    )
    manifest = service.resolve_preview(game.id)
    assert manifest.video_ogv is not None
    assert manifest.video_ogv.suffix == ".ogv"
    assert calls
    command = calls[0]
    assert "libtheora" in command
    assert "libvorbis" in command
    assert "fps=30" in " ".join(command)
