# AirWar 项目维护任务清单

**创建日期:** 2026-05-10
**背景:** 经过三轮代码审查和修复（10 个 Major + Minor 问题已修），以下为剩余待处理项，按优先级和模块分组。

---

## 一、已修复汇总（供参考）

| 轮次 | 问题 | 文件 |
|------|------|------|
| R1 | 全屏 `storm.copy()` 每帧分配 | `haunting_renderer.py` |
| R1 | `random.Random()` 渲染热路径 | `haunting_renderer.py` |
| R1 | 8 个全屏 SRCALPHA 每帧分配 → 复用 `_get_overlay()` | `haunting_renderer.py` |
| R1 | 无 `dispose()` 资源清理 | `haunting_renderer.py` |
| R1 | `GameConstants` 7 个死字段 | `constants.py` |
| R1 | `HauntingRenderer` 双重实例化 | `game_scene.py` |
| R2 | `dispose()` 从未被调用 + 渲染调用无 None 守卫 | `game_scene.py` |
| R3 | `_cached_font_label` 死字段 | `haunting_renderer.py` |
| R3 | `_draw_silhouette` 缺 @staticmethod | `haunting_renderer.py` |
| R3 | `particles.py` 缺类型标注 | `particles.py` |
| R3 | `scaled_viewport.py` 旧式 `Tuple` 导入 | `scaled_viewport.py` |

---

## 二、P0 — 性能隐患

### 2.1 `_apply_screen_distortion` 每帧 `surface.copy()` 两次
**文件:** `airwar/game/rendering/haunting_renderer.py:883,896`
**问题:** `source = surface.copy()` 创建全屏像素拷贝，strength > 0.18 时再 `ghost = source.copy()` 第二次。每帧可产生 2 个 1920x1080 surface 分配。
**建议:** 预分配两个全屏 buffer surface，用 `blit(source, (0,0))` 替代 `copy()`。

### 2.2 `_render_rain` 粒子密度计算可能产生巨量绘制调用
**文件:** `airwar/game/rendering/haunting_renderer.py:302`
**问题:** `density = int((width * height / 8200) * (0.24 + self._strength * 1.15))` — 在 1920x1080 下 strength=1.0 时 density ≈ 350。每条雨线一个 `pygame.draw.line` 调用。
**建议:** 评估是否可降低密度系数或使用 pre-rendered rain texture tile。

### 2.3 `_get_storm_surface` 中仍使用 `random.Random()` 
**文件:** `airwar/game/rendering/haunting_renderer.py:276`
**问题:** Cache-miss 路径创建 `random.Random(seed)` 实例。虽然仅在 resize 时触发，但风格与其他已修复的 LCG 替代方案不一致。
**建议:** 统一为 LCG 或复用 `self._rng`。

---

## 三、P1 — 代码组织

### 3.1 `game_scene.py` 过长（1282 行）
**文件:** `airwar/scenes/game_scene.py`
**问题:** 渲染方法 `_render_gameplay` 混合了游戏渲染 + haunting 渲染 + HUD + 多种条件覆盖层。整个类承担了过多职责。
**建议:** 将 haunting 渲染调用抽取为独立方法 `_render_haunting_layer(surface)`，减少 `_render_gameplay` 的长度。

### 3.2 `_draw_broken_biplane` 方法过长（~90 行）
**文件:** `airwar/game/rendering/haunting_renderer.py:445-536`
**问题:** 单个方法绘制完整的双翼飞机，包含翅膀、机身、尾翼、机头、烟雾、血迹。难以独立测试或修改。
**建议:** 拆分为 `_draw_biplane_wings()`, `_draw_biplane_fuselage()`, `_draw_biplane_details()`。

### 3.3 `_draw_spirit_ship` 方法过长（~85 行）
**文件:** `airwar/game/rendering/haunting_renderer.py:589-674`
**问题:** 类似 3.2，同时处理普通敌人、精英敌人、Boss 三种变体，内部有多处条件分支。
**建议:** 拆分为 `_draw_spirit_hull()`, `_draw_spirit_wings()`, `_draw_spirit_skull()` 等子方法。

### 3.4 `MemoryFragment` dataclass 位置不当
**文件:** `airwar/game/rendering/haunting_renderer.py:15-25`
**问题:** `MemoryFragment` 是 `HauntingRenderer` 的专属数据结构，但定义在模块顶层。如果今后拆分文件，它应随 `HauntingRenderer` 一同移动。
**建议:** 作为嵌套类移入 `HauntingRenderer`，或提取到独立的 `haunting_types.py`。

---

## 四、P2 — 风格一致性

