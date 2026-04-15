# Air War - 飞机大战

一款街机风格的纵向卷轴射击游戏，使用 Python 和 Pygame 开发。

## 🚀 项目状态

### ✅ 架构重构已完成

本项目已完成架构重构，实现了以下改进：

#### Phase 1: 输入层抽象
- ✅ 创建 `airwar/input/` 模块
- ✅ 实现 `InputHandler` 抽象接口
- ✅ 实现 `PygameInputHandler` 和 `MockInputHandler`
- ✅ 重构 `Player` 类使用依赖注入

#### Phase 2: Enemy/Boss 解耦
- ✅ 创建 `IBulletSpawner` 接口
- ✅ 创建 `EnemyBulletSpawner` 实现类
- ✅ 重构 `Enemy` 和 `Boss` 类移除 `GameScene` 引用
- ✅ 重构 `EnemySpawner` 使用依赖注入

#### Phase 3: GameScene 拆分
- ✅ 创建 `GameController` - 游戏主控制器
- ✅ 创建 `SpawnController` - 生成控制器
- ✅ 创建 `CollisionController` - 碰撞控制器
- ✅ 创建 `GameRenderer` - 游戏渲染器
- ✅ 创建 `NotificationManager` - 通知系统
- ✅ 提取 `RewardSelector` 到独立模块
- ✅ GameScene 集成所有新组件

#### Phase 4: RewardSystem 重构
- ✅ 创建 `Buff` 基类和 `BuffResult`
- ✅ 实现所有 `Buff` 具体类（15个）
- ✅ 创建 `BuffRegistry` 注册表
- ✅ 重构 `RewardSystem` 使用策略模式

---

## 🏗️ 架构设计概览

### 设计原则

本项目严格遵循以下架构设计原则：

| 原则 | 描述 | 实施状态 |
|------|------|----------|
| **单一职责 (SRP)** | 每个类/函数只负责一件事 | ✅ 完全遵循 |
| **开闭原则 (OCP)** | 对扩展开放，对修改关闭 | ✅ 通过策略模式实现 |
| **里氏替换 (LSP)** | 子类可替换父类而不影响功能 | ✅ 接口规范一致 |
| **依赖倒置 (DIP)** | 依赖抽象而非具体实现 | ✅ 使用接口和依赖注入 |
| **接口隔离 (ISP)** | 客户依赖最小接口 | ✅ IBulletSpawner 等 |

### 核心模块职责

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                  │
│                      (入口点，仅调度)                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
         ┌─────────────────┴──────────────────┐
         ▼                                    ▼
┌─────────────────────┐          ┌─────────────────────┐
│   SceneManager      │          │   SceneDirector     │
│   (场景管理)         │          │   (场景协调)        │
└─────────┬───────────┘          └─────────┬───────────┘
          │                                │
    ┌─────┴─────┬──────┬───────┐     ┌─────┴──────┐
    ▼           ▼      ▼       ▼     ▼           ▼
┌──────┐  ┌────────┐ ┌─────┐ ┌──────┐  ┌──────────────┐
│Login │  │ Menu   │ │Game │ │Pause │  │ GameOver    │
│Scene │  │ Scene  │ │Scene│ │Scene │  │ Scene       │
└──────┘  └────────┘ └─────┘ └──────┘  └──────────────┘
```

### GameScene 内部架构

```
┌────────────────────────────────────────────────────────────────────┐
│                         GameScene                                   │
│                    (游戏主场景，协调者)                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────┐    ┌─────────────────┐    ┌────────────────┐│
│  │   Player        │    │   EnemySpawner   │    │  Boss           ││
│  │   (玩家实体)    │    │   (敌人生成器)   │    │  (Boss实体)     ││
│  └────────┬────────┘    └────────┬─────────┘    └───────┬────────┘│
│           │                     │                     │          │
│  ┌────────┴────────┐    ┌───────┴────────┐    ┌───────┴─────────┐│
│  │ InputHandler   │    │ IBulletSpawner │    │ IBulletSpawner  ││
│  │ (输入抽象)      │    │ (子弹生成接口)  │    │ (子弹生成接口)  ││
│  └─────────────────┘    └────────────────┘    └────────────────┘│
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐
│  │                     GameController                              │
│  │                  (游戏主控制器，管理游戏状态)                   │
│  ├─────────────────────────────────────────────────────────────────┤
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  │HealthSystem │  │ Notification│  │ update_ripples()        │ │
│  │  │(生命系统)   │  │ Manager     │  │ (涟漪效果管理)          │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│  └─────────────────────────────────────────────────────────────────┘
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐
│  │                   SpawnController                              │
│  │                     (生成控制器)                                 │
│  ├─────────────────────────────────────────────────────────────────┤
│  │  ┌─────────────────────┐  ┌──────────────────────────────────┐│
│  │  │ EnemyBulletSpawner   │  │ enemy_bullets                     ││
│  │  │ (敌弹生成器)         │  │ (敌弹列表，GameScene引用)         ││
│  │  └─────────────────────┘  └──────────────────────────────────┘│
│  └─────────────────────────────────────────────────────────────────┘
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 接口规范

