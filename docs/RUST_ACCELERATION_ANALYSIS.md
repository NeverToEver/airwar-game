# Rust 加速性能优化可行性分析

**日期:** 2026/04/26
**目标:** 评估通过 Rust 扩展模块解决性能问题的可行性

---

## 一、问题分类与 Rust 加速潜力

| 问题 | Rust 可加速 | 加速效果 | 备注 |
|------|:-----------:|---------|------|
| 碰撞检测 O(n*m) | ✅ 是 | **高** | 空间哈希批量检测，避免 Python 循环 |
| 粒子更新对象分配 | ⚠️ 部分 | **中** | Rust 可做计算，但 Python 对象创建不可避免 |
| getattr() 字符串查找 | ❌ 否 | - | Python 属性访问，Rust 无法优化 |
| 内存泄漏 (_hit_enemies) | ❌ 否 | - | Python 列表管理，需修改 Python 代码 |
| Surface 每帧创建 | ❌ 否 | - | pygame 库调用，必须在 Python 层处理 |
| get_game_constants() 开销 | ❌ 否 | - | Python 函数调用，Rust 无法优化 |
| 列表推导式内存抖动 | ⚠️ 部分 | **低** | Rust 侧可避免，但收益有限 |
| 子弹循环无提前退出 | ❌ 否 | - | Python 控制流逻辑问题 |

---

## 二、详细分析

### 2.1 碰撞检测系统 ✅ 可大幅加速

**当前问题:**
- 每帧重建空间哈希网格（`collision_controller.py:153`）
- 回退路径使用 O(n*m) 暴力检测
- `spatial_hash_collide_single` 每次调用创建新 HashSet

**Rust 加速方案:**

```rust
// 保持持久化的空间哈希网格，避免每帧重建
struct SpatialHash {
    cells: HashMap<(i32, i32), Vec<i32>>,
    positions: HashMap<i32, (f32, f32, f32)>,  // 避免每次 .copied()
}

impl SpatialHash {
    pub fn update_positions(&mut self, entities: &[(i32, f32, f32, f32)]) {
        // 批量更新位置，而不是每帧清空重建
    }

    pub fn query(&self, rect: &Rect) -> Vec<i32> {
        // 复用 HashSet 而非每次新建
    }
}
```

**预期效果:**
- 消除每帧网格重建开销
- 查询复杂度从 O(n) 降至 O(1) ~ O(k)，k 为相邻区域实体数
- 预计性能提升: **3-5x**

**工作量:** 中等（需修改 Rust 侧 API 和 Python 调用方）

**状态:** ✅ `PersistentSpatialHash` 已实现，待集成到 `collision_controller.py`

---

### 2.2 粒子系统 ⚠️ 部分可加速

**当前问题:**
```python
# explosion_effect.py:205-218
for (x, y, vx, vy, life, size, is_alive), original_max_life in zip(results, max_lives):
    if is_alive:
        self._particles.append(ExplosionParticle(  # 每帧创建数千个对象
            x=x, y=y, vx=vx, vy=vy,
            life=life, max_life=original_max_life, size=size
        ))
```

**当前 Rust 实现 (`particles.rs`):**
```rust
pub fn batch_update_particles(
    particles: &[(f32, f32, f32, f32, f32, f32, f32)],
    dt: f32,
) -> Vec<(f32, f32, f32, f32, f32, f32, bool)>
```

Rust 只做物理计算，返回元组列表，Python 仍需创建新对象。

**解决方案:** Python 侧对象池已实现，消除了对象分配问题。

**Rust 加速效果:** 部分（计算在 Rust，对象管理在 Python）

---

### 2.3 敌人移动模式 ✅ 已有 Rust 实现

**当前问题:**
- 15+ 次 `getattr()` 字符串查找（`enemy.py:192-253`）
- 每次查找都是 Python 侧开销

**现状:** `movement.rs` 已有 `update_movement` 函数

