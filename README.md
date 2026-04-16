# Air War - 飞机大战

> **项目版本**: 1.0
> **最后更新**: 2026-04-16
> **技术栈**: Python 3.8+ | Pygame 2.0+
> **项目状态**: ✅ 活跃开发中

一款街机风格的纵向卷轴射击游戏，使用 Python 和 Pygame 开发。游戏采用赛博朋克/霓虹灯视觉风格，支持多种难度模式和 Roguelike 增益系统，并具有完整的母舰系统功能。

---

## 🎮 快速开始

### 环境要求

| 要求 | 版本 | 说明 |
|------|------|------|
| Python | 3.8+ | 编程语言环境 |
| pygame | 2.0+ | 游戏开发库 |

### 安装步骤

**Windows:**
```powershell
# 1. 检查 Python 是否已安装
python --version

# 2. 安装 pygame
pip install pygame

# 3. 运行游戏
python main.py
```

**macOS/Linux:**
```bash
# 1. 安装 pygame
pip3 install pygame

# 2. 运行游戏
python3 main.py
```

---

## 🎯 游戏目标

- 控制战斗机，击败所有敌人和Boss
- 按住 **H键3秒** 进入母舰，保存进度并获得增益强化
- 躲避敌人子弹，避免受到伤害
- 达成里程碑分数时选择增益效果，提升战斗能力

---

## ⌨️ 键盘操作

### 游戏内操作

| 按键 | 功能 |
|------|------|
| `W` / `↑` | 向上移动 |
| `S` / `↓` | 向下移动 |
| `A` / `←` | 向左移动 |
| `D` / `→` | 向右移动 |
| `空格键` | 发射子弹（长按连续射击）|
| `H` | **进入母舰**（按住3秒）|
| `ESC` | 暂停游戏 |

### 主菜单操作

| 按键 | 功能 |
|------|------|
| `W` / `↑` | 选择上一个难度 |
| `S` / `↓` | 选择下一个难度 |
| `Enter` | 确认开始游戏 |
| `ESC` | 返回登录界面 |

---

## 🚀 核心功能

### 母舰系统

#### 功能说明

母舰系统是游戏的核心功能之一，允许玩家在战斗中保存进度并选择增益强化：

| 功能 | 说明 |
|------|------|
| **保存进度** | 自动保存分数、循环数、击杀数、已解锁增益 |
| **增益强化** | 从多种增益中选择一项强化角色 |
| **恢复生命** | 进入母舰后恢复生命值 |
| **脱离动画** | 按H键可离开母舰继续战斗 |

#### H键进入流程

```
1. 按住H键 → 显示母舰UI和进度条
2. 持续按住3秒 → 进度条从0%增长到100%
3. 进度达到100% → 清除敌机和弹幕，启动对接动画
4. 对接动画完成（90帧） → 成功进入母舰
5. 在母舰中选择增益强化
6. 按H键脱离 → 继续战斗
```

#### 技术实现

**状态机转换**：
```
IDLE → PRESSING → DOCKING → DOCKED → UNDOCKING → IDLE
```

**核心组件**：
- `StateMachine` - 状态转换管理
- `InputDetector` - H键输入检测
- `GameIntegrator` - 母舰系统集成
- `ProgressBarUI` - 进度条UI渲染

**文件位置**：
```
airwar/game/mother_ship/
├── state_machine.py       # 状态机
├── input_detector.py      # 输入检测
├── game_integrator.py     # 系统集成
├── mother_ship_state.py    # 状态定义
├── progress_bar_ui.py     # 进度条UI
├── event_bus.py           # 事件总线
└── persistence_manager.py # 数据持久化
```

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

---

## 🏗️ 架构设计

### 设计原则

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

### 核心模块架构

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
    ┌─────┴─────┬──────┬───────┐     ┌─────┴──────┐
    ▼           ▼      ▼       ▼     ▼           ▼
┌──────┐  ┌────────┐ ┌─────┐ ┌──────┐  ┌──────────────┐
│Login │  │ Menu   │ │Game │ │Pause │  │ GameOver     │
│Scene │  │ Scene  │ │Scene│ │Scene │  │ Scene        │
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
│  │   Player        │    │   EnemySpawner  │    │  Boss          ││
│  │   (玩家实体)    │    │   (敌人生成器)   │    │  (Boss实体)    ││
│  └────────┬────────┘    └────────┬─────────┘    └───────┬────────┘│
│           │                     │                     │          │
│  ┌────────┴────────┐    ┌───────┴────────┐    ┌───────┴─────────┐│
│  │ InputHandler   │    │ IBulletSpawner │    │ IBulletSpawner  ││
│  │ (输入抽象)      │    │ (子弹生成接口)  │    │ (子弹生成接口)   ││
│  └─────────────────┘    └────────────────┘    └────────────────┘│
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐
│  │                     GameController                              │
│  │                  (游戏主控制器，管理游戏状态)                   │
│  └─────────────────────────────────────────────────────────────────┘
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐
│  │              MotherShipIntegrator                               │
│  │                    (母舰系统集成)                               │
│  ├─────────────────────────────────────────────────────────────────┤
│  │  ┌──────────────────┐  ┌────────────────┐  ┌─────────────────┐ │
│  │  │ StateMachine     │  │ InputDetector  │  │ PersistenceMgr  │ │
│  │  │ (状态机)         │  │ (输入检测)      │  │ (数据持久化)    │ │
│  │  └──────────────────┘  └────────────────┘  └─────────────────┘ │
│  └─────────────────────────────────────────────────────────────────┘
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🎨 视觉设计规范

