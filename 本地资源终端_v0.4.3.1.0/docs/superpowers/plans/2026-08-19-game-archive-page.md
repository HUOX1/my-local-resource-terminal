# Game Archive Content Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将游戏档案从模态窗口入口升级为主内容区整页，并加入图片/GIF Hero 媒体及回退逻辑。

**Architecture:** 保留现有 `GameDetailDialog` 作为“编辑档案”对话框，新建只负责展示和导航的 `GameArchivePage`。主窗口内容区增加 library/archive 两层堆叠；Hero 媒体持久化扩展通过现有 GameMetadata → JSON → SQLite → GameAssetService 链路完成。

**Tech Stack:** Python 3.11+, PySide6 Widgets, SQLite, JSON, Pillow

**Spec:** `docs/superpowers/specs/2026-08-19-game-archive-page-design.md`

## Global Constraints
- 版本目标：`0.4.1.8`。
- Hero 仅支持 JPG/JPEG/PNG/WebP/BMP/GIF，禁止视频。
- 不改影片档案骨架。
- 不使用 Windows 外窗玻璃/DWM 透明方案。
- 保持旧 JSON/SQLite 数据可升级读取。

---

### Task 1: Hero 数据字段与终端拥有资源

**Files:**
- Modify: `app/models/game.py`
- Modify: `app/config/data_dirs.py`
- Modify: `app/services/game_asset_service.py`
- Modify: `app/services/game_metadata_service.py`
- Modify: `app/services/game_catalog_service.py`
- Modify: `app/repositories/game_repository.py`
- Modify: `app/db/schema.sql`
- Modify: `app/db/database.py`
- Modify: `app/bootstrap.py`
- Test: `tests/test_game_archive_page_v0418.py`

**Interfaces:**
- Produces: `GameMetadata.archive_media_path: str | None`
- Produces: `GameAssetService.import_archive_media(game_uuid, source) -> Path | None`
- Produces: `GameCatalogService.update_archive_media(uuid, source=None, remove=False) -> GameRecord`

- [ ] 写失败测试：旧库迁移到 schema 4 且字段默认为 NULL；图片/GIF 可导入，视频被拒绝；JSON 往返保留 `archive_media_path`。
- [ ] 运行目标测试确认 RED。
- [ ] 最小实现字段、目录、资源服务、JSON/DB 持久化。
- [ ] 运行目标测试确认 GREEN。

### Task 2: Hero 选择与回退策略

**Files:**
- Create: `app/ui/game_archive_page.py`
- Test: `tests/test_game_archive_page_v0418.py`

**Interfaces:**
- Produces: `resolve_game_archive_media(record, screenshot_service) -> Path | None`
- Priority: archive media → preview GIF → newest screenshot → None

- [ ] 写失败测试覆盖回退顺序和“封面永不参与”。
- [ ] 运行目标测试确认 RED。
- [ ] 实现纯函数回退策略和媒体类型判断。
- [ ] 运行目标测试确认 GREEN。

### Task 3: 游戏档案整页 UI 与主窗口切换

**Files:**
- Create/Modify: `app/ui/game_archive_page.py`
- Modify: `app/ui/main_window.py`
- Modify: `app/ui/flat_theme.py`
- Modify: `app/ui/flat_icons.py`
- Test: `tests/test_game_archive_page_v0418.py`
- Modify: `tests/test_game_ui_source.py`

**Interfaces:**
- `GameArchivePage.back_requested`
- `GameArchivePage.launch_requested(str)`
- `GameArchivePage.edit_requested(str)`
- `GameArchivePage.archive_media_change_requested(str)`
- `GameArchivePage.archive_media_clear_requested(str)`
- `GameArchivePage.set_record(GameRecord)`

- [ ] 写失败测试：主窗口使用内容区档案页而不是直接 `GameDetailDialog.exec()`；页面具有返回按钮、Hero、资料/记录/媒体展示。
- [ ] 运行目标测试确认 RED。
- [ ] 实现页面、主题样式、图标和主窗口切换。
- [ ] 运行目标测试确认 GREEN。

### Task 4: 编辑/保存刷新与版本发布

**Files:**
- Modify: `app/ui/main_window.py`
- Modify: `pyproject.toml`
- Modify: `app/ui/app_chrome.py`
- Create: `升级说明_v0.4.1.8.txt`
- Test: `tests/test_game_archive_page_v0418.py`

**Interfaces:**
- Existing `GameDetailDialog` remains editor.
- After save, both wall and archive page refresh from catalog.

- [ ] 写失败测试：版本号 0.4.1.8、编辑保存后档案页刷新、返回逻辑保持。
- [ ] 运行目标测试确认 RED。
- [ ] 实现刷新和版本信息。
- [ ] 运行目标测试确认 GREEN。
- [ ] 跑完整 pytest 与 compileall。
- [ ] 生成完整源码 ZIP 与基于 v0.3.4.7 的累计覆盖包，做运行文件一致性和 ZIP 完整性检查。