### 核心接口列表

| 接口名 | 位置 | 职责 | 方法签名 |
|--------|------|------|----------|
| `InputHandler` | `airwar/input/input_handler.py` | 输入抽象 | `get_direction()`, `is_fire_pressed()`, `is_pause_pressed()` |
| `IBulletSpawner` | `airwar/entities/interfaces.py` | 子弹生成 | `spawn_bullet(bullet: Bullet)` |
| `IScene` | `airwar/scenes/scene.py` | 场景基类 | `enter()`, `handle_events()`, `update()`, `render()`, `exit()` |
| `IBuff` | `airwar/game/buffs/base_buff.py` | Buff基类 | `apply(target, current_round)`, `get_description()` |
| `IRewardStrategy` | `airwar/game/systems/reward_system.py` | 奖励策略 | `select_rewards(score, round_count)` |

### InputHandler 接口规范

```python
class InputHandler(ABC):
    """输入处理抽象接口"""

    @abstractmethod
    def get_movement_direction(self) -> Vector2:
        """
        获取移动方向
        Returns:
            Vector2: (x方向, y方向)，值为 -1, 0, 1
        """

    @abstractmethod
    def is_pause_pressed(self) -> bool:
        """是否按下暂停键"""

    @abstractmethod
    def is_quit_requested(self) -> bool:
        """是否请求退出游戏"""
```

### IBulletSpawner 接口规范

```python
class IBulletSpawner(ABC):
    """子弹生成抽象接口"""

    def spawn_bullet(self, bullet: Bullet) -> None:
        """
        生成子弹
        Args:
            bullet: 要生成的子弹实例
        Note:
            实现类应将子弹添加到游戏世界的子弹列表中
        """
        raise NotImplementedError
```

---

## 📋 代码审查清单

### 新增代码必须满足

- [ ] 每个类都有单一、清晰的职责（能用一句话描述）
- [ ] 所有公共API通过接口/抽象类暴露
- [ ] 没有魔法数字，所有常量已命名
- [ ] 没有函数超过40行（超过需拆分）
- [ ] 没有超过3层嵌套（超过需重构）
- [ ] 没有重复代码超过3处（需提取到工具函数或基类）
- [ ] 没有跨模块直接访问内部状态
- [ ] 底层库调用已封装在抽象层中
- [ ] 游戏逻辑独立于渲染/输入/UI
- [ ] 配置已集中管理

### 禁止的 Anti-Patterns

| Anti-Pattern | 检测方法 | 解决方案 |
|--------------|----------|----------|
| God Class | 类名包含"Manager"且方法>10 | 按职责拆分 |
| 魔法数字 | 搜索 `if .* > [0-9]+` | 提取为常量 |
| 硬编码依赖 | 直接 `import` 具体类 | 使用接口/抽象 |
| 分散逻辑 | 同一功能在多个文件 | 集中到单一模块 |
| 深层嵌套 | 4层以上 if/while | 使用卫句/提取方法 |
| 长函数 | >40行 | 拆分辅助函数 |
| 全局状态 | 跨模块 mutable 变量 | 集中到状态管理器 |
| 泄露抽象 | 暴露 pygame 细节 | 封装接口 |

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 变量 | snake_case，描述性 | `player_health`, `bullet_list` |
| 函数 | snake_case，动词 | `update_position`, `spawn_enemy` |
| 类 | PascalCase，名词 | `Player`, `EnemySpawner` |
| 常量 | UPPER_SNAKE_CASE | `MAX_HEALTH`, `FPS` |
| 私有成员 | 前缀 `_` | `_internal_state` |

