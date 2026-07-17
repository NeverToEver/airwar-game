<div align="center">

# 🛩️ 空战 · Air War

**一款 2D 太空射击游戏 —— 使用 Python + Pygame 构建,可选 Rust 扩展加速性能热点**

[English](./README.en.md) · **中文**

[![CI](https://github.com/NeverToEver/airwar-game/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/NeverToEver/airwar-game/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Pygame](https://img.shields.io/badge/pygame-2.6%2B-2e8b57)](https://www.pygame.org/)
[![Rust](https://img.shields.io/badge/rust-PyO3-orange?logo=rust)](https://pyo3.rs/)
[![Release](https://img.shields.io/github/v/release/NeverToEver/airwar-game)](https://github.com/NeverToEver/airwar-game/releases)
[![Tests](https://img.shields.io/badge/tests-215%20passed-brightgreen)](#运行测试)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

<img src="https://raw.githubusercontent.com/NeverToEver/airwar-game/master/.github/screenshots/gameplay.png" alt="空战游戏画面" width="760">

</div>

---

## 目录

- [✨ 亮点](#-亮点)
- [🖼️ 截图](#-截图)
- [🎮 操作](#-操作)
- [🚀 快速开始](#-快速开始)
  - [一键启动](#一键启动)
  - [手动启动](#手动启动)
  - [运行测试](#运行测试)
- [🏆 排行榜](#-排行榜)
- [🛠️ 技术栈](#-技术栈)
- [🏗️ 架构](#-架构)
- [📦 打包](#-打包)
- [🗺️ 路线图](#-路线图)
- [🤝 参与贡献](#-参与贡献)
- [📄 许可证](#-许可证)

## ✨ 亮点

- **可选 Rust 加速**：碰撞检测、向量运算、批量移动、粒子与子弹更新等热点可由 Rust 处理；未安装扩展时自动回退到纯 Python。
- **场景化生命周期**：每个场景独立管理 `enter/exit/update/render`，状态切换清晰。
- **分层状态机**：玩家与 Boss 使用 HSM 驱动复杂行为。
- **优先级锁系统**：`HOMECOMING > MOTHERSHIP > BOSS_ENRAGE > PHASE_DASH > GIVE_UP > GAME_PAUSE`，统一管理无敌、控制锁与暂停。
- **新手教程**：7 阶段教学关卡，复用正式游戏的 UI 与系统。
- **运行时素材缓存**：首次启动生成并缓存字体、光效等 Surface，后续启动更快。

## 🖼️ 截图

所有截图均由 `scripts/capture_screenshots.py` 在 headless 环境下从真实场景渲染生成。

| 主菜单 | 游戏画面 | 暂停菜单 |
|--------|----------|----------|
| ![主菜单](https://raw.githubusercontent.com/NeverToEver/airwar-game/master/.github/screenshots/welcome.png) | ![游戏画面](https://raw.githubusercontent.com/NeverToEver/airwar-game/master/.github/screenshots/gameplay.png) | ![暂停菜单](https://raw.githubusercontent.com/NeverToEver/airwar-game/master/.github/screenshots/pause.png) |

| 设置 | 结算画面 |
|------|----------|
| ![设置](https://raw.githubusercontent.com/NeverToEver/airwar-game/master/.github/screenshots/settings.png) | ![结算画面](https://raw.githubusercontent.com/NeverToEver/airwar-game/master/.github/screenshots/death.png) |

## 🎮 操作

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

## 🚀 快速开始

### 一键启动

脚本会自动检测环境、创建虚拟环境、安装依赖、编译 Rust 扩展并启动游戏。

| 平台 | 命令 |
|------|------|
| Windows | 双击 `run.bat` |
| Linux / macOS | `chmod +x run.sh && ./run.sh` |

常用选项：

```bash
./run.sh --prepare-only             # 仅准备运行环境
./run.sh --skip-rust                # 使用 Python 回退路径启动
./run.sh --rebuild-rust             # 强制重建可选 Rust 扩展
./run.sh -- --debug                 # 将参数转发给游戏
```

如需同时启动本地排行榜服务器：

| 平台 | 命令 |
|------|------|
| Windows | 双击 `run_with_server.bat` |
| Linux / macOS | `chmod +x run_with_server.sh && ./run_with_server.sh` |
| macOS（双击） | `run_with_server.command` |

可通过 `./run_with_server.sh --port 8001 --debug` 指定服务端口并以调试模式启动游戏。

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

### 运行测试

```bash
python3 -m pytest tests/
```

测试覆盖核心架构组件（帧时间、锁仲裁、场景管理、存档持久化、视口坐标）与关键玩法逻辑（碰撞结算、爆炸计分、子弹管理、HUD 缓存等）。

## 🏆 排行榜

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

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 游戏引擎 | Python 3.11+, Pygame 2.6+, Pillow 12.2+ |
| 原生扩展 | Rust 2021 + PyO3 0.22（可选） |
| 后端服务 | FastAPI 0.115+, uvicorn 0.34+, SQLite |
| 构建工具 | PyInstaller 6+, maturin |
| 代码质量 | ruff, mypy, pytest |

## 🏗️ 架构

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

## 📦 打包

```bash
# Linux
bash build_linux.sh

# macOS
bash build_macos.sh

# Windows
build_windows.bat
```

产物输出到 `dist/AirWar`。打包需要 Python 3.11+、Rust 工具链与对应平台编译器；最终用户无需安装 Python 或 Rust。

## 🗺️ 路线图

- [x] 场景驱动的游戏主循环
- [x] 玩家与 Boss 分层状态机
- [x] 优先级锁与暂停仲裁
- [x] 本地 JSON 用户数据库与排行榜
- [x] 可选 Rust 原生扩展
- [ ] 更多 Boss 与敌人种类
- [ ] 联机排行榜增强（账户、赛季）
- [ ] Steam / itch.io 页面
- [ ] Mod 与自定义关卡支持

## 🤝 参与贡献

欢迎 PR、Issue 和反馈！请先阅读 [CONTRIBUTING.md](./CONTRIBUTING.md) 与 [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)。

提交前请运行：

```bash
python3 -m ruff check .
python3 -m compileall -q airwar main.py
python3 -m pytest tests/
```

## 📄 许可证

本项目采用 [MIT 许可证](./LICENSE)。

---

*Air War 是一个业余维护的个人项目，欢迎试用与反馈。*
