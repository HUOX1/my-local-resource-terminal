# Identity Motion v1

## 状态

Flat Pro 默认皮肤 Identity 进入动画已冻结。

## 目标

表达用户点击身份头像后，从 Identity 页面进入 Main Shell 的过程。

设计方向： - 扁平化 UI 风格 - 保持简洁、轻量 - 保留一定仪式感 -
不使用重特效（炉石式头像砸入、能量扩散等留给未来特殊皮肤）

## 动画流程

### 01 Identity Start

初始状态。

-   身份页面完整显示
-   头像、用户名、身份区域正常
-   主界面隐藏

### 02 Avatar Press

用户点击头像。

变化： - 头像缩小 - 轻微下移 - 其他身份元素透明度降低

目的： 表现按下反馈。

### 03 Avatar Release

点击释放。

变化： - 头像反弹放大 - 身份信息继续淡出 - 主界面元素开始显现

目的： 表现身份确认。

### 04 Avatar Launch

主转场阶段。

变化： - 主界面完全出现 - 中央头像保持视觉焦点 - Identity 页面继续退出 -
头像进行动态变化

目的： 完成 Identity 到 Main Shell 的视觉转换。

### 05 Avatar Transfer

头像转移完成。

变化： - 中央头像消失 - 左上用户区域准备接收头像

目的： 建立身份落点。

### 06 Avatar Activation

左上头像激活。

变化： - 小头像出现 - 放大 - 轻微旋转

目的： 表现身份进入系统后的激活感。

### 07 Avatar Settled

最终稳定状态。

变化： - 头像恢复正常尺寸 - 进入 Main Shell 常态

目的： 结束动画。

## Motion 原则

-   点击行为必须产生明确反馈。
-   Identity 到 Main Shell 是连续过程，不是页面切换。
-   中央头像与左上头像代表同一个身份对象。
-   默认 Flat Pro 保持克制。
-   高表现力特效皮肤以后单独设计。

## 实现提示

代码实现时不要移动整个头像组件。

应拆分： - Avatar 内容 - Avatar Slot / Frame - Floating Avatar 临时层

动画逻辑： Avatar Content 从 Identity 状态转移到 Main Shell 身份槽。

## 后续

此动画作为 Flat Pro Identity Motion 规范。

下一阶段进入软件开发实现。
