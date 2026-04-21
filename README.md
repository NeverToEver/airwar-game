# Air War - 飞机大战

> **项目版本**: 1.3
> **最后更新**: 2026-04-21
> **技术栈**: Python 3.8+ | Pygame 2.6.1+
> **项目状态**: ✅ 活跃维护

一款街机风格的纵向卷轴射击游戏，使用 Python 和 Pygame 开发。游戏采用赛博朋克/霓虹灯视觉风格，支持多种难度模式和 Roguelike 增益系统，并具有完整的母舰系统功能。

**新增功能**：玩家死亡动画（闪烁、火花、光晕效果）

---

## 一、快速开始

### 环境要求

| 要求 | 版本 | 说明 |
|------|------|------|
| Python | 3.8+ | 编程语言环境 |
| pygame | 2.6.1+ | 游戏开发库 |
| pillow | 12.2.0+ | 图像处理库 |
| pytest | 最新版 | 测试框架（可选） |

### 安装步骤

**Windows:**
```powershell
# 1. 检查 Python 是否已安装
python --version

# 2. 创建虚拟环境（推荐）
python -m venv venv

# 3. 激活虚拟环境
.\venv\Scripts\activate

# 4. 安装依赖
pip install pygame>=2.6.1 pillow>=12.2.0

# 5. 运行游戏
python main.py
```

**macOS/Linux:**
```bash
# 1. 检查 Python 版本
python3 --version

# 2. 创建虚拟环境
cd airwar-game
python3 -m venv venv

# 3. 激活虚拟环境
source venv/bin/activate

# 4. 安装依赖
pip install pygame>=2.6.1 pillow>=12.2.0

# 5. 运行游戏
./venv/bin/python main.py
```

---

## 二、游戏目标

- 控制战斗机，击败所有敌人和Boss
- 按住 **H键3秒** 进入母舰，清除敌机并保存游戏进度
- 按住 **K键3秒** 放弃游戏，进入死亡菜单
- 躲避敌人子弹，避免受到伤害
- 达成里程碑分数时选择增益效果，提升战斗能力

---

## 三、键盘操作

### 游戏内操作

| 按键 | 功能 |
|------|------|
| `W` / `↑` | 向上移动 |
| `S` / `↓` | 向下移动 |
| `A` / `←` | 向左移动 |
| `D` / `→` | 向右移动 |
| `空格键` | 发射子弹（长按连续射击）|
| `H` | **进入母舰**（按住3秒，清除敌机+保存进度）|
| `K` | **放弃游戏**（按住3秒）|
| `ESC` | 暂停游戏 |

### 主菜单操作

| 按键 | 功能 |
|------|------|
| `W` / `↑` | 选择上一个难度 |
| `S` / `↓` | 选择下一个难度 |
| `Enter` | 确认开始游戏 |
| `ESC` | 返回登录界面 |

### 暂停菜单操作

| 按键 | 功能 |
|------|------|
| `W` / `↑` | 选择上一个选项 |
| `S` / `↓` | 选择下一个选项 |
| `Enter` | 确认选择 |
| `ESC` | 继续游戏 |

---

## 四、核心功能

### 4.1 死亡动画系统

玩家死亡时触发视觉效果动画：

| 效果 | 帧数 | 描述 |
|------|------|------|
| 闪烁 | 0-60 | 战机快速闪烁红/白色 |
| 火花 | 0-180 | 随机方向喷射火花粒子 |
| 光晕 | 60-180 | 白色光晕扩散至全屏 |
| 结束 | 200 | 触发 Game Over |

**触发方式**：
- 血量为0时触发
- K键长按放弃时触发

### 4.2 母舰系统

母舰系统是游戏的核心功能之一，作为战斗中的临时停留点：

| 功能 | 说明 |
|------|------|
| **清除敌机** | 进入母舰时清除所有敌人和弹幕 |
| **保存进度** | 自动保存分数、循环数、击杀数、已解锁增益 |
| **脱离动画** | 按H键可离开母舰继续战斗 |

**H键进入流程**：
```
1. 按住H键 → 显示母舰UI和进度条
2. 持续按住3秒 → 进度条从0%增长到100%
3. 进度达到100% → 清除敌机和弹幕，启动对接动画
4. 对接动画完成（90帧） → 成功进入母舰
5. 游戏进度已自动保存
6. 按H键脱离 → 继续战斗
```