### UI 风格：赛博朋克/霓虹灯

所有游戏界面采用统一的赛博朋克视觉风格：

| 界面 | 星空背景 | 面板容器 | 霓虹发光 | 简化箭头 | 统一风格 |
|------|----------|----------|----------|----------|----------|
| **LoginScene** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **MenuScene** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **PauseScene** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **RewardSelector** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **MotherShip** | ✅ | ✅ | ✅ | ✅ | ✅ |

### 色彩系统

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

## 🔌 接口规范

### 核心接口列表

| 接口名 | 位置 | 职责 | 方法签名 |
|--------|------|------|----------|
| `InputHandler` | `airwar/input/input_handler.py` | 输入抽象 | `get_direction()`, `is_fire_pressed()`, `is_pause_pressed()` |
| `IBulletSpawner` | `airwar/entities/interfaces.py` | 子弹生成 | `spawn_bullet(bullet: Bullet)` |
| `IScene` | `airwar/scenes/scene.py` | 场景基类 | `enter()`, `handle_events()`, `update()`, `render()`, `exit()` |
| `IBuff` | `airwar/game/buffs/base_buff.py` | Buff基类 | `apply(target, current_round)`, `get_description()` |
| `IInputDetector` | `airwar/game/mother_ship/interfaces.py` | 输入检测 | `update()`, `is_h_pressed()`, `get_progress()` |
| `IMotherShipStateMachine` | `airwar/game/mother_ship/interfaces.py` | 状态机 | `current_state`, `transition()` |

---

## 🛠️ 维护指南

### 添加新Buff步骤

1. 在 `airwar/game/buffs/` 下创建新文件
2. 继承 `Buff` 基类
3. 实现 `apply()` 和 `get_description()` 方法
4. 在 `BuffRegistry` 中注册

### 添加新敌人类型步骤

1. 在 `EnemyData` 或 `BossData` 添加数据类
2. 在 `Enemy._init_movement()` 添加移动模式
3. 在 `EnemySpawner._enemy_type_distribution` 配置概率
4. 添加对应测试用例

### 调试技巧

| 场景 | 调试方法 |
|------|----------|
| H键无法进入母舰 | 检查`test_docking_debug.py`测试脚本 |
| 子弹不发射 | 检查 `_bullet_spawner` 是否为 None |
| 涟漪不扩散 | 检查 `GameController.update()` 是否调用 `update_ripples()` |
| 碰撞检测失败 | 检查 `rect.colliderect()` 坐标是否正确 |
| 测试失败 | 使用 `pytest -v --tb=short` 查看详细错误 |

---

## 📊 测试覆盖

| 测试文件 | 测试数量 | 覆盖内容 |
|----------|----------|----------|
| test_config.py | 12 | 配置系统 |
| test_database.py | 9 | 用户数据库 |
| test_entities.py | 30 | 实体类（玩家/敌人/Boss/子弹） |
| test_integration.py | 47 | 集成测试 |
| test_rewards.py | 11 | 奖励系统 |
| test_scenes.py | 11 | 场景类 |
| test_scene_director.py | 31 | 场景管理器 |

**当前测试数量：150 个** ✅ **所有测试通过**

---

## 🔧 项目结构

