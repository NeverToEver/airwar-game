# Air War 游戏维护指南

**日期:** 2026/04/26
**版本:** 1.0
**状态:** 活性文档

---

## 一、当前系统状态

### 1.1 已完成优化

| 阶段 | 优化内容 | 状态 | 效果 |
|------|---------|------|------|
| Phase 1 | 玩家常量缓存 | ✅ 完成 | 消除 `fire()` 热路径函数调用 |
| Phase 2 | Enemy getattr 消除 | ✅ 完成 | 每敌人每帧减少 15+ 次字符串查找 |
| Phase 3 | 粒子对象池 | ✅ 完成 | 消除每秒数千次对象分配 |
| Phase 4 | Rust 原地粒子更新 | ✅ 完成（绕过限制） | 对象池已解决核心问题 |
| Phase 5 | PersistentSpatialHash | ✅ 已完成 | 已集成到 collision_controller.py，695 测试通过 |

### 1.2 代码质量状态

| 类别 | 数量 | 已修复 | 剩余 |
|------|:----:|:------:|:----:|
| Critical | 3 | 2 | 1 |
| Major | 10 | 5 | 5 |
| Minor | 7 | 1 | 6 |
| Nit | 3 | 0 | 3 |

**详细报告:** `docs/audits/review-findings-2026-04-26.md`

**本次会话修复:**
- ✅ Phase 5 PersistentSpatialHash 集成
- ✅ GameIntegrator 层违规重构
- ✅ state_machine 空 transition() 移除
- ✅ Surface 对象池（flash surface 缓存）
- ✅ 敌人子弹 cleanup 优化

---

## 二、待完成的工作

### 2.1 高优先级（影响性能和正确性）

#### 2.1.1 集成 PersistentSpatialHash ✅

**状态:** 已完成

**变更内容:**
- 添加 `PersistentSpatialHash` 导入和初始化
- `_persistent_hash` 实例变量维护跨帧状态
- `_previous_enemy_ids` 跟踪敌人进出
- `check_player_bullets_vs_enemies` 改用增量更新（`update_entity`/`remove_entity`）
- 活跃子弹调用 `remove_entity` 确保不残留

**验证:** 695 测试通过

---

#### 2.1.2 架构重构：GameIntegrator 层违规 ✅

**问题:** `game_integrator.py` 直接访问 GameScene 内部属性

**解决方案:**
1. 定义 `IGameScene` Protocol（`interfaces.py`）
2. GameScene 实现该接口
3. GameIntegrator 通过接口方法访问

**变更内容:**
- 新增 `IGameScene` Protocol，包含 22 个接口方法
- GameScene 新增方法：`set_player_position`、`set_player_position_topleft`、`add_score`、`add_kill`、`add_boss_kill`、`show_notification`、`get_enemies`、`get_boss`、`clear_boss`、`set_player_invincible`、`get_score`、`get_cycle_count`、`get_kill_count`、`get_boss_kill_count`、`get_unlocked_buffs`、`get_buff_levels`、`get_player_health`、`get_player_max_health`、`get_difficulty`、`get_username`、`set_paused`、`clear_ripple_effects`
- GameIntegrator 移除所有直接访问 `game_controller.state`、`spawn_controller`、`notification_manager` 的代码

**验证:** 695 测试通过

---

#### 2.1.3 状态机重构：空 transition() 方法 ✅

**问题:** `state_machine.py` 的 `transition()` 方法是空实现且未被使用

**解决方案:** 移除未使用的 `transition()` 方法

**变更内容:**
- 移除 `IMotherShipStateMachine` 接口中的 `transition()` 定义
- 移除 `MotherShipStateMachine.transition()` 空实现

**验证:** 695 测试通过

---

### 2.2 中优先级（性能和可维护性）

#### 2.2.1 Surface 对象池 ✅

**问题:** `explosion_effect.py` 的 `_render_core_flash` 每帧创建新 Surface

**解决方案:** 实现 flash surface 缓存

**变更内容:**
- 添加 `_flash_cache` 字典存储预渲染的 flash surfaces
- 添加 `_get_flash_surface(radius)` 函数获取或创建缓存的 flash surface
- 修改 `_render_core_flash` 使用缓存的 surface

