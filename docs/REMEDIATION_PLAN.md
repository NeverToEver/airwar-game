# Airwar 代码规范修复计划

**日期：** 2026/04/26
**基于：** REFACTORING_GUIDE.md v1.1
**状态：** ✅ 已完成（Phase 1-5，708 tests passed）

---

## 当前状态摘要

| 维度 | 现状 | 目标 |
|------|------|------|
| 导入风格 | manager 模块大量使用绝对导入 | 同包内统一相对导入 |
| 局部导入注释 | 22 处方法内导入，0 处有注释 | 每处标注原因或移到顶部 |
| 方法排序 | Player/Enemy/GameController 偏离 | 按规范 7 层顺序排列 |
| 模块 docstring | ~80 个文件缺失 | 全部补全 |
| 类 docstring | 116/186 (62%) 缺失 | 全部补全 |
| 公开方法 docstring | 几乎全部缺失 | 核心模块补全 |

---

## 修复原则

1. **每阶段独立可验证** — 完成后运行验证命令确认
2. **不改变行为** — 仅调整代码组织和文档，不修改逻辑
3. **分批提交** — 每阶段一个 commit，出问题易于回滚
4. **优先处理高频文件** — 被多处引用的模块优先修

---

## Phase 1: 导入风格统一

### 1.1 绝对导入 → 相对导入（manager 模块）

将同包内的绝对导入改为相对导入。只处理同一 `airwar` 包内的导入，标准库和第三方库不动。

**涉及文件及修改：**

```python
# === game/managers/game_controller.py ===
# 修改前:
from airwar.config import DIFFICULTY_SETTINGS, VALID_DIFFICULTIES, RIPPLE_FADE_SPEED
from airwar.game.constants import GAME_CONSTANTS
from airwar.game.systems.health_system import HealthSystem
from airwar.game.systems.reward_system import RewardSystem
from airwar.game.systems.notification_manager import NotificationManager
from airwar.game.systems.difficulty_manager import DifficultyManager

# 修改后:
from ...config import DIFFICULTY_SETTINGS, VALID_DIFFICULTIES, RIPPLE_FADE_SPEED
from ..constants import GAME_CONSTANTS
from ..systems.health_system import HealthSystem
from ..systems.reward_system import RewardSystem
from ..systems.notification_manager import NotificationManager
from ..systems.difficulty_manager import DifficultyManager
```

```python
# === game/managers/collision_controller.py ===
# 修改前:
from airwar.game.constants import GAME_CONSTANTS
from airwar.entities.enemy import Enemy, Boss
from airwar.entities.bullet import Bullet, EnemyBullet
# (方法内局部导入同样改为相对)

# 修改后:
from ..constants import GAME_CONSTANTS
from ...entities.enemy import Enemy, Boss
from ...entities.bullet import Bullet, EnemyBullet
```

```python
# === game/managers/boss_manager.py ===
# 修改前:
from airwar.game.constants import GAME_CONSTANTS
from airwar.entities.enemy import Boss, BossData
from airwar.config import BOSS_SPAWN_INTERVAL

# 修改后:
from ..constants import GAME_CONSTANTS
from ...entities.enemy import Boss, BossData
from ...config import BOSS_SPAWN_INTERVAL
```

```python
# === game/managers/bullet_manager.py ===
# 修改前:
from airwar.game.constants import GAME_CONSTANTS
from airwar.entities.bullet import Bullet, EnemyBullet

# 修改后:
from ..constants import GAME_CONSTANTS
from ...entities.bullet import Bullet, EnemyBullet
```

```python
# === game/managers/spawn_controller.py ===
# 修改前:
from airwar.game.constants import GAME_CONSTANTS
from airwar.entities.enemy import Enemy, EnemySpawner, EnemyData

# 修改后:
from ..constants import GAME_CONSTANTS
from ...entities.enemy import Enemy, EnemySpawner, EnemyData
```

```python
# === game/managers/milestone_manager.py ===
# 修改前:
from airwar.game.constants import GAME_CONSTANTS
from airwar.config import MILESTONE_THRESHOLDS

# 修改后:
from ..constants import GAME_CONSTANTS
from ...config import MILESTONE_THRESHOLDS
```

