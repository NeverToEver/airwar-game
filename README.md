# Air War - 飞机大战

一款使用 Python + Pygame 开发的 2D 太空射击游戏，支持 Rust 原生加速。

## 快速开始

```bash
# 进入项目目录
cd airwar

# 安装依赖
pip install -r requirements.txt

# 运行游戏
python main.py
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
- 18 种 Buff 系统，丰富的强化选择
- 母舰存档机制，支持随时保存进度
- 6 种敌人移动模式（直线、正弦、锯齿、俯冲、悬停、螺旋）
- Boss 战，多阶段攻击
- 里程碑奖励系统，定期触发 buff 选择

## 技术架构

### 核心架构
- **Scene Pattern**: 基于场景的架构，支持场景切换和状态保存
- **Manager Pattern**: 各子系统独立管理器（生成、碰撞、子弹、Boss 等）
- **Observer Pattern**: 事件总线用于母舰停靠等跨系统通信

### 技术栈
- Python 3.x + Pygame + Pillow
- Rust (PyO3 0.22 / maturin 1.0) — `airwar_core` 原生扩展模块
- 架构：Scene Pattern, Manager Pattern, Observer Pattern

### 主要模块

| 模块 | 位置 | 说明 |
|------|------|------|
| 场景 | `airwar/scenes/` | login, menu, game, pause, death, exit_confirm, tutorial |
| 实体 | `airwar/entities/` | Player, Enemy, Boss, Bullet |
| 管理器 | `airwar/game/managers/` | GameController, SpawnController, CollisionController 等 |
| 渲染 | `airwar/game/rendering/` | GameRenderer, HUDRenderer |
| 系统 | `airwar/game/systems/` | HealthSystem, RewardSystem, DifficultyManager 等 |
| 存档 | `airwar/game/mother_ship/` | 母舰停靠保存系统 |
| 投降 | `airwar/game/give_up/` | 长按 K 投降机制 |
| Rust 扩展 | `airwar_core/` | 性能热点原生加速（向量、碰撞、移动、粒子、精灵 glow） |

## 项目结构

```
airwar/
├── main.py                  # 入口：python main.py
├── airwar/                  # Python 源码包
│   ├── config/              配置/设计令牌/难度参数
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
│   │   ├── buffs/           Buff 系统（18种）
│   │   ├── mother_ship/     母舰存档（状态机、持久化、事件总线）
│   │   ├── give_up/         投降检测
│   │   ├── explosion_animation/ 爆炸特效
│   │   └── death_animation/     死亡动画
│   ├── scenes/              场景管理（7个场景）
│   ├── ui/                  UI 组件（奖励选择、HUD、面板等）
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
│       ├── movement.rs       移动更新
│       ├── particles.rs      粒子系统
│       └── sprites.rs        精灵 glow 表面创建
├── docs/                     文档（Rust 优化方案、审查报告）
└── plans/                    实现计划
```

## Rust 原生扩展

`airwar_core/` 使用 PyO3 + maturin 构建，为性能热点提供 Rust 加速：

```bash
# 构建 Rust 扩展
cd airwar_core && maturin develop --release
```

Rust 模块不可用时自动降级到纯 Python 实现，无需额外处理。

渲染采用纯 pygame 方案（Phase 6 移除了 ModernGL GPU 依赖），Rust sprites 模块仅用于 glow 表面创建。

## 测试

```bash
# 运行所有测试
cd airwar && python -m pytest

# 仅运行核心功能测试
cd airwar && python -m pytest -m smoke

# 排除慢速测试
cd airwar && python -m pytest -m "not slow"

# 运行 Rust 绑定测试
cd airwar && python -m pytest tests/test_vector2_bindings.py tests/test_collision_bindings.py tests/test_movement_bindings.py tests/test_particle_bindings.py tests/test_sprite_bindings.py
```
