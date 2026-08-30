# G3 功能地图（Games Vertical Slice）

这份地图用于区分 **已经能用**、**已经实现但仍需 Windows 实机验收**、**目前只有入口** 和 **尚未实现** 的功能。以后测试 G3 不再依赖“看到什么就试什么”。

| 模块 / 功能 | 状态 | 说明 |
|---|---|---|
| `run_windows.vbs → Python Core → Godot` | 已可用 | 单入口启动链已经跑通 |
| localhost WebSocket / JSON | 已可用 | 只绑定 `127.0.0.1` |
| SQLite 游戏库 | 已可用 | G3 使用全新 `%LOCALAPPDATA%\G3` 数据根目录 |
| 顶部 XMB 模块切换 | 已可用 | Games / Movies / Comics / Music / Search / System |
| Classic Cyan / GPU 动态背景 | 已可用 | 当前默认主题 |
| 添加 Direct EXE 游戏 | 已可用 | 适合雨世界这类直接 EXE |
| 真实 3D GLB 游戏盒管线 | 待实机验收 | 正式加载 `game_case.glb`，无最终模型时用真实 3D 占位 GLB |
| Carousel 附近实例虚拟化 | 待实机验收 | 最多保留附近约 9 个盒子实例，大库不会全部渲染 |
| 单击游戏盒预览 | 待实机验收 | Preview 框架、图片/GIF/视频/音频管线已存在 |
| 右键游戏管理菜单 | 待实机验收 | 启动 / 预览 / 编辑资料 / 媒体素材 / 启动设置 / 移除收藏 |
| Launch Profile 编辑器 | 待实机验收 | Direct / Launcher / Emulator |
| 启动器与真实游戏进程分离 | 待实机验收 | `launch_exe` 负责启动，`monitor_exe` 负责真正游戏会话 |
| 游戏退出后回到 G3 | 待实机验收 | 真游戏进程消失后恢复 G3 并更新游玩时间 |
| 编辑资料 | 仅入口 | 右键菜单已有入口，编辑器待补齐 |
| 媒体素材管理 | 仅入口 | 右键菜单已有入口，管理 UI 待补齐 |
| 移除收藏 | 仅入口 | 右键菜单已有入口，安全确认流程待补齐 |
| Movies / Comics / Music / Search | 仅入口 | 当前先集中做完整 Games Vertical Slice |
| 完整主题选择 / 编辑器 | 未实现 | Theme manifest 基础已存在 |

## 四个游戏验收样本

### 1. 雨世界

- 类型：Direct
- 启动程序：`RainWorld.exe`
- 监控程序：同一个 `RainWorld.exe`
- 目标：验证最简单的直接 EXE 启动、计时、退出返回。

### 2. 艾尔登法环 + Mod Engine

- 类型：Launcher
- 启动程序：Mod Engine 启动入口
- 监控程序：原版 `eldenring.exe`
- 目标：验证“启动器退出/常驻与真正游戏进程不是同一个程序”的情况。

### 3. 寂静岭 / PS1 模拟器

- 类型：Emulator
- 启动程序：PS1 模拟器 EXE
- 游戏内容：CUE/BIN/CHD 等实际游戏内容路径
- 参数：可使用 `{content}` 占位符
- 监控程序：模拟器 EXE
- 目标：验证 emulator + ROM/content path。

### 4. 战神系列 / RPCS3

- 类型：Emulator
- 启动程序：RPCS3
- 游戏内容：对应游戏目录/EBOOT/启动目标
- 参数：按 RPCS3 实际命令行配置，可使用 `{content}`
- 监控程序：RPCS3 EXE
- 目标：验证更复杂的模拟器启动参数与游戏会话监控。

## 当前验收主链

```text
G3 启动
→ Games 真实 3D 收藏
→ 选择游戏
→ 单击 Preview / 右键管理
→ Launch Profile
→ 启动 launch_exe
→ 等待 monitor_exe
→ 真正游戏会话开始
→ monitor_exe 退出
→ G3 恢复前台
→ 更新游玩时间
```
