# 本地影片管理器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个 Windows 优先、完全本地运行的 PySide6 影片档案管理器，支持多影片库扫描、集中式封面、永久元数据与观看痕迹、在线/离线影片状态、封面墙/列表双视图及外部播放器调用。

**Architecture:** UI 只通过服务层访问数据；SQLite 负责快速索引与查询，集中式 JSON 负责永久档案与可恢复观看痕迹。扫描器负责文件发现与在线/离线关联，封面、ffprobe、播放和设置分别放在独立服务中；Qt 主线程只更新界面，扫描和缩略图工作放后台线程。

**Tech Stack:** Python 3.11+、PySide6 Widgets 6.x、标准库 `sqlite3` / `json` / `pathlib` / `subprocess`、FFmpeg/ffprobe、pytest、pytest-qt。

## Global Constraints

- Windows 为第一目标平台；不得启动 Web 服务或依赖浏览器。
- 第一版不包含网站刮削、GIGA 专用抓取、内置播放器、视频转码、远程访问、实时目录监听、图片集 UI 或批量元数据编辑。
- 视频文件可删除、移动或暂时离线；影片档案、封面、评分、收藏、备注与观看痕迹不得因扫描自动删除。
- 永久删除档案必须由用户显式执行并确认；默认不删除视频文件或集中封面。
- 集中式 JSON 以稳定 UUID 命名；数据库删除后必须能从 JSON 重建永久档案。
- 集中封面以持久化 `cover_key` 匹配，格式优先级固定为 `jpg > jpeg > png > webp`，Windows 下大小写不敏感。
- 默认主界面是封面墙；必须可切换列表视图。
- UI 不直接访问 SQLite；扫描器不直接操作 Qt 控件。
- 单个损坏视频、JSON、封面或 ffprobe 失败不得中断整个扫描。
- 逐次观看历史只记录“从管理器成功发起播放”的时间，不声称代表播放完成或播放进度。

---

## File Structure

```text
local_movie_manager/
├─ pyproject.toml
├─ README.md
├─ app/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ bootstrap.py
│  ├─ config/
│  │  ├─ __init__.py
│  │  ├─ settings.py
│  │  └─ data_dirs.py
│  ├─ models/
│  │  ├─ __init__.py
│  │  ├─ library.py
│  │  ├─ movie.py
│  │  └─ scan.py
│  ├─ db/
│  │  ├─ __init__.py
│  │  ├─ database.py
│  │  └─ schema.sql
│  ├─ repositories/
│  │  ├─ __init__.py
│  │  └─ movie_repository.py
│  ├─ services/
│  │  ├─ __init__.py
│  │  ├─ metadata_service.py
│  │  ├─ media_probe.py
│  │  ├─ cover_service.py
│  │  ├─ discovery_service.py
│  │  ├─ scanner.py
│  │  ├─ catalog_service.py
│  │  ├─ player_service.py
│  │  └─ viewing_service.py
│  ├─ ui/
│  │  ├─ __init__.py
│  │  ├─ main_window.py
│  │  ├─ movie_models.py
│  │  ├─ movie_delegate.py
│  │  ├─ movie_detail.py
│  │  ├─ settings_dialog.py
│  │  └─ scan_worker.py
│  └─ utils/
│     ├─ __init__.py
│     ├─ logging.py
│     └─ time.py
└─ tests/
   ├─ conftest.py
   ├─ test_settings.py
   ├─ test_metadata_service.py
   ├─ test_movie_repository.py
   ├─ test_discovery_service.py
   ├─ test_media_probe.py
   ├─ test_cover_service.py
   ├─ test_scanner.py
   ├─ test_viewing_service.py
   ├─ test_catalog_service.py
   ├─ test_movie_models.py
   ├─ test_movie_detail.py
   └─ test_main_window.py
```

---

### Task 1: Project foundation, settings, and data directories

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/config/__init__.py`
- Create: `app/config/settings.py`
- Create: `app/config/data_dirs.py`
- Create: `tests/conftest.py`
- Create: `tests/test_settings.py`

**Interfaces:**
- Produces: `LibraryConfig(id: str, name: str, path: Path, enabled: bool)`
- Produces: `AppSettings(data_dir: Path, cover_dir: Path, libraries: list[LibraryConfig], player_mode: str, player_path: Path | None, ffprobe_path: str, ffmpeg_path: str, auto_scan: bool)`
- Produces: `SettingsStore(path: Path).load() -> AppSettings` and `.save(settings: AppSettings) -> None`
- Produces: `ensure_data_layout(data_dir: Path) -> DataLayout`

- [ ] **Step 1: Create packaging metadata and test dependencies**

```toml
[project]
name = "local-movie-manager"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["PySide6>=6,<7"]

[project.optional-dependencies]
test = ["pytest>=8,<9", "pytest-qt>=4,<5"]