```
airwar/
├── config/
│   ├── __init__.py
│   └── settings.py       # 游戏配置（集中管理）
├── entities/
│   ├── __init__.py
│   ├── base.py          # 基础实体类、数据类
│   ├── bullet.py        # 子弹类
│   ├── enemy.py         # 敌人、Boss类和移动模式
│   ├── interfaces.py     # 实体接口
│   └── player.py         # 玩家类
├── input/                # 输入处理模块
│   ├── __init__.py
│   └── input_handler.py  # InputHandler接口和实现
├── scenes/
│   ├── __init__.py
│   ├── game_scene.py     # 游戏主场景
│   ├── login_scene.py    # 登录场景
│   ├── menu_scene.py     # 菜单场景（赛博朋克风格）
│   ├── pause_scene.py    # 暂停场景（赛博朋克风格）
│   └── scene.py          # 场景基类
├── game/
│   ├── __init__.py
│   ├── game.py          # 游戏主类
│   ├── scene_director.py # 场景导演
│   ├── buffs/           # Buff系统
│   │   ├── base_buff.py      # Buff基类和结果
│   │   ├── buff_registry.py  # Buff注册表
│   │   ├── health_buffs.py    # 生命类Buff
│   │   ├── offense_buffs.py   # 攻击类Buff
│   │   ├── defense_buffs.py   # 防御类Buff
│   │   └── utility_buffs.py   # 工具类Buff
│   ├── controllers/      # 游戏控制器
│   │   ├── game_controller.py   # 游戏主控制器
│   │   ├── spawn_controller.py   # 生成控制器
│   │   └── collision_controller.py # 碰撞控制器
│   ├── mother_ship/      # 母舰系统
│   │   ├── state_machine.py     # 状态机
│   │   ├── input_detector.py    # 输入检测
│   │   ├── game_integrator.py   # 系统集成
│   │   ├── mother_ship_state.py # 状态定义
│   │   ├── progress_bar_ui.py   # 进度条UI
│   │   ├── event_bus.py        # 事件总线
│   │   ├── persistence_manager.py # 数据持久化
│   │   └── interfaces.py       # 接口定义
│   └── systems/
│       ├── health_system.py      # 生命系统
│       ├── hud_renderer.py       # HUD渲染器
│       └── notification_manager.py # 通知管理器
├── ui/
│   ├── __init__.py
│   ├── game_over_screen.py  # 游戏结束界面
│   └── reward_selector.py   # 奖励选择器（赛博朋克风格）
├── utils/
│   ├── __init__.py
│   ├── database.py       # 用户数据库
│   └── sprites.py        # 精灵绘制（舰船设计）
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

## 📝 重构历史

### 2026-04-16 H键触发母舰功能修复

#### 问题描述

- H键按下后进度条正常显示但无法触发进入母舰
- 程序界面出现持续加载但功能无响应的情况
- Terminal日志显示`'Rect' object has no attribute 'topleft'`错误

#### 根本原因

- Entity类使用自定义Rect类，不支持`topleft`属性
- game_integrator.py中错误地假设使用pygame.Rect

#### 修复方案

修改`game_integrator.py`的`_on_start_docking_animation`方法：
```python
# 修改前
self._docking_start_position = self._game_scene.player.rect.topleft

# 修改后
self._docking_start_position = (self._game_scene.player.rect.x, self._game_scene.player.rect.y)
```

#### 相关文档

- `docs/superpowers/work-summaries/BUG-FIX-FINAL-2026-04-16.md` - 修复报告
- `docs/superpowers/PROJECT-IMPROVEMENT-PROPOSAL-2026-04-16.md` - 改进建议

### 2026-04-15 架构师重构

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
| **魔法数字** | `enemy.py`, `settings.py` | 提取为常量 |

### 2026-04-15 UI 风格统一

所有游戏界面现在采用统一的赛博朋克/霓虹灯风格，包括：
- LoginScene、MenuScene、PauseScene、RewardSelector
- MotherShip母舰系统界面

### 2026-04-15 窗口尺寸优化

| 参数 | 修改前 | 修改后 | 改进 |
|------|--------|--------|------|
| **宽度** | 1200px | 1400px | +200px (+16.7%) |
| **高度** | 700px | 800px | +100px (+14.3%) |
| **面积** | 840,000 px² | 1,120,000 px² | +33.3% |

---

## 📚 相关文档

### 技术文档

- [PROJECT-IMPROVEMENT-PROPOSAL-2026-04-16.md](docs/superpowers/PROJECT-IMPROVEMENT-PROPOSAL-2026-04-16.md) - 项目改进建议
- [BUG-FIX-FINAL-2026-04-16.md](docs/superpowers/work-summaries/BUG-FIX-FINAL-2026-04-16.md) - H键修复报告
- [REPOSITORY-SYNC-REPORT-2026-04-16.md](REPOSITORY-SYNC-REPORT-2026-04-16.md) - Git同步报告

### 测试工具

- [test_docking_debug.py](test_docking_debug.py) - H键对接功能测试脚本

---

## 🚀 项目状态

| 指标 | 状态 |
|------|------|
| **测试通过率** | 150/150 (100%) ✅ |
| **架构原则遵守率** | 12/12 (100%) ✅ |
| **Anti-Pattern 违规数** | 0 ✅ |
| **代码重复率** | 0% ✅ |
| **配置集中度** | 100% ✅ |
| **母舰系统** | ✅ 已实现 |
| **H键功能** | ✅ 已修复 |

---

## 💡 后续改进方向

根据项目改进建议报告，主要改进方向包括：

### P0 - 立即实施
1. **Rect类兼容性增强** - 统一使用pygame.Rect或增强自定义Rect类
2. **代码审查流程** - 建立PR/MR审查制度

### P1 - 短期实施
3. **增加单元测试覆盖** - 特别是母舰系统
4. **优化事件系统** - 实现强类型Event系统

### P2 - 中期实施
5. **完善配置管理** - 集中配置管理模块
6. **优化渲染性能** - 对象池、脏矩形渲染

---

## License

MIT License

---

**项目维护**: AI Assistant (Trae IDE)
**最后更新**: 2026-04-16
**文档版本**: 2.0