---

## 🛠️ 维护指南

### 添加新Buff步骤

1. 在 `airwar/game/buffs/` 下创建新文件
2. 继承 `Buff` 基类
3. 实现 `apply()` 和 `get_description()` 方法
4. 在 `BuffRegistry` 中注册

```python
# 示例：新增护盾Buff
class ShieldBuff(Buff):
    def __init__(self):
        super().__init__("Shield", "SHD", BuffType.DEFENSE)

    def apply(self, target: 'Player', current_round: int) -> BuffResult:
        target.is_shielded = True
        return BuffResult(
            applied=True,
            description="获得护盾，抵挡下一次攻击",
            health_gained=0
        )
```

### 添加新敌人类型步骤

1. 在 `EnemyData` 或 `BossData` 添加数据类
2. 在 `Enemy._create_bullets()` 添加攻击模式
3. 在 `DifficultySettings` 配置参数
4. 添加对应测试用例

### 调试技巧

| 场景 | 调试方法 |
|------|----------|
| 子弹不发射 | 检查 `_bullet_spawner` 是否为 None |
| 涟漪不扩散 | 检查 `GameController.update()` 是否调用 `update_ripples()` |
| 碰撞检测失败 | 检查 `rect.colliderect()` 坐标是否正确 |
| 测试失败 | 使用 `pytest -v --tb=short` 查看详细错误 |

---

## 📊 测试覆盖

当前测试数量：**150 个**

| 测试文件 | 测试数量 | 覆盖内容 |
|----------|----------|----------|
| test_config.py | 12 | 配置系统 |
| test_database.py | 9 | 用户数据库 |
| test_entities.py | 30 | 实体类（玩家/敌人/Boss/子弹） |
| test_integration.py | 47 | 集成测试 |
| test_rewards.py | 11 | 奖励系统 |
| test_scenes.py | 11 | 场景类 |
| test_scene_director.py | 31 | 场景管理器 |

**所有测试通过** ✅

---

## 🎮 游戏特色

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

---

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

---

## 配置说明

游戏配置文件位于 `airwar/config/settings.py`：

```python
# 屏幕设置
SCREEN_WIDTH = 1400      # 默认宽度
SCREEN_HEIGHT = 800      # 默认高度
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

---

## 运行测试

### 运行所有测试

```bash
pytest airwar/tests/ -v
```

---

## 项目结构

```
airwar/
├── config/
│   ├── __init__.py
│   └── settings.py       # 游戏配置
├── entities/
│   ├── __init__.py
│   ├── base.py          # 基础实体类、数据类
│   ├── bullet.py        # 子弹类
│   ├── enemy.py         # 敌人和Boss类
│   ├── interfaces.py     # 实体接口
│   └── player.py         # 玩家类
├── input/                # 输入处理模块
│   ├── __init__.py
│   └── input_handler.py  # InputHandler接口和实现
├── scenes/
│   ├── __init__.py
│   ├── game_scene.py     # 游戏主场景
│   ├── login_scene.py    # 登录场景
│   ├── menu_scene.py     # 菜单场景
│   ├── pause_scene.py    # 暂停场景
│   └── scene.py          # 场景基类
├── game/
│   ├── __init__.py
│   ├── game.py          # 游戏主类
│   ├── buffs/           # Buff系统
│   │   ├── __init__.py
│   │   ├── base_buff.py      # Buff基类和结果
│   │   ├── buff_registry.py  # Buff注册表
│   │   ├── health_buffs.py   # 生命类Buff
│   │   ├── offense_buffs.py # 攻击类Buff
│   │   ├── defense_buffs.py # 防御类Buff
│   │   └── utility_buffs.py # 工具类Buff
│   ├── controllers/      # 游戏控制器
│   │   ├── __init__.py
│   │   ├── game_controller.py   # 游戏主控制器
│   │   ├── spawn_controller.py   # 生成控制器
│   │   └── collision_controller.py # 碰撞控制器
│   ├── rendering/       # 渲染层
│   │   ├── __init__.py
│   │   └── game_renderer.py      # 游戏渲染器
│   ├── spawners/         # 生成器
│   │   ├── __init__.py
│   │   └── enemy_bullet_spawner.py # 敌弹生成器
│   └── systems/
│       ├── __init__.py
│       ├── health_system.py      # 生命系统
│       ├── hud_renderer.py       # HUD渲染器
│       ├── notification_manager.py # 通知管理器
│       └── reward_system.py      # 奖励系统
├── ui/
│   ├── __init__.py
│   ├── game_over_screen.py  # 游戏结束界面
│   └── reward_selector.py   # 奖励选择器
├── utils/
│   ├── __init__.py
│   ├── database.py       # 用户数据库
│   └── sprites.py        # 精灵绘制
└── tests/
    ├── __init__.py
    ├── test_config.py
    ├── test_database.py
    ├── test_entities.py
    ├── test_integration.py
    ├── test_rewards.py
    ├── test_scenes.py
    └── test_scene_director.py
