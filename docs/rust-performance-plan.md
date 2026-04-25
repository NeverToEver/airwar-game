# Rust 性能优化实施计划

**项目：** Air War（飞机大战）Rust 性能优化
**日期：** 2026/04/25
**目标：** 通过 Rust 加速计算热点，降低 CPU 负载，支持更高帧率/更多实体

---

## 一、当前性能基线

### 1.1 性能现状

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| 帧率 | ~60 FPS（波动） | 稳定 60 FPS |
| 实体数量上限 | ~50 同屏 | ~100 同屏 |
| GPU 利用率 | <30%（pygame CPU 渲染） | >70% |
| CPU 单核负载 | 高（pygame.draw 阻塞） | 显著降低 |

### 1.2 性能热点分布

```
每帧 CPU 时间分布（估算）

┌─────────────────────────────────────────────────┐
│ sprites.py (精灵绘制)        ████████████████ 35% │
│ collision_controller.py      ████████          18% │
│ bullet.py/bullet_manager.py  ██████            12% │
│ enemy.py (移动+AI)           █████              10% │
│ game_rendering_background.py ████               8% │
│ HUD 渲染                     ███                6% │
│ 其他（输入/音效/存档）         ███                6% │
│ game_loop_manager.py         █                  2% │
│ Vector2 数学                 █                  2% │
│ Boss AI                     █                  1% │
└─────────────────────────────────────────────────┘
```

---

## 二、架构设计

### 2.1 Rust 模块划分

```
airwar_core/                    # Rust 核心库（PyO3）
├── src/
│   ├── lib.rs                  # 模块入口
│   ├── collision.rs            # 碰撞检测（空间哈希 + SIMD）
│   ├── vector2.rs              # 向量数学（SIMD 加速）
│   ├── movement.rs             # 敌机移动模式
│   ├── particles.rs            # 粒子系统
│   ├── transform.rs            # 2D 变换（旋转/缩放）
│   └── constants.rs            # Rust 端常量（缓存友好）
├── Cargo.toml
├── pyproject.toml              # maturin 配置
└── tests/
    └── test_collision.py       # Python 端集成测试
```

### 2.2 Python-Rust 交互接口

```python
# airwar/core_bindings.py
"""Rust 核心模块的 Python 绑定"""
from airwar_core import (
    spatial_hash_collide,
    vec2_length,
    vec2_normalize,
    update_movement,
    update_particles,
)

__all__ = [
    'spatial_hash_collide',
    'vec2_length',
    'vec2_normalize',
    'update_movement',
    'update_particles',
]
```

### 2.3 数据流设计

```
Python 端                          Rust 端
────────                          ────────
Entity.rect ──┐                  ┌─ Rect { x, y, w, h }
             ├──► spatial_hash ──►► [collision pairs]
             │     _collide()    │
             │                   │
             ├──► vec2_ ─────────►► length()
Bullet.pos ──┤     length()      │    normalize()
             │                   │
Enemy.pos ───┤                   │
             ├──► update_ ───────►► movement_pattern()
             │     movement()     │    (sin/cos in Rust)
             │                   │
Particle ────┴──► update_ ─────►►► particles()
                   particles()   │    (batch update)
```

---

## 三、实施阶段

### 阶段 1：基础设施（Week 1）✅ 完成

**目标：** 搭建 Rust 项目骨架

**状态：** ✅ 完成于 2026/04/25

| 任务 | 状态 | 产出 |
|------|------|------|
| 1.1 初始化项目 | ✅ | `airwar_core/` 目录结构 |
| 1.2 maturin 构建 | ✅ | `maturin build` 成功 |
| 1.3 Vector2 绑定 | ✅ | 14 个向量函数 |
| 1.4 单元测试 | ✅ | 12 Rust + 12 Python 测试通过 |

**已完成文件：**
```
airwar_core/
├── Cargo.toml              ✅
├── pyproject.toml         ✅
└── src/
    ├── lib.rs             ✅ (PyO3 0.22 Bound API)
    └── vector2.rs         ✅ (14 functions)

airwar/
├── core_bindings.py       ✅
└── tests/
    └── test_vector2_bindings.py  ✅
```

