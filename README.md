# Air War - 飞机大战

一款街机风格的纵向卷轴射击游戏，使用 Python 和 Pygame 开发。

## 游戏截图

> TODO: 添加游戏截图

## 目录

- [游戏特色](#游戏特色)
- [快速开始](#快速开始)
- [游戏操作](#游戏操作)
- [游戏系统](#游戏系统)
  - [难度系统](#难度系统)
  - [Boss 机制](#boss-机制)
  - [增益系统](#增益系统)
  - [回血机制](#回血机制)
- [配置说明](#配置说明)
- [运行测试](#运行测试)

## 游戏特色

- **三种难度模式**：简单 / 普通 / 困难
- **Boss 挑战**：周期性出现的 Boss，具有多种攻击模式和逃跑机制
- **Roguelike 增益**：每次里程碑触发可选择增益效果
- **自适应窗口**：自动适配不同屏幕分辨率
- **用户系统**：支持注册登录，记录最高分

## 快速开始

### 环境要求

- Python 3.8+
- Pygame 2.0+

### 安装依赖

```bash
pip install pygame
```

### 运行游戏

```bash
python main.py
```

## 游戏操作

### 主菜单

| 按键 | 功能 |
|------|------|
| `W` / `↑` | 选择上一个难度 |
| `S` / `↓` | 选择下一个难度 |
| `Enter` | 确认开始游戏 |
| `ESC` | 返回登录界面 |

### 游戏内

| 按键 | 功能 |
|------|------|
| `W` / `↑` | 向上移动 |
| `S` / `↓` | 向下移动 |
| `A` / `←` | 向左移动 |
| `D` / `→` | 向右移动 |
| `Space` | 发射子弹（长按连续射击）|
| `ESC` | 暂停游戏 |

### 暂停菜单

| 按键 | 功能 |
|------|------|
| `W` / `↑` | 选择上一个选项 |
| `S` / `↓` | 选择下一个选项 |
| `Enter` | 确认选择 |
| `ESC` | 返回游戏 |

## 游戏系统

### 难度系统

| 难度 | 敌人血量 | 子弹伤害 | 敌人速度 | 生成间隔 | 计分倍率 |
|------|----------|----------|----------|----------|----------|
| 简单 | 300 HP | 100 | 2.5 | 40帧 | x1 |
| 普通 | 200 HP | 50 | 3.0 | 30帧 | x2 |
| 困难 | 170 HP | 34 | 3.5 | 25帧 | x3 |

> **击败敌人所需子弹数**：所有难度都是 3 发

### Boss 机制

- **生成间隔**：每 1800 帧（约30秒）生成一次
- **逃跑机制**：Boss 有存活时间限制，超时后会自动逃跑
  - 时间计算：`总血量 / 玩家子弹伤害 * 2.5`
  - 基础时间：10-30秒
- **攻击模式**：
  1. **扇形弹幕** - 多颗子弹呈扇形散开
  2. **追踪弹** - 向玩家方向发射
  3. **全方位弹幕** - 向四面八方发射
- **进化阶段**：Boss 每 300 帧会升级，攻击更加凶猛
- **击败奖励**：基础 5000 分，随循环增加

### 增益系统

每达成里程碑分数时会触发奖励选择界面，提供 3 个随机增益：

#### 生命类 (Health)

| 增益 | 图标 | 效果 |
|------|------|------|
| Extra Life | HP | 最大生命值+50，当前生命+30 |
| Regeneration | REG | 每秒回复2点生命 |
| Lifesteal | LST | 击杀敌人时恢复10%伤害值的生命 |

#### 攻击类 (Offense)

| 增益 | 图标 | 效果 |
|------|------|------|
| Power Shot | DMG | 子弹伤害+25% |
| Rapid Fire | RPD | 射击间隔-20% |
| Piercing | PIR | 子弹穿透1个敌人 |
| Spread Shot | SPD | 同时发射3颗子弹 |
| Explosive | EXP | 子弹造成30点范围伤害 |

#### 防御类 (Defense)

| 增益 | 图标 | 效果 |
|------|------|------|
| Shield | SHD | 抵挡下一次攻击 |
| Armor | ARM | 受到伤害-15% |
| Evasion | EVD | 20%几率闪避攻击 |
| Barrier | BAR | 获得50点临时生命 |

#### 工具类 (Utility)

| 增益 | 图标 | 效果 |
|------|------|------|
| Speed Boost | SPD | 移动速度+15% |
| Magnet | MAG | 分数拾取范围+30% |
| Slow Field | SLO | 敌人移动速度-20% |

### 回血机制

玩家在战斗中会缓慢回复生命值：

| 难度 | 开始回血延迟 | 每次回血量 | 回血间隔 |
|------|-------------|-----------|----------|
| 简单 | 3秒 | 3 HP | 0.75秒 |
| 普通 | 4秒 | 2 HP | 1秒 |
| 困难 | 5秒 | 1 HP | 1.5秒 |

> 注意：拥有 Regeneration 增益后，回血速度会大幅提升（2HP/秒）

## 配置说明

游戏配置文件位于 `airwar/config/settings.py`：

```python
# 屏幕设置
SCREEN_WIDTH = 1200      # 默认宽度
SCREEN_HEIGHT = 700      # 默认高度
FPS = 60                 # 帧率

# 玩家设置
PLAYER_SPEED = 5        # 移动速度
BULLET_SPEED = 10       # 子弹速度
PLAYER_FIRE_RATE = 8    # 射击间隔（帧）

# 回血配置
HEALTH_REGEN = {
    'easy': {'delay': 180, 'rate': 3, 'interval': 45},
    'medium': {'delay': 240, 'rate': 2, 'interval': 60},
    'hard': {'delay': 300, 'rate': 1, 'interval': 90},
}

# 难度配置
DIFFICULTY_SETTINGS = {
    'easy': {...},
    'medium': {...},
    'hard': {...},
}
```

## 运行测试

### 运行所有测试

```bash
pytest airwar/tests/ -v
```

### 运行特定测试

```bash
# 只运行实体测试
pytest airwar/tests/test_entities.py -v

# 只运行配置测试
pytest airwar/tests/test_config.py -v

# 只运行场景测试
pytest airwar/tests/test_scenes.py -v
```

### 测试覆盖率

当前测试数量：**99 个**

| 测试文件 | 测试数量 |
|----------|----------|
| test_config.py | 7 |
| test_database.py | 9 |
| test_entities.py | 24 |
| test_integration.py | 37 |
| test_rewards.py | 11 |
| test_scenes.py | 11 |

## 项目结构

```
airwar/
├── config/
│   ├── __init__.py
│   └── settings.py       # 游戏配置
├── entities/
│   ├── __init__.py
│   ├── base.py          # 基础实体类
│   ├── bullet.py        # 子弹类
│   ├── enemy.py         # 敌人和Boss类
│   └── player.py        # 玩家类
├── scenes/
│   ├── __init__.py
│   ├── game_scene.py    # 游戏主场景
│   ├── login_scene.py   # 登录场景
│   ├── menu_scene.py    # 菜单场景
│   ├── pause_scene.py   # 暂停场景
│   └── scene.py         # 场景基类
├── utils/
│   ├── __init__.py
│   ├── database.py       # 用户数据库
│   ├── rewards.py        # 奖励系统
│   └── sprites.py        # 精灵绘制
├── game/
│   ├── __init__.py
│   └── game.py          # 游戏主类
└── tests/
    ├── __init__.py
    ├── test_config.py
    ├── test_database.py
    ├── test_entities.py
    ├── test_integration.py
    ├── test_rewards.py
    └── test_scenes.py
```

## License

MIT License
