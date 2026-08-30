# v0.6 主机终端架构设计

## 1. 目标

v0.6 不再继续扩展 v0.5 的 QWidget / QPainter Retro Overlay，而是建立一套全新的 Windows 主机终端架构。

核心定位不是“带动画的桌面资源管理器”，而是：

> 运行在 Windows 上的私人数字收藏主机终端。

它吸收 PSP / PS3 XMB 的克制、主题化和系统氛围感，以及 Wii 时代游戏 Loader 的实体收藏展示记忆，但不机械复刻任何一台主机界面。

v0.5 作为原型机和历史参考保留；v0.6 的前端、数据结构、设置结构和运行时状态从零开始，不读取或迁移 v0.5 的测试数据库与设置。

## 2. 平台与技术栈

第一阶段仅面向 Windows。

- 前端：Godot 4.7.x Stable
- UI/动画：Godot Control / 2D / 3D / Animation / Shader / GPU 粒子
- 后端：Python 3.11+
- 数据库：SQLite，全新 v0.6 schema
- 前后端通信：仅监听 `127.0.0.1` 的本机 WebSocket + JSON
- 用户入口：继续使用仓库根目录的 `run_windows.vbs`
- 默认显示：无边框最大化窗口

`run_windows.vbs` 的使用方式不改变。最终它负责启动 Python Core 和 Godot Frontend；用户不需要直接管理两个进程。

## 3. 总体架构

```text
run_windows.vbs
        |
        v
Terminal Launcher
        |
        +-------------------+
        |                   |
        v                   v
Python Core             Godot Frontend
CPU / 业务              GPU / 表现
        |                   |
        |  localhost WS     |
        +<----------------->+
```

### 3.1 Python Core 负责

- SQLite 数据库
- 资源库扫描与索引
- 游戏启动与进程监控
- 游戏游玩时间记录
- 影片外部播放器启动
- 漫画/音乐外部程序配置与启动
- 元数据与媒体素材索引
- 设置持久化
- 主题包索引
- 终端状态持久化
- 统一搜索
- 日志
- Godot 前端所需的数据查询与命令执行

### 3.2 Godot Frontend 负责

- XMB 风格顶层导航
- Games / Movies / Comics / Music / Search / System 场景
- 3D 实体盒、海报、漫画墙、专辑封面
- Hover / Focus / Carousel
- 页面转场与启动/返回动画
- Shader 波浪
- `△ ○ × □` 动态符号
- 粒子、Glow、材质、高光、视差
- 图片 / GIF / 视频预览
- 预览音频与主题背景音乐混音
- 鼠标、键盘、手柄输入呈现
- FPS / Backend 状态等开发信息

### 3.3 边界原则

Python 决定“发生什么”，Godot 决定“如何显示、如何运动”。

不得把 SQLite、文件扫描、路径发现、业务规则写进 Godot；也不得让 Python 按帧计算 UI 动画、盒体 Transform、背景波浪或粒子。

## 4. 产品视觉语言

v0.6 的设计目标是“老 PlayStation 系统美学的现代延伸”，而不是 Steam 卡片墙或 PS5 风格的大型信息磁贴。

核心特征：

- 大量留白
- 轻量图标与文字
- 背景长期流动但不过度抢眼
- 主题是一级系统功能
- 内容通过空间、焦点、材质和运动建立层级
- 3D 用于增强实体收藏感，而非把整个界面做成夸张 3D 场景

顶层大模块必须拥有统一设计的图标；默认不使用 Emoji。图标允许被主题包替换。

## 5. 顶层导航

默认顶层：

```text
GAMES    MOVIES    COMICS    MUSIC    SEARCH    SYSTEM
```

不设置 FAVORITES。进入并长期留在终端中的内容本身就是收藏。

导航理念继承 XMB：顶层横向切换大类，但各大类的内容展示方式根据媒介本身设计，不强制统一成同一种卡片组件。

### 5.1 启动恢复

启动时恢复：

- 上次停留的大模块
- 上次选中的资源
- 相应浏览位置

不恢复：

- 已展开的预览状态
- 正在播放的预览视频
- 正在播放的预览音频

因此重新启动不会突然发声或直接进入内容预览。

## 6. Games：旗舰模块

Games 是 v0.6 第一阶段的旗舰模块和其他模块的体验基准。

### 6.1 浏览态

- 单排横向 Carousel
- 中央始终存在一个“主盒”
- 主盒就是当前选中游戏，不需要额外点击确认选择
- 两侧盒子是候选项
- 整体排列保持克制、规整
- 3D 感主要来自单个游戏盒真实厚度、侧脊、材质和光照
- 不采用整排夸张弧形 3D Carousel

### 6.2 鼠标优先