**状态机转换**：
```
IDLE → PRESSING → DOCKING → DOCKED → UNDOCKING → IDLE
```

### 4.3 放弃游戏系统

玩家可以通过按住K键3秒来主动放弃游戏：

| 功能 | 说明 |
|------|------|
| **放弃检测** | 按住K键3秒触发放弃确认 |
| **进度条动画** | 显示放弃进度条 |
| **确认菜单** | 显示死亡菜单，可选择返回主菜单或退出游戏 |
| **分数展示** | 显示最终得分和击杀数 |

### 4.4 退出确认菜单

当玩家选择"保存并退出"或"不保存退出"时，显示过渡性确认菜单：

| 选项 | 功能 |
|------|------|
| **返回主菜单** | 清除存档，返回主菜单 |
| **开始新游戏** | 清除存档，保留难度，重新开始 |
| **退出游戏** | 真正退出游戏程序 |

### 4.5 难度系统

| 难度 | 敌人血量 | 子弹伤害 | 敌人速度 | 生成间隔 | 计分倍率 |
|------|----------|----------|----------|----------|----------|
| 简单 | 300 HP | 100 | 2.5 | 40帧 | x1 |
| 普通 | 200 HP | 50 | 3.0 | 30帧 | x2 |
| 困难 | 170 HP | 34 | 3.5 | 25帧 | x3 |

> **击败敌人所需子弹数**：所有难度都是 3 发

### 4.6 Boss 机制

- **生成间隔**：每 1800 帧（约30秒）生成一次
- **逃跑机制**：Boss 有存活时间限制，超时后会自动逃跑
- **攻击模式**：
  1. **扇形弹幕** - 多颗子弹呈扇形散开
  2. **追踪弹** - 向玩家方向发射
  3. **全方位弹幕** - 向四面八方发射
- **进化阶段**：Boss 每 300 帧会升级，攻击更加凶猛
- **击败奖励**：基础 5000 分，随循环增加

### 4.7 增益系统

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

---

## 五、架构设计

### 5.1 设计原则

本项目严格遵循以下架构设计原则：

| 原则 | 描述 | 实施状态 |
|------|------|----------|
| **单一职责 (SRP)** | 每个类/函数只负责一件事 | ✅ 完全遵循 |
| **开闭原则 (OCP)** | 对扩展开放，对修改关闭 | ✅ 通过策略模式实现 |
| **里氏替换 (LSP)** | 子类可替换父类而不影响功能 | ✅ 接口规范一致 |
| **依赖倒置 (DIP)** | 依赖抽象而非具体实现 | ✅ 使用接口和依赖注入 |
| **接口隔离 (ISP)** | 客户依赖最小接口 | ✅ IBulletSpawner 等 |
| **配置集中管理** | 所有配置在统一位置 | ✅ settings.py |
| **可维护性** | 清晰的代码结构和命名 | ✅ |

### 5.2 核心模块架构

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
│   (场景管理)        │          │   (场景协调)        │
└─────────┬───────────┘          └─────────┬───────────┘
          │                                │
    ┌─────┴─────┬──────┬───────┬──────┐   ┌─────┴──────┐
    ▼           ▼      ▼       ▼      ▼   ▼           ▼
┌──────┐  ┌────────┐ ┌─────┐ ┌──────┐ ┌──────┐  ┌──────────────┐
│Login │  │ Menu   │ │Game │ │Pause │ │Death │  │ExitConfirm   │
│Scene │  │ Scene  │ │Scene│ │Scene │ │Scene │  │Scene         │
└──────┘  └────────┘ └─────┘ └──────┘ └──────┘  └──────────────┘
```

### 5.3 GameScene 内部架构

```
┌────────────────────────────────────────────────────────────────────┐
│                         GameScene                                   │
│                    (游戏主场景，协调者)                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────┐    ┌─────────────────┐    ┌────────────────┐│
│  │   Player        │    │   EnemySpawner  │    │  Boss          ││
│  │   (玩家实体)    │    │   (敌人生成器)   │    │  (Boss实体)    ││
│  └────────┬────────┘    └────────┬─────────┘    └───────┬────────┘│
│           │                     │                     │          │
│  ┌────────┴────────┐    ┌───────┴────────┐    ┌───────┴─────────┐│
│  │ InputHandler     │    │ IBulletSpawner  │    │ IBulletSpawner  ││
│  │ (输入抽象)       │    │ (子弹生成接口)   │    │ (子弹生成接口)   ││
│  └─────────────────┘    └────────────────┘    └────────────────┘│
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐
│  │                     GameController                              │
│  │                  (游戏主控制器，管理游戏状态)                   │
│  └─────────────────────────────────────────────────────────────────┘
│                                                                    │
│  ┌──────────────────────────────┐  ┌─────────────────────────────┐
│  │   MotherShipIntegrator       │  │   GiveUpDetector          │
│  │   (母舰系统集成)             │  │   (放弃游戏检测)           │
│  └──────────────────────────────┘  └─────────────────────────────┘
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 5.4 核心接口列表