[tool.pytest.ini_options]
testpaths = ["tests"]
qt_api = "pyside6"
```

- [ ] **Step 2: Write failing settings round-trip test**

```python
def test_settings_round_trip(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    settings = AppSettings(
        data_dir=tmp_path / "data",
        cover_dir=tmp_path / "covers",
        libraries=[LibraryConfig("main", "主收藏", tmp_path / "movies", True)],
        player_mode="system",
        player_path=None,
        ffprobe_path="ffprobe",
        ffmpeg_path="ffmpeg",
        auto_scan=True,
    )
    store.save(settings)
    loaded = store.load()
    assert loaded == settings
```

- [ ] **Step 3: Run the test and verify failure**

Run: `python -m pytest tests/test_settings.py::test_settings_round_trip -v`
Expected: FAIL because `SettingsStore` and dataclasses do not exist.

- [ ] **Step 4: Implement immutable config dataclasses and atomic JSON save**

```python
@dataclass(frozen=True, slots=True)
class LibraryConfig:
    id: str
    name: str
    path: Path
    enabled: bool = True

@dataclass(frozen=True, slots=True)
class AppSettings:
    data_dir: Path
    cover_dir: Path
    libraries: list[LibraryConfig]
    player_mode: Literal["system", "custom"] = "system"
    player_path: Path | None = None
    ffprobe_path: str = "ffprobe"
    ffmpeg_path: str = "ffmpeg"
    auto_scan: bool = True
```

`SettingsStore.save()` must write `settings.json.tmp`, flush, then `Path.replace()` to avoid partial files.

- [ ] **Step 5: Add data layout test and implementation**

```python
def test_ensure_data_layout_creates_expected_directories(tmp_path):
    layout = ensure_data_layout(tmp_path / "data")
    assert layout.database_path == tmp_path / "data" / "library.db"
    assert layout.metadata_dir.is_dir()
    assert layout.thumbnail_cache_dir.is_dir()
    assert layout.generated_cover_dir.is_dir()
```

- [ ] **Step 6: Run foundation tests**

Run: `python -m pytest tests/test_settings.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml app/config tests/conftest.py tests/test_settings.py
git commit -m "feat: add settings and data layout"
```

---

### Task 2: Domain models and permanent metadata archives

**Files:**
- Create: `app/models/__init__.py`
- Create: `app/models/library.py`
- Create: `app/models/movie.py`
- Create: `app/services/__init__.py`
- Create: `app/services/metadata_service.py`
- Create: `tests/test_metadata_service.py`

**Interfaces:**
- Produces: `PlayEvent(played_at: datetime)`
- Produces: `MovieMetadata` with stable `uuid`, `cover_key`, editable metadata, `play_count`, first/last watch timestamps, and `play_history`
- Produces: `MetadataService(metadata_dir: Path)` with `create()`, `load()`, `save()`, `delete()`, `load_all()`

- [ ] **Step 1: Write failing archive persistence test**

```python
def test_metadata_survives_without_video_path(tmp_path):
    service = MetadataService(tmp_path / "metadata")
    movie = MovieMetadata.new(cover_key="SPSD-62", code="SPSD-62")
    movie.title = "示例影片"
    service.save(movie)

    loaded = service.load(movie.uuid)
    assert loaded.uuid == movie.uuid
    assert loaded.cover_key == "SPSD-62"
    assert loaded.title == "示例影片"
    assert not hasattr(loaded, "video_path")
```

- [ ] **Step 2: Run test to verify failure**

Run: `python -m pytest tests/test_metadata_service.py::test_metadata_survives_without_video_path -v`
Expected: FAIL because `MovieMetadata` and service do not exist.

- [ ] **Step 3: Implement metadata model with schema version 1**

```python
@dataclass(slots=True)
class PlayEvent:
    played_at: datetime

@dataclass(slots=True)
class MovieMetadata:
    uuid: str
    cover_key: str
    code: str = ""
    title: str = ""
    actors: list[str] = field(default_factory=list)
    series: str = ""
    studio: str = ""
    release_date: str = ""
    tags: list[str] = field(default_factory=list)
    rating: int = 0
    watched: bool = False
    play_count: int = 0
    favorite: bool = False
    notes: str = ""
    first_watched_at: datetime | None = None
    last_watched_at: datetime | None = None
    play_history: list[PlayEvent] = field(default_factory=list)

    @classmethod
    def new(cls, cover_key: str, code: str = "") -> "MovieMetadata":
        return cls(uuid=str(uuid4()), cover_key=cover_key, code=code)
```

Validate `rating` in `0..5`; normalize actor/tag whitespace; preserve unknown future JSON keys only through schema migrations, not arbitrary writes.

- [ ] **Step 4: Implement atomic UUID-named JSON archives**

`MetadataService.save(movie)` writes `<uuid>.json.tmp` then replaces `<uuid>.json`. Datetimes serialize as ISO 8601 strings. `load_all()` skips malformed JSON, returns `(movies, errors)` rather than aborting.

- [ ] **Step 5: Add corrupted-file isolation test**

```python
def test_load_all_skips_corrupt_json(tmp_path):
    service = MetadataService(tmp_path)
    good = MovieMetadata.new("GOOD-1", "GOOD-1")
    service.save(good)
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")

    movies, errors = service.load_all()
    assert [m.uuid for m in movies] == [good.uuid]
    assert len(errors) == 1
```

- [ ] **Step 6: Run metadata tests**

Run: `python -m pytest tests/test_metadata_service.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/models app/services/metadata_service.py tests/test_metadata_service.py
git commit -m "feat: add permanent movie metadata archives"
```

---

### Task 3: SQLite schema, repository, and archive rebuild

**Files:**
- Create: `app/db/__init__.py`
- Create: `app/db/database.py`
- Create: `app/db/schema.sql`
- Create: `app/repositories/__init__.py`
- Create: `app/repositories/movie_repository.py`
- Create: `tests/test_movie_repository.py`

**Interfaces:**
- Produces: `Database(path: Path)` context manager and `.initialize()`
- Produces: `MovieRuntime` and `MovieRecord(metadata, runtime)`
- Produces: `MovieRepository.upsert_metadata()`, `update_runtime()`, `mark_library_offline()`, `record_play_event()`, `delete_archive()`, `get()`, `search()`, `rebuild_from_archives()`

- [ ] **Step 1: Write failing repository rebuild test**

```python
def test_rebuild_from_archives_restores_permanent_fields(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()
    repo = MovieRepository(db)
    movie = MovieMetadata.new("SPSD-62", "SPSD-62")
    movie.favorite = True
    movie.play_count = 3

    repo.rebuild_from_archives([movie])
    record = repo.get(movie.uuid)
    assert record.metadata.favorite is True
    assert record.metadata.play_count == 3
    assert record.runtime.availability_status == "offline"
```

- [ ] **Step 2: Run test and verify failure**

Run: `python -m pytest tests/test_movie_repository.py::test_rebuild_from_archives_restores_permanent_fields -v`
Expected: FAIL because database/repository are missing.

- [ ] **Step 3: Create normalized schema**

`schema.sql` must define:

```sql
CREATE TABLE movies (
  uuid TEXT PRIMARY KEY,
  cover_key TEXT NOT NULL,
  code TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL DEFAULT '',
  series TEXT NOT NULL DEFAULT '',
  studio TEXT NOT NULL DEFAULT '',
  release_date TEXT NOT NULL DEFAULT '',
  rating INTEGER NOT NULL DEFAULT 0 CHECK(rating BETWEEN 0 AND 5),
  watched INTEGER NOT NULL DEFAULT 0,
  play_count INTEGER NOT NULL DEFAULT 0,
  favorite INTEGER NOT NULL DEFAULT 0,
  notes TEXT NOT NULL DEFAULT '',
  first_watched_at TEXT,
  last_watched_at TEXT,
  video_path TEXT,
  library_id TEXT,
  availability_status TEXT NOT NULL DEFAULT 'offline',
  subtitle_status INTEGER NOT NULL DEFAULT 0,
  duration REAL,
  width INTEGER,
  height INTEGER,
  video_codec TEXT,
  audio_codec TEXT,
  file_size INTEGER,
  cover_path TEXT,
  last_scanned_at TEXT
);
```

Also create `libraries`, `actors`, `movie_actors`, `tags`, `movie_tags`, and `play_events(movie_uuid, played_at)` with foreign keys and indexes on `code`, `title`, `cover_key`, `availability_status`, `favorite`, and `watched`.

- [ ] **Step 4: Implement transaction-safe repository mapping**

Use one transaction for metadata upsert + actor/tag relation replacement. `rebuild_from_archives()` clears only runtime index tables, recreates movies as offline, and restores every archived `play_history` event into `play_events`.

- [ ] **Step 5: Add offline path preservation test**

```python
def test_mark_offline_keeps_last_known_path(repo, movie_record):
    repo.update_runtime(movie_record.metadata.uuid, video_path="D:/Movies/X/X.mp4", availability_status="available")
    repo.mark_offline(movie_record.metadata.uuid)
    record = repo.get(movie_record.metadata.uuid)
    assert record.runtime.video_path.endswith("X.mp4")
    assert record.runtime.availability_status == "offline"
```

- [ ] **Step 6: Run repository tests**

Run: `python -m pytest tests/test_movie_repository.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/db app/repositories tests/test_movie_repository.py
git commit -m "feat: add sqlite movie repository"
```

---

### Task 4: Filesystem discovery and main-video selection

**Files:**
- Create: `app/models/scan.py`
- Create: `app/services/discovery_service.py`
- Create: `tests/test_discovery_service.py`

**Interfaces:**
- Produces: `MovieCandidate(folder: Path, video_path: Path, cover_key: str, inferred_code: str, subtitle_paths: list[Path])`
- Produces: `DiscoveryService.discover(root: Path) -> list[MovieCandidate]`

- [ ] **Step 1: Write failing recursive discovery test**

```python
def test_discovery_stops_below_identified_movie_folder(tmp_path):
    movie = tmp_path / "SPSD-62"
    extras = movie / "extras"
    extras.mkdir(parents=True)
    (movie / "SPSD-62.mp4").write_bytes(b"x" * 100)
    (extras / "bonus.mp4").write_bytes(b"x" * 200)

    candidates = DiscoveryService().discover(tmp_path)
    assert [c.video_path.name for c in candidates] == ["SPSD-62.mp4"]
```

- [ ] **Step 2: Run test and verify failure**

Run: `python -m pytest tests/test_discovery_service.py::test_discovery_stops_below_identified_movie_folder -v`
Expected: FAIL.

- [ ] **Step 3: Implement extension sets and selection rules**

Supported video extensions: `.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.m4v`, `.ts`, `.webm`.

Supported subtitle extensions: `.srt`, `.ass`, `.ssa`, `.vtt`.

For multiple videos in one folder:
1. exact stem match with folder name, case-insensitive;
2. otherwise largest file by byte size;
3. deterministic name sort as final tie-breaker.

`cover_key = selected_video.stem`; `inferred_code = selected_video.stem` initially.

- [ ] **Step 4: Add subtitle matching test**

```python
def test_discovers_external_subtitles_for_main_video(tmp_path):
    folder = tmp_path / "ABC-1"
    folder.mkdir()
    (folder / "ABC-1.mkv").write_bytes(b"video")
    (folder / "ABC-1.zh.srt").write_text("", encoding="utf-8")
    candidate = DiscoveryService().discover(tmp_path)[0]
    assert candidate.subtitle_paths[0].name == "ABC-1.zh.srt"
```

- [ ] **Step 5: Run discovery tests**

Run: `python -m pytest tests/test_discovery_service.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/models/scan.py app/services/discovery_service.py tests/test_discovery_service.py
git commit -m "feat: discover local movie folders"
```

---

### Task 5: ffprobe media inspection and subtitle state

**Files:**
- Create: `app/services/media_probe.py`
- Create: `tests/test_media_probe.py`

**Interfaces:**
- Produces: `MediaInfo(duration, width, height, video_codec, audio_codec, embedded_subtitle_count)`
- Produces: `MediaProbe(ffprobe_path: str).probe(path: Path) -> MediaInfo | None`
- Produces: `compute_subtitle_status(external_subtitles: Sequence[Path], media_info: MediaInfo | None) -> bool`

- [ ] **Step 1: Write failing JSON parse test without invoking real ffprobe**

```python
def test_parse_ffprobe_json_extracts_media_info():
    payload = {
        "format": {"duration": "123.5"},
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080},
            {"codec_type": "audio", "codec_name": "aac"},
            {"codec_type": "subtitle", "codec_name": "subrip"},
        ],
    }
    info = parse_ffprobe_payload(payload)
    assert info.duration == 123.5
    assert info.embedded_subtitle_count == 1
