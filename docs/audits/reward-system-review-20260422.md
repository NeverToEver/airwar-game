# 天赋奖励系统审查记录

**日期**: 2026-04-22
**审查范围**: Scycle 游戏阶段性奖励机制
**状态**: 最终版 (等差数列阈值设计)

---

## 一、系统概述

天赋奖励系统是 Scycle 游戏的核心成长机制。玩家通过击杀敌人积累分数，达到特定里程碑阈值后，从随机生成的3个天赋选项中选择一个来增强角色能力。

---

## 二、核心概念澄清

### 2.1 术语定义

| 术语 | 定义 | 代码字段 |
|------|------|----------|
| **Cycle (循环)** | 每击杀2个Boss视为一个循环 | `GameController.cycle_count` |
| **Boss Kill Count** | 累计击杀的Boss数量 | `DifficultyManager._boss_kill_count` |
| **Milestone (里程碑)** | 分数达到的阈值点，触发天赋选择 | `GameController.milestone_index` |
| **Talent (天赋)** | 玩家可选择的增益能力 | `RewardSystem.unlocked_buffs` |
| **Reward (奖励)** | 里程碑触发的天赋选项 | `RewardSelector.options` |

### 2.2 重要区别

```
cycle_count (循环数) = boss_kill_count // 2

cycle_count: 每击杀2个Boss +1
boss_kill_count: 每次击杀Boss +1
```

---

## 三、阈值系统设计

### 3.1 设计原则

- **分数不重置**: 玩家累计分数永久保存，用于最高分记录
- **等差数列递增**: 相邻里程碑的分数差值恒定增长
- **差值上限**: 差值增长到上限后保持恒定
- **难度差异化**: 不同难度有不同初始倍率和差值上限

### 3.2 阈值计算公式

```
当前差值 (current_delta_n) = min(initial_delta × (1 + n), max_delta)
                           = min(500 × (1 + n), max_delta)
                           = 500, 1000, 1500, 2000, ... → max_delta

阈值 (threshold) = Σ(current_delta_i)
                 = 500 → 1500 → 3000 → 5000 → 7500 → ...
```

| 参数 | easy | medium | hard | 说明 |
|------|------|--------|------|------|
| `initial_delta` | 500 | 500 | 500 | 第一个里程碑所需分数 |
| `max_delta` | 1500 | 2000 | 3000 | 最大差值上限 |
| `max_threshold` | 40000 | 50000 | 50000 | 最大阈值 |

### 3.3 难度配置

| 难度 | 难度倍率 | 差值上限 | 第一个阈值 | 最大阈值 |
|------|---------|---------|-----------|---------|
| easy | 0.8 | 1500 | 400 | 40000 |
| medium | 1.0 | 2000 | 500 | 50000 |
| hard | 1.5 | 3000 | 750 | 50000 |

### 3.4 阈值示例 (medium难度, max_delta=2000)

| Milestone Index | 差值 | 累计阈值 | 说明 |
|-----------------|------|---------|------|
| 0 | 500 | **500** | 第一个里程碑 |
| 1 | 1000 | **1500** | 需要再+1000分 |
| 2 | 1500 | **3000** | 需要再+1500分 |
| 3 | 2000 | **5000** | 差值已达上限2000 |
| 4 | 2000 | **7000** | 差值保持2000 |
| 5 | 2000 | **9000** | 差值保持2000 |
| 6 | 2000 | **11000** | 差值保持2000 |
| 7 | 2000 | **13000** | 差值保持2000 |
| 8 | 2000 | **15000** | 差值保持2000 |
| 9 | 2000 | **17000** | 差值保持2000 |
| 10+ | 2000 | ... | 差值恒定 |

### 3.5 难度对比

| Milestone | easy (max_delta=1500) | medium (max_delta=2000) | hard (max_delta=3000) |
|-----------|----------------------|------------------------|----------------------|
| 0 | 400 | 500 | 750 |
| 1 | 1200 | 1500 | 2250 |
| 2 | 2400 | 3000 | 4500 |
| 3 | 3900 | 5000 | 7500 |
| 4 | 5400 | 7000 | 10500 |
| 5 | 6900 | 9000 | 13500 |
| 6+ | 8400+ | 11000+ | 16500+ |

---

## 四、触发条件分析

### 4.1 天赋选择触发流程

```
玩家击杀敌人 → 获得分数 → 分数达到里程碑阈值 → 显示天赋选择界面
```

