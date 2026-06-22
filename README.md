# 空战

[English version](./README.en.md)

一款基于 Python + Pygame 的 2D 空战射击游戏，支持可选 Rust 原生扩展加速。

## 项目特点

- **可选 Rust 加速** — `airwar_core/` 使用 PyO3 + maturin 提供性能热点的原生实现（向量运算、碰撞检测、批量移动、粒子系统、子弹更新、光效生成），缺失时自动回退纯 Python 实现，零配置开箱即用
- **场景架构** — `SceneManager` 管理 Welcome → Tutorial → Game → Pause/Death/Settings/Exit 完整生命周期，每个场景独立封装 `enter/exit/handle_events/update/render` 接口
- **HSM 状态机** — 玩家和 Boss 均采用分层状态机驱动：Player 使用 `_ALIVE_TRANSITIONS` 转移表 + `IllegalPlayerTransition` 异常保护；Boss 使用 8 状态 `_BOSS_TRANSITIONS` 转移表 + 暴走子状态机
- **LockManager 优先级仲裁** — 6 层优先级（HOMECOMING 100 / MOTHERSHIP 80 / BOSS_ENRAGE 60 / PHASE_DASH 40 / GIVE_UP 20 / GAME_PAUSE 10）统一管理无敌、控制锁、暂停互锁
- **15 步更新流水线** — `GameScene.update()` 严格按序执行：tick_hit_stop → 输入/动画/暂停门 → 碰撞检测 → 死实体清理 → 里程碑检查，保证状态一致性
- **i18n 国际化** — 支持 zh_CN / en_US，134 个翻译键，`t(key, **kwargs)` 公共 API
- **可选远程排行榜** — `airwar/leaderboard/` 提供 FastAPI + SQLite 本地模拟服务器，`LeaderboardService` 自动在远程与本地 JSON 排行榜之间切换，远程不可用时无缝回退
- **运行期素材缓存** — 首次启动生成飞船/光效等 Surface 并缓存到本地，后续启动直接复用
- **1015 个测试用例** — pytest 驱动，支持 headless SDL 环境运行，覆盖率门禁 40%

## 技术路线

本项目采用 **Pygame-native** 技术路线：

```
Python 3.11+ + Pygame (核心)
       ↓
Rust + PyO3 (可选性能层)
       ↓
maturin (构建工具)
```

- **核心层**: Python + Pygame 负责游戏逻辑、渲染、输入处理
- **性能层**: Rust 通过 PyO3 绑定加速热点计算（碰撞、向量、粒子、批量更新）
- **回退策略**: `core_bindings.py` 使用 `try: from airwar_core import ... except (ImportError, OSError)` 实现优雅降级，`RUST_AVAILABLE` 标志位供消费方检查
- **不依赖外部引擎**: 纯 Pygame 实现，不迁移 Godot/Unity 等引擎

## 开发框架

| 组件 | 技术 | 用途 |
|------|------|------|
| **语言** | Python 3.11+ | 游戏逻辑、配置、测试 |
| **游戏引擎** | Pygame 2.6+ | 渲染、事件循环、音频 |
| **图像处理** | Pillow 12+ | 精灵缩放、格式转换 |
| **原生扩展** | Rust + PyO3 0.22 | 性能热点加速 |
| **构建工具** | maturin 1.0 | Rust → Python 绑定编译 |
| **打包** | PyInstaller 6+ | 生成独立可执行文件 |
| **测试** | pytest 8+ | 单元测试、属性测试 |
| **Lint** | ruff 0.8+ | 代码风格检查（E/W/F 规则） |
| **排行榜服务** | FastAPI + uvicorn | 本地模拟远程排行榜服务器 |

## 详细项目描述

### 游戏玩法

玩家驾驶战机在太空中与敌机和 Boss 战斗，通过击杀获取分数和增益，最终挑战 Boss 完成关卡。

**核心系统:**

