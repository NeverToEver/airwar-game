# 存档机制隐性问题报告
Date: 2026-04-23
Reviewer: AI Agent (深度审查)

> ⚠️ **审核状态**: 本报告已通过元审查，部分问题严重程度已修正

## ⚠️ 发现的问题摘要

| 严重程度 | 问题数量 | 标签 | 审核结果 |
|---------|---------|------|----------|
| 🔴 Critical | 1 | [DATA] | ✅ 确认 |
| 🟠 Major | 3 | [DATA], [ARCH] | ⚠️ 2个降级为Minor |
| 🟡 Minor | 2 | [LOGIC] | ✅ 确认 |

---

## 🔴 Critical Issues

### 1. ✅ [DATA] milestone_index 恢复逻辑严重错误 - **已修复**

**文件:** [game_scene.py:586](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/scenes/game_scene.py#L586)
**影响:** 游戏状态不一致，导致分数计算错误

**修复内容:**
```python
# 修复后代码 (2026-04-23)
self.game_controller.milestone_index = save_data.cycle_count  # ✓ 直接赋值
self.game_controller.cycle_count = save_data.cycle_count
```

**验证状态:** ✅ 测试通过

---

## 🟠 Major Issues

### 2. ⚠️ [DESIGN] 单一存档位导致多用户存档覆盖

> ⚠️ **审核修正**: 降级为 Minor。这是设计选择而非bug。

**文件:** [persistence_manager.py:14](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/game/mother_ship/persistence_manager.py#L14)
**影响:** 用户A的存档会被用户B覆盖

**问题代码:**
```python
class PersistenceManager(IPersistenceManager):
    DEFAULT_SAVE_FILE_NAME = "user_docking_save.json"  # 固定文件名
    DEFAULT_SAVE_DIRECTORY = "airwar/data"
```

**问题分析:**
- 所有用户共享同一个存档文件
- 虽然加载时检查用户名匹配，但保存时会直接覆盖
- 用户切换后，旧存档会被新用户的存档覆盖

**当前流程:**
```
用户A登录 → 用户A游戏 → 保存 → [user_docking_save.json = 用户A数据]
用户B登录 → 用户B游戏 → 保存 → [user_docking_save.json = 用户B数据] ← 用户A存档丢失！
```

**修复建议:**
```python
def __init__(self, username: str = None, ...):
    safe_username = re.sub(r'[^a-zA-Z0-9]', '_', username or 'default')
    self.SAVE_FILE_NAME = f"save_{safe_username}.json"
```

---

### 3. ⚠️ [ARCH] 存档恢复时机问题

> ⚠️ **审核修正**: 降级为 Minor。实际影响较小。

**文件:** [scene_director.py:136-138](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/game/scene_director.py#L136-L138)
**影响:** 恢复存档时游戏已开始运行，可能导致状态不一致

**问题代码:**
```python
self._scene_manager.switch("game", ...)
current_scene = self._scene_manager.get_current_scene()

# 恢复在游戏初始化之后，第一帧之前
if self._pending_save_data and isinstance(current_scene, GameScene):
    current_scene.restore_from_save(self._pending_save_data)
```

**问题分析:**
- `switch("game")` 调用 `game_scene.enter()`，游戏开始初始化
- 敌人生成器、子弹管理器等子系统已创建
- 恢复时只恢复了部分状态，但敌人、子弹等未清理

**潜在后果:**
- 恢复后可能有残留的敌人或子弹
- 游戏循环可能已经执行了部分帧

**修复建议:**
```python
# 选项1: 在 enter() 中添加可选的存档参数
def enter(self, **kwargs) -> None:
    save_data = kwargs.get('save_data')
    # ... 初始化逻辑 ...
    if save_data:
        self.restore_from_save(save_data)

# 选项2: 在恢复后立即清理游戏状态
if self._pending_save_data:
    current_scene.restore_from_save(self._pending_save_data)
    current_scene.clear_game_state()  # 清理残留实体
```

---

### 4. ❌ [DESIGN] 敌人/子弹状态未保存

> ⚠️ **审核修正**: 移除此问题。这是设计决策，不应作为bug。

**文件:** [game_integrator.py:93-116](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/game/mother_ship/game_integrator.py#L93-L116)
**影响:** 恢复存档后需要重新击杀当前波次的敌人

**问题描述:**
存档只保存玩家状态和游戏进度，但未保存：
- 当前波次的敌人位置和状态
- 场上的子弹
- Boss状态（如果有）

**当前存档数据:**
```python
save_data = GameSaveData(
    score=self._game_scene.score,
    cycle_count=self._game_scene.cycle_count,
    kill_count=self._game_scene.game_controller.state.kill_count,
    unlocked_buffs=self._game_scene.unlocked_buffs,
    buff_levels=self._get_buff_levels(),
    player_health=self._game_scene.player.health,
    # ... 缺少敌人和子弹状态 ...
)
```

**影响:**
- 玩家可能需要重新击杀当前波次的大量敌人
- 如果在Boss战中存档，恢复后Boss状态丢失

**修复建议:**
> ⚠️ **审核修正**: 这不是bug，是设计权衡。建议移至"未来优化建议"章节。

这是设计权衡问题：
- **完整保存**: 存档数据量大，但体验一致
- **简化保存**: 当前实现，快速但需要重玩当前波次

**建议:** 在文档中添加说明这是有意为之的设计选择。

---

## 🟡 Minor Issues

### 5. ✅ [LOGIC] entrance_animation 状态恢复不一致 - **已修复**

**文件:** [game_scene.py:599-607](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/scenes/game_scene.py#L599-L607)
**影响:** 非母舰状态存档恢复后可能看到入口动画

**修复内容:**
```python
# 修复后代码 (2026-04-23)
if save_data.is_in_mothership:
    self._restore_to_mothership_state()
    self.game_controller.state.entrance_animation = False
else:
    self.game_controller.state.entrance_animation = False
```

**验证状态:** ✅ 测试通过

---

### 6. ✅ [LOGIC] 存档恢复后游戏状态未完全同步 - **已修复**

**文件:** [game_scene.py:566-607](file:///Users/xiepeilin/TRAE1/AIRWAR/airwar/scenes/game_scene.py#L566-L607)
**影响:** 某些游戏状态可能不一致

**修复内容:**
```python
# 修复后代码 (2026-04-23)
# 1. score_multiplier 恢复
self.game_controller.state.score_multiplier = {'easy': 1, 'medium': 2, 'hard': 3}.get(save_data.difficulty, 1)

# 2. boss_kill_count 保存和恢复
# - GameSaveData 添加 boss_kill_count 字段
# - game_integrator.py 的 create_save_data() 保存 boss_kill_count
# - game_scene.py 的 restore_from_save() 恢复 boss_kill_count
```

**验证状态:** ✅ 测试通过

---

## 📊 存档保存 vs 恢复字段对比

| 字段 | 保存 | 恢复 | 状态 |
|------|------|------|------|
| score | ✓ | ✓ | ✅ |
| cycle_count | ✓ | ✓ | ✅ |
| kill_count | ✓ | ✓ | ✅ |
| unlocked_buffs | ✓ | ✓ | ✅ |
| buff_levels | ✓ | ✓ | ✅ |
| player_health | ✓ | ✓ | ✅ |
| player_max_health | ✓ | ✓ | ✅ |
| difficulty | ✓ | ✓ | ✅ |
| username | ✓ | ✓ | ✅ |
| is_in_mothership | ✓ | ✓ | ⚠️ 特殊处理 |
| **milestone_index** | ✗ | ⚠️ | ❌ **计算错误** |
| **enemies** | ✗ | N/A | ⚠️ 设计限制 |
| **bullets** | ✗ | N/A | ⚠️ 设计限制 |
| **boss_state** | ✗ | N/A | ⚠️ 设计限制 |

---

## 🎯 优先级修复建议

> ⚠️ **审核修正**: 已根据元审查调整优先级

### 必须立即修复 (P0)
1. **修复 milestone_index 恢复逻辑** - 导致游戏状态严重不一致

### 建议修复 (P1)
2. **统一 entrance_animation 处理** - 提升用户体验

### 可选优化 (P2)
3. **boss_kill_count 未保存** - 可选功能增强
4. **优化存档恢复时机** - 代码改进
5. **支持多用户存档分离** - 功能建议

### 建议移除 (P3)
6. **敌人/子弹状态保存** - 设计决策，非bug

---

## ✅ 修复完成总结

### 已修复问题

| # | 问题 | 状态 | 日期 |
|---|------|------|------|
| 1 | milestone_index 恢复错误 | ✅ 已修复 | 2026-04-23 |
| 5 | entrance_animation 状态不一致 | ✅ 已修复 | 2026-04-23 |
| 6 | 游戏状态未完全同步 | ✅ 已修复 | 2026-04-23 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `game_scene.py` | 修复 milestone_index 恢复逻辑，添加 score_multiplier 和 boss_kill_count 恢复 |
| `mother_ship_state.py` | 添加 boss_kill_count 字段 |
| `game_integrator.py` | 添加 boss_kill_count 保存 |
| `test_persistence_manager.py` | 添加 boss_kill_count 测试用例 |

### 测试结果

```
============================== 36 passed in 0.19s ==============================
```

---

*报告生成时间: 2026-04-23*
*最后更新: 2026-04-23*
*审查范围: 存档机制深度分析*
*状态: ✅ 所有关键问题已修复*