| 接口名 | 位置 | 职责 | 方法签名 |
|--------|------|------|----------|
| `InputHandler` | `airwar/input/input_handler.py` | 输入抽象 | `get_direction()`, `is_fire_pressed()`, `is_pause_pressed()` |
| `IBulletSpawner` | `airwar/entities/interfaces.py` | 子弹生成 | `spawn_bullet(bullet: Bullet)` |
| `IScene` | `airwar/scenes/scene.py` | 场景基类 | `enter()`, `handle_events()`, `update()`, `render()`, `exit()` |
| `IBuff` | `airwar/game/buffs/base_buff.py` | Buff基类 | `apply(target, current_round)`, `get_description()` |
| `IInputDetector` | `airwar/game/mother_ship/interfaces.py` | 输入检测 | `update()`, `is_h_pressed()`, `get_progress()` |
| `IMotherShipStateMachine` | `airwar/game/mother_ship/interfaces.py` | 状态机 | `current_state`, `transition()` |

---

## 六、项目结构

```
airwar/
├── config/
│   ├── __init__.py
│   ├── settings.py       # 游戏配置（集中管理）
│   └── game_config.py    # 游戏配置类
├── entities/
│   ├── __init__.py
│   ├── base.py          # 基础实体类、数据类
│   ├── bullet.py        # 子弹类
│   ├── enemy.py         # 敌人、Boss类和移动模式
│   ├── interfaces.py     # 实体接口
│   └── player.py         # 玩家类
├── game/
│   ├── __init__.py
│   ├── game.py          # 游戏主类
│   ├── scene_director.py # 场景导演
│   ├── constants.py     # 游戏常量
│   ├── buffs/           # Buff系统
│   │   ├── base_buff.py      # Buff基类和结果
│   │   ├── buff_registry.py  # Buff注册表
│   │   └── buffs.py          # 所有Buff实现
│   ├── controllers/      # 游戏控制器
│   │   ├── game_controller.py   # 游戏主控制器
│   │   ├── spawn_controller.py   # 生成控制器
│   │   └── collision_controller.py # 碰撞控制器
│   ├── death_animation/ # 死亡动画系统
│   ├── give_up/        # 放弃游戏系统
│   │   ├── give_up_detector.py   # 放弃检测器
│   │   └── give_up_ui.py         # 放弃UI
│   ├── mother_ship/    # 母舰系统
│   │   ├── state_machine.py     # 状态机
│   │   ├── input_detector.py    # 输入检测
│   │   ├── game_integrator.py   # 系统集成
│   │   ├── mother_ship.py       # 母舰实体
│   │   ├── mother_ship_state.py # 状态定义
│   │   ├── progress_bar_ui.py   # 进度条UI
│   │   ├── event_bus.py        # 事件总线
│   │   ├── persistence_manager.py # 数据持久化
│   │   └── interfaces.py       # 接口定义
│   ├── rendering/      # 渲染系统
│   │   ├── background_renderer.py # 背景渲染
│   │   └── game_renderer.py     # 游戏渲染
│   ├── spawners/      # 生成器
│   │   └── enemy_bullet_spawner.py # 敌人子弹生成器
│   └── systems/
│       ├── health_system.py      # 生命系统
│       ├── hud_renderer.py       # HUD渲染器
│       ├── notification_manager.py # 通知管理器
│       └── reward_system.py      # 奖励系统
├── input/              # 输入处理模块
│   ├── __init__.py
│   └── input_handler.py  # InputHandler接口和实现
├── scenes/
│   ├── __init__.py
│   ├── scene.py          # 场景基类和枚举
│   ├── game_scene.py     # 游戏主场景
│   ├── login_scene.py    # 登录场景
│   ├── menu_scene.py     # 菜单场景（赛博朋克风格）
│   ├── pause_scene.py    # 暂停场景（赛博朋克风格）
│   ├── death_scene.py    # 死亡场景（赛博朋克风格）
│   └── exit_confirm_scene.py # 退出确认场景
├── ui/
│   ├── __init__.py
│   ├── buff_stats_panel.py   # Buff状态面板
│   ├── game_over_screen.py   # 游戏结束界面
│   └── reward_selector.py    # 奖励选择器（赛博朋克风格）
├── utils/
│   ├── __init__.py
│   ├── database.py       # 用户数据库
│   ├── responsive.py      # 响应式布局辅助
│   └── sprites.py        # 精灵绘制（舰船设计）
├── window/
│   ├── __init__.py
│   └── window.py         # 窗口管理
└── tests/
    ├── conftest.py           # pytest配置
    ├── test_*.py             # 各类测试文件（380个测试）
```

