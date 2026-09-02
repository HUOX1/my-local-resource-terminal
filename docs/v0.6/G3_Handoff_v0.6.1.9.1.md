# G3 v0.6.1.9.1 交接摘要

## 本轮针对的实机问题

1. v0.6.1.9 四盒中心位置虽接近参考，但近邻盒过小，造成四个“孤岛”，没有 G1 的连续队列感。
2. Preview 未选中盒缩得过小；主盒与右侧详情区距离过近。
3. 右下导航柄仍不可发现/不可触发。

## 当前参数

- Browse screen X：`0.20 / 0.455 / 0.71 / 0.89`
- Browse scale：`2.70 / 3.35 / 2.85 / 1.55`
- Browse yaw：`6 / 0 / -5 / -7` degrees
- Preview selected X：`0.26`
- Preview selected scale：`3.42`
- Preview background scale：`1.04–1.28`

## 保留不回退的修复

- 四槽 / 主盒第二槽。
- viewport-relative 位置计算。
- 真正屏外的进入/退出位置。
- 串行 transition + queued scroll steps。
- 普通可缩放 Windows 窗口，游戏返回恢复原窗口状态。

## Windows 实机重点

1. 浏览态近邻盒是否已经达到 G1 那种“大、靠近、层级明显但不拥挤”的感觉。
2. 快速滚轮是否仍无第五盒幽灵。
3. Preview 背景盒是否足够可读，同时不会压过详情 UI。
4. Preview 主盒与文字区是否留下合适空隙。
5. 右下 `≡` 是否始终可见，hover 与 click 是否都能展开导航。
