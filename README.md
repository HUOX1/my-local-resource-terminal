# G3

G3 是一个运行在 Windows 上的私人数字收藏终端。当前版本 `v0.6.1.9.2` 继续聚焦 **Games Vertical Slice**：
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

v0.6.1.9.2 的前端重点：

- 四槽继续以 G1 为参考：中心约 20% / 45.5% / 71% / 89%，近邻盒显著放大，使盒子之间接近/轻微压边，而不是四个孤立缩略图
- 副盒增加槽位级亮度与朝向层级，不再只靠尺寸变化；右侧盒会朝相机收角，降低刺眼书脊暴露
- 滚轮轨道改为串行过渡 + 输入队列；进入/退出点按真实窗口边缘计算，避免多个离场盒在屏内形成“幽灵”
- 保留普通可缩放 / 可最大化窗口行为，但移除 Windows 原生标题栏，改用随 G3 主题着色的自绘标题栏；支持拖动、八方向缩放、最小化、最大化/还原、关闭
- 修复右下导航 hover 后再点击会立即收起的问题；导航柄点击现在始终保持展开，离开导航区域后才延迟收起
- Preview 主盒保持约 26% 窗口宽度锚点；未选中盒维持可读背景尺度
- 最右槽 scale 从 1.55 提升到 2.15；离场盒不再二次缩到 0.62，只沿屏幕边缘滑出，减少滚动时的突缩/鬼畜感
- 右上操作/错误提示显示 4 秒后用 0.35 秒淡出，不再永久挂在界面上

## 文档

- `docs/v0.6/G3_Games_Vertical_Slice_Design.md`
- `docs/v0.6/G3_Games_Vertical_Slice_Plan.md`
- `docs/v0.6/Phase1_Feature_Status.md`
- `docs/v0.6/G3_Handoff_v0.6.1.9.2.md`
- `docs/development-logs/G3_v0.6_Development.md`