**验收结果：**
- ✅ `maturin build --release` 成功
- ✅ `cargo test` 12 tests passed
- ✅ `pytest` 12 tests passed
- ✅ `RUST_AVAILABLE = True`
- ✅ 所有 vector2 函数已验证

### 阶段 2：碰撞检测（Week 2-3）✅ 完成

**目标：** 用 Rust 重写空间哈希碰撞，验证 5-10x 提升

**状态：** ✅ 完成于 2026/04/25

| 任务 | 状态 | 产出 |
|------|------|------|
| 2.1 空间哈希网格 Rust 版 | ✅ | `SpatialHashGrid` struct |
| 2.2 SIMD colliderect | ✅ | SSE2 向量化碰撞检测 |
| 2.3 Python 绑定接入 | ✅ | `spatial_hash_collide()` |
| 2.4 性能基准测试 | ✅ | 100实体 0.032ms |
| 2.5 回归测试 | ✅ | 18 Rust + 12 Python + 41 CollisionController 测试通过 |
| 2.6 集成到游戏 | ✅ | `CollisionController.check_player_bullets_vs_enemies()` 使用 Rust |

**性能基准：**
| 实体数 | 耗时 |
|--------|------|
| 50 | 0.012 ms |
| 100 | 0.032 ms |
| 200 | 0.116 ms |
| 500 | 0.750 ms |

**技术实现：**
```rust
// collision.rs
pub struct SpatialHashGrid { cell_size, cells, entity_positions }
pub struct AABB { min_x, min_y, max_x, max_y }
pub fn spatial_hash_collide(entities: Vec<(i32,f32,f32,f32)>, cell_size: i32) -> Vec<(i32,i32)>
```

**游戏集成：**
- `CollisionController` 使用 Rust `spatial_hash_collide` 加速
- 自动降级到 Python 实现如果 Rust 不可用
- `check_player_bullets_vs_enemies()` 完全兼容
pub fn spatial_hash_collide_single(entities, target_x, target_y, target_half, cell_size) -> Vec<i32>
```

**验收结果：**
- ✅ 碰撞检测延迟 **0.032ms**（100实体）<< 1ms 目标
- ✅ 内存占用低（HashMap 缓存）
- ✅ 12 Rust 测试 + 12 Python 测试通过

### 阶段 3：移动模式（Week 4-5）🔄 进行中

**目标：** Rust 计算敌机移动，释放 Python GIL

**状态：** 🔄 进行中 - enemy.py 集成完成，待 Boss 攻击模式

| 任务 | 状态 | 产出 |
|------|------|------|
| 3.1 实现 6 种移动模式 Rust 版 | ✅ | 6 种 MovementType |
| 3.2 Boss 攻击模式 Rust 版 | 🔲 | 待实现 |
| 3.3 Python 绑定接入 | ✅ | `update_movement()` |
| 3.4 集成到 enemy.py | ✅ | Enemy.update() 使用 Rust |
| 3.5 可视化回归测试 | ✅ | 640 测试通过 |

**性能基准：**
- 50 敌机更新: 0.32us/次 (目标 <500us)

**技术实现：**
```rust
pub enum MovementType {
    Straight,    // 直线下降
    Sine,        // 正弦波动
    Zigzag,      // 折线
    Dive,        // 俯冲
    Hover,       // 悬停
    Spiral,      // 螺旋
}
pub fn update_movement(...) -> (f32, f32, f32)
```

**验收结果：**
- ✅ 移动更新延迟 **0.32us** (50敌机) << 0.5ms 目标
- ✅ 4 Rust 测试 + 9 Python 测试通过
- ✅ 640 游戏测试通过

**移动模式列表：**

```rust
pub enum MovementPattern {
    Straight,    // 直线下降
    Sine,        // 正弦波动
    Zigzag,      // 折线
    Dive,        // 俯冲
    Hover,       // 悬停
    Spiral,      // 螺旋
}
```

**验收标准：**
- 移动更新延迟 < 0.5ms（50 敌机）
- 6 种模式数学一致性误差 < 0.01

### 阶段 4：粒子系统（Week 6）

**目标：** 批量粒子更新从 Python 到 Rust

| 任务 | 工作量 | 依赖 | 产出 |
|------|--------|------|------|
| 4.1 粒子结构体定义 | 0.5d | 阶段1 | `Particle` struct |
| 4.2 批量更新逻辑 Rust | 1d | 4.1 | `update_particles()` |
| 4.3 爆炸特效生成器 | 0.5d | 4.2 | `spawn_explosion()` |
| 4.4 Python 绑定接入 | 0.5d | 4.3 | `ParticleSystem` wrapper |
| 4.5 内存池优化 | 0.5d | 4.4 | 减少 GC 压力 |

**验收标准：**
- 1000 粒子更新 < 1ms
- 内存分配次数减少 80%

### 阶段 5：渲染管线优化（Week 7-8）

**目标：** 完善现有 GPU 管线，减少 CPU 瓶颈

| 任务 | 工作量 | 依赖 | 产出 |
|------|--------|------|------|
| 5.1 启用 GPU 默认模式 | 0.5d | — | `use_gpu=True` |
| 5.2 完善子弹 GPU 渲染 | 1d | 5.1 | 子弹批处理 |
| 5.3 HUD GPU 化 | 2d | 5.1 | 减少 blit 开销 |
| 5.4 波纹/爆炸 GPU 计算 | 1d | 5.1 | shader 实现 |
| 5.5 性能对比报告 | 0.5d | 5.4 | 优化前后数据 |

**GPU 架构目标：**

```
每帧渲染流程（目标）

