# v0.6 Phase 1C Launcher, Cutover and Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把通过验收的 v0.6 Core + Godot Frontend 接入现有 Windows 启动入口，并在完整回归后退役旧 QWidget/Retro 运行时与碎片化日志。

**Architecture:** `run_windows.vbs` 文件名与用户操作不变，内部改为启动 `pythonw -m terminal_core` supervisor。Supervisor 负责 backend ready、Godot frontend、外部游戏生命周期和正常关停。旧 runtime 仅在 v0.6 完整生命周期验证通过后删除。

**Tech Stack:** Windows Script Host, Python 3.11+, Godot 4.7.x Stable.

**Spec:** `docs/v0.6/Console_Terminal_Architecture.md`

## Global Constraints

- 不改变用户双击 `run_windows.vbs` 的入口习惯。
- 外部游戏运行期间 Terminal 不退出；Godot 隐藏/暂停，Python Core 继续监控。
- 游戏结束后自动恢复前台和原资源位置。
- 清理旧 runtime 必须是最后一步，并且 Git 历史完整保留 v0.5。
- 旧开发日志先汇总覆盖，再删除碎片文件。

---

### Task 1: Supervisor / Launcher

**Files:** Create `terminal_core/launcher.py`, `terminal_tests/test_launcher.py`; modify `terminal_core/__main__.py`.

**Interfaces:** `python -m terminal_core` starts supervisor; backend ready precedes frontend start; frontend exit requests backend shutdown.

- [ ] 写 launcher 失败测试：fake process factory 记录顺序，断言 backend ready 发生在 Godot start 前。
- [ ] 实现 Godot executable 查找顺序：settings `godot_executable` → `GODOT4` env → PATH `godot.exe` / `godot`。
- [ ] 找不到 Godot 时写 terminal.log，并通过 Windows 可理解错误提示退出，不静默失败。
- [ ] 实现 Ctrl/normal frontend exit 的 backend shutdown 和 child cleanup。
- [ ] Run `python -m pytest terminal_tests/test_launcher.py -v`; commit `feat(v06): add terminal supervisor`.

### Task 2: 保持 VBS 名称并切换正式入口

**Files:** Modify `run_windows.vbs`, `run_windows.bat`, `run_windows_debug.bat`, `setup_windows.bat`.

- [ ] 写文本级回归测试/检查：`run_windows.vbs` 仍存在且必须包含 `-m terminal_core`，不得包含 `-m app.main`。
- [ ] 修改 VBS，只切 command，不改双击方式和隐藏窗口行为。
- [ ] `run_windows_debug.bat` 使用 `.venv\Scripts\python.exe -m terminal_core` 保留可见 console。
- [ ] setup 安装 v0.6 Python deps，并提示 Godot 4.7.x/FFmpeg 可在 SYSTEM 中配置；不自动下载第三方大型二进制。
- [ ] 在 Windows 手工验证 VBS 能启动 Core+Godot。
- [ ] Commit `feat(v06): switch windows entrypoint`.

### Task 3: 外部游戏运行时的隐藏/返回生命周期

**Files:** Modify launcher/server and Godot shell scripts.

- [ ] 端到端测试事件顺序：`game.launch response → game.started → game.exited`。
- [ ] `game.started` 后 Godot 窗口隐藏或进入低成本暂停态，Ambient 不继续无意义满速渲染。
- [ ] Python Core 继续监控进程与计时。
- [ ] `game.exited` 后 Godot 恢复、置前、恢复原 section/item/browser position，并播放 Return Transition。
- [ ] 记录真实测试程序和一个真实游戏的生命周期结果。
- [ ] Commit `feat(v06): restore terminal after external game`.

### Task 4: Phase 1 完整 Smoke 与性能记录

**Files:** Create `terminal_tools/backend_smoke.py`; create/update `docs/development-logs/v0.6_Phase1_Development_Log.md`.

- [ ] backend smoke 使用临时 v0.6 root：hello → game.create → list → preview → launch Python 短命程序 → wait exit → verify playtime/state。
- [ ] Run `python -m pytest terminal_tests -v`。
- [ ] Run `python terminal_tools/backend_smoke.py`。
- [ ] Run `terminal_tools\validate_godot.bat`。
- [ ] 手工完整路径：VBS → 空库/Add Game → 封面 → Carousel → Preview → 双击 Launch → Terminal 隐藏 → 程序退出 → Return 到原 item。
- [ ] 记录浏览 idle、空白鼠标移动、主盒 Hover、视频预览、窗口拖动的 FPS/CPU/GPU 实测值，不伪造通用阈值。
- [ ] Commit `test(v06): complete phase1 end-to-end smoke`.

### Task 5: 开发日志合并瘦身

**Files:** Create `docs/development-logs/Legacy_UI_Architecture_Summary.md`, `Retro_UI_Evolution_Summary.md`, `Retro_Performance_and_Smoke_Summary.md`; retain `v0.6_Phase1_Development_Log.md`.

- [ ] 枚举现有 `docs/development-logs/*.md` 并建立覆盖表。
- [ ] `Legacy_UI_Architecture_Summary.md` 汇总 Flat Pro、Identity、MainWindow/application shell 的阶段与关键决策。
- [ ] `Retro_UI_Evolution_Summary.md` 汇总 Retro Prototype、功能迁移、Games 主盒/预览等最终保留的交互经验。
- [ ] `Retro_Performance_and_Smoke_Summary.md` 汇总 15/30fps、QPainter repaint、cache、MouseMove 热点、smoke 经验以及转向 GPU/Godot 的依据。
- [ ] 对每份旧日志确认“阶段 + 关键决策 + 结果”至少被一个 summary 覆盖；细粒度 patch 命令留给 Git history。
- [ ] 删除被 summary 取代的旧碎片日志，只保留三份 summary + v0.6 开发日志。
- [ ] Commit `docs: consolidate development history`.

### Task 6: 退役旧 QWidget/Retro Runtime

**Files:** Delete legacy `app/`, legacy `tests/`, legacy `tools/`, `PATCH_NOTES.txt` only after Task 4 passes; modify `pyproject.toml`, `README.md`.

- [ ] 在删除前确认 v0.6 runtime 不存在任何 `import app` 或 PySide6 runtime dependency。
- [ ] 删除旧 `app/`, `tests/`, `tools/` 与 PATCH_NOTES；Git/main history 继续保存 v0.5 原型。
- [ ] `pyproject.toml` 改名 `local-resource-terminal`, version `0.6.0`, pytest path `terminal_tests`; 删除只服务旧 QWidget runtime 的 PySide6/pytest-qt 依赖，保留 v0.6 实际依赖。
- [ ] README 重写为 v0.6：产品定位、Godot 4.7.x、Python/FFmpeg、setup、VBS、数据目录、开发命令；不再维护逐小版本 patch wall。
- [ ] Run full Python tests + backend smoke + Godot validation + VBS manual lifecycle。
- [ ] Commit `refactor(v06): retire legacy runtime`.

## Final Verification

```text
python -m pytest terminal_tests -v
python terminal_tools/backend_smoke.py
terminal_tools\validate_godot.bat
```

最后必须在真实 Windows 上从 `run_windows.vbs` 完成一次完整的添加游戏、浏览、预览、启动、退出、回到原位置流程后，才允许把 Phase 1 标记为完成。