```

- [ ] **Step 2: Run test and verify failure**

Run: `python -m pytest tests/test_media_probe.py::test_parse_ffprobe_json_extracts_media_info -v`
Expected: FAIL.

- [ ] **Step 3: Implement subprocess call with timeout and no shell**

```python
cmd = [
    self.ffprobe_path, "-v", "error", "-show_streams", "-show_format",
    "-of", "json", str(path),
]
completed = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
```

Return `None` on missing executable, timeout, nonzero exit, or malformed JSON; log details without raising into the scanner.

- [ ] **Step 4: Add subtitle-state test**

```python
def test_external_or_embedded_subtitle_counts_as_available(tmp_path):
    assert compute_subtitle_status([tmp_path / "x.srt"], None) is True
    info = MediaInfo(None, None, None, None, None, 1)
    assert compute_subtitle_status([], info) is True
```

- [ ] **Step 5: Run media tests**

Run: `python -m pytest tests/test_media_probe.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/services/media_probe.py tests/test_media_probe.py
git commit -m "feat: inspect media with ffprobe"
```

---

### Task 6: Central cover lookup, replacement, thumbnail cache, and fallback frame

**Files:**
- Create: `app/services/cover_service.py`
- Create: `tests/test_cover_service.py`

**Interfaces:**
- Produces: `CoverResult(path: Path | None, source: Literal["library", "generated", "placeholder"])`
- Produces: `CoverService.resolve(cover_key: str, video_path: Path | None, duration: float | None) -> CoverResult`
- Produces: `CoverService.replace(cover_key: str, source_image: Path) -> Path`
- Produces: `CoverService.thumbnail(source: Path, size: QSize) -> Path`

- [ ] **Step 1: Write failing cover priority test**

```python
def test_cover_format_priority_is_stable(tmp_path):
    covers = tmp_path / "covers"
    covers.mkdir()
    (covers / "SPSD-62.png").write_bytes(b"png")
    (covers / "spsd-62.jpg").write_bytes(b"jpg")
    service = CoverService(covers, tmp_path / "cache", ffmpeg_path="ffmpeg")
    result = service.resolve("SPSD-62", None, None)
    assert result.path.name.lower() == "spsd-62.jpg"
    assert result.source == "library"
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/test_cover_service.py::test_cover_format_priority_is_stable -v`
Expected: FAIL.

- [ ] **Step 3: Implement case-insensitive indexed lookup**

Build a dictionary keyed by lowercase stem and extension on demand; invalidate the index after replacement. Exact priority is `.jpg`, `.jpeg`, `.png`, `.webp`.

- [ ] **Step 4: Implement replacement using `cover_key`, not video filename**

For `.jpg/.jpeg/.png/.webp`, copy to `<cover_key><original_supported_ext>`. If multiple existing formats for the key exist, remove stale alternatives only after the new file has been written successfully. For unsupported image types, use `QImage` to save `<cover_key>.jpg`.

- [ ] **Step 5: Implement generated-cover fallback**

If no library cover and `video_path` exists, call FFmpeg at `duration * 0.10` when duration is known, otherwise at 10 seconds. Write only to `cache/generated_covers/<uuid-or-hash>.jpg`; never copy generated frames to the user's cover directory.

- [ ] **Step 6: Add offline-cover test**

```python
def test_offline_movie_still_resolves_cover_by_cover_key(tmp_path):
    covers = tmp_path / "covers"
    covers.mkdir()
    (covers / "ABC-1.jpg").write_bytes(b"jpg")
    service = CoverService(covers, tmp_path / "cache", "ffmpeg")
    assert service.resolve("ABC-1", None, None).source == "library"
