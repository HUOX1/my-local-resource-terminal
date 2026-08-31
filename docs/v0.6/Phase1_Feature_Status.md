# G3 功能地图（Games Vertical Slice）

这份地图用于区分 **已经能用**、**已经实现但仍需 Windows 实机验收**、**目前只有入口** 和 **尚未实现** 的功能，方便后续继续在新对话里直接接手。

| 模块 / 功能 | 状态 | 说明 |
|---|---|---|
| `run_windows.vbs → Python Core → Godot` | 已可用 | 单入口启动链已经跑通 |
| localhost WebSocket / JSON | 已可用 | 只绑定 `127.0.0.1` |
| SQLite 游戏库 | 已可用 | 数据根目录为 `%LOCALAPPDATA%\G3` |
| 顶部 XMB 模块切换 | 已可用 | 当前中文化为：游戏 / 电影 / 漫画 / 音乐 / 搜索 / 系统 |
| Games 浏览态大封面轮播 | 已实现，待实机验收 | v0.6.1.6：主盒居中浏览，邻近盒数量减少，进入 Preview 后主盒左移并放大 |
| 真实 3D GLB 游戏盒管线 | 已可用 | 标准高盒 `standard_tall.glb` 已接入；中文节点接口 `盒体` / `封面正面`；旧模型 / 占位模型仅作回退 |
| 亚克力半透明盒体材质 | 已实现，待实机验收 | v0.6.1.6：盒体/书脊改为透明非金属 clearcoat 材质；封面维持独立无光照印刷层 |
| 产品灯光 / 聚焦实体盒查看 | 已实现，待实机验收 | 主盒聚焦放大 `2.18`；悬停约 `±12° / ±4°`；拖动检视 `±55° / ±14°` |
| Preview 图片 / GIF / 视频 / 音频 | 已实现，待实机验收 | 有媒体时直接显示内容；无媒体时显示“暂无预览素材”；新增文字/媒体入场动画 |
| Preview 点击返回规则 | 已实现，待实机验收 | 空白区域可返回；详情区文字/媒体点击不再误返回 |
| 右键游戏管理菜单 | 已实现，待实机验收 | 当前条目：启动 / 预览 / 编辑资料 / 媒体素材 / 启动设置 / 移除收藏；菜单已中文化且改为自绘 Panel |
| Launch Profile 编辑器 | 已实现，待实机验收 | Direct / Launcher / Emulator |
| 启动器与真实游戏进程分离 | 已实现，待实机验收 | `launch_exe` 启动，`monitor_exe` 监控；WinError 740 自动 UAC |
| 游戏退出后回到 G3 | 已实现，待实机验收 | 游戏会话开始时最小化并暂停渲染；退出后恢复 G3 并更新游玩时间 |
| 编辑资料 | 已实现，待实机验收 | 标题 / 平台 / 开发商 / 发行商 / 发行年份 / 标签 / 简介 / 收藏备注 |
| System 页面 | 已可用 | 添加游戏、窗口切换、退出 G3；支持 `Ctrl+Q` |
| 性能保守化设置 | 已实现，待实机验收 | 默认 `60 FPS` 上限、轻量 `MSAA 3D`、弱化背景 shader、收敛 SSAO |
| 媒体素材管理 | 仅入口 | UI 待补齐 |
| 移除收藏 | 仅入口 | 安全确认流程待补齐 |
| 电影 / 漫画 / 音乐 / 搜索 | 仅入口 | 当前先集中做完整 Games Vertical Slice |
| 完整主题选择 / 编辑器 | 未实现 | Theme manifest 基础已存在 |

## 当前基础结构（交接版）

### 1. 前端

- `g3_frontend/`
- 技术：Godot 4.7.2（当前工程目标仍按 4.7）
- 关键脚本：
  - `scripts/main.gd`：主界面、XMB、后端通讯、预览/启动/状态恢复
  - `scripts/game_carousel.gd`：Games 轮播、选中态、聚焦态、点击/右键/拖动
  - `scripts/game_case_3d.gd`：GLB 游戏盒实例、材质、封面绑定、悬停/拖动旋转
  - `scripts/preview_panel.gd`：右侧详情 + 媒体预览 + 音频
  - `scripts/manage_menu.gd`：右键管理面板
  - `scripts/launch_profile_dialog.gd`：启动设置
  - `scripts/game_metadata_dialog.gd`：编辑资料
- 关键资源：
  - `assets/models/cases/standard_tall.glb`
  - `shaders/ambient.gdshader`

### 2. 后端

- `g3_core/`
- 技术：Python 3.11 + SQLite + localhost WebSocket
- 关键模块：
  - `backend_app.py`：命令路由 / 事件广播
  - `repository.py`：库与资料持久化
  - `services/game_runtime.py`：游戏启动、WinError 740 / UAC、进程会话等待
  - `services/process_monitor.py`：监控 `monitor_exe`
  - `schema.sql`：数据库结构（已含 `game_metadata`）

### 3. 启动链

- `run_windows.vbs`：用户可见入口
- `run_windows_debug.bat`：调试入口
- `g3_launcher/`：负责启动 Python Core 和 Godot 前端

## 建议下一步

1. Windows 实机验收 v0.6.1.6：重点看材质观感、GPU 占用、最小化/恢复、预览点击规则。
2. 如果浏览态仍不够理想，可继续做“显示模式切换”（例如海报墙 / 中央大盒 / 沉浸轮播）。
3. 媒体素材管理与移除收藏，是当前右键菜单里最明确的两个待补入口。
4. Movies / Comics / Music / Search 暂不扩写，保持入口即可，先把 Games slice 打磨稳。

## 验收样本（保留）

- 雨世界：验证最简单的 Direct EXE 启动、计时、退出返回。
- 艾尔登法环 + Mod Engine：验证 Launcher / monitor_exe 分离。
- 寂静岭 / PS1 模拟器：验证 Emulator + `{content}` 内容路径。
- 战神系列 / RPCS3：验证更复杂的模拟器启动参数与游戏会话监控。
