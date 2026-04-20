# 调试会话：奖励里程碑保存/恢复Bug ✅ 已修复

**日期**: 2026-04-21  
**问题**: 保存游戏时距离触发奖励还有分数差距，但恢复后立即获得奖励  
**状态**: ✅ 已修复

## ✅ 问题确认

### 测试结果

```
保存时的状态:
  milestone_index = 45
  cycle_count = 9
  下一阈值 = 57665.0390625
  当前分数 = 50000
  距离下一阈值 = 7665.0390625

恢复存档...
恢复后的状态 (使用错误逻辑):
  milestone_index = 9 ❌ (正确应该是 45)
  cycle_count = 9
  下一阈值 = 45000.0 ❌ (正确应该是 57665.0390625)
  当前分数 = 50000

检查是否触发奖励:
  ❌ 会触发奖励！分数50000 >= 阈值45000.0
     这是错误的！应该不触发奖励！
```

## ✅ 根本原因

**错误的恢复逻辑**：
```python
self.game_controller.milestone_index = save_data.cycle_count % self.game_controller.max_cycles
```

**问题分析**：
- `milestone_index` 和 `cycle_count` 的关系：`cycle_count = milestone_index // 5`
- 当 `cycle_count = 9` 时，`milestone_index = 9 * 5 = 45`
- 但恢复时错误地使用：`milestone_index = 9 % 10 = 9` ❌

**阈值计算差异**：
- 基于 `milestone_index = 9` 的阈值 = 45000.0
- 基于 `milestone_index = 45` 的阈值 = 57665.0390625
- **差异 = 1.28倍**

## ✅ 修复方案

**正确的恢复逻辑**：
```python
self.game_controller.milestone_index = save_data.cycle_count * 5
```

**公式推导**：
- `cycle_count = milestone_index // 5`
- 因此：`milestone_index = cycle_count * 5`

## ✅ 修复验证

### 所有场景测试通过

```
测试场景: Cycle 0的各个里程碑
cycle_count = 0, score = 4
  ✅ milestone_index正确: 0
  ✅ 没有触发奖励（正确）

测试场景: Cycle 0的最后一个里程碑（边界）
cycle_count = 4, score = 4
  ✅ milestone_index正确: 20
  ✅ 没有触发奖励（正确）

测试场景: Cycle 1的最后一个里程碑
cycle_count = 5, score = 4
  ✅ milestone_index正确: 25
  ✅ 没有触发奖励（正确）

测试场景: Cycle 9的最后一个里程碑（接近max）
cycle_count = 9, score = 4
  ✅ milestone_index正确: 45
  ✅ 没有触发奖励（正确）
```

### 完整测试套件通过

```
============================= 358 passed in 1.58s ==============================
```

## 修复文件

- [game_scene.py#L623](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/scenes/game_scene.py#L623) - 修复milestone_index恢复逻辑

## 经验总结

1. **milestone_index和cycle_count的关系**：`cycle_count = milestone_index // 5`
   - `milestone_index` 表示"下一个要获取的里程碑的索引"
   - `cycle_count` 表示"已完成多少个完整的5里程碑周期"

2. **恢复公式**：`milestone_index = cycle_count * 5`
   - 不要使用取模运算 (`%`)，这会导致边界条件错误
   - 直接使用乘法运算即可

3. **边界条件**：
   - 当 `cycle_count = 0` 时，`milestone_index = 0`
   - 当 `cycle_count = 9` 时，`milestone_index = 45`
   - 当 `cycle_count = 10` 时，`milestone_index = 50`（达到max_cycles）