```rust
pub fn update_movement(
    x: f32, y: f32, move_type: &str,
    timer: f32, offset: f32, amplitude: f32, frequency: f32,
    screen_width: f32, screen_height: f32, dt: f32,
) -> ((f32, f32), f32, f32, f32)
```

**问题:** `getattr()` 发生在调用 Rust 函数**之前**，Rust 无法优化。

**真正解决:** 在 Python 侧用正式属性替代 getattr()，Rust 只负责计算密集型部分。

**状态:** ✅ Python 侧 `_rust_params` 预计算已实现

---

### 2.4 无法通过 Rust 加速的问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `_hit_enemies` 内存泄漏 | Python 列表无限增长 | 定期清空或在场景切换时清理 |
| `pygame.Surface` 每帧创建 | pygame 是 Python 库 | 预分配 Surface 池并复用 |
| 列表推导式创建新列表 | Python 内存分配 | 用 `deque` 或原地过滤 |
| `get_game_constants()` 开销 | Python 函数调用 | 在 `__init__` 时缓存引用 |
| 子弹循环无提前退出 | Python 控制流 | 重构循环逻辑，添加 break |

---

## 三、Rust 加速优先级建议

```
┌─────────────────────────────────────────────────────────────┐
│                      投入产出比分析                          │
├─────────────────────────────────────────────────────────────┤
│  高优先级（加速效果明显，工作量适中）                        │
│  ├── 碰撞检测持久化空间哈希网格 ✅ 已实现                   │
│  └── 粒子系统对象池 ✅ 已实现                               │
├─────────────────────────────────────────────────────────────┤
│  中优先级（有一定效果，但有更简单的 Python 方案）            │
│  ├── enemy.py 属性访问优化 ✅ 已实现                        │
│  └── player.py 常量缓存 ✅ 已实现                           │
├─────────────────────────────────────────────────────────────┤
│  低优先级（Rust 收益小，优先考虑 Python 重构）              │
│  ├── 列表推导式优化 ✅ 已实现                               │
│  └── 控制流重构                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、结论

| 类别 | 数量 | 可 Rust 加速 | 必须 Python 改代码 |
|------|:----:|:------------:|:-----------------:|
| 严重问题 | 3 | 1 | 2 |
| 高危问题 | 3 | 2 | 1 |
| 中等问题 | 4 | 1 | 3 |
| 低严重 | 1 | 0 | 1 |

**核心结论:**

1. **Rust 能解决约 40% 的问题**，主要是计算密集型（碰撞检测、粒子物理计算）

2. **最严重的问题（粒子对象分配）**已通过 Python 侧对象池解决

3. **60% 的问题必须修改 Python 代码**：
   - `getattr()` → 正式属性 ✅
   - 内存泄漏 → 定期清理
   - Surface 创建 → 对象池
   - 函数调用开销 → 缓存引用 ✅

4. **已完成:**
   - 碰撞检测持久化网格（Rust API 就绪）
   - 粒子对象池（消除严重问题）
   - Python 属性访问优化（消除高危问题）
   - Python 常量缓存（消除低严重问题）

---

## 五、工作量估算

| 任务 | 复杂度 | 预估工时 | 性能收益 | 状态 |
|------|:------:|:--------:|:--------:|:----:|
| 碰撞检测持久化 | 中 | 4-6h | +30-50% | ✅ 已实现 |
| 粒子对象池 | 中 | 4-6h | +20-30% | ✅ 已实现 |
| enemy.py 属性优化 | 低 | 1-2h | +10-15% | ✅ 已实现 |
| player.py 常量缓存 | 低 | 0.5-1h | +2-5% | ✅ 已实现 |
| Surface 对象池 | 中 | 2-3h | +5-10% | ⏳ 待处理 |
| 子弹循环优化 | 低 | 1h | +5-10% | ⏳ 待处理 |

**已完成:** 约 7-10 小时工作
**待处理:** 约 3-4 小时工作
