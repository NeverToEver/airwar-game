# PersistentSpatialHash 集成技术文档

**日期:** 2026/04/26
**状态:** 规划中
**目标:** 将 `PersistentSpatialHash` 集成到 `CollisionController`，实现增量碰撞检测

---

## 一、背景与目标

### 当前问题

`collision_controller.py` 的 `check_all_collisions` 方法每帧执行：

```python
# 第 153 行
self._clear_grid()  # 清空网格
for enemy in enemies:
    if enemy.active:
        self._add_to_grid(enemy, enemy.get_hitbox())  # 重建所有敌人
```

**问题：**
- 每帧清空并重建整个空间哈希网格
- O(n) 复杂度，n = 敌人数量
- 对于 50+ 敌人，每帧重复插入/删除操作

### 目标

使用 `PersistentSpatialHash` 维护持久化状态，实现：

1. **增量更新**：仅更新位置变化的实体，而非全量重建
2. **状态保持**：网格状态跨帧保持，仅在实体进出时修改
3. **向后兼容**：Rust 不可用时回退到现有 Python 实现

---

## 二、API 回顾

### PersistentSpatialHash 类

```python
from airwar_core import PersistentSpatialHash

hash = PersistentSpatialHash(cell_size=100)

# 批量更新实体位置（insert 或 update）
hash.update_entities([(id, x, y, half_size), ...])

# 单个实体更新
hash.update_entity(id, x, y, half_size)

# 删除实体
hash.remove_entity(id)

# 清空所有实体
hash.clear()

# 获取所有碰撞对
collisions = hash.get_collisions()  # 返回 [(id1, id2), ...]

# 查询某位置的可能碰撞实体
query_result = hash.query(x, y, half_size)  # 返回 [id, ...]
```

### 已知行为

1. `update_entity`: 如果实体已存在，先从旧单元格移除，再插入新位置
2. `get_collisions`: 返回所有发生碰撞的 (id, id) 对，自动去重
3. ID 约定：`id >= 0` 是子弹，`id < 0` 是敌人

---

## 三、集成方案

### 3.1 修改 CollisionController

**文件:** `airwar/game/managers/collision_controller.py`

#### 3.1.1 新增导入

```python
try:
    from airwar.core_bindings import (
        spatial_hash_collide,
        spatial_hash_collide_single,
        PersistentSpatialHash,  # 新增
        RUST_AVAILABLE,
    )
except ImportError:
    PersistentSpatialHash = None  # 回退
    # ...
```

#### 3.1.2 新增实例变量

在 `__init__` 中添加：

```python
def __init__(self):
    # ... 现有代码 ...
    self._use_rust = RUST_AVAILABLE
    # 新增：持久化空间哈希实例
    self._persistent_hash = None
    if self._use_rust and PersistentSpatialHash is not None:
        self._persistent_hash = PersistentSpatialHash(self._grid_cell_size)
```

#### 3.1.3 修改 check_player_bullets_vs_enemies

**现有流程（每帧重建）:**
```python
# 构建实体列表
entities = []
for i, enemy in enumerate(enemies):
    if enemy.active:
        entities.append((-i - 1, cx, cy, half_size))
for i, bullet in enumerate(player_bullets):
    if bullet.active:
        entities.append((i, cx, cy, half_size))

# 调用 Rust 一次性碰撞检测
collision_pairs = spatial_hash_collide(entities, self._grid_cell_size)
```

**新流程（增量更新）:**

```python
if self._use_rust and self._persistent_hash is not None:
    # 1. 更新敌人位置（使用持久化哈希）
    for i, enemy in enumerate(enemies):
        if enemy.active:
            hitbox = enemy.get_hitbox()
            cx = float(hitbox.centerx)
            cy = float(hitbox.centery)
            half_size = float(max(hitbox.width, hitbox.height)) / 2.0
            self._persistent_hash.update_entity(-i - 1, cx, cy, half_size)

    # 2. 更新子弹位置
    for i, bullet in enumerate(player_bullets):
        if bullet.active:
            rect = bullet.rect
            cx = float(rect.centerx)
            cy = float(rect.centery)
            half_size = float(max(rect.width, rect.height)) / 2.0
            self._persistent_hash.update_entity(i, cx, cy, half_size)
        else:
            # 子弹变为非活跃时从哈希中移除
            self._persistent_hash.remove_entity(i)

    # 3. 获取碰撞对
    collision_pairs = self._persistent_hash.get_collisions()

    # 4. 处理碰撞（与现有逻辑相同）
    for id1, id2 in collision_pairs:
        # ... 处理逻辑 ...
```