- **自动射击 + 鼠标辅瞄** — 战机持续自动射击，鼠标控制瞄准方向；`AimAssistSystem` 实现两层目标选择（自动锁定最近敌人 / 大幅鼠标移动时优先切换到移动方向目标），原始输入加入短延迟平滑
- **加速系统** — 长按 Shift 启动推进，1.7 倍速，消耗燃料并延迟恢复；270° 弧形仪表 UI
- **相位冲刺** — 需天赋解锁，按下松开 Shift 触发，消耗 25% 燃料进行 250px 无敌突进
- **武器模式** — 散射弹（扇形 3 发，-10°/0°/+10°）和激光（单发高伤害 35），两种模式可组合形成散射激光
- **13 种增益** — 覆盖生命、攻击、防御、功能四类，含双路线天赋系统（进攻/支援）与路线内互斥选项
- **里程碑奖励** — 达到分数阈值后选择强化，支持天赋路线切换与配置保存

### 母舰与基地

- **母舰系统** — 长按 H 对接保存进度，母舰可移动并提供爆炸导弹支援（250 伤害 / 80px 范围），10 发弹匣限制
- **基地指挥中心** — 长按 B 返航后进入停机坪，使用征用点数（RP）进行维修（-2RP）、补给（-2RP）和天赋路线切换；RP 通过击杀 Boss（+5）和完成基地任务（+3）获得
- **轨道打击** — 从基地出发时触发全屏清弹，提供安全的出击窗口

### Boss 战

- 多阶段移动和攻击模式（巡逻/扫描/悬停/追击）
- Boss 血量降至 30% 时触发核心过载：6 秒暴走序列，攻击节奏加快、枪口焰跳动频率大幅提升
- 暴走视觉表现：Boss 扩散光圈 + 屏幕边缘暗角 + 扰动叠加
- 受击清弹：玩家受击进入短暂无敌时清理普通敌弹，Boss 暴走弹幕不被清除

### 新手教程

主菜单可进入 7 阶段教学关卡：
1. 移动瞄准
2. 加速突进
3. 战斗基础
4. 母舰停靠（虚影显现、火力支援、弹射脱离三阶段演示）
5. 返航基地（含整备流程）
6. Boss 遭遇

教程复用真实游戏 UI 组件，体验与正式战斗一致。

## 技术架构

### 场景系统

```
WelcomeScene → TutorialScene (首次游戏) → GameScene
     │                                      ├─ PauseScene (ESC)
     │                                      ├─ DeathScene (玩家死亡)
     │                                      ├─ ExitConfirmScene (退出确认)
     │                                      ├─ SettingsScene (设置)
     └─ GameScene (返回玩家)
```

### 实体层次

```
Entity (base) — rect, collision_rect, active
  ├─ Player — HSM 驱动，_ALIVE_TRANSITIONS 转移表
  ├─ Enemy — 8 种移动模式
  │    └─ Boss — 4 组件协调器
  │         ├─ BossStateMachine (8 状态 HSM + 暴走子状态)
  │         ├─ BossMovement (巡逻/扫描/悬停/追击)
  │         ├─ BossAttackPatterns (散射/瞄准/波浪/快照)
  │         └─ BossRenderer (精灵/朝向/暴走尾迹)
  └─ Bullet
```

### Manager 拆分

| Manager | 职责 |
|---------|------|
| `CollisionController` | 碰撞检测（支持 Rust 批量碰撞） |
| `SpawnManager` | 敌机生成与波次管理 |
| `BulletManager` | 子弹生命周期管理 |
| `BossManager` | Boss 出现与行为协调 |
| `MilestoneManager` | 里程碑触发与奖励选择 |
| `InputCoordinator` | 输入事件分发 |

### LockManager 优先级

| 层级 | 优先级 | 触发条件 |
|------|--------|----------|
| `HOMECOMING` | 100 | FTL 返航基地 |
| `MOTHERSHIP` | 80 | 母舰停靠 |
| `BOSS_ENRAGE` | 60 | Boss HP < 30% |
| `PHASE_DASH` | 40 | 相位冲刺 |
| `GIVE_UP` | 20 | 放弃出击 |
| `GAME_PAUSE` | 10 | ESC 暂停 / 奖励选择 |

## 快速开始

**推荐方式 — 一键启动脚本**（自动检测 Python、创建虚拟环境、安装依赖、编译 Rust 扩展、启动游戏）：

