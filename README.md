# G3

G3 是一个运行在 Windows 上的私人数字收藏终端。当前 v0.6.1 聚焦 Games Vertical Slice：
Godot 4.7.2 负责 GPU/3D 前端，Python Core 负责 SQLite、素材、启动配置、进程监控和本地 WebSocket。

## 启动

1. 运行 `setup_windows.bat`
2. 双击 `run_windows.vbs`
3. 调试时运行 `run_windows_debug.bat`

首次启动如果找不到 Godot，会要求选择 Godot 4.7.2 Standard 可执行文件。

## 当前数据目录

`%LOCALAPPDATA%\G3\`

G3 不读取旧 v0.5 / v0.6 Phase1 的测试数据库或设置。

## 3D 游戏盒

最终模型路径：

`g3_frontend/assets/models/game_case.glb`

没有该文件时会使用内置的真实 3D placeholder GLB。建模规范见：

`g3_frontend/assets/models/README.md`

## 文档

- `docs/v0.6/G3_Games_Vertical_Slice_Design.md`
- `docs/v0.6/G3_Games_Vertical_Slice_Plan.md`
- `docs/v0.6/Phase1_Feature_Status.md`
- `docs/development-logs/G3_v0.6_Development.md`
