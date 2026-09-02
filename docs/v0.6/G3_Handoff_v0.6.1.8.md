# G3 v0.6.1.8 交接摘要

## 当前方向

G3 的 Games 视觉语言从 v0.6.1.8 起正式转向“收藏本身就是界面”。G1 作为成熟设计参考，但 G3 保留 Godot 真 3D、实时灯光、材质与 GPU 动态背景能力。

## 浏览态核心规则

- 最多显示 4 个游戏盒。
- 主盒固定视觉第二槽。
- 槽位故意不对称：左远 / 主盒 / 右近 / 右边缘。
- 浏览态不显示标题、平台、时间。
- 主盒浏览时就足够大；副盒逐级缩小、压暗、推远。
- 轨道有明确方向，盒子从对应屏幕边缘进入/退出，不允许 wrap 后跨屏飞行。

## 聚焦态

- 主盒维持大尺寸并左下移。
- 右侧资料与 Preview 保留完整呼吸距离。
- 后台盒仅作环境层，不参与命中。
- 点击详情区不返回；点击真实空白可返回。

## UI 外壳

- 顶部文字导航隐藏。
- 右下角隐藏式图标抽屉承担顶级导航。
- 后端状态、FPS、操作说明、功能地图集中到 System。
- `Ctrl+Q` 与 System“退出 G3”继续有效。

## 启动状态

- `default_start_section` 决定启动板块，默认 `games`。
- 不再读取 `last_section` 作为启动首页。
- `last_item_id` 仍用于恢复上次选中的游戏。

## 本轮关键文件

- `g3_frontend/scripts/game_carousel.gd`
- `g3_frontend/scripts/navigation_drawer.gd`
- `g3_frontend/scripts/main.gd`
- `g3_core/settings.py`
- `g3_frontend/themes/classic_cyan/theme.json`
- `docs/superpowers/specs/2026-08-31-g3-games-clean-ui-track-design.md`
- `docs/superpowers/plans/2026-08-31-g3-v0618-clean-ui-track.md`

## 下一轮实机重点

1. 四槽尺寸与位置是否达到 G1 那种视觉冲击力。
2. 连续滚轮时左右边缘的进入/退出叙事是否正确。
3. 右下抽屉是否足够隐蔽又容易发现。
4. 深青黑 Classic Cyan 是否真正把主盒从背景里托出来。
5. 聚焦主盒与右侧文字/媒体之间是否已经足够透气。