### 4.1 `particles.py` 中文 docstring
**文件:** `airwar/ui/particles.py:12,23,42,57,68,95`
**问题:** 类和方法 docstring 使用中文（"粒子系统"、"预创建常用尺寸的粒子纹理"等），与项目 CLAUDE.md 规定的 "Docstrings: English, Google style" 不一致。
**建议:** 全局搜索 `airwar/ui/` 下的中文 docstring，统一替换为英文。

### 4.2 `window.py` 使用旧式 typing 导入
**文件:** `airwar/window/window.py:3`
**问题:** `from typing import Optional, Tuple, List` — 项目其他新文件已使用 `from __future__ import annotations` + `tuple[Foo]` 语法。
**建议:** 统一迁移到 `from __future__ import annotations`，替换 `Optional[X]` → `X | None`，`List[X]` → `list[X]`，`Tuple[X, Y]` → `tuple[X, Y]`。

### 4.3 `haunting_renderer.py` 公开方法参数缺少类型标注
**文件:** `airwar/game/rendering/haunting_renderer.py:112,164`
**问题:** `render_world_styles` 的 `player`、`boss` 参数，`render_foreground_distortion` 的 `state`、`player` 参数无类型标注。虽然有意使用 duck-typing 避免循环导入，但可加 `Any` 标注或 `Protocol`。
**建议:** 评估是否值得引入 `typing.Protocol` 定义实体接口。

### 4.4 `_draw_entity_veil` 是 staticmethod 但不依赖类
**文件:** `airwar/game/rendering/haunting_renderer.py:392`
**问题:** 与已降为模块级函数的 `_entity_center`、`_mix_color` 模式相同——staticmethod 不引用 self/cls。为保持一致性，应统一处理。
**建议:** 降为模块级函数。

---

## 五、P3 — 测试覆盖

### 5.1 `HauntingRenderer` 缺少 scheduler 状态机测试
**文件:** 需新建或追加到 `airwar/tests/test_haunting_renderer.py`
**缺失覆盖:**
- `_update_event_schedule` 的事件触发/结束循环
- `_calculate_strength` 的 pulse/envelope 波形
- `_advance_memory_fragments` 的过期清理
- `dispose()` 后 `is_active()` 行为

### 5.2 `ParticleSystem._texture_size_for_particle` 仅测试了小尺寸
**文件:** `airwar/tests/test_ui_particles.py`
**缺失覆盖:** `size=6..20` 的映射、`size>20` 的回退边界。

### 5.3 `ScaledViewport` 缺少 `screen_to_logical` 测试
**文件:** `airwar/tests/test_scaled_viewport.py`
**缺失覆盖:** 缩放/居中后的坐标转换正确性。

### 5.4 `game_scene.py` 中 haunting 集成无集成测试
**文件:** 无
**缺失覆盖:** `_update_haunting_effect` 中 `enemy_pressure` 计算逻辑、`exit()` 中 `dispose()` 调用、`enter()` 中旧实例清理。

---

## 六、建议执行顺序

| 优先级 | 条目 | 预估改动量 | 风险 |
|--------|------|-----------|------|
| 1 | 2.1 `surface.copy()` 优化 | ~15 行 | 低 |
| 2 | 2.3 `random.Random()` 统一 | ~10 行 | 低 |
| 3 | 4.4 `_draw_entity_veil` 降级 | ~5 行 | 低 |
| 4 | 3.1 抽取 `_render_haunting_layer` | ~30 行 | 中 |
| 5 | 5.1 scheduler 状态机测试 | ~60 行 | 低 |
| 6 | 4.1 中文 docstring → English | ~15 行 | 低 |
| 7 | 3.2 + 3.3 长方法拆分 | ~80 行 | 中 |
| 8 | 4.2 `window.py` typing 现代化 | ~30 行 | 中 |
| 9 | 5.2-5.4 补充测试 | ~40 行 | 低 |
| 10 | 2.2 rain density + 3.4 MemoryFragment 位置 | ~20 行 | 低 |

---

## 七、不做事项

以下为评审中发现但建议**暂不处理**的项：

- **`particles.py` 视觉效果变更（0.4→0.28）** — 已在 commit 中，属于设计决策，不是 bug
- **`test_ui_particles.py` 间接导入** — 因循环导入（`airwar.ui.particles` → `airwar.ui` → `airwar.game` → `airwar.ui`）必须保持 `welcome_scene` 导入路径
- **`window.py` `process_events` 返回类型复杂** — 功能正常，重构收益低
- **`haunting_renderer.py` 渲染方法参数用 duck-typing** — 避免与 entity 包产生循环导入，属于有意的架构取舍
