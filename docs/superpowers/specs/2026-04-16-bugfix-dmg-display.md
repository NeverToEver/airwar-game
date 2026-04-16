# 2026-04-16 Bug修复文档 - DMG显示异常问题

## 修复日期: 2026-04-16

---

## 1. Bug概述

### 1.1 问题描述
玩家在游戏中观察到侧边Buff统计栏显示 **"DMG +400%"** 的异常增益效果，但玩家确认自己从未主动选择或获取过此类Buff。

### 1.2 影响范围
- 侧边Buff统计栏的伤害加成显示
- 汇总区的DMG统计值
- Power Shot和Rapid Fire的数值显示

### 1.3 严重程度
**等级**: 中

---

## 2. 根本原因分析

### 2.1 错误代码位置
1. `airwar/ui/buff_stats_panel.py` 第23行
2. `airwar/ui/buff_stats_panel.py` 第114行

### 2.2 错误代码
```python
# 错误的伤害计算公式
'Power Shot': lambda rs, p: f"{int((p.bullet_damage / 10 - 1) * 100)}%"

# 汇总区错误计算
total_damage_bonus = int((player.bullet_damage / 10 - 1) * 100)
```

### 2.3 问题根因

| 问题点 | 说明 |
|--------|------|
| **硬编码基准值** | 公式假设 `bullet_damage = 10` 是游戏基础伤害 |
| **实际基准值不符** | 游戏中不同难度的初始bullet_damage分别为: Easy=100, Medium=50, Hard=34 |
| **显示逻辑错误** | 显示的是"当前伤害相对10的百分比"，而非"Buff提供的真实加成" |

### 2.4 数学推演

**Medium难度下的错误计算**:
```
初始 bullet_damage = 50

错误公式: (50 / 10 - 1) * 100 = 400%
显示结果: DMG +400%

但实际上玩家没有获得任何Buff加成！
```

**正确的理解应该是**:
```
难度初始伤害 - 50
无Buff时加成 - 0%
获得Power Shot Lv.1后: 50 * 1.25 = 62.5
正确加成: (62.5 / 50 - 1) * 100 = 25%
```

---

## 3. 修复方案

### 3.1 设计思路
- 在 `RewardSystem` 中记录难度对应的基础伤害值
- 修改 `BuffStatsPanel` 使用正确的基础值计算Buff加成

### 3.2 修改文件清单

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `reward_system.py` | 新增属性 | 添加 `base_bullet_damage` 和 `base_fire_cooldown` |
| `buff_stats_panel.py` | 修复公式 | 使用正确的基础值计算百分比 |
| `game_controller.py` | 参数传递 | 传递difficulty参数给RewardSystem |

### 3.3 具体修改

#### 3.3.1 reward_system.py

**新增属性**:
```python
def __init__(self, difficulty: str = 'medium'):
    # ... existing code ...

    from airwar.config import DIFFICULTY_SETTINGS
    settings = DIFFICULTY_SETTINGS.get(difficulty, DIFFICULTY_SETTINGS['medium'])
    self._base_bullet_damage: int = settings.get('bullet_damage', 50)
    self._base_fire_cooldown: int = 8

@property
def base_bullet_damage(self) -> int:
    return self._base_bullet_damage

@property
def base_fire_cooldown(self) -> int:
    return self._base_fire_cooldown
```

#### 3.3.2 buff_stats_panel.py

**修复Power Shot公式**:
```python
# 修复前 (错误)
'Power Shot': lambda rs, p: f"{int((p.bullet_damage / 10 - 1) * 100)}%"

# 修复后 (正确)
'Power Shot': lambda rs, p: f"+{int((p.bullet_damage / rs.base_bullet_damage - 1) * 100)}%"
```

**修复Rapid Fire公式**:
```python
# 修复前 (错误)
'Rapid Fire': lambda rs, p: f"{int((1 - p.fire_cooldown / 8) * 100)}%"

# 修复后 (正确)
'Rapid Fire': lambda rs, p: f"+{int((1 - p.fire_cooldown / rs.base_fire_cooldown) * 100)}%"
```

**修复汇总区DMG计算**:
```python
# 修复前 (错误)
total_damage_bonus = int((player.bullet_damage / 10 - 1) * 100)

# 修复后 (正确)
base_damage = reward_system.base_bullet_damage
current_damage = player.bullet_damage
total_damage_bonus = int((current_damage / base_damage - 1) * 100)
```

#### 3.3.3 game_controller.py

**传递difficulty参数**:
```python
# 修复前
self.reward_system = RewardSystem()

# 修复后
self.reward_system = RewardSystem(difficulty)
```

---

## 4. 修复后效果

### 4.1 显示对比

| 场景 | 修复前显示 | 修复后显示 |
|------|-----------|-----------|
| Medium难度，无Buff | DMG +400% | DMG +0% |
| Medium难度，Power Shot Lv.1 | DMG +525% | DMG +25% |
| Medium难度，Power Shot Lv.2 | DMG +681% | DMG +56% |
| Hard难度，无Buff | DMG +240% | DMG +0% |
| Easy难度，Power Shot Lv.1 | DMG +1150% | DMG +25% |

### 4.2 计算验证

**Medium难度 + Power Shot Lv.2**:
```
base_bullet_damage = 50
bullet_damage after 2 upgrades = 50 * 1.25 * 1.25 = 78.125

显示加成 = (78.125 / 50 - 1) * 100 = 56.25% ≈ 56%
```

---

## 5. 测试验证

### 5.1 单元测试
```
总测试数: 155
通过: 155
失败: 0
通过率: 100%
```

### 5.2 边界条件测试

| 测试场景 | 预期结果 | 实际结果 |
|----------|----------|----------|
| 无Buff激活 | DMG +0% | ✅ 通过 |
| 单个Power Shot | DMG +25% | ✅ 通过 |
| 多个Power Shot叠加 | DMG +56%, +88%... | ✅ 通过 |
| 不同难度设置 | 基准值正确获取 | ✅ 通过 |
| Rapid Fire加成 | RATE +20%, +36%... | ✅ 通过 |

### 5.3 性能影响
- 无额外性能开销
- 仅在初始化时获取难度设置
- 计算公式优化后更简洁

---

## 6. 相关文件

- [Buff统计栏设计文档](./2026-04-16-buff-stats-panel-design.md)
- [项目重构设计](./2026-04-14-airwar-refactoring-design.md)
- [优化报告](./2026-04-16-optimization-report.md)

---

## 7. 版本历史

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| 1.0 | 2026-04-16 | 初始Bug修复文档 |

---

**修复日期**: 2026-04-16
**修复者**: AI Assistant (Claude)
**验证状态**: 已通过全部测试