```

- [ ] **Step 7: Run cover tests**

Run: `python -m pytest tests/test_cover_service.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add app/services/cover_service.py tests/test_cover_service.py
git commit -m "feat: add centralized cover management"
```

---

### Task 7: Playback launching and durable viewing history

**Files:**
- Create: `app/services/player_service.py`
- Create: `app/services/viewing_service.py`
- Create: `app/utils/time.py`
- Create: `tests/test_viewing_service.py`

**Interfaces:**
- Produces: `PlayerService.play(video_path: Path, settings: AppSettings) -> None`
- Produces: `ViewingService.record_launch(movie_uuid: str, played_at: datetime | None = None) -> MovieMetadata`

- [ ] **Step 1: Write failing viewing-history persistence test**

```python
def test_record_launch_updates_json_and_sqlite(metadata_service, repo, archived_movie):
    viewing = ViewingService(repo, metadata_service)
    when = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    updated = viewing.record_launch(archived_movie.uuid, when)

    assert updated.watched is True
    assert updated.play_count == 1
    assert updated.first_watched_at == when
    assert updated.last_watched_at == when
    assert updated.play_history[-1].played_at == when
    assert repo.get(archived_movie.uuid).metadata.play_count == 1
```

- [ ] **Step 2: Run test and verify failure**

Run: `python -m pytest tests/test_viewing_service.py::test_record_launch_updates_json_and_sqlite -v`
Expected: FAIL.

- [ ] **Step 3: Implement viewing history as one coordinated transaction boundary**

Load archive, append `PlayEvent`, increment count, set watched, set first timestamp if absent, set last timestamp, then persist JSON and repository. If repository write fails after JSON save, retry repository from the saved archive; never drop the play event silently.

- [ ] **Step 4: Implement Windows/default and custom-player launch paths**

```python
if settings.player_mode == "custom":
    subprocess.Popen([str(settings.player_path), str(video_path)])
