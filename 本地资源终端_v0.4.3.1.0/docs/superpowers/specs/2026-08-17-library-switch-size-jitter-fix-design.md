# v0.3.3.1 切库窗口尺寸弹动修复设计

日期：2026-08-17
基线：v0.3.3

## 问题

v0.3.3 为了让用户在本次运行中缩放窗口后，切换“影片/游戏”仍保持当前窗口尺寸，采用了：

1. 切换前记录 `self.size()`；
2. 完成页面/控件切换；
3. `QTimer.singleShot(0, ...)` 在下一轮事件循环中 `resize()` 回原尺寸。

当窗口接近最小尺寸时，Qt 布局可能在步骤 2 后先按新页面的 size hint / minimum hint 临时调整窗口，步骤 3 再把窗口缩回，因此用户可见一次“先弹大再缩回”的抖动。

## 修复

切库期间把主窗口临时固定在切换前的当前尺寸：

1. 保存当前尺寸、原 minimumSize、原 maximumSize；
2. `setFixedSize(runtime_size)`；
3. 同步完成影片/游戏切换、控件重配置、catalog 刷新；
4. 在 `finally` 中恢复原 minimumSize / maximumSize；
5. 不使用延迟 `QTimer.singleShot` 事后纠正尺寸。

由于锁定和解锁都发生在同一同步调用中，窗口不会先绘制一个中间尺寸；调用结束后用户仍可正常拖动窗口大小。

## 不改变

- 默认启动窗口仍为 1320×840；
- 窗口尺寸仍然只在当前运行期间保留，不写 settings；
- 不改变最小窗口尺寸策略；
- 不修改 Movie/Game 数据、计时、截图、详情页、编辑页；
- 不处理单实例功能（另行安排）。

## 验证

- 源码回归测试要求切库使用同步固定尺寸策略；
- 不再存在 `_restore_runtime_size()` + `QTimer.singleShot(0, ...)` 的事后恢复；
- 全量 pytest、Python 3.11 compatibility、compileall 通过；
- 模拟把补丁覆盖在 v0.3.3 完整包上后，v0.3.3 原测试继续通过。
