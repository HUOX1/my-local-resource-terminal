# v0.3.4.1 游戏档案窗口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 合并游戏“查看详情/编辑游戏”为单一可编辑游戏档案窗口，并加入作品介绍字段，同时保持游玩与媒体功能独立分区。

**Architecture:** 保留现有 `GameEditDialog` 专用于新增游戏；将 `GameDetailDialog` 演进为可编辑 `GameArchiveDialog`，以资料/游玩/媒体三个页签承载现有能力。新增 `description` 贯穿 GameMetadata、JSON、SQLite、repository、catalog service；旧 notes 数据不迁移，只在 UI 改称“我的记录”。

**Tech Stack:** Python 3.11+, PySide6 Widgets, SQLite, JSON, Pillow.

## Global Constraints

- 版本号为 `0.3.4.1`，不升 `0.3.5`。
- 不增加第三方依赖。
- 不改影片模块行为。
- 不加入在线资料搜索、Hero 图、成就、Overlay、模拟器适配或第二阶段视觉包装。
- 封面/GIF 清除继续删除终端受管理副本，不删除原始导入文件。
- 当前项目不是 Git 仓库，所有计划中的 commit 步骤以“记录验证结果”替代。

---

### Task 1: `description` 永久数据字段

**Files:**
- Modify: `app/models/game.py`
- Modify: `app/services/game_metadata_service.py`
- Modify: `app/repositories/game_repository.py`
- Modify: `app/services/game_catalog_service.py`
- Modify: `app/db/schema.sql`
- Modify: `app/db/database.py`
- Test: `tests/test_game_metadata_service.py`
- Test: `tests/test_game_repository.py`
- Test: `tests/test_database_migrations.py`
- Test: `tests/test_game_catalog_service.py`

**Interfaces:**
- Produces `GameMetadata.description: str` and `GameMetadataPatch.description: str | None`.
- `GameCatalogService.create_game(..., description="")` and `update_game()` persist it.

- [ ] Step 1: Add tests that old JSON decodes `description == ""`, new JSON round-trips a description, DB v2 gains the column/schema v3, repository round-trips it, and catalog update changes it without changing notes.
- [ ] Step 2: Run those targeted tests and verify they fail because `description`/schema v3 do not exist.
- [ ] Step 3: Add the field through model, JSON, DB migration, repository and catalog service with defaults preserving old archives.
- [ ] Step 4: Re-run targeted tests; all pass.

### Task 2: 可编辑游戏档案窗口

**Files:**
- Modify: `app/ui/game_detail.py`
- Reuse: `app/ui/game_edit_dialog.py` helpers/behavior where appropriate without changing Add Game semantics.
- Test: `tests/test_game_ui_source.py` (or existing UI source test file)

**Interfaces:**
- `GameDetailDialog` remains import-compatible but becomes the single game archive UI.
- Add signal `save_requested` carrying an immutable edit payload, or expose validated result through a focused method used by main window.
- Existing `launch_requested` stays intact.

- [ ] Step 1: Add UI source/Qt tests requiring tabs `资料/游玩/媒体`, labels `作品介绍/我的记录`, no large cover widget, and existing screenshot media controls under the media tab.
- [ ] Step 2: Run targeted UI tests and verify failure against the old long detail page.
- [ ] Step 3: Rebuild `GameDetailDialog` with `QTabWidget`: editable fields + save on 资料, read-only stats/session table on 游玩, current media browser on 媒体; retain cover/GIF browse/clear and screenshot directory browse.
- [ ] Step 4: Re-run targeted tests; pass or skip only where PySide6 is unavailable.

### Task 3: 主窗口只保留“游戏档案”入口并保存更新

**Files:**
- Modify: `app/ui/main_window.py`
- Test: `tests/test_game_ui_source.py`
- Test: relevant main-window source tests

**Interfaces:**
- `_open_game_detail(record)` opens the unified archive dialog and handles save callbacks via `GameCatalogService.update_game()`.
- Remove separate `_edit_game(record)` use from right-click/selected-game menus; `GameEditDialog` remains for `_add_game()` only.

- [ ] Step 1: Add source tests asserting right-click menus contain `游戏档案` and no simultaneous `查看详情`/`编辑游戏` actions.
- [ ] Step 2: Run and verify failure.
- [ ] Step 3: Wire archive save into catalog update including `description`, notes, launch paths, screenshot directory and cover/GIF import/removal; refresh game wall after save.
- [ ] Step 4: Re-run targeted tests.

### Task 4: 版本、回归和交付

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Create: `升级说明_v0.3.4.1.txt`
- Create release ZIPs under `/mnt/data/`.

- [ ] Step 1: Set product version to `0.3.4.1` and document only this release's changes.
- [ ] Step 2: Run full `python -m pytest -q`.
- [ ] Step 3: Run `python -m pytest -q tests/test_python_compatibility.py` and `python -m compileall -q app tests`.
- [ ] Step 4: Overlay the patch onto a clean v0.3.4 release and run the previous v0.3.4 test suite.
- [ ] Step 5: Build patch ZIP and full ZIP, exclude caches/pyc/user data, and run ZIP integrity checks.