else:
    os.startfile(str(video_path))  # Windows only branch
```

Validate `video_path.is_file()` first. Validate custom player path if selected. Raise a domain `PlaybackError` for UI display.

- [ ] **Step 5: Add player validation tests**

```python
def test_player_rejects_missing_video(tmp_path, settings):
    service = PlayerService()
    with pytest.raises(PlaybackError):
        service.play(tmp_path / "missing.mp4", settings)
```

Also mock `subprocess.Popen` for custom-player mode and assert the executable and video path are passed as two argument-list elements, never through `shell=True`. Playback/history orchestration is tested in Task 11 where both services are wired together.

- [ ] **Step 6: Run viewing and player tests**

Run: `python -m pytest tests/test_viewing_service.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/services/player_service.py app/services/viewing_service.py app/utils/time.py tests/test_viewing_service.py
git commit -m "feat: persist playback history"
```

---

### Task 8: Scanner orchestration, matching, and offline preservation

**Files:**
- Create: `app/services/scanner.py`
- Create: `tests/test_scanner.py`

**Interfaces:**
- Produces: `ScanSummary(new: int, updated: int, offline: int, errors: list[ScanError], ambiguities: list[MatchAmbiguity])`
- Produces: `Scanner.scan(settings: AppSettings) -> ScanSummary`
- Consumes: `DiscoveryService`, `MetadataService`, `MovieRepository`, `MediaProbe`, `CoverService`

- [ ] **Step 1: Write failing “delete video keeps archive” test**

```python
def test_second_scan_marks_movie_offline_but_keeps_archive(scan_env):
    movie_file = scan_env.create_movie("SPSD-62")
    first = scan_env.scanner.scan(scan_env.settings)
    record = scan_env.repo.find_by_code("SPSD-62")[0]
    movie_file.unlink()

    second = scan_env.scanner.scan(scan_env.settings)
    record = scan_env.repo.get(record.metadata.uuid)
    assert record.runtime.availability_status == "offline"
    assert scan_env.metadata.load(record.metadata.uuid).code == "SPSD-62"
    assert second.offline == 1
```

- [ ] **Step 2: Run test and verify failure**

Run: `python -m pytest tests/test_scanner.py::test_second_scan_marks_movie_offline_but_keeps_archive -v`
Expected: FAIL.

- [ ] **Step 3: Implement deterministic matching order**

For each candidate, match in this order:
1. exact normalized last-known `video_path`;
2. one and only one offline archive with matching lowercase `cover_key`;
3. one and only one offline archive with matching normalized `code`;
4. otherwise create new archive.

If step 2 or 3 yields multiple possible archives, add `MatchAmbiguity` and do not auto-link or create a duplicate.

- [ ] **Step 4: Implement scan lifecycle**

For each enabled library:
- if root is missing, mark its currently available records offline and continue;
- discover candidates;
- match/create archive;
- probe media;
- resolve cover;
- update runtime as available;
- collect seen UUIDs.

After the library completes, mark previously available but unseen UUIDs for that library offline. Disabled libraries are not scanned and their state is not changed.

- [ ] **Step 5: Add relink test**

```python
def test_offline_archive_relinks_when_same_cover_key_returns(scan_env):
    first_path = scan_env.create_movie("ABC-1")
    scan_env.scanner.scan(scan_env.settings)
    uuid = scan_env.repo.find_by_code("ABC-1")[0].metadata.uuid
    first_path.unlink()
    scan_env.scanner.scan(scan_env.settings)
    new_path = scan_env.create_movie("ABC-1", library="secondary")
    scan_env.scanner.scan(scan_env.settings)
    record = scan_env.repo.get(uuid)
    assert Path(record.runtime.video_path) == new_path
    assert record.runtime.availability_status == "available"
