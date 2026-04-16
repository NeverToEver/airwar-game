# Mother Ship Docking System - Implementation Report

**Document Version:** 1.0
**Date:** 2026-04-16
**Author:** AI Assistant
**Task Reference:** Mother Ship Docking System Development

---

## 1. 改动背景与目的

### 1.1 项目背景

根据游戏设计文档 `2026-04-16-mother-ship-docking-system-design.md`，需要在现有的空战游戏 `airwar` 中实现母舰停靠系统。该系统允许玩家在战斗中召唤母舰、进入母舰进行存档、离开母舰继续战斗。

### 1.2 改动目的

1. **实现母舰召唤与停靠机制**：玩家长按 H 键 3 秒触发母舰召唤
2. **游戏状态持久化**：在母舰中存档，下次登录可恢复到母舰状态
3. **视觉效果优化**：重新设计母舰外观，提升游戏视觉品质
4. **动画系统完善**：实现平滑的进入/离开母舰动画

---

## 2. 具体实现方案

### 2.1 模块架构

新建 `airwar/game/mother_ship/` 模块，包含以下文件：

```
airwar/game/mother_ship/
├── __init__.py              # 模块导出
├── interfaces.py            # 抽象接口定义
├── mother_ship_state.py     # 状态数据结构
├── event_bus.py             # 事件总线
├── input_detector.py        # H键输入检测
├── state_machine.py         # 状态机
├── progress_bar_ui.py       # 进度条UI
├── persistence_manager.py    # 数据持久化
├── mother_ship.py           # 母舰渲染
└── game_integrator.py       # 游戏场景集成
```

### 2.2 核心功能实现

#### 2.2.1 状态机设计

状态转换图：

```
IDLE ──[H按下]──> PRESSING ──[3秒完成]──> DOCKING ──[动画完成]──> DOCKED
  ^                    │                                          │
  │                    │                                          │
  └──[松开/取消]───────┴──[H按下]──> UNDOCKING ──[动画完成]──────┘
```

关键状态：
- **IDLE**: 默认状态，正常游戏
- **PRESSING**: 检测 H 键按下，累积进度
- **DOCKING**: 执行进入母舰动画
- **DOCKED**: 已进入母舰，游戏暂停，可存档
- **UNDOCKING**: 执行离开母舰动画

#### 2.2.2 输入检测

`InputDetector` 类负责：
- 实时检测 H 键按下/释放状态
- 累积按压时间，计算进度百分比
- 通过 EventBus 发布事件：`H_PRESSED`、`H_RELEASED`、`PROGRESS_COMPLETE`

#### 2.2.3 数据持久化

`GameSaveData` 数据结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| score | int | 当前分数 |
| cycle_count | int | 循环计数 |
| kill_count | int | 击杀数 |
| unlocked_buffs | List[str] | 已解锁技能 |
| buff_levels | Dict[str, int] | 技能等级 |
| player_health | int | 玩家生命值 |
| difficulty | str | 难度设置 |
| is_in_mothership | bool | 是否在母舰中 |
| username | str | 用户名 |

存储路径：`airwar/data/user_docking_save.json`

#### 2.2.4 视觉效果

**母舰外观设计**：
- 多层船体：深色底 → 主色 → 高亮渐变
- 发动机光晕：脉冲动画效果
- 机翼细节：几何形状 + 装饰线条
- 驾驶舱：半透明玻璃 + 反射高光

**动画效果**：
- 进入动画：90帧，cubic ease-in-out
- 离开动画：60帧，quad ease-out
- 玩家控制：在动画期间禁用

---

## 3. 关键代码变更

### 3.1 新增文件

#### `airwar/game/mother_ship/__init__.py`
模块入口，导出所有公共接口和类。

#### `airwar/game/mother_ship/interfaces.py`
定义抽象接口：
- `IInputDetector`: 输入检测接口
- `IMotherShipUI`: UI接口
- `IEventBus`: 事件总线接口
- `IPersistenceManager`: 持久化管理接口
- `IMotherShipStateMachine`: 状态机接口

#### `airwar/game/mother_ship/event_bus.py`
发布-订阅模式的事件总线，用于模块间通信。

#### `airwar/game/mother_ship/state_machine.py`
状态机实现，管理母舰的 5 种状态及转换逻辑。

#### `airwar/game/mother_ship/game_integrator.py`
游戏场景集成器，核心功能：
- 管理动画状态
- 清除敌方单位
- 提供公共接口供 GameScene 调用

### 3.2 修改文件

#### `airwar/scenes/game_scene.py`
```python
# 新增导入
from airwar.game.mother_ship import (
    EventBus, InputDetector, MotherShipStateMachine,
    PersistenceManager, ProgressBarUI, MotherShip, GameIntegrator,
)

# 新增属性
self._mother_ship_integrator = None

# 新增方法
restore_from_save(save_data)      # 从存档恢复游戏状态
_restore_to_mothership_state()   # 恢复到母舰状态
```

