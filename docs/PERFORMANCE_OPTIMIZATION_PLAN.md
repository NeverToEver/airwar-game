# Airwar 性能优化计划

**日期：** 2026/04/26
**基于：** 性能瓶颈分析报告
**状态：** ✅ 已完成（Phase 1.1, 1.3, 2.1, 2.2 已完成；Phase 3 分析后放弃）

---

## 瓶颈总览

| 优先级 | 热点 | 触发条件 | 类型 |
|--------|------|----------|------|
| P0 | 字体渲染 — 静态标签每帧重建 | 始终 | Python 缓存 |
| P0 | 敌人精灵渲染 — 无缓存重绘多边形 | 敌人 > 0 | Python 缓存 |
| P1 | Noise/Aggressive 移动 — 纯 Python | 40% 敌人 | Rust 扩展 |
| P1 | 爆炸粒子渲染 — 数百次 circle draw | 爆炸触发时 | Python 批量 |
| P2 | 碰撞检测 — 3/4 路径纯 Python 线性扫描 | 始终 | Rust 扩展 |
| P2 | 空间哈希网格 — Python 构建每帧 | 敌人 > 0 | Rust 扩展 |

---

## Phase 1: Python 侧渲染缓存（零风险，立竿见影）

### 1.1 HUD 字体缓存

**文件：** `game/rendering/integrated_hud.py`

静态标签 "SCORE"、"HP"、"KILLS"、"MODE"、"BOSS"、"BUFFS"、"COEFF"、"PROGRESS" 等每帧都调用 `pygame.font.Font.render()` 重建。改为在 `__init__` 或首次渲染时预渲染并缓存。

```python
# 修改前：每帧 render
label = label_font.render("SCORE", True, colors.TEXT_MUTED)

# 修改后：缓存后直接 blit
label = self._cached_labels["SCORE"]
```

**文件：** `game/rendering/hud_renderer.py`

同理，"SCORE:"、"NEXT:"、"HP:"、"KILLS:"、"BOSS:" 标签可预渲染。

### 1.2 敌人精灵缓存

**文件：** `utils/sprites.py`

`draw_enemy_ship()` 每帧被调用时都用 `pygame.draw.polygon()` 重绘。参照 `draw_player_ship()` 的模式加 LRU 缓存。

```python
@lru_cache(maxsize=32)
def get_enemy_sprite(width, height, health_ratio):
    # 预渲染到 Surface，后续直接 blit
```

### 1.3 爆炸粒子渲染批量化

**文件：** `game/explosion_animation/explosion_effect.py`

当前每个粒子单独 `pygame.draw.circle()`。改为预渲染粒子 glow 纹理，渲染时只做 `surface.blit()`。

---

## Phase 2: Rust 移动扩展（中风险，需编译）

### 2.1 Noise 移动类型

**文件：** `airwar_core/src/movement.rs`

噪声移动基于 Perlin/Simplex 噪声或简化的正弦组合，需实现 Rust 版本。入参与 `update_movement` 一致。

### 2.2 Aggressive 移动类型

**文件：** `airwar_core/src/movement.rs`

攻击型移动是噪声移动 + 向玩家位置的平滑追踪。需实现 Rust 版本。

### 2.3 启用 Zigzag Rust 路径

**文件：** `entities/enemy.py:193`

当前 zigzag 被故意排除（Rust 从 active_x 计算 vs Python 从 rect.x 累加）。修复 Rust 侧使其行为一致后启用。

---

## Phase 3: Rust 碰撞扩展（中风险，需编译）

### 3.1 全路径 Rust 碰撞

**文件：** `game/managers/collision_controller.py`

将以下 Python 线性扫描改为 Rust spatial hash：
- `check_player_bullets_vs_boss()` (line 357)
- `check_enemy_bullets_vs_player()` (line 395)
- `check_player_vs_enemies()` (line 380)

### 3.2 空间哈希网格构建移入 Rust

**文件：** `game/managers/collision_controller.py:152-156`

Python 当前每帧遍历所有敌人构建网格再传给 Rust。改为传实体列表给 Rust，在 Rust 侧构建网格。

---

## 执行顺序

```
Phase 1.1 → HUD 字体缓存           [1 文件] ✅ 完成
Phase 1.2 → 敌人精灵缓存           [已存在] ✅ 跳过
Phase 1.3 → 爆炸粒子渲染批量       [1 文件] ✅ 完成
Phase 2.1 → Noise 移动 Rust 实现   [1 Rust] ✅ 完成
Phase 2.2 → Aggressive 移动 Rust   [1 Rust] ✅ 完成
Phase 2.3 → 启用 Zigzag Rust       [保留]  ⏸️  行为差异待修
Phase 3.1 → 全路径 Rust 碰撞       ❌ 放弃 (1对N线性扫描, N小, 不值得)
Phase 3.2 → 网格构建移入 Rust      ❌ 放弃 (同上)
```

---

## 验证

每阶段完成后：
```bash
# 编译语法检查
python3 -m py_compile airwar/airwar/**/*.py

# Rust 编译（Phase 2+）
cd airwar_core && cargo build --release && maturin develop --release

# 测试
cd .. && python3 -m pytest -m smoke

# 帧率观测
sudo -u ubt python3 main.py  # 观察 FPS 和卡顿
```

---

*文档版本：1.0*
*创建日期：2026/04/26*
