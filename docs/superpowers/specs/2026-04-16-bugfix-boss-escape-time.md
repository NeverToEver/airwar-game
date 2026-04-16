# 2026-04-16 Bug修复文档 - Boss逃跑时间异常

## 修复日期: 2026-04-16

---

## 1. Bug概述

### 1.1 问题描述
玩家在选择特定攻击型天赋（如 Power Shot）后，Boss 的逃跑时间变得异常短。正常情况下 Boss 应该存活 20-60 秒，但选择天赋后可能提前几秒甚至几十秒就逃跑。

### 1.2 影响范围
- Boss 生成时的逃跑时间计算
- 玩家选择攻击增益后的 Boss 行为
- Boss 难度平衡性

### 1.3 严重程度
**等级**: 高

---

## 2. 根本原因分析

### 2.1 错误代码位置
`airwar/scenes/game_scene.py` 第133行

### 2.2 错误代码
```python
boss = self.spawn_controller.spawn_boss(
    self.game_controller.cycle_count,
    self.player.bullet_damage  # 错误：使用了天赋增强后的伤害值
)
```

### 2.3 问题根因

| 问题点 | 说明 |
|--------|------|
| **使用增强后伤害** | `player.bullet_damage` 包含所有天赋加成 |
| **公式错误** | `escape_time = base_health / bullet_damage * 2.5` |
| **结果** | 伤害越高，逃跑时间越短 |

### 2.4 数学分析

**Medium 难度原始伤害**: 50

**选择 Power Shot Lv.1** (+25%):
```
增强后伤害: 50 * 1.25 = 62.5

原计算: escape_time = 2000 / 62.5 * 2.5 = 80 帧 ≈ 1.3秒 ❌
正确计算: escape_time = 2000 / 50 * 2.5 = 100 帧 ≈ 1.67秒
```

---

## 3. 修复方案

### 3.1 修复代码
```python
# 修复前 (错误)
boss = self.spawn_controller.spawn_boss(
    self.game_controller.cycle_count,
    self.player.bullet_damage
)

# 修复后 (正确)
boss = self.spawn_controller.spawn_boss(
    self.game_controller.cycle_count,
    self.reward_system.base_bullet_damage  # 使用基础伤害值
)
```

### 3.2 修改文件

| 文件 | 修改内容 |
|------|---------|
| `airwar/scenes/game_scene.py` | 第133行，使用 `base_bullet_damage` |

---

## 4. 架构师审查

### 4.1 遵循的原则
| 原则 | 状态 | 说明 |
|------|------|------|
| **单一职责** | ✅ | SpawnController 只负责生成，不处理伤害逻辑 |
| **依赖抽象** | ✅ | 使用 RewardSystem 的属性而非 player 属性 |
| **稳定状态** | ✅ | 使用基础值，不受天赋影响 |
| **低耦合** | ✅ | 修复仅影响 Boss 生成逻辑 |

### 4.2 代码质量
- ✅ 无魔法数字
- ✅ 函数长度 < 40行
- ✅ 使用已有属性，无需新增代码

---

## 5. 测试验证

### 5.1 测试结果
```
155 passed in 0.49s ✅
```

### 5.2 验证场景
| 场景 | 预期结果 | 实际结果 |
|------|----------|----------|
| 无攻击天赋 | Boss 正常逃跑时间 | ✅ 正确 |
| Power Shot Lv.1 | Boss 逃跑时间不变 | ✅ 正确 |
| 多次攻击天赋 | Boss 逃跑时间稳定 | ✅ 正确 |

---

## 6. 提交信息

### 6.1 Git提交
```
2a33268 fix: use base_bullet_damage for Boss escape time calculation
```

### 6.2 变更统计
```
1 file changed, 1 insertion(+), 1 deletion(-)
```

---

## 7. 修复效果

### 7.1 修复前
- 选择 Power Shot 后 Boss 提前逃跑
- 游戏平衡性受影响
- 玩家体验下降

### 7.2 修复后
- Boss 逃跑时间基于基础伤害值计算
- 不受玩家天赋选择影响
- 游戏难度保持平衡

---

## 8. 相关文档

- [2026-04-16-bugfix-rate-display.md](./2026-04-16-bugfix-rate-display.md)
- [2026-04-16-bugfix-dmg-display.md](./2026-04-16-bugfix-dmg-display.md)