#### `airwar/game/scene_director.py`
```python
# 新增方法
_check_and_get_saved_game(username)  # 检查并获取存档
_save_game_on_quit(game_scene)       # 退出时保存
_clear_saved_game()                   # 清除存档

# 修改 _run_login_flow() 返回 (success, save_data)
# 修改 _run_game_flow() 支持存档恢复
```

---

## 4. 功能测试结果

### 4.1 单元测试

```bash
$ python -m pytest airwar/tests/ -q
........................................................................ [ 46%]
........................................................................ [ 92%]
...........                                                              [100%]
155 passed in 1.08s
```

所有 155 个测试用例通过。

### 4.2 功能验证清单

| 功能 | 状态 | 说明 |
|------|------|------|
| H键检测 | ✅ | 正确检测按下/释放 |
| 进度条显示 | ✅ | 实时更新进度 |
| 进入母舰动画 | ✅ | 平滑移动到母舰 |
| 离开母舰动画 | ✅ | 从母舰位置移出 |
| 玩家控制禁用 | ✅ | 动画期间不可操作 |
| 敌方单位清除 | ✅ | 进入母舰时清空 |
| 游戏存档 | ✅ | 保存到JSON文件 |
| 存档恢复 | ✅ | 登录后恢复状态 |
| 视觉风格一致 | ✅ | 深色科幻主题 |

### 4.3 兼容性说明

- **Python 版本**: 3.11+
- **Pygame 版本**: 2.6.1
- **屏幕分辨率**: 自适应（通过 `airwar.config`）
- **操作系统**: Windows (PowerShell)

---

## 5. 任务编号与提交信息

### 5.1 相关任务

| 任务类型 | 描述 | 参考文档 |
|----------|------|----------|
| SPEC | 母舰系统设计 | `2026-04-16-mother-ship-docking-system-design.md` |
| IMPL | 系统实现 | 本文档 |
| BUGFIX | 离开母舰动画Bug | - |
| ENHANCE | 视觉效果优化 | - |

### 5.2 Git 提交信息

```
feat: 实现母舰停靠系统

主要功能:
- 新增 mother_ship 模块，包含完整的停靠系统
- 实现 H 键长按 3 秒触发母舰召唤机制
- 新增平滑的进入/离开母舰动画
- 实现游戏状态持久化（进入母舰时自动存档）
- 重新设计母舰视觉效果（深色科幻主题）
- 进入母舰时自动清除敌方单位

文件变更:
+ airwar/game/mother_ship/__init__.py
+ airwar/game/mother_ship/interfaces.py
+ airwar/game/mother_ship/mother_ship_state.py
+ airwar/game/mother_ship/event_bus.py
+ airwar/game/mother_ship/input_detector.py
+ airwar/game/mother_ship/state_machine.py
+ airwar/game/mother_ship/progress_bar_ui.py
+ airwar/game/mother_ship/persistence_manager.py
+ airwar/game/mother_ship/mother_ship.py
+ airwar/game/mother_ship/game_integrator.py
M  airwar/scenes/game_scene.py
M  airwar/game/scene_director.py

技术规格:
- 状态机: 5 种状态 (IDLE/PRESSING/DOCKING/DOCKED/UNDOCKING)
- 进入动画: 90帧, cubic ease-in-out
- 离开动画: 60帧, quad ease-out
- 存档格式: JSON (airwar/data/user_docking_save.json)

测试: 155 passed
```

---

## 6. 附录

### 6.1 关键常量

| 常量 | 值 | 说明 |
|------|-----|------|
| H_KEY | pygame.K_h | 触发键 |
| DOCKING_DURATION | 90 帧 | 进入动画时长 |
| UNDOCKING_DURATION | 60 帧 | 离开动画时长 |
| REQUIRED_HOLD_TIME | 3.0 秒 | 触发停靠所需时间 |

### 6.2 事件列表

| 事件名 | 发布者 | 说明 |
|--------|--------|------|
| H_PRESSED | InputDetector | H 键按下 |
| H_RELEASED | InputDetector | H 键释放 |
| PROGRESS_COMPLETE | InputDetector | 进度达到100% |
| STATE_CHANGED | StateMachine | 状态切换 |
| START_DOCKING_ANIMATION | StateMachine | 开始进入动画 |
| DOCKING_ANIMATION_COMPLETE | GameIntegrator | 进入动画完成 |
| START_UNDOCKING_ANIMATION | StateMachine | 开始离开动画 |
| UNDOCKING_ANIMATION_COMPLETE | GameIntegrator | 离开动画完成 |
| SAVE_GAME_REQUEST | StateMachine | 请求保存游戏 |
| GAME_RESUME | StateMachine | 游戏恢复 |