PC 是主要运行环境，输入优先级：

1. 鼠标
2. 键盘
3. 手柄

三种输入最终映射到统一 Selection / Focus 状态。

鼠标行为：

- 滚轮：横向切换游戏，新的中央主盒自动成为选中项
- 单击侧盒：该盒平滑移动到中央主位
- 单击主盒：进入当前页面内的预览态
- 双击主盒：直接启动游戏
- 主盒 Hover：轻微抬升、缩放、鼠标位置驱动的 3D 倾斜和材质高光

键盘和手柄不复制一套独立 UI，仅提供同等导航能力。

## 7. Games 预览态

预览不跳转到独立 Scene，而是在当前页面中完成空间重排。

### 7.1 布局

进入预览后：

- 主盒从中央平滑移动到左侧
- 右侧出现游戏名称、简短信息、媒体预览与快捷操作
- 原 Carousel 的其他游戏盒不完全消失
- 其他盒子缩小、后退、降低亮度/透明度，保留“收藏架仍在”的空间提示

### 7.2 连续浏览

预览态下滚轮继续切换上一/下一款游戏，不退出预览。

切换时：

- 左侧主盒替换
- 后方收藏队列继续移动
- 标题与文本轻量过渡
- 媒体区交叉淡化
- 预览态保持不变

### 7.3 预览媒体

素材优先级：

1. 用户手动指定
2. 自动发现
3. 程序生成默认展示

支持：

- Cover
- Background
- Screenshots
- Preview Video
- Preview GIF / 动图
- Preview Audio
- Logo

预览策略：

- 有视频：自动播放
- 有 GIF：自动循环
- 有截图：自动轮播/轻微缓动
- 只有静态背景：保持克制的呼吸/视差
- 无素材：使用封面和当前主题生成默认展示

快速滚动时不立即启动重型媒体解码；用户停留约 300–500ms 后再启动对应预览。

### 7.4 预览音频

允许视频/动态内容自动带声音。

System > Audio 至少提供：

- Preview Audio On/Off
- Preview Volume
- Preview Auto Play

切换游戏时旧预览快速淡出，新预览渐入。

## 8. 游戏启动与返回

双击主盒或预览态中的 PLAY：

```text
Godot Launch Transition
        ↓
Python 启动游戏进程
        ↓
Godot 隐藏/暂停高频渲染
        ↓
Python 监控游戏并计时
        ↓
游戏退出
        ↓
Godot 恢复前台
        ↓
Return Transition
        ↓
恢复原分类、原游戏位置
```

终端在外部程序运行期间不退出。

对 Games 而言，这是完整沉浸闭环，因此第一阶段优先把这条链做到稳定。

## 9. Movies / Comics / Music 的长期展示方向

Phase 1 不实现完整功能，但数据模型、模块入口和架构必须允许自然扩展。

### 9.1 Movies

- 电影海报或 DVD / Blu-ray 风格实体盒
- 终端负责收藏、浏览、预览、元数据与进入内容
- 第一阶段后续继续调用 PotPlayer 等外部播放器
- 播放器退出后终端自动恢复到原位置

### 9.2 Comics

- 核心视觉方向：多排漫画封面/实体收藏墙
- 作品进入后可按卷展示
- 初期调用外部漫画阅读器
- 长期可考虑 Godot 内置图片型漫画阅读模式

### 9.3 Music

- 专辑封面 / 唱片式浏览
- 初期允许调用外部播放器
- 长期可考虑内置音频播放，使音乐在切换模块时继续播放
- 未来允许主题 Shader 对音乐做非常克制的响应

## 10. Search

SEARCH 是全终端统一搜索，而非当前模块内搜索。

同时搜索：

- Games
- Movies
- Comics
- Music

结果按模块分组展示。

统一搜索由 Python Core 执行，Godot 仅负责查询请求与结果呈现。

## 11. 全新 v0.6 数据模型

v0.6 不读取、迁移或兼容 v0.5 的测试数据库和设置。

目标是让功能和数据从新结构上自然生长，避免继承 Flat/Retro 原型时代字段与兼容债务。

### 11.1 核心 LibraryItem

建议统一核心字段：

- id
- media_type
- title
- sort_title
- description
- cover_asset_id
- background_asset_id
- created_at
- updated_at

媒介特有信息进入各自扩展表，而不是把所有字段塞进单张通用表。

### 11.2 Game 扩展

至少包括：

- executable_path
- launch_args
- working_directory
- platform
- playtime_seconds
- last_played_at
- installed_state

### 11.3 MediaAsset

统一管理：

- cover
- screenshot
- background
- preview_video
- preview_gif
- preview_audio
- logo