```

- [ ] **Step 6: Run scanner tests**

Run: `python -m pytest tests/test_scanner.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/services/scanner.py tests/test_scanner.py
git commit -m "feat: scan and relink local movies"
```

---

### Task 9: Catalog queries, search, filters, edit, relink, and delete APIs

**Files:**
- Create: `app/services/catalog_service.py`
- Create: `tests/test_catalog_service.py`

**Interfaces:**
- Produces: `MovieFilter(library_id=None, favorite=None, watched=None, subtitle_status=None, availability_status=None, tag=None)`
- Produces: `CatalogService.list_movies(search: str = "", filters: MovieFilter = MovieFilter(), sort: str = "code") -> list[MovieRecord]`
- Produces: `CatalogService.update_metadata(uuid: str, patch: MovieMetadataPatch) -> MovieRecord`
- Produces: `CatalogService.relink_video(uuid: str, path: Path) -> MovieRecord`
- Produces: `CatalogService.delete_archive(uuid: str) -> None`

- [ ] **Step 1: Write failing search/filter test**

```python
def test_search_actor_and_filter_offline(catalog, seeded_movies):
    results = catalog.list_movies(
        search="卡丽娜",
        filters=MovieFilter(availability_status="offline"),
    )
    assert [r.metadata.code for r in results] == ["SPSD-62"]
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/test_catalog_service.py::test_search_actor_and_filter_offline -v`
Expected: FAIL.

- [ ] **Step 3: Implement repository search SQL**

Search must cover code, title, actors, series, studio, tags, and notes using parameterized `LIKE` queries. Filters are composable. Default query includes available and offline records.

- [ ] **Step 4: Implement metadata patch coordination**

`update_metadata()` must save the centralized JSON and SQLite metadata together. Changing `code` does not automatically change `cover_key`; add an explicit `cover_key` edit field only in the detail dialog's advanced section so a code correction does not unexpectedly break cover matching.

- [ ] **Step 5: Implement manual relink**

`relink_video()` validates a supported video extension, probes the file, updates runtime/library association, and preserves UUID, metadata, cover_key, and history.

- [ ] **Step 6: Implement permanent delete semantics**

Delete repository relations and metadata JSON. Do not delete `cover_path` or `video_path`. Return the paths to the caller so the UI can explicitly state that files were left untouched.

- [ ] **Step 7: Run catalog tests**

Run: `python -m pytest tests/test_catalog_service.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add app/services/catalog_service.py tests/test_catalog_service.py
git commit -m "feat: add movie catalog operations"
```

---

### Task 10: Qt data models, cover-wall delegate, and list view

**Files:**
- Create: `app/ui/__init__.py`
- Create: `app/ui/movie_models.py`
- Create: `app/ui/movie_delegate.py`
- Create: `tests/test_movie_models.py`

**Interfaces:**
- Produces: `MovieListModel(QAbstractListModel)` for the cover wall
- Produces: `MovieTableModel(QAbstractTableModel)` for the list view
- Produces: custom roles `MovieUuidRole`, `CoverPathRole`, `AvailabilityRole`, `SubtitleRole`, `FavoriteRole`, `WatchedRole`
- Produces: `MovieCardDelegate(QStyledItemDelegate)`

- [ ] **Step 1: Write failing list-model role test**

```python
def test_list_model_exposes_offline_status(qtbot, movie_record):
    model = MovieListModel([movie_record])
    index = model.index(0, 0)
    assert model.data(index, MovieListModel.AvailabilityRole) == "offline"
    assert model.data(index, Qt.DisplayRole) == movie_record.metadata.code
```

- [ ] **Step 2: Run and verify failure**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_movie_models.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement model reset/update APIs**

Both models expose `set_movies(records: Sequence[MovieRecord])`. Do not store widgets per movie. Table columns are exactly: thumbnail, code, title, actors, series, studio, release date, rating, subtitle, watched, local status, file size.

- [ ] **Step 4: Implement lightweight painted delegate**

`MovieCardDelegate.paint()` draws poster, code/title, favorite/watched/subtitle icons, and an offline badge. `sizeHint()` uses a fixed poster aspect ratio and card width so `QListView` can wrap efficiently.

- [ ] **Step 5: Add 2,000-item model smoke test**

```python
def test_list_model_handles_two_thousand_records_without_widgets(qtbot, record_factory):
    model = MovieListModel([record_factory(i) for i in range(2000)])
    assert model.rowCount() == 2000
```

- [ ] **Step 6: Run model tests**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_movie_models.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/ui/movie_models.py app/ui/movie_delegate.py tests/test_movie_models.py
git commit -m "feat: add movie grid and table models"
```

---

### Task 11: Movie detail dialog and archive actions

**Files:**
- Create: `app/ui/movie_detail.py`
- Create: `tests/test_movie_detail.py`

**Interfaces:**
- Produces: `MovieDetailDialog(record, catalog_service, cover_service, player_service, viewing_service, settings)`
- Emits: `movie_updated(str uuid)`, `movie_deleted(str uuid)`

- [ ] **Step 1: Write failing offline-state UI test**

