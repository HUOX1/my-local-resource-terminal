# v0.6 Phase 1B Godot Games Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付 Godot 4.7.x 主机前端：XMB 顶层、GPU Ambient、真实 3D 游戏盒 Carousel、当前页面预览态、预览音频和 SYSTEM 基础页。

**Architecture:** Godot 只通过 BackendBridge 消费 Python Core 的 JSON 数据，不直接读 SQLite。持续动画留在 Godot/GPU；脚本只更新高层状态。

**Tech Stack:** Godot 4.7.x Stable, GDScript, Control, Node3D, Shader, Audio buses.

**Spec:** `docs/v0.6/Console_Terminal_Architecture.md`

## Global Constraints

- 默认无边框最大化。
- 顶层：GAMES / MOVIES / COMICS / MUSIC / SEARCH / SYSTEM，全部有统一图标节点，不用 Emoji。
- 鼠标优先，键盘/手柄共享同一个 selection/focus 状态。
- Games 为单排横向 Carousel，中央主盒始终代表当前选中项。
- 单盒是真 3D 厚度，整排不做夸张 3D 弧线。
- 主盒单击预览；双击启动；侧盒单击只滑到主位。
- 预览态不切 Scene，并支持继续滚轮换游戏。

---

### Task 1: Godot 主壳与 Backend Bridge

**Files:** Create `godot_frontend/project.godot`, `main.tscn`, `scenes/shell/TerminalShell.tscn`, `scripts/bridge/backend_bridge.gd`, `scripts/shell/terminal_shell.gd`, `terminal_tools/validate_godot.bat`.

**Interfaces:** `BackendBridge.request(type,payload)`, signals `connected`, `response_received`, `event_received`.

- [ ] 在项目文件不存在时运行 `godot --headless --path godot_frontend --editor --quit`，记录预期失败。
- [ ] 创建最小 project/main scene，使同一 headless 命令退出 0。
- [ ] 实现 `ws://127.0.0.1:8765` hello、request ID、response dispatch、断线重连。
- [ ] Backend 离线时显示轻量 Offline 状态，UI 不崩溃。
- [ ] Run `terminal_tools\validate_godot.bat`; commit `feat(v06): add godot shell and backend bridge`.

### Task 2: XMB 顶层与 GPU Ambient

**Files:** Create `scripts/theme/theme_controller.gd`, `shaders/ambient.gdshader`; modify shell/main.

**Interfaces:** `ThemeController.apply_manifest(manifest: Dictionary)`.

- [ ] 建立 GAMES/MOVIES/COMICS/MUSIC/SEARCH/SYSTEM 横向顶层，每项独立 icon node + label。
- [ ] Phase 1 只有 GAMES/SYSTEM 进入完整内容，其余进入统一占位页，但导航/焦点行为必须完整。
- [ ] Ambient 使用单个全屏 shader 生成渐变、4 层柔和波浪和 36 个程序化 `△ ○ × □`；不得创建 36 个逐帧脚本节点。
- [ ] 将 Classic Violet colors/ambient 参数映射到 shader uniforms。
- [ ] Run Godot validation; commit `feat(v06): add xmb shell and gpu ambient`.

### Task 3: 真实 3D GameCase3D

**Files:** Create `scenes/games/GameCase3D.tscn`, `scripts/games/game_case_3d.gd`.

**Interfaces:** `bind(item: Dictionary)`, signals `single_clicked(item_id)`, `double_clicked(item_id)`, `hover_changed(item_id, hovered)`.

- [ ] 使用 `Node3D + BoxMesh + front Quad + spine Quad + Area3D` 做真实盒体。
- [ ] cover path 变成贴图；无封面时使用主题生成 fallback，而非 crash。
- [ ] Hover 只做轻微 Y 轴倾斜、抬升、scale 和材质高光，离开平滑回零。
- [ ] 鼠标位置只驱动当前盒体 transform/material，不触发全场景资源重建。
- [ ] Run Godot validation; commit `feat(v06): add real 3d game case`.

### Task 4: Games 单排 Carousel 与主盒交互

**Files:** Create `scenes/games/GamesView.tscn`, `scripts/games/games_view.gd`; modify shell.

**Interfaces:** `load_games(items: Array)`, `selected_item_id`; signals `preview_requested`, `launch_requested`, `selection_changed`.