记录 owner、kind、path、priority、source（manual/auto/generated）等信息。

### 11.4 新数据目录

v0.6 使用新的命名空间，与原型机物理隔离。

```text
LocalResourceTerminal/
└─ v0.6/
   ├─ library.db
   ├─ assets/
   ├─ cache/
   ├─ themes/
   ├─ logs/
   └─ settings.json
```

## 12. 设置系统

不继承 v0.5 中与 QWidget/Flat UI 绑定的字段，例如 `flat_pro`、sidebar 宽度、旧 movie view mode 等。

新设置按领域组织：

```text
TerminalSettings
├─ display
├─ audio
├─ input
├─ themes
├─ libraries
├─ external_apps
└─ startup
```

至少支持：

- Display Mode：Borderless / Windowed / Fullscreen
- Monitor
- Preview Audio
- Preview Volume
- Theme Music
- Restore Last Section
- Restore Last Item
- 外部播放器/阅读器/音乐软件配置

## 13. 主题系统

主题从 v0.6 第一阶段就是一级功能，不作为 UI 完成后的附加功能。

主题应是本地、可保存、可导入导出的包，不依赖远程商店。

主题可控制：

- 背景颜色
- Shader 参数
- 波浪数量/速度/幅度
- `△ ○ × □` 数量、透明度、运动参数
- 粒子
- Glow
- UI Accent
- 顶层图标
- 字体（未来）
- 导航音效
- 系统提示音
- 背景音乐
- 转场参数

### 13.1 背景音乐接口

主题允许没有背景音乐。

若存在音乐，至少支持：

- Music Path
- Music Volume
- Loop
- Fade In
- Fade Out
- Preview Ducking

当游戏预览开始发声时，主题音乐自动降低；预览结束后恢复。

### 13.2 可编辑参数

优先把视觉参数暴露给 Godot Inspector 或 System > Themes，而不是写死在脚本中，使非代码用户可以调节：

- Wave Speed
- Wave Strength
- Symbol Amount
- Symbol Opacity
- Glow Strength
- Particle Amount
- Music / Sound 路径和音量

长期目标是提供终端内主题编辑与 Export Theme。

## 14. Ambient GPU 渲染

Godot Spike 已验证目标方向：动态波浪和 36 个符号可以在 GPU Shader 路径中低成本运行。

正式版本继续遵循：

- 动态背景不得回到 Python/QPainter 式按帧绘制
- 波浪使用 Shader 或等价 GPU 路径
- 36 个符号使用 GPU 友好的批处理/Shader/Particles 实现
- CPU 不逐个驱动符号的位置、旋转和透明度
- UI 动画优先使用 Godot Transform / Animation 系统

## 15. 本机通信协议

Godot 和 Python 通过本机 WebSocket + JSON 通信，仅绑定 `127.0.0.1`。

该接口不是 NAS/网页管理服务，不对局域网或互联网开放。

示例：

```json
{"type":"game.launch","id":42}
```

Python 返回：

```json
{"type":"game.launch.started","id":42,"pid":1234}
```

协议必须：

- 有明确 message type
- request/response 可关联
- 错误使用结构化错误消息
- 后端断线时 Godot 显示可理解状态
- 不允许 Godot 直接访问 SQLite

## 16. 进程生命周期

### 16.1 启动

`run_windows.vbs` 保持用户入口不变。

目标启动顺序：

1. 启动 Terminal Launcher / Python Core
2. Python Core 初始化数据目录、数据库、日志、本机 WebSocket
3. 启动 Godot Frontend
4. Godot 连接 Backend
5. Backend Ready 后进入终端首页

### 16.2 外部应用运行中

- Godot 不退出
- 主窗口隐藏或暂停高频渲染
- Python 继续监控外部进程
- 不需要背景继续 60fps 空转

### 16.3 返回

外部进程结束后：

- 恢复 Godot 窗口
- 拉回前台
- 恢复之前的分类和资源位置
- 播放 Return Transition
- 刷新游玩时间/最近使用等状态

## 17. 开发模式与日志

由于前端大量可视化调试将在 Godot 编辑器中进行，v0.6 应自带轻量 Dev Panel。

至少显示：

- FPS
- Backend Connected
- Backend Port
- 当前 Scene / Section
- Selected Item ID
- Preview State
- External Process State

开发动作可包括：

- Reload Data
- Fake/Test Library
- Toggle Ambient
- Toggle Preview
- Open Logs

Python Core 日志统一写入 v0.6 `logs/`；Godot 的可理解错误也应同步进入统一日志或独立 frontend 日志。

## 18. 文档与开发日志瘦身

现有 `docs/development-logs/` 已积累大量按小版本拆分的 Prototype、Smoke Fix、Performance Hotfix 文档。Git 本身已经保留完整历史，因此 v0.6 不继续采用“一次小修一个日志文件”的方式。

