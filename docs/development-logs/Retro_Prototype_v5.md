# Retro Prototype v5 — v0.5.0.4

## STATUS

FOCUS / PACKAGE POLISH BASELINE.

本轮基于 v0.5.0.3 的实际截图反馈，不扩大功能范围，只修正盒体几何与单击聚焦态构图。

## ADAPTIVE FRONT FACE

- 平台 Package Profile 不再强制规定真实封套的正面宽高比。
- 平台 Profile 继续负责 family / depth / spine / material。
- 存在真实封面时，盒体正面宽高比直接跟随图片宽高比。
- 正面内缩边框使用等比例 inset，避免因为内边距重新制造上下/左右黑边。
- 无封面时才回退到平台 Profile 的 nominal face ratio。

目标：FULL COVER，封面不因模板比例被裁切或 letterbox。

## FOCUS COMPOSITION

- 单击聚焦态主盒放大幅度由约 +25% 收敛到约 +12%。
- 主盒中心下移到更接近窗口视觉中线的位置。
- 右侧简短文字区保持原结构，使左侧藏品与右侧文字视觉重量更匹配。
- MORE 展开态通过独立 scale / y 补偿，尽量保持 v0.5.0.3 中相对满意的主盒存在感。

## BACKDROP DIM

- 单击聚焦态增加独立背景压暗层。
- 压暗层绘制在动态背景之后、Showcase 之前，因此不会把当前盒与右侧文字一起压灰。
- 目的不是做黑色遮罩效果，而是提高动态波带与聚焦内容之间的层次差。

## SCOPE

本轮不重做 MORE 详情板、不调整设置抽屉、不改变 Wide Rail 结构、不修改数据库 schema。
