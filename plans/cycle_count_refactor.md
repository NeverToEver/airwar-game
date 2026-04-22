# Cycle Count 变量冲突修复设计

## 问题背景

`cycle_count` 变量被两个独立系统混用，导致计数混乱：

1. **天赋系统**：`cycle_count` 应表示玩家已选择的奖励次数（应等于 `milestone_index`）
2. **难度系统**：`boss_kill_count` 用于计算 Boss 难度倍率

## 当前问题代码

### 问题 1: [boss_manager.py:135](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/game/managers/boss_manager.py#L135)

```python
def _on_boss_killed(self) -> None:
    self._game_controller.cycle_count += 1  # ❌ 错误：难度系统不应修改 cycle_count
    ...
```

**应该**: 难度系统只应更新 `boss_kill_count`，不应触碰 `cycle_count`

### 问题 2: [game_controller.py:176](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/game/controllers/game_controller.py#L176)

```python
def on_reward_selected(self, reward: dict, player) -> None:
    notification = self.reward_system.apply_reward(reward, player)
    self.milestone_index += 1
    self.cycle_count = self.difficulty_manager.get_boss_kill_count() // 2  # ❌ 错误：cycle_count 应等于 milestone_index
    ...
```

**应该**: `cycle_count = milestone_index`（天赋奖励次数 = 里程碑索引）

### 问题 3: [game_loop_manager.py:162](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/game/managers/game_loop_manager.py#L162)

```python
boss = self._spawn_controller.spawn_boss(
    self._game_controller.cycle_count,  # ❌ 错误：应该使用 boss_kill_count
    self._reward_system.base_bullet_damage
)
```

**应该**: `boss_kill_count` 用于计算 Boss 难度缩放

## 正确设计

### 变量职责

| 变量 | 系统 | 增长来源 | 用途 |
|------|------|----------|------|
| `milestone_index` | 天赋系统 | 选择奖励时 +1 | 里程碑索引，决定下一个阈值 |
| `cycle_count` | 天赋系统 | = milestone_index | HUD 显示：`CYCLE: X/Y` |
| `boss_kill_count` | 难度系统 | Boss 被击杀时 +1 | 决定 Boss 属性和难度倍率 |

### 修复方案

#### 修改 1: [boss_manager.py:135](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/game/managers/boss_manager.py#L135)

**删除** `cycle_count += 1` 这一行。难度系统只需确保 `on_boss_killed` 正确更新 `boss_kill_count`（这已经在 `game_controller.on_boss_killed` 中完成了）。

#### 修改 2: [game_controller.py:176](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/game/controllers/game_controller.py#L176)

```python
def on_reward_selected(self, reward: dict, player) -> None:
    notification = self.reward_system.apply_reward(reward, player)
    self.milestone_index += 1
    self.cycle_count = self.milestone_index  # ✅ 修复：cycle_count = milestone_index
    ...
```

#### 修改 3: [game_loop_manager.py:162](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/game/managers/game_loop_manager.py#L162)

```python
boss = self._spawn_controller.spawn_boss(
    self._game_controller.state.boss_kill_count,  # ✅ 修复：使用 boss_kill_count
    self._reward_system.base_bullet_damage
)
```

#### 修改 4: [test_integration.py:170](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/tests/test_integration.py#L170)

更新测试断言以匹配修复后的行为：

```python
def test_reward_cycle_increments_at_threshold(self):
    scene.game_controller.milestone_index = 4
    scene.game_controller.difficulty_manager._boss_kill_count = 2
    reward = {'name': 'Speed Boost', 'desc': '+15% move speed', 'icon': 'SPD'}
    scene._on_reward_selected(reward)
    assert scene.cycle_count == 5  # ✅ 修复后：cycle_count = milestone_index + 1
```

### 流程对比

#### 修复前（有问题）

```
Boss 击杀 → cycle_count += 1 → 错误地影响后续 Boss 难度
分数达标 → cycle_count = boss_kill_count // 2（覆盖）
Boss 生成 → 使用 cycle_count（bug！）
```

#### 修复后（正确）

```
Boss 击杀 → boss_kill_count += 1 → 难度倍率更新
Boss 生成 → 使用 boss_kill_count ✅
分数达标 → milestone_index += 1 → cycle_count = milestone_index ✅
```

### 验收标准

1. `cycle_count` 在 HUD 上显示的值始终等于 `milestone_index`
2. Boss 击杀不影响 `cycle_count` 的值
3. 选择天赋奖励后，`cycle_count` 正确递增
4. **Boss 难度缩放基于 `boss_kill_count`**（而非 `cycle_count`）
5. **所有相关测试通过**（包含修改后的测试）

### 相关测试需确认

- `test_reward_cycle_increments_at_threshold`: 验证选择奖励时 `cycle_count` 正确更新（需要修改断言）
- `test_reward_max_cycles_limit`: 验证达到上限时不再触发奖励选择
- `test_cycle_count_boundary`: 验证 `cycle_count` 边界行为

## 实施步骤

1. 修改 [boss_manager.py:135](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/game/managers/boss_manager.py#L135)：删除 `cycle_count += 1`
2. 修改 [game_controller.py:176](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/game/controllers/game_controller.py#L176)：`cycle_count = milestone_index`
3. 修改 [game_loop_manager.py:162](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/game/managers/game_loop_manager.py#L162)：`cycle_count` → `boss_kill_count`
4. 修改 [test_integration.py:170](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/tests/test_integration.py#L170)：更新断言为 `== 5`
5. 运行所有相关测试验证修复