```python
def test_offline_movie_disables_play_but_keeps_editing(qtbot, offline_record, services):
    dialog = MovieDetailDialog(offline_record, **services)
    qtbot.addWidget(dialog)
    assert dialog.play_button.isEnabled() is False
    assert dialog.relink_button.isEnabled() is True
    assert dialog.title_edit.isEnabled() is True
```

- [ ] **Step 2: Run and verify failure**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_movie_detail.py::test_offline_movie_disables_play_but_keeps_editing -v`
Expected: FAIL.

- [ ] **Step 3: Build form layout**

Include large cover, code, title, actors, series, studio, release date, tags, 0–5 rating, watched, favorite, subtitle state, local state, play count, first/last watch times, notes, and read-only media info.

Buttons: Play, Open Folder, Relink Local File, Replace Cover, Save, Delete Archive, Close.

- [ ] **Step 4: Wire safe actions**

- Play: call `PlayerService.play()`; only after success call `ViewingService.record_launch()` and refresh fields.
- Relink: `QFileDialog.getOpenFileName()` then `CatalogService.relink_video()`.
- Replace cover: choose image then `CoverService.replace(record.metadata.cover_key, source)`.
- Delete: confirmation text explicitly says video and cover files are not deleted; call `CatalogService.delete_archive()` only after confirmation.

- [ ] **Step 5: Add delete-semantics UI test**

Mock confirmation Yes and verify catalog delete is called once while filesystem delete APIs are never called by the dialog.

- [ ] **Step 6: Run detail tests**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_movie_detail.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/ui/movie_detail.py tests/test_movie_detail.py
git commit -m "feat: add movie detail editing"
```

---

### Task 12: Main window, filters, view switching, and background scanning

**Files:**
- Create: `app/ui/scan_worker.py`
- Create: `app/ui/main_window.py`
- Create: `tests/test_main_window.py`

**Interfaces:**
- Produces: `ScanWorker(QObject)` with `finished(ScanSummary)` and `failed(str)` signals
- Produces: `MainWindow(catalog_service, scanner, settings, services...)`

- [ ] **Step 1: Write failing main-window structure test**

```python
def test_main_window_has_required_filters_and_view_switch(qtbot, window):
    qtbot.addWidget(window)
    labels = [window.sidebar.item(i).text() for i in range(window.sidebar.count())]
    assert "全部影片" in labels
    assert "本地可播放" in labels
    assert "仅档案" in labels
    assert window.view_stack.count() == 2
```

- [ ] **Step 2: Run and verify failure**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_main_window.py::test_main_window_has_required_filters_and_view_switch -v`
Expected: FAIL.

- [ ] **Step 3: Build the desktop shell**

Top toolbar: search field, grid/list toggle, rescan, settings.

Sidebar: all, favorites, unwatched, watched, with subtitles, without subtitles, local playable, archive only; then configured libraries and common tags.

Center: `QStackedWidget` containing `QListView` cover wall and `QTableView` list.

- [ ] **Step 4: Connect search and filters through `CatalogService` only**

Debounce search input by ~200 ms using `QTimer`. On every filter/search change, call `CatalogService.list_movies()` and replace model data. Do not run SQL in UI classes.

- [ ] **Step 5: Implement background scan worker**

Move scanner execution to a worker object on `QThread`; scanner emits no Qt UI calls. On completion, show concise status such as `新增 12 / 更新 4 / 离线 1 / 错误 2`, refresh the catalog, and destroy the thread cleanly.

- [ ] **Step 6: Wire double click and context menu**

Grid/list double click opens detail. Context menu includes play, detail, open folder, favorite toggle, watched toggle. Disable file actions for offline records.

- [ ] **Step 7: Run main-window tests**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_main_window.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add app/ui/scan_worker.py app/ui/main_window.py tests/test_main_window.py
git commit -m "feat: add main movie library window"
```

---

### Task 13: Settings dialog, data-directory migration, and application bootstrap

**Files:**
- Create: `app/ui/settings_dialog.py`
- Create: `app/bootstrap.py`
- Create: `app/main.py`
- Create: `app/utils/logging.py`
- Modify: `app/config/data_dirs.py`
- Modify: `tests/test_settings.py`
- Modify: `tests/test_main_window.py`

**Interfaces:**
- Produces: `DataDirectoryMigrator.migrate(old: DataLayout, new_root: Path) -> DataLayout`
- Produces: `SettingsDialog(settings, settings_store)`
- Produces: `build_application(settings_path: Path | None = None) -> QApplication`

- [ ] **Step 1: Write failing data-directory migration test**

```python
def test_data_directory_migration_copies_db_and_metadata_but_not_cache(tmp_path):
    old = ensure_data_layout(tmp_path / "old")
    old.database_path.write_bytes(b"db")
    (old.metadata_dir / "a.json").write_text("{}", encoding="utf-8")
    (old.thumbnail_cache_dir / "temp.jpg").write_bytes(b"cache")

    new = DataDirectoryMigrator().migrate(old, tmp_path / "new")
    assert new.database_path.read_bytes() == b"db"
    assert (new.metadata_dir / "a.json").exists()
    assert not (new.thumbnail_cache_dir / "temp.jpg").exists()
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/test_settings.py::test_data_directory_migration_copies_db_and_metadata_but_not_cache -v`
Expected: FAIL.

- [ ] **Step 3: Build settings dialog**

Sections:
- application data directory;
- central cover directory;
- library roots table with Add/Remove/Rename/Enable;
- system/custom player and executable path;
- ffprobe/ffmpeg paths with detection buttons;
- auto-scan checkbox.