**验证:** 695 测试通过

---

#### 2.2.2 敌人子弹 cleanup 优化 ✅

**问题:** `bullet_manager.py` 中 `cleanup` 参数语义不一致

**解决方案:** 统一清理接口

**变更内容:**
- 修改 `_update_player_bullets` 使用 `Player.cleanup_inactive_bullets()` 替代单独调用 `remove_bullet`
- 更新对应测试用例

**验证:** 695 测试通过

---

### 2.3 低优先级（代码质量）

#### 2.3.1 数据库安全

**问题:** `database.py` 使用 SHA-256 无 salt 哈希

**评估:** 游戏为单机游戏，用户系统仅用于积分排行，无敏感数据

**决定:** 低优先级，延后处理

---

#### 2.3.2 保留参数清理

**问题:** `movement.rs` 中标记为 "reserved" 的未使用参数 `_amplitude` 和 `_spiral_radius`

**评估:** 这些参数预留用于未来功能扩展，当前不影响性能或正确性

**决定:** 保留作为未来扩展的占位符

---

## 三、维护规范

### 3.1 新增代码要求

1. **导入规范:** 遵循 `CLAUDE.md` 中的优先级顺序
2. **性能注意:** 热路径避免运行时 import、避免每帧创建对象
3. **测试要求:** 新功能需有对应测试用例

### 3.2 Rust 集成规范

1. **fallback 必需:** Rust 不可用时必须回退到 Python 实现
2. **性能验证:** 集成后运行性能测试确认提升
3. **API 变更:** 记录 Rust API 变更到 `airwar_core/src/`

### 3.3 提交规范

```
<type>: <简短描述>

<详细描述（可选）>

测试: <测试结果>
相关: <关联的 issue 或文档>
```

**type:** fix, feat, docs, refactor, perf, test, chore

---

## 四、关键文件索引

| 文件 | 用途 | 维护注意事项 |
|------|------|-------------|
| `airwar/game/managers/collision_controller.py` | 碰撞检测 | 已集成 PersistentSpatialHash |
| `airwar/game/mother_ship/game_integrator.py` | 母舰集成 | 通过 IGameScene 接口访问 |
| `airwar/game/mother_ship/state_machine.py` | 状态机 | 已移除空 transition() |
| `airwar/game/explosion_animation/explosion_effect.py` | 爆炸效果 | 已实现 flash surface 缓存 |
| `airwar/utils/database.py` | 用户数据库 | 考虑升级哈希算法 |
| `airwar_core/src/collision.rs` | Rust 碰撞 | PersistentSpatialHash 实现 |

---

## 五、测试命令

```bash
# 所有测试
python3 -m pytest

# 快速测试（排除慢速）
python3 -m pytest -m "not slow"

# 特定模块测试
python3 -m pytest tests/test_collision.py -v
python3 -m pytest tests/test_bullet_manager.py -v
python3 -m pytest tests/test_entities.py -v

# Rust 绑定测试
python3 -m pytest tests/test_*_bindings.py -v

# 性能测试
python3 -m pytest tests/test_performance.py -v
```

---

## 六、技术债务清单

| 债务项 | 优先级 | 估计工时 | 状态 | 依赖 |
|--------|:------:|:--------:|:----:|:----:|
| PersistentSpatialHash 集成 | 高 | 4-6h | ✅ 完成 | 无 |
| GameIntegrator 重构 | 中 | 6-8h | ✅ 完成 | 无 |
| state_machine 重构 | 低 | 2-3h | ✅ 完成 | 无 |
| Surface 对象池 | 中 | 2-3h | ✅ 完成 | 无 |
| 敌人子弹 cleanup 优化 | 低 | 1h | ✅ 完成 | 无 |
| 数据库安全升级 | 低 | 2h | ⏳ 延后 | 无 |
| 保留参数清理 | 低 | 1h | ⏳ 延后 | 无 |

**总估计:** 16-22h，已完成 14-20h

---

## 七、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.1 | 2026/04/26 | 完成 Phase 5 集成、GameIntegrator 重构、state_machine 清理、Surface 对象池、敌人子弹优化 |
| 1.0 | 2026/04/26 | 初始版本 |