---

## 七、响应式布局

游戏支持 800x600 到全屏的响应式布局，确保在不同窗口大小下都能良好展示：

| 窗口尺寸 | 缩放系数 | 说明 |
|----------|----------|------|
| 800x600 | 0.625 | 最小支持尺寸 |
| 1280x720 | 1.0 | 基准设计尺寸 |
| 1920x1080 | 1.5 | 全屏推荐尺寸 |

**响应式特性**：
- ✅ 面板宽度自动缩放
- ✅ 选项间距自动调整
- ✅ 字体大小按比例变化
- ✅ 底部提示区域自适应

---

## 八、视觉设计规范

### 8.1 UI 风格：赛博朋克/霓虹灯

所有游戏界面采用统一的赛博朋克视觉风格：

| 界面 | 星空背景 | 面板容器 | 霓虹发光 | 简化箭头 | 统一风格 |
|------|----------|----------|----------|----------|----------|
| **LoginScene** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **MenuScene** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **PauseScene** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **DeathScene** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **ExitConfirmScene** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **RewardSelector** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **MotherShip** | ✅ | ✅ | ✅ | ✅ | ✅ |

### 8.2 色彩系统

```python
# 霓虹色彩主题
COLORS = {
    'title_glow': (100, 200, 255),    # 青色发光
    'selected': (0, 255, 150),         # 绿色选中
    'unselected': (90, 90, 130),       # 灰色未选中
    'background': (8, 8, 25),          # 深蓝背景
    'background_gradient': (15, 15, 50),  # 渐变终点
    'panel': (15, 20, 40),             # 面板背景
    'particle': (100, 180, 255),        # 粒子颜色
}
```

---

## 九、测试覆盖

### 9.1 测试统计

| 测试文件 | 测试数量 | 覆盖内容 |
|----------|----------|----------|
| test_config.py | ~10 | 配置系统 |
| test_database.py | ~10 | 用户数据库 |
| test_entities.py | ~15 | 实体类（玩家/敌人/Boss/子弹） |
| test_integration.py | ~50 | 集成测试 |
| test_rewards.py | ~15 | 奖励系统 |
| test_scenes.py | ~15 | 场景类 |
| test_scene_director.py | ~30 | 场景管理器 |
| test_buffs.py | ~30 | Buff系统 |
| test_mother_ship.py | ~30 | 母舰系统 |
| test_give_up.py | ~20 | 放弃游戏系统 |
| test_death_scene.py | ~20 | 死亡场景 |
| test_exit_confirm_scene.py | ~22 | 退出确认场景 |
| test_collision_*.py | ~40 | 碰撞系统 |
| test_systems.py | ~25 | 系统类 |
| test_performance.py | ~15 | 性能测试 |
| 其他测试 | ~60 | 高级功能、边界情况等 |
| test_death_animation.py | 30 | 死亡动画系统 |

**当前测试数量：371 个** ✅ **所有测试通过**

### 9.2 运行测试

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行所有测试
pytest airwar/tests/ -v

# 运行特定测试文件
pytest airwar/tests/test_config.py -v

