# Air War - 项目技术文档汇总

**项目**: Air War (飞机大战游戏)
**版本**: 2.0
**日期**: 2026-04-16
**状态**: 综合文档

---

## 文档目录

| 编号 | 文档名称 | 内容概要 |
|------|----------|----------|
| SPEC-001 | 架构重构设计文档 | 4阶段架构重构方案 |
| SPEC-002 | Bug修复记录 | 所有Bug修复汇总 |
| SPEC-003 | UI功能设计 | 侧边Buff统计栏 |
| SPEC-004 | 母舰停靠系统 | 完整功能规格 |

---

# SPEC-001: 架构重构设计文档

**日期**: 2026-04-14
**状态**: ✅ 已完成

## 1. 重构概述

### 1.1 当前架构问题

| 问题 | 严重程度 | 描述 |
|------|----------|------|
| GameScene 上帝类 | 🔴 严重 | 524行，混合所有职责 |
| Enemy/Boss 循环依赖 | 🔴 严重 | 实体直接持有GameScene引用 |
| Player 直接操作pygame | 🟡 中等 | 违反解耦要求 |
| RewardSystem if-elif链 | 🟡 中等 | 违反开闭原则 |
| HUDRenderer 直接使用pygame | 🟢 轻微 | 渲染层未解耦 |

### 1.2 重构目标

- ✅ 消除上帝类 (God Class)
- ✅ 实现完全解耦
- ✅ 遵循开闭原则
- ✅ 提升可测试性
- ✅ 保持功能完全兼容

---

## 2. Phase 1: 输入层抽象

### 2.1 核心接口

```python
class InputHandler(ABC):
    @abstractmethod
    def get_movement_direction(self) -> Vector2:
        pass
    
    @abstractmethod
    def is_fire_pressed(self) -> bool:
        pass
    
    @abstractmethod
    def is_pause_pressed(self) -> bool:
        pass
```

### 2.2 文件结构

```
airwar/
├── input/
│   ├── __init__.py
│   └── input_handler.py
└── entities/
    └── player.py
```

---

## 3. Phase 2: GameScene 拆分

### 3.1 拆分后的子系统架构

```
airwar/
├── scenes/
│   └── game_scene.py              # ~150行
├── game/
│   ├── controllers/
│   │   ├── game_controller.py
│   │   ├── spawn_controller.py
│   │   └── collision_controller.py
│   ├── systems/
│   │   ├── health_system.py
│   │   ├── reward_system.py
│   │   ├── hud_renderer.py
│   │   └── notification_manager.py
│   └── rendering/
│       └── game_renderer.py
```

### 3.2 GameController

```python
@dataclass
class GameState:
    difficulty: str = 'medium'
    username: str = 'Player'
    score: int = 0
    score_multiplier: int = 1
    paused: bool = False
    running: bool = True
    entrance_animation: bool = True
    entrance_timer: int = 0
    entrance_duration: int = 60
```

---

## 4. Phase 3: Enemy/Boss 解耦

### 4.1 核心接口

```python
class IBulletSpawner(ABC):
    @abstractmethod
    def spawn_bullet(self, bullet: Bullet) -> None:
        pass
```

### 4.2 架构对比

```
【重构前】
Enemy ──→ GameScene (循环依赖!)

【重构后】
Enemy ──→ IBulletSpawner (接口)
           ↑
GameScene ─┘ (实现注入)
```

---

## 5. Phase 4: RewardSystem 重构

### 5.1 Buff 基类

```python
class Buff(ABC):
    @abstractmethod
    def apply(self, player) -> BuffResult:
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        pass
```

### 5.2 Buff 注册表

```python
BUFF_REGISTRY: Dict[str, Type[Buff]] = {
    'Extra Life': ExtraLifeBuff,
    'Regeneration': RegenerationBuff,
    'Lifesteal': LifestealBuff,
    'Power Shot': PowerShotBuff,
    'Rapid Fire': RapidFireBuff,
    'Piercing': PiercingBuff,
    'Spread Shot': SpreadShotBuff,
    'Explosive': ExplosiveBuff,
}
```

---

## 6. 文件结构规划

```
airwar/
├── input/
│   ├── __init__.py
│   └── input_handler.py
├── entities/
│   ├── interfaces.py
│   ├── enemy.py
│   └── player.py
├── game/
│   ├── buffs/
│   │   ├── __init__.py
│   │   ├── base_buff.py
│   │   ├── buff_registry.py
│   │   ├── health_buffs.py
│   │   ├── offense_buffs.py
│   │   └── defense_buffs.py
│   ├── controllers/
│   ├── rendering/
│   └── systems/
└── scenes/
    └── game_scene.py
```

---

## 7. 预期成果

### 7.1 代码质量指标

