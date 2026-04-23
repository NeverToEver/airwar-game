# Air War - 飞机大战

一款使用 Python + Pygame 开发的 2D 太空射击游戏。

## 快速开始

```bash
pip install -r requirements.txt
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
- 架构：Scene Pattern, Manager Pattern, Observer Pattern

### 主要模块

| 模块 | 位置 | 说明 |
|------|------|------|
| 场景 | `scenes/` | login, menu, game, pause, death, exit_confirm, tutorial |
| 实体 | `entities/` | Player, Enemy, Boss, Bullet |
| 管理器 | `game/managers/` | GameController, SpawnController, CollisionController 等 |
| 渲染 | `game/rendering/` | GameRenderer, HUDRenderer |
| 系统 | `game/systems/` | HealthSystem, RewardSystem, DifficultyManager 等 |
| 存档 | `game/mother_ship/` | 母舰停靠保存系统 |

## 项目结构

```
airwar/
|-- config/          配置文件（设置、设计令牌、难度）
|-- components/      可复用组件
|-- entities/        游戏实体（玩家、敌人、子弹）
|-- game/            核心游戏逻辑
|   |-- managers/    各类管理器
|   |-- rendering/   渲染系统
|   |-- systems/     游戏系统
|   |-- buffs/       Buff 系统
|   |-- mother_ship/ 母舰存档
|   |-- explosion_animation/ 爆炸特效
|   `-- death_animation/    死亡动画
|-- scenes/          场景管理
|-- ui/              UI 组件
|-- utils/           工具类
|-- window/          窗口管理
|-- input/           输入处理
`-- tests/           测试套件
```

## 测试

```bash
# 运行所有测试
cd airwar && python -m pytest

# 仅运行核心功能测试
cd airwar && python -m pytest -m smoke

# 排除慢速测试
cd airwar && python -m pytest -m "not slow"
```
