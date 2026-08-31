# G3

G3 是一个运行在 Windows 上的私人数字收藏终端。当前版本 `v0.6.1.6` 继续聚焦 **Games Vertical Slice**：
Godot 4.7.2 负责 GPU/3D 前端，Python Core 负责 SQLite、素材、启动配置、进程监控和本地 WebSocket。

## 启动

1. 运行 `setup_windows.bat`
2. 双击 `run_windows.vbs`
3. 调试时运行 `run_windows_debug.bat`

首次启动如果找不到 Godot，会要求选择 Godot 4.7.2 Standard 可执行文件。

## 当前数据目录

`%LOCALAPPDATA%\G3`

G3 不读取旧 v0.5 / v0.6 Phase1 的测试数据库或设置。

## 3D 游戏盒

当前正式标准高盒使用中文节点接口 `盒体` / `封面正面`；G3 会自动发现游戏目录中的 `cover.png/.jpg/.jpeg/.webp`，并在运行时绑定到 `封面正面`。正式资源缺失时仍保留旧模型 / placeholder 回退。建模规范见：

`g3_frontend/assets/models/README.md`

v0.6.1.6 的前端重点：

- 浏览态回到更接近 G1 的大封面居中轮播
- Preview 主盒更大，右侧详情区更完整
- 盒体尝试推进到亚克力半透明方向
- Preview 详情点击边界与入场动画更新
- 默认 60 FPS + 轻量 MSAA，背景 shader 进一步收敛

## 文档

- `docs/v0.6/G3_Games_Vertical_Slice_Design.md`
- `docs/v0.6/G3_Games_Vertical_Slice_Plan.md`
- `docs/v0.6/Phase1_Feature_Status.md`
- `docs/v0.6/G3_Handoff_v0.6.1.6.md`
- `docs/development-logs/G3_v0.6_Development.md`