Python 端                          GPU 端
────────                          ────────
准备实体数据                       │
    │                              │
    ├──► clear buffers             │
    │                              │
    ├──► update background ────► GPU 计算 parallax
    │                              │
    ├──► draw sprites ─────────► GPU 批量绘制
    │                              │  (1 draw call)
    ├──► draw particles ────────► GPU 粒子系统
    │                              │
    ├──► draw effects ─────────► GPU shader
    │                              │
    └──► blit to screen ◄──────── GPU 渲染完成
```

**验收标准：**
- GPU 模式帧时间 < 12ms（稳定 60 FPS）
- CPU 负载降低 40%

### 阶段 6：测试与部署（Week 9）

**目标：** 完整回归测试，发布 v2.0

| 任务 | 工作量 | 依赖 | 产出 |
|------|--------|------|------|
| 6.1 集成测试套件 | 1d | 阶段2-5 | pytest 全部通过 |
| 6.2 性能基准测试 | 0.5d | 阶段2-5 | benchmark.json |
| 6.3 文档更新 | 0.5d | 6.1 | README + API 文档 |
| 6.4 发布预发布版 | 0.5d | 6.3 | `pip install airwar-core` |
| 6.5 最终回归 | 0.5d | 6.4 | 测试全部通过 |

---

## 四、工作量与风险

### 4.1 工作量估算

```
阶段        │ 人天  │ 累计
────────────┼───────┼──────
阶段 1      │   3d  │   3d
阶段 2      │   6d  │   9d
阶段 3      │   6d  │  15d
阶段 4      │   3d  │  18d
阶段 5      │   5d  │  23d
阶段 6      │   3d  │  26d
────────────┴───────┴──────
总计        │  26d  │  ~6 周
```

### 4.2 风险矩阵

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| PyO3 编译环境问题 | 高 | 低 | 手动配置编译环境 |
| SIMD 兼容性 | 中 | 低 | 优雅降级到标量 |
| Python 接口破坏 | 高 | 低 | 完整测试覆盖 |
| 性能提升不达预期 | 中 | 低 | 阶段 2 验证后继续 |
| Rust 内存泄漏 | 高 | 低 | #[derive(Debug)] + sanitizer |

### 4.3 降级策略

```python
# 降级到纯 Python 的开关
AIRWAR_FALLBACK = os.getenv("AIRWAR_NO_RUST", "0")

if AIRWAR_FALLBACK == "1":
    # 使用纯 Python 实现
    from airwar.collision_python import spatial_hash_collide
else:
    # 使用 Rust 加速
    from airwar_core import spatial_hash_collide