```python
# === game/managers/ui_manager.py ===
# 修改前:
from airwar.game.constants import GAME_CONSTANTS

# 修改后:
from ..constants import GAME_CONSTANTS
```

**注意：**
- `__init__.py` 的惰性加载保持绝对导入不变（包级别导出需要）
- `config/constants_access.py` 保持绝对导入不变（解决循环依赖）

### 1.2 局部导入注释

为所有方法内局部导入添加 `# NOTE:` 注释标注原因。

```python
# 模式 A：打破循环依赖
def _setup_boss_spawn(self):
    # NOTE: Lazy import to avoid circular dependency between managers
    from ..managers.game_controller import GameController
    ...

# 模式 B：类型检查
def _on_collision(self):
    # NOTE: Lazy import for TYPE_CHECKING — avoids circular import at module level
    from ...entities.player import Player
    ...

# 模式 C：可移到顶部（不需要惰性加载）
def update(self):
    from ...config import EXPLOSION_RADIUS  # ← 移除，改为模块顶部导入
    ...
```

**验证命令：**
```bash
# 检查是否还有同包内绝对导入
grep -rn "from airwar\.game\." airwar/airwar/game/ --include="*.py" | grep -v "__init__\.py"

# 检查局部导入是否都已标注
grep -B2 "^\s\+from airwar\." airwar/airwar/ --include="*.py" -rn \
  | grep -v "/tests/" | grep -v "__init__\.py" | grep -v "core_bindings" \
  | grep -v "NOTE:"
```

---

## Phase 2: 方法排列顺序修复

### 2.1 Player 类 (`entities/player.py`)

**当前问题：** 私有生命周期方法 `_update_movement`、`_update_weapons` 插在公开方法之间；`render()` 在类末尾而非与其他生命周期方法在一起。

**目标布局：**
```
1. __init__                                  # 特殊方法
2. @property fire_cooldown, bullet_damage    # 属性
3. update, render                            # 公开生命周期
4. fire, auto_fire, activate_shotgun,        # 公开行为
   activate_laser, activate_explosive,
   take_damage, heal, activate_shield,
   get_hitbox, get_bullets,
   remove_bullet, cleanup_inactive_bullets,
   is_colliding_with, add_listener
5. _update_movement, _update_weapons,        # 私有生命周期
   _update_effects
6. _create_bullets_for_shot_mode,            # 私有行为
   _render_hitbox_indicator
```

### 2.2 Enemy 类 (`entities/enemy.py`)

**当前问题：** `_sync_rects`（私有行为）在 `_init_movement`（私有生命周期）之前；setter 方法分散。

**目标布局：**
```
1. __init__                                  # 特殊方法
2. @property collision_rect                  # 属性
3. update, render                            # 公开生命周期
4. take_damage, get_hitbox,                  # 公开行为
   check_point_collision, set_bullet_spawner,
   set_difficulty, set_sprite
5. _init_movement                            # 私有生命周期
6. _fire, _create_bullets, _get_damage,      # 私有行为
   _sync_rects
```

### 2.3 GameController 类 (`game/managers/game_controller.py`)

**当前问题：** `_update_invincibility`（私有生命周期）插在公开方法 `is_game_over` 之后。

**目标布局：**
```
1. __init__                                  # 特殊方法
2. (无 @property)                            # 属性
3. update                                    # 公开生命周期
4. is_playing, is_game_over,                 # 公开行为
   get_current_threshold, get_previous_threshold,
   get_next_progress, get_next_threshold,
   on_player_hit, on_enemy_killed,
   on_boss_killed, update_ripples,
   show_notification, on_reward_selected
5. _update_invincibility                     # 私有生命周期
6. _calculate_threshold, _get_threshold_for_index  # 私有行为
```

### 2.4 Boss 类 (`entities/enemy.py`)

**当前问题：** `update` 中调用的 `_fire` 在 `set_bullet_spawner` 之前。