**触发位置**: [game_scene.py:229](file:///d:/TPR/AIRWAR/airwar/scenes/game_scene.py#L229)
```python
self._milestone_manager.check_and_trigger(self.player)
```

### 4.2 触发检查逻辑

**位置**: [milestone_manager.py:71-92](file:///d:/TPR/AIRWAR/airwar/game/managers/milestone_manager.py#L71-L92)

```python
def check_and_trigger(self, player) -> bool:
    if self._game_controller.state.gameplay_state != GameplayState.PLAYING:
        return False

    threshold = self._game_controller.get_next_threshold()
    if self._game_controller.state.score >= threshold:
        self._trigger_reward_selection(player)
        return True
    return False
```

---

## 五、天赋选项生成逻辑

### 5.1 选项数量

**当前实现**: 每次生成 **3个** 天赋选项

### 5.2 奖励池结构

**位置**: [reward_system.py:7-33](file:///d:/TPR/AIRWAR/airwar/game/systems/reward_system.py#L7-L33)

```
REWARD_POOL
├── health (生命) - 3个
│   ├── Extra Life: +50 Max HP, +30 HP
│   ├── Regeneration: 被动每秒回复2HP
│   └── Lifesteal: 击杀时吸血10%
│
├── offense (攻击) - 8个
│   ├── Power Shot: +25% 子弹伤害
│   ├── Rapid Fire: +20% 射击速度
│   ├── Piercing: 子弹穿透1个敌人
│   ├── Spread Shot: 同时发射3发子弹
│   ├── Explosive: 子弹造成30范围伤害 ⚠️ 需2个Boss击杀
│   ├── Shotgun: 霰弹枪散射
│   └── Laser: 激光束攻击
│
├── defense (防御) - 4个
│   ├── Shield: 抵挡下一次伤害
│   ├── Armor: -15% 承受伤害
│   ├── Evasion: +20% 闪避几率
│   └── Barrier: 获得50临时生命
│
└── utility (功能) - 3个
    ├── Speed Boost: +15% 移动速度
    ├── Magnet: +30% 拾取范围
    └── Slow Field: 敌人减速20%
```

### 5.3 限制条件

**Explosive 天赋解锁**:
```python
if cat == 'offense' and boss_kill_count < 2:
    rewards = [r for r in rewards if r['name'] not in ['Explosive']]
```

**条件**: `boss_kill_count >= 2` 才能选择 Explosive 天赋

---

## 六、数据存储结构

### 6.1 Runtime 数据 (内存)

**RewardSystem 内部状态** ([reward_system.py:36-68](file:///d:/TPR/AIRWAR/airwar/game/systems/reward_system.py#L36-L68)):

| 字段 | 类型 | 说明 |
|------|------|------|
| `unlocked_buffs` | `List[str]` | 已解锁的天赋名称列表 |
| `buff_levels` | `Dict[str, int]` | 天赋等级 (可叠加) |
| `active_buffs` | `Dict[str, Buff]` | 激活的天赋实例 |

### 6.2 GameController 配置

```python
self.initial_delta = 500      # 第一个里程碑所需分数
self.delta_growth = 500     # 每个里程碑的增量
self.max_threshold = 50000  # 最大阈值（难度调整前）
self.difficulty_multiplier = {
    'easy': 0.8,
    'medium': 1.0,
    'hard': 1.5
}
```

### 6.3 存档数据 (持久化)

```python
save_data = {
    'score': int,              # 累计分数
    'kill_count': int,         # 总击杀数
    'cycle_count': int,        # 循环数 (= boss_kill_count // 2)
    'milestone_index': int,    # 里程碑索引
    'player_health': int,      # 当前生命
    'player_max_health': int,  # 最大生命
    'unlocked_buffs': list,    # 已解锁天赋
    'buff_levels': dict,       # 天赋等级
    'difficulty': str,         # 难度
    'username': str,           # 玩家名
}
```

---

## 七、天赋应用机制

### 7.1 应用流程

```
选择天赋 → RewardSystem.apply_reward() → handler(player) → 数值变更
```

### 7.2 天赋效果分类

| 类型 | 天赋 | 效果 |
|------|------|------|
| 即时 | Power Shot | `bullet_damage = base × 1.25^level` |
| 即时 | Rapid Fire | `fire_cooldown = base × 0.8^level` |
| 即时 | Extra Life | `max_health += 50` |
| 即时 | Barrier | `max_health += 50; health = max` |
| 即时 | Slow Field | `slow_factor = 0.8` |
| 被动 | Armor | 伤害 × 0.85 |
| 被动 | Evasion | 20% 闪避 |
| 被动 | Lifesteal | 击杀回复 10% 最大生命 |
| 机制 | Piercing | 穿透 `level` 个敌人 |
| 机制 | Spread/Shotgun | 霰弹模式 |
| 机制 | Laser | 激光模式 |
| 机制 | Explosive | 范围伤害 |

---

## 八、关键代码位置索引

| 功能 | 文件 | 行号 |
|------|------|------|
| 阈值配置 | `game_controller.py` | 54-60 |
| 阈值计算 | `game_controller.py` | 106-118 |
| 里程碑检查 | `milestone_manager.py` | 71-92 |
| 奖励池定义 | `reward_system.py` | 7-33 |
| 选项生成 | `reward_system.py` | 136-155 |
| 奖励应用 | `reward_system.py` | 220-241 |
| UI渲染 | `reward_selector.py` | 299-322 |
| 存档/恢复 | `game_scene.py` | 433-491 |

---

## 九、设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 阈值计算方式 | 等差数列求和 | 分数差值均匀增长 |
| 差值上限 | easy:1500, medium:2000, hard:3000 | 确保后期仍能获取奖励 |
| 难度倍率 | easy 0.8x, medium 1.0x, hard 1.5x | easy 更简单，hard 更难 |
| 天赋选项数量 | 固定3个 | 保持一致的游戏节奏 |
| Cycle 计算方式 | boss_kill_count // 2 | 每2个Boss一个循环 |

---

## 十、修改历史

### 10.1 问题1: 旧版锯齿波设计

旧版使用 `base_thresholds = [1000, 2500, 5000, 10000, 20000]` 数组，
每5个里程碑循环一次，导致分数达到30000后选择天赋，下一个阈值降到2250，
立即触发多个里程碑。

### 10.2 问题2: 指数增长过快

修复为指数增长后，玩到后期阈值增长过快，难以触发奖励。

### 10.3 问题3: 差值无限增长

修复为等差数列后，虽然阈值增长可控，但差值仍会无限增长，
导致后期玩家难以在合理时间内完成一个里程碑。

### 10.4 最终方案: 差值上限

为差值设置上限，确保游戏后期仍能获取奖励：
- easy: 差值上限 1500
- medium: 差值上限 2000
- hard: 差值上限 3000

```
medium 难度阈值序列:
500 → 1500 → 3000 → 5000 → 7000 → 9000 → 11000 → ...
(差值达到2000后保持恒定)
```

---

**审查完成，阈值系统最终设计已确定并验证通过。**