When changing the data directory, copy `library.db` and `metadata/`, recreate caches, then update bootstrap settings. Refuse migration into a non-empty directory containing another `library.db` unless the user explicitly chooses that directory as an existing library; do not overwrite silently.

- [ ] **Step 4: Implement bootstrap order**

1. Determine bootstrap settings path using `QStandardPaths.AppConfigLocation`.
2. Load settings; if missing, create defaults using a writable local application-data directory and an initially empty library list. If no library is configured, open Settings on first launch rather than guessing a media folder.
3. Ensure data layout and initialize DB.
4. Load all metadata JSON; if DB is new/empty, rebuild repository from archives.
5. Construct services.
6. Construct and show `MainWindow`.
7. If `auto_scan`, start background scan after the event loop begins.

- [ ] **Step 5: Add logging**

Create rotating log file under `<data_dir>/logs/app.log`. Scanner/service exceptions include movie path or UUID. UI receives short user-facing messages only.

- [ ] **Step 6: Run all unit/UI tests**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest -v`
Expected: PASS.

- [ ] **Step 7: Manual smoke run**

Run: `python -m app.main`
Expected on Windows: app opens with no browser/server; settings can add three libraries and a cover directory; closing and reopening preserves settings.

- [ ] **Step 8: Commit**

```bash
git add app/ui/settings_dialog.py app/bootstrap.py app/main.py app/utils/logging.py tests
git commit -m "feat: bootstrap configurable desktop app"
```

---

### Task 14: Acceptance tests and documentation

**Files:**
- Create: `tests/test_acceptance_archive_lifecycle.py`
- Create: `README.md`
- Modify: `docs/superpowers/specs/2026-08-16-local-movie-manager-design.md` only if implementation exposes a concrete mismatch that must be documented

**Interfaces:**
- Verifies complete lifecycle without depending on real media codecs.

- [ ] **Step 1: Write end-to-end archive lifecycle test**

```python
def test_archive_lifecycle_survives_video_delete_and_db_rebuild(app_services, tmp_path):
    video = app_services.create_movie_file("SPSD-62")
    app_services.scan()
    movie = app_services.catalog.list_movies(search="SPSD-62")[0]
    app_services.catalog.update_metadata(movie.metadata.uuid, title="保留档案", favorite=True)
    app_services.viewing.record_launch(movie.metadata.uuid, fixed_time())

    video.unlink()
    app_services.scan()
    offline = app_services.catalog.list_movies(search="SPSD-62")[0]
    assert offline.runtime.availability_status == "offline"
    assert offline.metadata.favorite is True
    assert offline.metadata.play_count == 1

    app_services.delete_database_and_rebuild()
    rebuilt = app_services.catalog.list_movies(search="SPSD-62")[0]
    assert rebuilt.metadata.title == "保留档案"
    assert rebuilt.metadata.play_history[0].played_at == fixed_time()
```

- [ ] **Step 2: Run acceptance test first and fix only real integration defects**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_acceptance_archive_lifecycle.py -v`
Expected: PASS after integration fixes.

- [ ] **Step 3: Run complete suite**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest -v`
Expected: all tests PASS; no skipped core behavior tests.

- [ ] **Step 4: Write concise README**

README must include:
- Python 3.11+ requirement;
- install command `python -m pip install -e ".[test]"` for development;
- FFmpeg/ffprobe requirement and how to select paths in Settings;
- recommended one-movie-per-folder structure;
- central cover naming rule using `cover_key` / initial video stem;
- explanation that deleting video does not delete archive;
- run command `python -m app.main`;
- backup guidance: back up the configured data directory plus the cover directory.

- [ ] **Step 5: Final verification**

Run:

```bash
git status --short
QT_QPA_PLATFORM=offscreen python -m pytest -q
python -m compileall app
```

Expected: clean test pass and no Python syntax errors.

- [ ] **Step 6: Commit**

```bash
git add README.md tests/test_acceptance_archive_lifecycle.py
git commit -m "test: verify durable movie archive lifecycle"
```

---

## Plan Self-Review

### Spec coverage

- Multiple configurable libraries: Tasks 1, 8, 12, 13.
- Central UUID metadata and DB rebuild: Tasks 2, 3, 14.
- Video-independent permanent archives: Tasks 3, 8, 9, 14.
- Durable watch count/history: Tasks 2, 3, 7, 14.
- Central cover directory and offline covers: Task 6.
- ffprobe and subtitle status: Task 5.
- External playback: Task 7.
- Search/filter including online/offline: Tasks 9, 12.
- Grid/list dual view: Tasks 10, 12.
- Detail editing, relink, delete semantics: Task 11.
- Background scan and error isolation: Tasks 8, 12, 13.
- Settings/data-dir migration: Tasks 1, 13.

### Type consistency

- `MovieMetadata.uuid` is the permanent identity across JSON, SQLite, UI, and scanner.
- `cover_key` is independent of `code` and `video_path` after initial creation.
- `availability_status` is runtime-only and always `available` or `offline`.
- `play_history` contains `PlayEvent` objects in memory and ISO timestamps in JSON/SQLite.
- UI consumes `MovieRecord` and never opens database connections directly.

### Scope check

The plan remains one coherent desktop application. Each task leaves a testable layer or user-visible slice and can be reviewed independently; no website scraping, media playback engine, or network subsystem is included.