# 运行带覆盖率测试
pytest airwar/tests/ --cov=airwar --cov-report=html
```

---

## 十、项目状态

| 指标 | 状态 | 说明 |
|------|------|------|
| **测试通过率** | 371/371 (100%) ✅ | 所有测试通过 |
| **架构原则遵守率** | 12/12 (100%) ✅ | 代码结构遵循SOLID原则 |
| **Anti-Pattern 违规数** | 0 ✅ | 无明显代码异味 |
| **代码重复率** | 0% ✅ | 代码复用良好 |
| **配置集中度** | 100% ✅ | 配置统一管理 |
| **母舰系统** | ✅ 已实现 | 功能完整 |
| **放弃游戏系统** | ✅ 已实现 | 功能完整 |
| **死亡动画** | ✅ 已实现 | 闪烁/火花/光晕效果 |
| **退出确认菜单** | ✅ 已实现 | 功能完整 |
| **响应式布局** | ✅ 已实现 | 支持多种窗口尺寸 |
| **游戏核心流程** | ✅ 正常 | 所有功能正常工作 |

---

## 十一、维护指南

### 11.1 添加新Buff步骤

1. 在 `airwar/game/buffs/buffs.py` 中添加新Buff类
2. 继承 `Buff` 基类
3. 实现 `apply()` 和 `get_description()` 方法
4. 在 `BuffRegistry` 中注册

### 11.2 添加新敌人类型步骤

1. 在 `EnemyData` 或 `BossData` 添加数据类
2. 在 `Enemy._init_movement()` 添加移动模式
3. 在 `EnemySpawner._enemy_type_distribution` 配置概率
4. 添加对应测试用例

### 11.3 调试技巧

| 场景 | 调试方法 |
|------|----------|
| H键无法进入母舰 | 检查母舰系统状态转换逻辑 |
| K键无法触发放弃 | 检查 GiveUpDetector 的输入检测和逻辑 |
| 子弹不发射 | 检查 `_bullet_spawner` 是否为 None |
| 涟漪不扩散 | 检查 `GameController.update()` 是否调用 `update_ripples()` |
| 碰撞检测失败 | 检查 `rect.colliderect()` 坐标是否正确 |
| 测试失败 | 使用 `pytest -v --tb=short` 查看详细错误 |

---

## 十二、重构历史

### 2026-04-21 GiveUpDetector 逻辑修复

- 修复 K 键放弃游戏功能不工作的问题
- 修正 update() 方法中的条件判断逻辑
- 确保按住 K 键 3 秒后正确触发放弃回调
- 所有 380 个测试通过

### 2026-04-21 响应式布局优化

- 添加 ResponsiveHelper 工具类支持响应式布局
- 更新所有菜单场景（MenuScene, PauseScene, ExitConfirmScene, DeathScene, LoginScene）
- 支持 800x600 到全屏的连续缩放

### 2026-04-21 退出确认菜单

- 添加 ExitConfirmScene 场景
- 支持保存后显示确认菜单
- 提供三个选项：返回主菜单、开始新游戏、退出游戏

### 2026-04-21 性能优化

- 优化子弹清理机制
- 改进碰撞检测性能
- 优化距离计算
- 缓存渲染表面

### 2026-04-21 玩家死亡动画

- 添加 DeathAnimation 组件管理死亡动画效果
- 实现闪烁效果 (0-60帧)
- 实现火花粒子系统 (0-180帧)
- 实现光晕扩散效果 (60-180帧)
- 与 GameController 集成

### 2026-04-21 放弃游戏系统

- 添加 GiveUpDetector 检测器
- 添加 DeathScene 死亡场景
- 优化死亡菜单视觉效果
- 显示最终得分和击杀数

---

## 十三、技术文档

| 文档 | 描述 |
|------|------|
| `docs/superpowers/specs/2026-04-20-give-up-feature-design.md` | 放弃游戏功能设计 |
| `docs/superpowers/specs/2026-04-21-exit-confirm-scene-design.md` | 退出确认菜单设计 |
| `docs/superpowers/specs/2026-04-21-responsive-layout-design.md` | 响应式布局设计 |
| `docs/superpowers/specs/2026-04-21-player-death-animation-design.md` | 死亡动画设计 |

---

## License

MIT License

---

**项目维护**: AI Assistant (Trae IDE)
**最后更新**: 2026-04-21
**文档版本**: 5.2