- [ ] 从 BackendBridge 请求 `library.games.list`；空库显示 Add Game 引导，不使用假数据。
- [ ] 维护不变式：`selected_index` 对应中央主盒。
- [ ] 鼠标滚轮切 selected_index，并 Tween 整排到新主位。
- [ ] 侧盒单击只移动到中央，不进入预览。
- [ ] 主盒首次单击启动约 220ms Timer；若期间收到 double-click，取消 Timer 并发 `launch_requested`；否则 Timer 到期发 `preview_requested`。
- [ ] 键盘左右和手柄左右调用同一 selection 函数，不另写 UI 状态。
- [ ] Run Godot validation; commit `feat(v06): add main-case game carousel`.

### Task 5: 当前页面预览态

**Files:** Create `scenes/games/GamePreviewPanel.tscn`, `scripts/games/game_preview_panel.gd`; modify GamesView.

**Interfaces:** `show_manifest(game, preview)`, `hide_preview`, signals `play_pressed`, `details_pressed`.

- [ ] 单击主盒后：主盒 Tween 到左侧；其余盒缩小/后退/降亮度但保持可见；右侧 panel 淡入。
- [ ] 预览态滚轮继续切游戏，保持 preview mode。
- [ ] 切换时先换主盒与轻量文字，再请求新的 `game.preview`。
- [ ] 加 400ms 稳定选择门槛；快速滚动不启动重型媒体。
- [ ] Media priority 固定为 `video_ogv > gif_frames > screenshots > background > cover`。
- [ ] GIF 根据后端 duration 播缓存 PNG；screenshots 自动轮播；无素材显示主题 fallback。
- [ ] Run Godot validation; commit `feat(v06): add in-place game preview`.

### Task 6: 预览音频、主题音乐与 Launch/Return UI 状态

**Files:** Modify main scene, PreviewPanel, GamesView; add audio bus layout.

**Interfaces:** Audio buses `ThemeMusic`, `PreviewAudio`, `UI`.

- [ ] ThemeMusic 支持主题音乐为空、有 loop/volume/fade 参数。
- [ ] 自动视频允许声音；PreviewAudio 设置关闭时静音但视频仍可播放。
- [ ] 预览开始时 ThemeMusic duck 到 30%，结束/切换时恢复。
- [ ] `launch_requested` 发 `game.launch` 后进入 Launch Transition；收到 `game.started` 隐藏/暂停高成本呈现。
- [ ] 收到 `game.exited` 恢复窗口状态、原 selected item 并播放 Return Transition。
- [ ] Run Godot validation; commit `feat(v06): add preview audio and launch transitions`.

### Task 7: SYSTEM 基础页与 Add Game

**Files:** Create `scenes/system/SystemView.tscn`, `scripts/system/system_view.gd`; modify shell.

- [ ] Add Game 用 FileDialog 选 exe 和可选 cover；title 默认 exe stem，可编辑。
- [ ] 提交 `game.create` 成功后回到 GAMES 并刷新列表。
- [ ] SYSTEM 暴露 Display Mode、Preview Audio、Preview Volume、Preview Auto Play、Theme Music、Restore Last Section/Item。
- [ ] 启动时 `state.get` 恢复 section/item/browser position，但 preview 必须关闭。
- [ ] Run Godot validation; commit `feat(v06): add system settings and game creation`.

### Task 8: Dev HUD 与 Godot 行为 Smoke

**Files:** Create `scripts/dev/dev_hud.gd`; modify main scene.

- [ ] F3 toggle Dev HUD；默认隐藏且不改变正式布局。
- [ ] 显示 FPS、Backend Connected、section、selected item、preview state、external process state。
- [ ] 在 Godot 编辑器完成手工行为 smoke：滚轮主盒、侧盒单击、主盒单击预览、预览态继续滚动、双击只触发 launch。
- [ ] 记录 smoke 结果到 `docs/development-logs/v0.6_Phase1_Development_Log.md`。
- [ ] Commit `test(v06): add godot dev hud and interaction smoke`.

## Verification

```text
terminal_tools\validate_godot.bat
```

Windows 手工验收必须看到：GPU Ambient 持续流畅；鼠标空白移动不造成旧 QWidget 式 CPU 跃升；真实 game list/cover；主盒与侧盒交互符合原型经验；预览不切页面；视频/GIF/图片自动预览；预览音频可开关。