- **Windows**：双击 `run.bat`
- **Linux**：`chmod +x run.sh && ./run.sh`

首次运行时会自动创建虚拟环境并安装 Python 依赖。Rust 工具链和系统依赖只会在显式传入 `--install-deps` 或设置 `AIRWAR_INSTALL_DEPS=1` 时安装。

**带远程排行榜服务器的启动方式**（本地模拟，自动后台启动服务器并连接）：

- **Windows**：双击 `run_with_server.bat`
- **Linux / macOS**：`chmod +x run_with_server.sh && ./run_with_server.sh`
- **macOS 双击**：`run_with_server.command`

这会自动启动 FastAPI 排行榜服务器（默认 `http://127.0.0.1:8000`），游戏结束后服务器一同关闭。只玩单机模式时仍使用 `run.sh` / `run.bat`。

**本地清理**：双击 `uninstall.bat`（Windows）或执行 `./uninstall.sh`（Linux/macOS）会移除本地虚拟环境、构建产物和缓存，但不会删除源码、存档、账号数据或配置。

> Windows 用户注意：Rust 编译需要 Visual C++ Build Tools。如果编译失败，脚本会提供下载链接。选择「Desktop development with C++」安装即可。

**手动启动：**

```bash
cd airwar-game
pip install -r requirements.txt
cd airwar_core && maturin develop --release && cd ..
python3 main.py
```

## 操作方式

| 按键 / 输入 | 功能 |
|-------------|------|
| 方向键 / WASD | 移动战机 |
| Ctrl 长按 | 微调姿态，移动速度降至 35%，战机外圈显示蓝色指示环 |
| 鼠标 | 控制瞄准方向，带目标辅瞄与平滑输入延迟 |
| Shift 长按 | 加速推进，消耗加速燃料，速度提升至 1.7 倍 |
| Shift 按下松开 | 相位冲刺（需天赋解锁），消耗 25% 燃料，无敌冲刺 250px |
| 自动开火 | 战机会持续自动射击 |
| ESC | 暂停游戏 |
| B 长按 2.4 秒 | 返航基地，进入基地指挥中心整备 |
| H 长按 3 秒 | 呼叫母舰并对接保存进度 |
| K 长按 3 秒 | 放弃当前出击 |
| L | 展开 / 收起 HUD 面板 |

## 远程排行榜

项目内置一个可选的远程排行榜子系统，用于验证「游戏客户端 + FastAPI 远程数据库」架构。

### 架构

```
Game / UI
    │
    ▼
LeaderboardService  ── 本地 UserDB (JSON, 始终写穿)
    │
    ▼
RemoteLeaderboardClient ── urllib (stdlib)
    │
    ▼
FastAPI server ── SQLiteLeaderboardStore
```

- **本地优先回退**：无论远程是否可用，分数都会写入本地 `UserDB`；远程不可用时排行榜自动显示本地数据
- **模式**：`auto`（自动探测）/ `remote`（仅远程）/ `local`（仅本地），通过 `AIRWAR_LEADERBOARD_MODE` 设置
- **零运行时依赖**：游戏客户端使用标准库 `urllib.request`；FastAPI/uvicorn 只在 `[server]` extras 中

### 启动服务器

```bash
# 安装 server 依赖
pip install -e ".[server]"

# 手动启动
python -m airwar.leaderboard.server --port 8000 --db-path ./leaderboard.db
```

### 一键启动（服务器 + 游戏）

```bash
# Linux / macOS
./run_with_server.sh

# Windows
run_with_server.bat
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AIRWAR_LEADERBOARD_URL` | `http://localhost:8000` | 远程服务器地址 |
| `AIRWAR_LEADERBOARD_MODE` | `auto` | `auto` / `remote` / `local` |
| `AIRWAR_LEADERBOARD_TIMEOUT` | `3.0` | HTTP 请求超时（秒） |
| `AIRWAR_LEADERBOARD_DB_PATH` | 平台数据目录下的 `leaderboard.db` | 服务器 SQLite 路径 |

## Rust 原生扩展

`airwar_core/` 使用 PyO3 + maturin 提供可选性能加速。模块包括：