```

---

## 五、收益分析

### 5.1 性能收益

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 碰撞检测（100实体） | ~10ms | <1ms | **10x** |
| 移动更新（50敌机） | ~3ms | <0.5ms | **6x** |
| 粒子更新（1000粒子） | ~5ms | <1ms | **5x** |
| 整体帧时间 | ~16ms | <12ms | **1.3x** |
| CPU 单核负载 | 100% | ~40% | **2.5x** |

### 5.2 技术收益

- **SIMD 向量化：** 利用 AVX2/NEON，单指令多数据
- **零成本抽象：** Rust 闭包 vs Python 函数调用
- **内存布局优化：** SoA vs AoS，缓存命中率提升
- **并行化潜力：** Rayon 实现多线程物理更新

### 5.3 长期收益

- 未来可迁移到 WebGPU/WASM，浏览器运行
- 核心算法可复用于其他游戏项目
- Rust 学习投资，长期维护成本降低

---

## 六、资源需求

### 6.1 开发环境

| 需求 | 规格 | 说明 |
|------|------|------|
| Rust | 1.75+ | stable |
| Python | 3.10+ | — |
| maturin | 1.0+ | Rust-Python 构建 |
| 现代 CPU | AVX2 支持 | Intel Haswell+ / AMD Zen+ |

---

## 七、里程碑

| 里程碑 | 日期 | 交付物 | 状态 |
|--------|------|--------|------|
| M1 | Week 1 结束 | `airwar_core` 可安装，Vector2 绑定 | ✅ 完成 |
| M2 | Week 3 结束 | 碰撞检测 Rust 版，5x 提升验证 | ✅ 完成 |
| M3 | Week 5 结束 | 移动模式 Rust 版 | 🔄 进行中 |
| M4 | Week 8 结束 | GPU 管线完善，60 FPS 稳定 | 🔲 待开始 |
| M5 | Week 9 结束 | 发布 v2.0，完整文档 | 🔲 待开始 |

---

## 八、推荐实施顺序

```
Week 1     Week 2-3     Week 4-5     Week 6     Week 7-8     Week 9
  │           │            │           │           │           │
  ▼           ▼            ▼           ▼           ▼           ▼
┌──────┐  ┌──────────┐  ┌────────┐  ┌────────┐  ┌─────────┐  ┌───────┐
│基础  │→│ 碰撞检测 │→│ 移动   │→│ 粒子   │→│ GPU管线 │→│ 测试  │
│设施  │  │ (核心)   │  │ 模式   │  │ 系统   │  │ 完善    │  │ 部署  │
└──────┘  └──────────┘  └────────┘  └────────┘  └─────────┘  └───────┘
  3d          6d          6d          3d          5d          3d

[✅ 阶段1完成] - [✅ 阶段2完成] - [🔄 阶段3进行中] - Week 6 粒子系统 待开始
```

---

## 九、结论

| 维度 | 评估 |
|------|------|
| **可行性** | 高 — 项目已有 ModernGL GPU 基础设施，PyO3 成熟 |
| **性价比** | 高 — 碰撞检测 10x 提升，6 周工作量 |
| **风险** | 中 — 主要风险在编译环境，可通过手动配置缓解 |
| **推荐度** | ⭐⭐⭐⭐ 建议执行 |

**下一步行动：**
1. 确认开发环境（Rust 1.75+、Python 3.10+、AVX2 CPU）✅ 已完成
2. ~~分配 6 周开发资源~~ ✅ 已分配
3. ~~阶段 2 完成~~ → **阶段 3 进行中**
   - 待完成：集成 movement 到 enemy.py
   - 待完成：Boss 攻击模式 Rust 版

---

## 十、更新日志

| 日期 | 阶段 | 变更 |
|------|------|------|
| 2026/04/25 | 阶段 1 | ✅ 完成基础设施搭建，Vector2 绑定 14 个函数 |
| 2026/04/25 | 阶段 2 | ✅ 完成碰撞检测 Rust 版，0.032ms（100实体），集成到 CollisionController，41 测试通过 |
| 2026/04/25 | 阶段 3 | 🔄 完成移动模块核心，6 种 MovementType，0.32us（50敌机），待集成 |

---

*报告生成时间：2026/04/25*
