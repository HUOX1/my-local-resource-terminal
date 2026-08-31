# G3 v0.6.1.6 Patch Notes

## 这次更新做了什么

- Games 浏览态调整为更接近 G1 直观感受的“大封面居中轮播”。
- 聚焦态主盒进一步放大，拖动检视范围扩大。
- 盒体材质向“亚克力半透明”方向推进。
- Preview 右侧详情区补上点击边界和文字/媒体入场动画。
- 顶部 XMB / 右键管理 / System 入口继续中文化；System 新增退出 G3，支持 `Ctrl+Q`。
- 项目默认 `60 FPS` 上限、轻量 `MSAA 3D`，背景 shader 简化并去掉 glow，进一步收敛 GPU 开销。
- 日志、功能地图与交接文档已同步更新。

## 关键交接文档

- `docs/v0.6/Phase1_Feature_Status.md`
- `docs/v0.6/G3_Handoff_v0.6.1.6.md`
- `docs/development-logs/G3_v0.6_Development.md`

## 测试

- 命令：`PYTHONPATH=. pytest -q`
- 结果：`114 passed`
