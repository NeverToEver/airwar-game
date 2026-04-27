# Air War - 飞机大战

一款使用 Python + Pygame 开发的 2D 太空射击游戏，支持 Rust 原生加速。

## 快速开始

```bash
# 进入项目目录
cd airwar-game

# 安装依赖
pip install -r requirements.txt

# 运行游戏
python3 main.py
```

## 游戏操作

| 按键 | 功能 |
|------|------|
| 方向键 / WASD | 移动飞船 |
| 空格键 | 射击 |
| ESC | 暂停游戏 |
| H (长按) | 停靠母舰存档 |
| K (长按3秒) | 投降 |

## 游戏特色

- 三种难度模式（简单/普通/困难），动态难度调整
- 12 种 Buff 系统（生命/攻击/防御/辅助 4 类），含一次性天赋限制
- **母舰存档机制**：大型主力舰级母舰，爆炸导弹 AoE 攻击（5 目标），出入港双阶段动画（战机缓入弹出 + 母舰飞离），WASD 操控移动
- 8 种敌人移动模式（直线、正弦、锯齿、俯冲、悬停、螺旋、噪声、攻击型），入场 ease-out 减速 + 移动模式平滑过渡
- Boss 战，多阶段攻击，Rust 原生加速移动计算
- 里程碑奖励系统，定期触发 buff 选择
- 集成 HUD 面板（可折叠），电池式血量指示器
- 全屏模式（FULLSCREEN），冷钢蓝视觉主题

## 技术架构

### 核心架构
- **Scene Pattern**: 基于场景的架构，支持场景切换和状态保存
- **Manager Pattern**: 各子系统独立管理器（生成、碰撞、子弹、Boss 等）
- **Observer Pattern**: 事件总线用于母舰停靠等跨系统通信

### 技术栈
- Python 3.x + Pygame + Pillow
- Rust (PyO3 0.22 / maturin 1.0) — `airwar_core` 原生扩展模块

### 主要模块

| 模块 | 位置 | 说明 |
|------|------|------|
| 场景 | `airwar/scenes/` | login, menu, game, pause, death, exit_confirm, tutorial |
| 实体 | `airwar/entities/` | Player, Enemy, Boss, Bullet |
| 管理器 | `airwar/game/managers/` | GameController, SpawnController, CollisionController 等 |
| 渲染 | `airwar/game/rendering/` | GameRenderer, HUDRenderer |
| 系统 | `airwar/game/systems/` | HealthSystem, RewardSystem, DifficultyManager 等 |
| Buff | `airwar/game/buffs/` | 12 种 Buff（生命/攻击/防御/辅助 4 类） |
| UI | `airwar/ui/` | GameHUD（集成 HUD）、奖励选择、面板、图标等 |
| 存档 | `airwar/game/mother_ship/` | 母舰停靠保存（状态机、接口层、事件总线、GameIntegrator） |
| 投降 | `airwar/game/give_up/` | 长按 K 投降机制 |
| Rust 扩展 | `airwar_core/` | 性能热点原生加速（向量、碰撞、移动、粒子、精灵 glow） |

## 项目结构

```
airwar-game/                  # 项目根目录
├── main.py                  # 入口：python3 main.py
├── airwar/                  # Python 源码包
│   ├── config/              配置 / 设计令牌 / 难度参数
│   ├── entities/            游戏实体（Player, Enemy, Boss, Bullet）
│   ├── game/
│   │   ├── game.py          游戏主循环入口
│   │   ├── scene_director.py 场景编排
│   │   ├── constants.py     全局常量（GameConstants dataclass）
│   │   ├── managers/        核心管理器
│   │   ├── controllers/     子系统控制器
│   │   ├── spawners/        敌人子弹生成器
│   │   ├── systems/         游戏系统（难度、奖励、通知等）
│   │   ├── rendering/       渲染器
│   │   ├── buffs/           Buff 系统（12 种）
│   │   ├── mother_ship/     母舰存档（状态机、接口层、事件总线、GameIntegrator）
│   │   ├── give_up/         投降检测
│   │   ├── explosion_animation/ 爆炸特效
│   │   └── death_animation/     死亡动画
│   ├── scenes/              场景管理（7 个场景，GameScene 实现 IGameScene 接口）
│   ├── ui/                  UI 组件（GameHUD 集成 HUD、奖励选择、面板等）
│   ├── input/               输入处理
│   ├── utils/               工具类（数据库、鼠标交互）
│   ├── window/              窗口管理
│   ├── data/                运行时存档
│   ├── tests/               测试套件
│   └── core_bindings.py     Rust ↔ Python 桥接层
├── airwar_core/              Rust 原生扩展（maturin + PyO3）
│   └── src/
│       ├── lib.rs            模块入口，导出所有函数
│       ├── vector2.rs        向量数学运算
│       ├── collision.rs       空间哈希碰撞检测
│       ├── movement.rs       移动更新（8 种模式）
│       ├── particles.rs      粒子系统
│       ├── bullets.rs        子弹批量更新
│       └── sprites.rs        精灵 glow 表面创建
├── docs/                     文档（优化方案、审查报告、重构指南、维护指南）
└── plans/                    实现计划
```

## Rust 原生扩展（可选）

`airwar_core/` 使用 PyO3 + maturin 构建，为碰撞检测、移动计算等性能热点提供 Rust 加速。**此为可选模块**——未安装时自动降级到纯 Python 实现，游戏正常运行。

### 前置条件

- [Rust 工具链](https://rustup.rs/)（`rustup` 安装）
- Python 虚拟环境（推荐 `.venv`）

### 安装

```bash
# 方式一：虚拟环境中直接安装（推荐）
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd airwar_core && maturin develop --release

# 方式二：无虚拟环境时构建 wheel 后安装
cd airwar_core
maturin build --release
pip install --force-reinstall target/wheels/airwar_core-*.whl
```

### 验证

```bash
python3 -c "from airwar.core_bindings import RUST_AVAILABLE; print('Rust 加速:', '启用' if RUST_AVAILABLE else '未安装（纯 Python 运行）')"
```

## 测试

测试必须从项目根目录运行，而非 `airwar/` 子目录。

```bash
# 运行所有测试
python3 -m pytest

# 仅运行核心功能测试
python3 -m pytest -m smoke

# 排除慢速测试
python3 -m pytest -m "not slow"

# 运行特定测试文件
python3 -m pytest airwar/tests/test_entities.py

# 运行特定测试类/方法
python3 -m pytest airwar/tests/test_entities.py::TestPlayer -v

# 运行 Rust 绑定测试
python3 -m pytest airwar/tests/test_vector2_bindings.py airwar/tests/test_collision_bindings.py airwar/tests/test_movement_bindings.py airwar/tests/test_particle_bindings.py
```
