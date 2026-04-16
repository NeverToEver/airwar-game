# Air War Bug 修复汇总

**日期**: 2026-04-16
**版本**: 1.0
**状态**: 已完成

---

## 1. Bug 修复概览

| Bug | 严重程度 | 修复日期 | 涉及文件 |
|-----|----------|----------|----------|
| Boss逃跑时间异常 | 高 | 2026-04-16 | game_scene.py |
| Boss倒计时时间流速异常 | 中高 | 2026-04-16 | enemy.py |
| DMG显示异常 | 中 | 2026-04-16 | reward_system.py, buff_stats_panel.py |
| RATE显示闪动 | 中高 | 2026-04-16 | reward_system.py, buff_stats_panel.py |

---

## 2. Bug 1: Boss逃跑时间异常

### 问题
玩家选择攻击型天赋后（如 Power Shot），Boss逃跑时间异常缩短。

### 根因
使用 `player.bullet_damage`（含加成）计算逃跑时间，导致伤害越高，逃跑时间越短。

### 修复
```python
# 修复前
boss = self.spawn_controller.spawn_boss(cycle, self.player.bullet_damage)

# 修复后
boss = self.spawn_controller.spawn_boss(cycle, self.reward_system.base_bullet_damage)
```

**文件**: `airwar/scenes/game_scene.py`

---

## 3. Bug 2: Boss倒计时时间流速异常

### 问题
选择 "Slow Field" 天赋后，Boss逃跑倒计时速度异常。

### 根因
`survival_timer` 每帧固定+1，未应用 `slow_factor` 影响。

### 修复
```python
# enemy.py - Boss.update
self.survival_timer += slow_factor  # 应用缓速因子
```

**文件**: `airwar/entities/enemy.py`

---

## 4. Bug 3: DMG显示异常

### 问题
侧边Buff统计栏显示 "DMG +400%"，但玩家未获得任何Buff。

### 根因
公式使用硬编码基准值 10，而实际难度基准值为 Easy=100, Medium=50, Hard=34。

### 修复
```python
# buff_stats_panel.py
# 修复前 (错误)
f"{int((p.bullet_damage / 10 - 1) * 100)}%"

# 修复后 (正确)
f"+{int((p.bullet_damage / rs.base_bullet_damage - 1) * 100)}%"
```

**文件**: `airwar/ui/buff_stats_panel.py`, `airwar/game/systems/reward_system.py`

---

## 5. Bug 4: RATE显示闪动

### 问题
选择 Laser 或 Rapid Fire 后，RATE数值在 0%~36% 间快速跳动。

### 根因
使用动态 `player.fire_cooldown` 实时值计算，该值每帧变化（射击后重置为8，逐帧递减）。

### 修复
- 在 `RewardSystem` 添加 `rapid_fire_level` 属性追踪等级
- 使用稳定等级值计算RATE，而非动态cooldown

```python
# reward_system.py
self.rapid_fire_level: int = 0

def _handle_rapid_fire(self, player) -> None:
    self._increment_stat('rapid_fire_level')
    cooldown = self._base_fire_cooldown
    for _ in range(self.rapid_fire_level):
        cooldown = max(1, int(cooldown * 0.8))
    player.fire_cooldown = cooldown
```

**文件**: `airwar/game/systems/reward_system.py`, `airwar/ui/buff_stats_panel.py`

---

## 6. 测试验证

```
155 passed in 0.48s ✅
通过率: 100%
```

| 验证场景 | 预期结果 | 实际结果 |
|----------|----------|----------|
| 无攻击天赋Boss逃跑 | 正常时间 | ✅ |
| Power Shot后Boss逃跑 | 时间不变 | ✅ |
| Slow Field下倒计时 | 正确应用 | ✅ |
| Rapid Fire RATE显示 | 稳定36% | ✅ |

---

**修复日期**: 2026-04-16
**验证状态**: 已通过全部测试
