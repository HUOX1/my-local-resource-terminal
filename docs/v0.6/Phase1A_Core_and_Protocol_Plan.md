# v0.6 Phase 1A Core and Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立与 v0.5 完全隔离的 Python Core、SQLite 数据、设置、主题、预览素材与 localhost WebSocket 协议。

**Architecture:** 新代码只放 `terminal_core/`，不从旧 `app/` 导入运行时代码。Godot 只通过 `127.0.0.1:8765` 的 JSON 协议读取数据和发命令。

**Tech Stack:** Python 3.11+, SQLite, websockets, Pillow, FFmpeg CLI.

**Spec:** `docs/v0.6/Console_Terminal_Architecture.md`

## Global Constraints

- Windows-only Phase 1.
- 新数据根目录 `%LOCALAPPDATA%\LocalResourceTerminal\v0.6\`。
- 不读取或迁移 v0.5 数据/设置。
- Godot 不直接访问 SQLite。
- 协议版本固定为 1，仅绑定 `127.0.0.1:8765`。

---

### Task 1: 路径、设置与日志

**Files:** Create `terminal_core/{__init__,__main__,paths,settings,logging_setup}.py`; create `terminal_tests/test_paths_settings.py`; modify `pyproject.toml`.

**Interfaces:** `TerminalPaths.from_environment()`, `TerminalSettings.default/load/save()`, `configure_logging()`.

- [ ] 写失败测试：`LOCALAPPDATA=<tmp>` 时 root 必须等于 `<tmp>/LocalResourceTerminal/v0.6`，database 必须为 `library.db`。
- [ ] Run `python -m pytest terminal_tests/test_paths_settings.py -v`; expected FAIL because module is missing.
- [ ] 实现 `root/database/assets/cache/themes/logs/settings` 和 `ensure()`。
- [ ] 写设置 round-trip 测试，覆盖 `display_mode`, `preview_audio`, `preview_volume`, `theme_music`, `restore_last_section`, `restore_last_item`, `current_theme`, `ffmpeg_path`, `godot_executable`。
- [ ] 实现原子 JSON save/load；未知字段拒绝写入。
- [ ] `pyproject.toml` 增加 `websockets>=15,<16`，旧依赖暂保留到最终切换。
- [ ] Run tests; commit `feat(v06): add isolated core paths and settings`.

### Task 2: 全新 SQLite 与 Game Repository

**Files:** Create `terminal_core/schema.sql`, `database.py`, `models.py`, `repository.py`; create `terminal_tests/test_database_repository.py`.

**Interfaces:** `Database.initialize()`, `LibraryRepository.create_game/list_games/get_game/update_play_stats()`.

- [ ] 写 schema 测试，要求存在 `library_items`, `games`, `media_assets`, `terminal_state`。
- [ ] 实现 foreign keys + transactions；ID 使用 UUID4 字符串。
- [ ] 写真实临时 exe 路径的 Game CRUD round-trip 测试。
- [ ] 实现通用 item 字段与 game 扩展字段；路径保存绝对路径。
- [ ] 写媒体优先级测试：`manual > auto > generated`，同 source 内 `priority` 小者优先。
- [ ] Run `python -m pytest terminal_tests/test_database_repository.py -v`; commit `feat(v06): add clean library database`.

### Task 3: localhost WebSocket + JSON

**Files:** Create `terminal_core/protocol.py`, `websocket_server.py`; create `terminal_tests/test_protocol.py`, `terminal_tools/protocol_smoke.py`.

**Interfaces:** request `{"id":str,"type":str,"payload":object}`; response `{"id":str,"type":"response","ok":bool,"data":object|null,"error":object|null}`. Phase 1 commands: `hello`, `library.games.list`, `game.create`, `game.launch`, `game.preview`, `settings.get/update`, `state.get/update`, `theme.current`. Events: `library.changed`, `game.started`, `game.exited`, `backend.error`.

- [ ] 写 parser 测试：缺 `id/type/payload` 必须抛 `ProtocolError`。
- [ ] 实现严格 parser/serializer；第一条消息必须 `hello` 且 `protocol == 1`。
- [ ] 写绑定测试，server host 必须为 `127.0.0.1`，不得 `0.0.0.0`。
- [ ] 实现 asyncio WebSocket server 和结构化错误。
- [ ] `protocol_smoke.py` 启动临时 backend，hello → 空 game list → 断开，成功退出码 0。
- [ ] Run tests/smoke; commit `feat(v06): add localhost websocket protocol`.

### Task 4: 游戏进程与计时

**Files:** Create `terminal_core/services/{__init__,game_runtime}.py`; create `terminal_tests/test_game_runtime.py`; modify `websocket_server.py`.

**Interfaces:** `GameRuntime.launch(game) -> RunningGame`; async `wait_for_exit() -> GameExit`.

- [ ] 用 `sys.executable -c "..."` 启动短命真实子进程写失败测试，验证 args/cwd/shell=False。
- [ ] 实现 `subprocess.Popen` 启动和 `launch_failed` 错误。
- [ ] 写进程结束后 `playtime_seconds`、`last_played_at` 更新测试。
- [ ] 实现 async wait 和 repository 更新。
- [ ] `game.launch` 成功后广播 `game.started`；退出广播 `game.exited`（item_id/elapsed_seconds/exit_code）。
- [ ] Run tests; commit `feat(v06): add game runtime lifecycle`.

### Task 5: 预览素材 Pipeline

**Files:** Create `terminal_core/services/media_assets.py`; create `terminal_tests/test_media_assets.py`; modify repository/server.

**Interfaces:** `MediaAssetService.resolve_preview(item_id) -> PreviewManifest`，字段固定为 `cover/background/screenshots/gif_frames/gif_durations_ms/video_ogv/preview_audio/logo`。

- [ ] 测试手动素材覆盖自动发现素材。
- [ ] 自动发现 `preview.*`, `background.*`, `logo.*`, `screenshots/*`。
- [ ] 用 Pillow 在测试中生成 2 帧 GIF；断言缓存 PNG 帧与 duration。
- [ ] GIF cache key 使用源绝对路径 + size + mtime 哈希，源不变不得重复解码。
- [ ] `.ogv` 直接使用；其他常见视频格式通过 FFmpeg 转为 cache `.ogv`，Theora + Vorbis，最高 1080p/30fps。
- [ ] FFmpeg 不存在/失败时返回静态 fallback 并写 warning，不让 preview request 整体失败。
- [ ] Run tests; commit `feat(v06): add preview media pipeline`.

### Task 6: 主题服务

**Files:** Create `terminal_core/services/themes.py`, `terminal_tests/test_themes.py`; create `godot_frontend/themes/classic_violet/theme.json`; modify server.

**Interfaces:** `ThemeService.list_themes/load()`，manifest 包含 colors/ambient/audio/icons/transitions。

- [ ] 写 manifest 校验测试：缺 `id/name/colors/ambient` 拒绝；music 为空合法。
- [ ] 内置主题与 `%LOCALAPPDATA%\LocalResourceTerminal\v0.6\themes` 合并，同 ID 用户主题优先。
- [ ] 测试并拒绝 `../` 主题资源路径逃逸。
- [ ] Classic Violet 定义柔和波浪、36 个 `△ ○ × □`、可空背景音乐接口。
- [ ] Run tests; commit `feat(v06): add local theme manifests`.

## Verification

Run:

```text
python -m pytest terminal_tests/test_paths_settings.py terminal_tests/test_database_repository.py terminal_tests/test_protocol.py terminal_tests/test_game_runtime.py terminal_tests/test_media_assets.py terminal_tests/test_themes.py -v
python terminal_tools/protocol_smoke.py
```

通过条件：Core 可在临时空数据目录独立启动、创建测试 Game、返回 PreviewManifest、启动短命进程并发出退出事件，且没有任何 `app.*` runtime import。