| 模块 | 功能 |
|------|------|
| `vector2.rs` | 向量运算（加减乘除、归一化、点积、插值、角度） |
| `collision.rs` | 空间哈希碰撞检测 |
| `movement.rs` | 敌机/Boss 移动计算（批量更新） |
| `particles.rs` | 粒子系统更新与渲染 |
| `bullets.rs` | 子弹批量更新 |
| `sprites.rs` | 光效素材生成（子弹光晕、爆炸光圈） |
| `starfield.rs` | 星空背景计算 |

### 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd airwar_core
maturin develop --release
```

### 验证

```bash
python3 -c "from airwar.core_bindings import batch_update_bullets; print('Rust 原生扩展: 已安装')"
```

## 项目结构

```text
airwar-game/
├── main.py                    # 游戏启动入口
├── airwar/                    # Python 游戏源码
│   ├── config/                # 配置、设计令牌、难度参数
│   ├── entities/              # 玩家、敌人、Boss、子弹等实体
│   ├── game/                  # 游戏主流程、管理器、系统、渲染、母舰、动画
│   │   ├── managers/          # 碰撞、生成、子弹、Boss、里程碑等管理器
│   │   ├── systems/           # 生命、奖励、难度、通知、天赋等系统
│   │   └── homecoming/        # 返航基地序列
│   ├── scenes/                # 欢迎、教程、战斗、暂停、死亡、退出、设置等场景
│   ├── ui/                    # HUD、奖励选择、基地指挥中心、准星、提示等 UI
│   ├── leaderboard/           # 远程排行榜客户端、服务层、FastAPI 服务器
│   ├── i18n/                  # 国际化翻译器
│   ├── locales/               # 语言文件 (zh_CN.json, en_US.json)
│   ├── input/                 # 输入处理
│   ├── utils/                 # 数据库、字体、素材绘制与缓存等工具
│   ├── window/                # 窗口创建与缩放
│   ├── tests/                 # Python 测试
│   └── core_bindings.py       # Rust 扩展绑定入口
├── airwar_core/               # Rust 原生扩展
│   └── src/
│       ├── lib.rs             # 模块导出入口
│       ├── vector2.rs         # 向量计算
│       ├── collision.rs       # 空间哈希碰撞
│       ├── movement.rs        # 敌人 / Boss 运动计算
│       ├── particles.rs       # 粒子更新与生成
│       ├── bullets.rs         # 子弹批量更新
│       ├── sprites.rs         # 光效素材生成
│       └── starfield.rs       # 星空背景计算
├── scripts/                   # 开发辅助脚本
├── tests/                     # 根目录级测试
├── docs/                      # 文档与架构决策记录 (ADR)
├── build_linux.sh             # Linux 打包脚本
├── build_macos.sh             # macOS 打包脚本
├── build_windows.bat          # Windows 打包脚本
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
└── pyproject.toml
```

## 测试与代码检查

请在项目根目录执行测试，不要在 `airwar/` 子目录内运行。

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 全量测试
python3 -m pytest

# 烟雾测试（快速验证核心功能）
python3 -m pytest -m smoke

# 代码检查
python3 -m ruff check .

# 指定测试文件
python3 -m pytest airwar/tests/test_core.py

# 指定测试用例
python3 -m pytest airwar/tests/test_core.py::TestPlayer -v
```

## CI（GitHub Actions）

每次 push 和 pull_request 触发，单 job 运行在 `ubuntu-latest`：

1. Python 3.11+ + Rust stable + libsdl2-dev
2. pip install + maturin build + ruff check + compileall + shellcheck + pytest

本地模拟 CI：

```bash
python3 -m ruff check . && python3 -m compileall -q airwar main.py && python3 -m pytest
```

## 打包

```bash
# Linux
bash build_linux.sh

# macOS
bash build_macos.sh

# Windows
build_windows.bat
```

打包产物位于 `dist/AirWar`。构建阶段需要 Python 3.11+、Rust 工具链和对应平台编译器；运行打包产物时不需要用户手动安装 Python 或 Rust。

## 许可证

本项目采用 [MIT 许可证](./LICENSE)。