```

---

## 重构说明

### 2026-04-15 架构师重构

本项目进行了架构师技能强制重构，解决了以下问题：

#### 🔴 高优先级问题（已修复）

| 问题 | 文件 | 解决方案 |
|------|------|----------|
| **150+行属性转发代码** | `game_scene.py` | 精简保留必要属性，删除重复代码 |
| **Boss生成逻辑重复** | `game_scene.py` | 删除 `_spawn_boss`，委托 `SpawnController` |
| **90%重复射击代码** | `player.py` | 提取 `_create_bullets_for_shot_mode()` 方法 |

#### 🟡 中优先级问题（已修复）

| 问题 | 文件 | 解决方案 |
|------|------|----------|
| **if-elif 链** | `reward_system.py` | 使用字典映射和策略模式 |
| **魔法数字** | `enemy.py`, `settings.py` | 提取为常量（ENEMY_BULLET_DAMAGE等）|

#### ✅ 验证结果

- **测试通过率**: 150/150 (100%)
- **代码行数减少**: GameScene.py 从 524 行减少到 405 行
- **DRY 原则**: 消除所有明显重复代码
- **可维护性**: 显著提升

### 2026-04-15 UI 风格统一与窗口尺寸优化

本项目完成了 UI 界面风格统一和窗口尺寸优化：

#### 🎨 UI 风格统一

所有游戏界面现在采用统一的赛博朋克/霓虹灯风格：

| 界面 | 星空背景 | 面板容器 | 霓虹发光 | 简化箭头 | 统一风格 |
|------|----------|----------|----------|----------|----------|
| **LoginScene** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **MenuScene** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **PauseScene** | ✅ | ❌ (全屏) | ✅ | ✅ | ✅ |
| **RewardSelector** | ✅ | ✅ | ✅ | ✅ | ✅ |

#### 🔧 界面改进详情

| 界面 | 改进内容 | 架构原则 |
|------|----------|----------|
| **LoginScene** | 面板容器、输入框发光、按钮悬停效果 | 单一职责 ✅ |
| **MenuScene** | 面板容器、简化布局、增大间距 | 单一职责 ✅ |
| **PauseScene** | 星空背景、霓虹发光、粒子装饰 | 单一职责 ✅ |
| **RewardSelector** | 星空背景、面板容器、简化信息展示 | 单一职责 ✅ |

#### 📐 窗口尺寸优化

| 参数 | 修改前 | 修改后 | 改进 |
|------|--------|--------|------|
| **宽度** | 1200px | 1400px | +200px (+16.7%) |
| **高度** | 700px | 800px | +100px (+14.3%) |
| **面积** | 840,000 px² | 1,120,000 px² | +33.3% |

#### ✅ UI 优化结果

- **测试通过率**: 150/150 (100%)
- **视觉体验**: 元素不再拥挤，留白充足
- **风格一致**: 所有界面采用统一的赛博朋克风格
- **架构标准**: 严格遵循架构师技能的所有原则

### 重构目标

- ✅ 消除上帝类 (God Class)
- ✅ 实现完全解耦
- ✅ 遵循开闭原则
- ✅ 提升可测试性
- ✅ 保持功能完全兼容

### 关键改进

1. **输入解耦** - Player 通过 `InputHandler` 抽象获取输入
2. **策略模式** - RewardSystem 使用 Buff 策略，支持扩展
3. **依赖注入** - 所有组件通过接口通信，降低耦合
4. **子系统分离** - 游戏逻辑拆分为多个独立子系统
5. **单一职责** - 各模块职责清晰，代码可维护性显著提升

---

## License

MIT License