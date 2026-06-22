# 空战 · Air War

[English](./README.en.md) | 中文

[![CI](https://github.com/NeverToEver/airwar-game/actions/workflows/ci.yml/badge.svg)](https://github.com/NeverToEver/airwar-game/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Rust](https://img.shields.io/badge/rust-PyO3-orange?logo=rust)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

一款 2D 太空射击游戏，使用 Python + Pygame 构建，并通过可选的 Rust 扩展加速性能热点。

---

## 概览

- **技术栈**：Python 3.11+、Pygame、Pillow；可选 Rust + PyO3 扩展（`airwar_core/`）。
- **架构**：场景驱动（Scene-based），包含 Welcome、Tutorial、Game、Pause、Death、Settings 等场景。
- **状态管理**：玩家与 Boss 使用分层状态机（HSM），复杂行为通过 `LockManager` 优先级仲裁。
- **国际化**：支持简体中文（zh_CN）与英文（en_US）。
- **排行榜**：本地 JSON 排行榜 + 可选 FastAPI + SQLite 远程服务器，远程不可用时自动回退。
- **测试**：970+ 自动化测试，支持 headless SDL 环境，GitHub Actions 持续集成。

## 特性

- **可选 Rust 加速**：碰撞检测、向量运算、批量移动、粒子与子弹更新等热点可由 Rust 处理；未安装扩展时自动回退到纯 Python。
- **场景化生命周期**：每个场景独立管理 `enter/exit/update/render`，状态切换清晰。
- **优先级锁系统**：`HOMECOMING > MOTHERSHIP > BOSS_ENRAGE > PHASE_DASH > GIVE_UP > GAME_PAUSE`，统一管理无敌、控制锁与暂停。
- **更新流水线**：`GameScene.update()` 按固定顺序执行命中停顿、输入、动画、暂停门、碰撞、清理、里程碑检查，避免状态竞争。
- **新手教程**：7 阶段教学关卡，复用正式游戏的 UI 与系统。
- **运行时素材缓存**：首次启动生成并缓存字体、光效等 Surface，后续启动更快。

## 快速开始

### 一键启动（推荐）

脚本会自动检测环境、创建虚拟环境、安装依赖、编译 Rust 扩展并启动游戏。

| 平台 | 命令 |
|------|------|
| Windows | 双击 `run.bat` |
| Linux / macOS | `chmod +x run.sh && ./run.sh` |

如需同时启动本地排行榜服务器：

| 平台 | 命令 |
|------|------|
| Windows | 双击 `run_with_server.bat` |
| Linux / macOS | `chmod +x run_with_server.sh && ./run_with_server.sh` |
| macOS（双击） | `run_with_server.command` |

> 清理本地构建产物与虚拟环境：Windows 运行 `uninstall.bat`，Linux / macOS 运行 `./uninstall.sh`。源码、存档与配置不会被删除。

### 手动启动

```bash
cd airwar-game
pip install -r requirements.txt

# 可选：编译 Rust 扩展
cd airwar_core && maturin develop --release && cd ..

python3 main.py
```

> Windows 编译 Rust 需要 Visual C++ Build Tools；脚本失败时会提示下载链接。

## 操作方式

| 按键 / 输入 | 功能 |
|-------------|------|
| 方向键 / WASD | 移动战机 |
| Ctrl 长按 | 微调姿态，速度降至 35% |
| 鼠标 | 控制瞄准方向，带自动辅瞄 |
| Shift 长按 | 加速推进（1.7 倍速，消耗燃料） |
| Shift 按下松开 | 相位冲刺（需天赋解锁），无敌突进 |
| 自动 | 战机持续自动射击 |
| ESC | 暂停 |
| B 长按 2.4 秒 | 返航基地整备 |
| H 长按 3 秒 | 对接母舰并保存进度 |
| K 长按 3 秒 | 放弃当前出击 |
| L | 展开 / 收起 HUD 面板 |

## 排行榜

排行榜子系统是可选的，默认本地运行；远程服务器用于模拟「客户端 + 服务端」架构。

- **本地优先**：分数始终写入本地 `UserDB`；远程不可用时自动显示本地榜单。
- **模式**：`auto`（默认） / `remote` / `local`，通过 `AIRWAR_LEADERBOARD_MODE` 设置。
- **手动启动服务器**：

```bash
pip install -e ".[server]"
python -m airwar.leaderboard.server --port 8000 --db-path ./leaderboard.db
```

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `AIRWAR_LEADERBOARD_URL` | `http://localhost:8000` | 远程服务器地址 |
| `AIRWAR_LEADERBOARD_MODE` | `auto` | `auto` / `remote` / `local` |
| `AIRWAR_LEADERBOARD_TIMEOUT` | `3.0` | HTTP 超时（秒） |
| `AIRWAR_LEADERBOARD_DB_PATH` | 平台数据目录 | 服务器 SQLite 路径 |

## 开发

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 完整测试
python3 -m pytest

# 快速烟雾测试
python3 -m pytest -m smoke

# 代码检查
python3 -m ruff check .

# 字节码检查
python3 -m compileall -q airwar main.py
```

请在项目根目录运行测试，不要在 `airwar/` 子目录内运行。

## 架构简介

```text
WelcomeScene → TutorialScene → GameScene
                    ├─ PauseScene
                    ├─ DeathScene
                    ├─ SettingsScene
                    └─ ExitConfirmScene
```

核心模块：

- `airwar/entities/` — 玩家、敌人、Boss、子弹等实体。
- `airwar/game/managers/` — 碰撞、生成、子弹、Boss、里程碑等管理器。
- `airwar/game/systems/` — 生命、奖励、难度、通知、天赋等系统。
- `airwar/scenes/` — 各场景实现。
- `airwar/leaderboard/` — 排行榜客户端、服务层、FastAPI 服务器。
- `airwar_core/` — Rust 原生扩展。

更详细的设计说明见 [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)。

## 打包

```bash
# Linux
bash build_linux.sh

# macOS
bash build_macos.sh

# Windows
build_windows.bat
```

产物输出到 `dist/AirWar`。打包需要 Python 3.11+、Rust 工具链与对应平台编译器；最终用户无需安装 Python 或 Rust。

## 参与贡献

- 提交 PR 前请运行 `python3 -m ruff check .` 与 `python3 -m pytest`。
- 详见 [`LICENSE`](./LICENSE)。

---

*Air War 是一个业余维护的个人项目，欢迎试用与反馈。*