#### 3.1.4 处理敌人进出

```python
def check_all_collisions(self, ...):
    # 跟踪当前帧存在的敌人 ID
    current_enemy_ids = set()

    for i, enemy in enumerate(enemies):
        if enemy.active:
            current_enemy_ids.add(-i - 1)
            # ... 更新位置 ...

    # 找出上一帧存在但本帧不存在的敌人，从哈希中移除
    if hasattr(self, '_previous_enemy_ids'):
        gone_enemies = self._previous_enemy_ids - current_enemy_ids
        for enemy_id in gone_enemies:
            self._persistent_hash.remove_entity(enemy_id)

    self._previous_enemy_ids = current_enemy_ids
```

---

## 四、实现步骤

### 步骤 1: 基础集成（不改变现有逻辑）

1. 在 `CollisionController.__init__` 中初始化 `_persistent_hash`
2. 在 `check_player_bullets_vs_enemies` 开头调用 `self._persistent_hash.clear()`
3. 保持现有 `spatial_hash_collide` 调用方式
4. 运行测试验证功能正常

### 步骤 2: 增量更新敌人

1. 添加 `_previous_enemy_ids` 跟踪
2. 在循环中调用 `update_entity` 而非构建列表后一次性传递
3. 循环结束后移除消失的敌人
4. 运行测试验证

### 步骤 3: 增量更新子弹

1. 对非活跃子弹调用 `remove_entity`
2. 对活跃子弹调用 `update_entity`
3. 运行测试验证

### 步骤 4: 使用 get_collisions 替代 spatial_hash_collide

1. 替换 `spatial_hash_collide(entities, ...)` 为 `self._persistent_hash.get_collisions()`
2. 移除构建 entities 列表的代码
3. 运行测试验证

### 步骤 5: 清理与优化

1. 移除不再需要的 Python 侧空间哈希实现（`_clear_grid`, `_add_to_grid`, `_get_potential_collisions`）
2. 添加性能基准测试对比

---

## 五、向后兼容

### Rust 不可用

```python
if self._use_rust and self._persistent_hash is not None:
    # 使用 Rust 持久化哈希
    # ...
else:
    # 回退到现有 Python 实现
    self._clear_grid()
    for enemy in enemies:
        if enemy.active:
            self._add_to_grid(enemy, enemy.get_hitbox())
    # ... 现有逻辑 ...
```

### 实体 ID 约定

- 子弹: `id >= 0`
- 敌人: `id < 0`

`get_collisions` 返回的碰撞对中，一个为正数（子弹），一个为负数（敌人）。

---

## 六、关键文件

| 文件 | 修改内容 |
|------|---------|
| `airwar/game/managers/collision_controller.py` | 集成 PersistentSpatialHash |
| `airwar/core_bindings.py` | 已完成导出 |
| `airwar_core/src/collision.rs` | 已完成 PersistentSpatialHash 实现 |
| `airwar_core/src/lib.rs` | 已完成类导出 |

---

## 七、验证方法

1. **单元测试**: `pytest airwar/tests/test_collision.py -v`
2. **集成测试**: `pytest airwar/tests/ -v`
3. **性能测试**: 对比优化前后碰撞检测耗时
4. **手动测试**: 运行游戏，验证碰撞行为一致

---

## 八、风险与注意事项

1. **ID 管理**: 必须正确映射 `enemy index -> negative id`，否则碰撞检测错误
2. **敌人复用**: 如果敌人对象池复用 ID，需要确保 `remove_entity` 在复用前调用
3. **线程安全**: `PersistentSpatialHash` 不是线程安全的，单线程游戏无影响
4. **内存泄漏**: 确保删除的实体正确调用 `remove_entity`，避免僵尸实体堆积
