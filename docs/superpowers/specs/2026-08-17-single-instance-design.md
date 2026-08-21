# v0.3.4 单实例保护设计

## 目标

本地资源终端同一 Windows 用户会话中只允许一个应用实例。用户第二次启动时，不创建第二套数据库/JSON/Session 服务，而是通知已经运行的实例把主窗口恢复并置前，然后第二个进程正常退出。

## 行为

- 第一次启动：正常创建主窗口并监听固定的本地 IPC 名称。
- 第二次启动：在初始化设置、数据库、影片/游戏服务之前检测现有实例。
- 若检测到现有实例：发送 `activate` 请求，第二个进程不构建服务、不打开任何窗口，随后退出码为 0。
- 已存在窗口若最小化：恢复普通状态；若被其他窗口遮挡：调用 Qt 的 `raise_()` 与 `activateWindow()` 请求置前。
- 不显示“程序已经运行”的多余提示。
- 不使用 `.lock` 文件，避免异常退出遗留死锁。
- 不修改当前数据格式、游戏 Session 格式、窗口尺寸策略或影片/游戏业务逻辑。

## 技术方案

使用 PySide6 `QLocalServer` / `QLocalSocket`：

- 新模块 `app/single_instance.py` 封装单实例 IPC。
- 固定服务器名保持内部历史身份 `LocalMovieManager.SingleInstance.v1`，品牌名以后变化不影响升级兼容。
- `build_application()` 创建 `QApplication` 后立即尝试取得主实例资格；只有主实例继续加载设置和服务。
- 主窗口建立后注册 activation handler。
- IPC 对象挂在 `QApplication` 属性上，保证整个应用生命周期中不被回收。

## 失败策略

- 正常连接已有 server：作为第二实例退出。
- 初始连接失败且成功 `listen()`：作为第一实例继续。
- 两个进程同时启动导致 `listen()` 竞争：再次尝试连接获胜实例；连接成功则退出。
- 若既无法监听又无法连接：抛出明确启动错误，不冒险启动第二个可写实例。

## 测试

- 源码回归：单实例检查发生在 `build_services()` 之前。
- 源码回归：使用 `QLocalServer` / `QLocalSocket`，没有 lock 文件。
- 源码回归：activation handler 恢复最小化窗口并执行 `raise_()` / `activateWindow()`。
- 有 PySide6 的环境额外验证第一次实例 / 第二实例消息行为；当前构建环境无 PySide6 时允许该类 Qt 运行测试 skip。
- 全量 pytest、Python 3.11 compatibility、compileall、v0.3.3.1 覆盖升级回归必须通过。