检查后确认 Boss 类排列基本可接受，仅需微调：`take_damage` 移到 `render` 之前。

**验证命令：**
```bash
# 无自动检查——需人工 review 类定义前后顺序
grep -n "def \|@property\|^class " airwar/airwar/entities/player.py
grep -n "def \|@property\|^class " airwar/airwar/entities/enemy.py
```

---

## Phase 3: 模块级 docstring 补全

为所有缺失模块 docstring 的 `.py` 文件补全一行英文描述。

**涉及文件（~80 个），按目录分组：**

| 目录 | 数量 | 优先级 |
|------|------|--------|
| `game/managers/` | 7 | 高 |
| `game/systems/` | 6 | 高 |
| `entities/` | 3 (`__init__`, `enemy`, `interfaces`) | 高 |
| `game/mother_ship/` | 9 | 中 |
| `game/rendering/` | 6 | 中 |
| `scenes/` | 8 | 中 |
| `ui/` | 8 | 中 |
| `config/` | 5 | 中 |
| `game/buffs/` | 4 | 中 |
| `game/explosion_animation/` | 5 | 低 |
| `game/spawners/` | 2 | 低 |
| `game/death_animation/` | 2 | 低 |
| `game/give_up/` | 2 | 低 |
| `input/` | 2 | 低 |
| `utils/` | 4 | 低 |
| `window/` | 2 | 低 |
| `game/` | 3 (`__init__`, `game`, `scene_director`) | 高 |

**格式要求：**
```python
"""Module purpose in one line."""
```

不需要像类 docstring 那样写 Google 风格的 Attributes/Returns 等详细段落，模块 docstring 简洁描述用途即可。

**验证命令：**
```bash
# 检查还有多少文件缺模块 docstring
find airwar/airwar -name "*.py" -not -path "*/__pycache__/*" -not -path "*/tests/*" \
  | while read f; do
    first=$(head -1 "$f")
    second=$(head -2 "$f" | tail -1)
    if ! echo "$first$second" | grep -q '"""'; then
      echo "MISSING: $f"
    fi
  done | wc -l
```

---

## Phase 4: 类级 docstring 补全

补全 116 个缺失 docstring 的类。按优先级分三批：

### 第一批（高优先级，~30 个）— 核心架构类

| 文件 | 类 |
|------|----|
| `game/managers/game_controller.py` | `GameplayState`, `GameState`, `GameController` |
| `game/managers/collision_controller.py` | `CollisionResult`, `CollisionEvent`, `CollisionController` |
| `game/managers/spawn_controller.py` | `SpawnController` |
| `game/managers/game_loop_manager.py` | `GameLoopManager` + 8 个 Protocol |
| `game/managers/ui_manager.py` | `UIManager` + 6 个 Protocol |
| `game/managers/input_coordinator.py` | `InputCoordinator` + 6 个 Protocol |
| `game/systems/reward_system.py` | `RewardSystem` |
| `game/systems/health_system.py` | `HealthSystem` |
| `game/systems/difficulty_manager.py` | `DifficultyManager`, `DifficultyListener` |
| `game/systems/notification_manager.py` | `NotificationManager` |
| `game/scene_director.py` | `SceneDirector` |
| `game/game.py` | `Game` |

### 第二批（中优先级，~40 个）— UI 和辅助系统

| 文件 | 类 |
|------|----|
| `ui/reward_selector.py` | `RewardSelector` |
| `ui/buff_stats_panel.py` | `BuffStatEntry`, `BuffStatsAggregator`, `BuffStatsPanel`, `AttackModeEntry` |
| `ui/game_over_screen.py` | `ScreenAction`, `GameOverScreen` |
| `ui/give_up_ui.py` | `GiveUpUI` |
| `ui/difficulty_coefficient_panel.py` | `DifficultyCoefficientPanel` |
| `ui/effects.py` | (如有) |
| `game/mother_ship/` 全部 9 个文件 | `EventBus`, `GameIntegrator`, `InputDetector`, `MotherShip`, `MotherShipState`, `DockingProgress`, `GameSaveData`, `MotherShipStateMachine`, `PersistenceManager`, `ProgressBarUI` + interfaces |
| `game/rendering/` 全部 | `GameRenderer`, `GameEntities`, `HUDRenderer`, `HUDLayout`, `IntegratedHUD`, `DifficultyIndicator` |
| `scenes/` 全部 | `LoginScene`, `MenuScene`, `GameScene`, `PauseScene`, `DeathScene`, `ExitConfirmScene` |