计划把历史日志按时代合并成少量总结：

```text
docs/development-logs/
├─ Legacy_Flat_Identity_Era_Summary.md
├─ Retro_Prototype_Era_Summary.md
├─ Retro_Functional_Migration_Era_Summary.md
├─ Retro_Performance_Era_Summary.md
└─ v0.6_Console_Terminal_Development.md
```

原则：

- 保留关键设计决策、阶段成果、失败经验、性能数据
- 删除重复的逐补丁说明
- 原始细节由 Git 历史负责保存
- v0.6 以后每个“大阶段”更新同一份 Development Log，而非为每次小修创建新文件
- 正式架构、协议、数据模型文档放在 `docs/v0.6/`

日志合并必须在独立改动中完成，先生成总结并核对覆盖范围，再删除旧碎片文档，避免信息直接丢失。

## 19. v0.6 Phase 1 范围

Phase 1 的目标不是同时完成四类媒体，而是造出一台真的可以日常选游戏和启动游戏的“小主机”。

必须完成：

- `run_windows.vbs` 作为正式入口
- Python Core + Godot Frontend 双进程骨架
- 本机 WebSocket + JSON
- 全新 v0.6 数据库与设置
- 无边框最大化
- XMB 风格顶层导航
- GAMES 顶层入口
- 单排 3D 实体游戏盒 Carousel
- 中央主盒
- 鼠标滚轮选择
- 侧盒单击进入主位
- 主盒单击进入预览态
- 预览态连续滚轮切换
- Screenshot / GIF / Video 预览基础
- Preview Audio
- 主盒双击启动真实游戏
- 游戏进程结束自动回终端
- 游戏游玩时间记录
- 主题系统基础
- GPU 波浪 + 36 个符号
- 主题背景音乐接口
- SYSTEM 基础页
- Dev Panel / 日志

Phase 1 只预留、不完整实现：

- Movies
- Comics
- Music
- 统一 Search 的完整 UI
- 主题编辑器
- 多种 Library View
- 内置漫画阅读
- 内置音乐播放

## 20. Phase 1 验收标准

功能：

1. 双击 `run_windows.vbs` 能启动完整终端。
2. 可以从空 v0.6 数据库添加测试游戏。
3. 可以展示真实封面和单排 3D 游戏盒。
4. 滚轮、侧盒单击、主盒单击、主盒双击符合既定交互。
5. 预览态不会切 Scene，且可以连续切换游戏。
6. 可以启动真实游戏进程。
7. 游戏退出后终端自动恢复，并回到原游戏位置。
8. 游玩时间正确更新。
9. 主题波浪、36 个符号和背景音乐接口工作。

性能：

- 动态背景由 GPU 路径承担，不以 Python/QPainter 全窗口 repaint 作为动画机制。
- 前端空闲 CPU 应显著低于旧 QWidget Retro 的约 12% 基线；具体阈值以真实 Windows 机器实测记录为准，不在设计阶段伪造硬指标。
- 鼠标在空白区域移动不得再次触发旧版那种 CPU 大幅跃升。
- 外部程序运行时终端隐藏/暂停后不得继续无意义满速渲染。

质量：

- Godot 不直接访问 SQLite。
- Python 不按帧驱动视觉动画。
- 每个 Scene / Script 有单一清晰职责，避免再次出现巨型 `retro_showcase.py`。
- 新数据目录完全独立于 v0.5。
- Phase 1 完成后，v0.5 仍能独立作为历史原型运行，不作为 v0.6 的运行时依赖。

## 21. 明确不做的事情

- 不兼容或迁移 v0.5 测试数据
- 不继续修补 v0.5 QPainter 性能架构
- 不把 Godot 嵌入旧 PySide6 MainWindow
- 不使用 QQuickWidget 作为过渡层
- 不把所有媒体模块一次实现完
- 不在 Phase 1 自研视频播放器替代 PotPlayer
- 不为了模仿 PS3 而复制其具体资产、系统图标或受版权保护的视觉资源
- 不把本机 Backend 接口开放到局域网

## 22. 最终方向

v0.6 的价值不在于“把旧 Retro 换个引擎重画一次”。

它要建立一套长期可扩展的终端基础：

- 前端可以继续成长到高级 2D、2.5D、3D、Shader、粒子和镜头动画
- 后端可以逐步增加 Movies / Comics / Music 等收藏能力
- 主题能够真正改变终端的气质
- 用户可以主要通过 Godot 编辑器和主题参数调视觉，而不需要修改业务代码
- 旧版积累的交互经验被继承，旧版实现层技术债不被继承