| 指标 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| **GameScene 行数** | 524 行 | ~150 行 | -71% |
| **单一职责遵循** | ❌ 违反 | ✅ 遵循 | 完全符合 |
| **子系统数量** | 0 | 10+ | 显著增加 |
| **耦合度** | 高 | 低 | 显著降低 |
| **可测试性** | 困难 | 各子系统可独立测试 | 显著提升 |

---

# SPEC-002: Bug修复记录

**日期**: 2026-04-16
**状态**: ✅ 已完成

## Bug #1: Boss逃跑时间异常

**严重程度**: 高
**日期**: 2026-04-16

### 问题描述
玩家在选择特定攻击型天赋后，Boss的逃跑时间变得异常短。

### 根本原因
```python
# 错误代码
boss = self.spawn_controller.spawn_boss(
    self.game_controller.cycle_count,
    self.player.bullet_damage  # 使用了天赋增强后的伤害值
)
```

### 修复方案
```python
# 修复后
boss = self.spawn_controller.spawn_boss(
    self.game_controller.cycle_count,
    self.reward_system.base_bullet_damage  # 使用基础伤害值
)
```

---

## Bug #2: Boss倒计时时间流速异常

**严重程度**: 中高
**日期**: 2026-04-16

### 问题描述
选择"Slow Field"天赋后，Boss的逃跑倒计时速度异常。

### 根本原因
`survival_timer`每帧+1，忽略`slow_factor`影响。

### 修复方案
```python
# enemy.py - Boss.update
self.survival_timer += slow_factor
```

---

## Bug #3: RATE显示闪动问题

**严重程度**: 中高
**日期**: 2026-04-16

### 问题描述
RATE数值在0%~36%之间快速跳动。

### 根本原因
使用动态`player.fire_cooldown`实时值计算，该值每帧变化。

### 修复方案
- 添加`rapid_fire_level`属性到RewardSystem
- 使用稳定等级值计算RATE

---

## Bug #4: DMG显示异常 (+400%)

**严重程度**: 中
**日期**: 2026-04-16

### 问题描述
显示"DMG +400%"的异常增益，但玩家未选择任何Buff。

### 根本原因
公式假设`bullet_damage = 10`是基准值，但实际Medium难度为50。

### 修复方案
```python
# 使用正确的基础值计算
'Power Shot': lambda rs, p: f"+{int((p.bullet_damage / rs.base_bullet_damage - 1) * 100)}%"
```

---

## Bug #5: Vector2对象访问错误

**严重程度**: 高
**日期**: 2026-04-15

### 问题描述
```python
TypeError: 'Vector2' object is not subscriptable
```

### 修复方案
```python
# 错误 ❌
self.rect.x += direction[0] * self.speed

# 正确 ✅
self.rect.x += direction.x * self.speed
```

---

## Bug #6: 离开母舰动画Bug

**严重程度**: 中
**日期**: 2026-04-16

### 问题描述
战机从左上角出现而非从母舰位置移出。

### 根本原因
状态机无法从DOCKED转换到UNDOCKING。

### 修复方案
在`_on_h_pressed()`中添加DOCKED状态处理：
```python
if self._current_state == MotherShipState.DOCKED:
    if self._can_transition_to(MotherShipState.UNDOCKING):
        self._change_state(MotherShipState.UNDOCKING)
```

---

## Bug #7: 进度条Surface无效分辨率

**严重程度**: 中
**日期**: 2026-04-16

### 问题描述
```python
pygame.error: Invalid resolution for Surface
```

### 根本原因
`progress_width`过小时创建无效Surface。

### 修复方案
```python
if progress_width > 4:
    highlight_surface = pygame.Surface((progress_width - 4, 4), pygame.SRCALPHA)
```

---

# SPEC-003: UI功能设计

**日期**: 2026-04-16
**状态**: ✅ 已完成

## 侧边Buff统计栏 (Buff Stats Panel)

### 1. 功能概述

在游戏进行过程中，于屏幕右侧显示实时生效的Buff信息统计栏。

### 2. 视觉设计

| 参数 | 值 |
|------|-----|
| 面板宽度 | 160像素 |
| 内边距 | 10像素 |
| 单项高度 | 28像素 |
| 项间距 | 4像素 |
| 汇总区高度 | 50像素 |
| 圆角半径 | 8像素 |

### 3. 配色方案

- **背景色**: `(15, 15, 30, 25)` - 深蓝黑色
- **边框色**: `(60, 60, 90, 80)` - 蓝灰色
- **标题色**: `(180, 180, 210)` - 浅蓝灰色

### 4. 数据显示规则

| Buff名称 | 显示格式 | 示例 |
|----------|----------|------|
| Power Shot | `+{N}%` | +25% |
| Rapid Fire | `+{N}%` | +20% |
| Piercing | `Lv.{N}` | Lv.2 |
| Armor | `-{N}%` | -30% |
| Evasion | `+{N}%` | +40% |

### 5. 新增文件

- `airwar/ui/buff_stats_panel.py` - 侧边统计栏组件

---

# SPEC-004: 母舰停靠系统