### 第三批（低优先级，~46 个）— 内部实现细节

| 文件 | 类 |
|------|----|
| `game/buffs/` | 所有 18 个 Buff 类和 `Buff`, `BuffResult` |
| `config/design_tokens.py` | `Colors`, `Typography`, `Spacing`, `Animation`, `UIComponents`, `DesignTokens` |
| `config/game_config.py` | `GameConfig` |
| `config/tutorial/tutorial_config.py` | `StepType`, `PanelConfig`, `ButtonConfig`, `ContentCardConfig` |
| `game/systems/difficulty_strategies.py` | `DifficultyStrategy`, `EasyStrategy`, `MediumStrategy`, `HardStrategy`, `DifficultyStrategyFactory` |
| `game/systems/movement_pattern_generator.py` | `MovementPatternGenerator` |
| `game/spawners/enemy_bullet_spawner.py` | `EnemyBulletSpawner` |
| `game/give_up/give_up_detector.py` | `GiveUpDetector` |
| `game/explosion_animation/` | 全部类 |
| `input/input_handler.py` | `InputHandler`, `PygameInputHandler`, `MockInputHandler` |
| `utils/database.py` | `SimpleDB`, `UserDB` |
| `utils/responsive.py` | `ResponsiveHelper` |
| `entities/interfaces.py` | `IBulletSpawner`, `IEntityObserver` |
| `window/window.py` | `Window` |

**格式要求（Google 风格，与 REFACTORING_GUIDE 5.1 一致）：**
```python
class GameController:
    """Manages game state, scoring, and milestone progression.

    Coordinates player health, enemy kill scoring, and difficulty
    thresholds. Delegates reward selection to RewardSystem.

    Attributes:
        score: Total score accumulated during the current game.
        difficulty: Current difficulty level string.
        state: Current game state (PLAYING, DYING, GAME_OVER).
    """
```

**验证命令：**
```bash
# 统计剩余缺失 docstring 的类
grep -rn "^class " airwar/airwar/ --include="*.py" | grep -v "/tests/" \
  | while read line; do
    file=$(echo "$line" | cut -d: -f1)
    linenum=$(echo "$line" | cut -d: -f2)
    nextline=$((linenum + 1))
    sed -n "${nextline}p" "$file"
  done | grep -cv '"""'
```

---

## Phase 5: 公开方法 docstring 补全

为核心类的关键公开方法补全 docstring。范围限定在：

- `Player` 的公开方法（`fire`, `take_damage`, `heal`, `update`, `render`）
- `Enemy` / `Boss` 的公开方法（`update`, `take_damage`, `render`）
- `GameController` 的公开方法（`update`, `on_player_hit`, `on_enemy_killed`）
- 各 `Scene` 的 `enter` / `exit` / `update` / `render`

不需要为简单的 getter/setter 或 buff 子类写详细 docstring。

---

## 执行顺序

```
Phase 1  →  导入风格统一          [22 文件] ✅ 完成
Phase 2  →  方法排列顺序修复        [3 文件]  ✅ 完成
Phase 3  →  模块 docstring 补全    [74 文件] ✅ 完成
Phase 4  →  类 docstring 补全      [~80 文件] ✅ 完成
Phase 5  →  公开方法 docstring 补全 [6 文件]  ✅ 完成
```

---

## 每阶段验收清单

- [ ] 运行 `find ... -exec python3 -m py_compile {} +` 语法检查
- [ ] 运行 `python3 -m pytest` 全部测试通过
- [ ] 运行该阶段对应的 grep 验证命令
- [ ] git diff 确认变更仅涉及目标文件

---

*文档版本：1.0*
*创建日期：2026/04/26*
