# G3 v0.6.1.9.2 Patch Notes — Edge Motion / Theme Window Chrome / Feedback Lifetime

## 本轮实机修复

1. **边缘游戏盒突缩 / 鬼畜**
   - 最右槽 scale 从 `1.55` 提升到 `2.15`，降低右近槽 `2.85 → 1.55` 的断崖式缩放。
   - 离场盒不再额外强制缩到 `0.62`，保持当前槽尺度向真正屏外滑出后回收。
   - 保留 v0.6.1.9 的串行 transition、queued scroll steps 与动态 offscreen 计算。

2. **右下导航点击无响应**
   - 根因：hover 先 `_reveal()`，随后 click 调 `_toggle_drawer()` 会立即反向 `_hide()`。
   - 现在 handle 的 hover 与 click 都只调用 `_reveal()`；离开 handle / drawer 后再延迟收起。

3. **主题一致的自绘窗口栏**
   - 默认仍是可缩放 Windowed 窗口，但 `borderless=true`，不再显示 Windows 原生标题栏。
   - 新增 `window_chrome.gd`：主题色标题栏、拖动、双击最大化/还原、最小化、最大化/还原、关闭。
   - 新增八方向 resize hit area，通过 Godot `Window.start_resize()` 保留自由调整窗口大小。
   - 游戏启动/退出继续保存并恢复进入游戏前的窗口模式、尺寸和位置。

4. **右上操作提示自动消失**
   - 操作/错误提示保持 `4.0s`，随后 `0.35s` 淡出并清空。
   - 新提示出现会取消上一轮淡出计时，避免旧提示把新提示提前清掉。

## 版本

- `0.6.1.9.2`