**日期**: 2026-04-16
**状态**: ✅ 已完成

## 1. 系统概述

母舰停靠系统允许玩家在战斗中召唤母舰、进入母舰进行存档、离开母舰继续战斗。

### 1.1 核心功能

- 长按H键3秒触发母舰召唤
- 平滑的进入/离开母舰动画
- 游戏状态持久化（进入母舰时自动存档）
- 进入母舰时自动清除敌方单位

## 2. 状态机设计

```
IDLE ──[H按下]──> PRESSING ──[3秒完成]──> DOCKING ──[动画完成]──> DOCKED
  ^                    │                                          │
  │                    │                                          │
  └──[松开/取消]───────┴──[H按下]──> UNDOCKING ──[动画完成]──────┘
```

### 状态说明

| 状态 | 说明 |
|------|------|
| IDLE | 默认状态，正常游戏 |
| PRESSING | 检测H键按下，累积进度 |
| DOCKING | 执行进入母舰动画 |
| DOCKED | 已进入母舰，游戏暂停，可存档 |
| UNDOCKING | 执行离开母舰动画 |

## 3. 模块架构

```
airwar/game/mother_ship/
├── __init__.py              # 模块导出
├── interfaces.py            # 抽象接口定义
├── mother_ship_state.py     # 状态数据结构
├── event_bus.py             # 事件总线
├── input_detector.py        # H键输入检测
├── state_machine.py         # 状态机
├── progress_bar_ui.py       # 进度条UI
├── persistence_manager.py     # 数据持久化
├── mother_ship.py           # 母舰渲染
└── game_integrator.py       # 游戏场景集成
```

## 4. 数据持久化

### GameSaveData 数据结构

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

### 存储路径
`airwar/data/user_docking_save.json`

## 5. 视觉效果

### 5.1 母舰外观设计

- 多层船体：深色底 → 主色 → 高亮渐变
- 发动机光晕：脉冲动画效果
- 机翼细节：几何形状 + 装饰线条
- 驾驶舱：半透明玻璃 + 反射高光

### 5.2 颜色方案

```python
_colors = {
    'hull_dark': (35, 40, 55),
    'hull_main': (55, 65, 85),
    'hull_light': (75, 85, 105),
    'hull_highlight': (95, 110, 140),
    'engine_core': (80, 160, 255),
    'engine_glow': (40, 100, 200),
    'cockpit_glass': (100, 180, 255),
    'accent': (60, 140, 220),
}
```

## 6. 动画系统

### 6.1 进入动画

- **持续时间**: 90帧 (~1.5秒 @ 60fps)
- **缓动函数**: cubic ease-in-out
- **玩家控制**: 禁用

### 6.2 离开动画

- **持续时间**: 60帧 (~1秒 @ 60fps)
- **缓动函数**: quad ease-out
- **玩家控制**: 禁用

### 6.3 缓动函数

```python
def _ease_in_out_cubic(self, t: float) -> float:
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - ((-2 * t + 2) ** 3) / 2

def _ease_out_quad(self, t: float) -> float:
    return 1 - (1 - t) * (1 - t)
```

## 7. 事件列表

| 事件名 | 发布者 | 说明 |
|--------|--------|------|
| H_PRESSED | InputDetector | H键按下 |
| H_RELEASED | InputDetector | H键释放 |
| PROGRESS_COMPLETE | InputDetector | 进度达到100% |
| STATE_CHANGED | StateMachine | 状态切换 |
| START_DOCKING_ANIMATION | StateMachine | 开始进入动画 |
| DOCKING_ANIMATION_COMPLETE | GameIntegrator | 进入动画完成 |
| START_UNDOCKING_ANIMATION | StateMachine | 开始离开动画 |
| UNDOCKING_ANIMATION_COMPLETE | GameIntegrator | 离开动画完成 |
| SAVE_GAME_REQUEST | StateMachine | 请求保存游戏 |
| GAME_RESUME | StateMachine | 游戏恢复 |

## 8. 测试验证

```
总测试数: 155
通过: 155
失败: 0
通过率: 100%
```

---

## 附录: 相关文档

| 原文档 | 合并后位置 |
|--------|------------|
| 2026-04-14-airwar-refactoring-design.md | SPEC-001 |
| 2026-04-15-boss-redesign-design.md | SPEC-001 |
| 2026-04-16-mother-ship-docking-system-design.md | SPEC-004 |
| 2026-04-16-mother-ship-implementation-report.md | SPEC-004 |
| 2026-04-16-bugfix-*.md | SPEC-002 |
| 2026-04-16-buff-stats-panel-design.md | SPEC-003 |
| 2026-04-15-optimization-tasks.md | 已归档 |
| 2026-04-16-*-review.md | 已归档 |
| 2026-04-16-docs-integration-summary.md | 已归档 |

---

**文档版本**: 2.0
**最后更新**: 2026-04-16
**维护者**: AI Assistant (Claude)
