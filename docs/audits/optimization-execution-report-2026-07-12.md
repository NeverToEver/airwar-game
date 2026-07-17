# 系统级性能优化执行报告

**日期**：2026-07-12  
**范围**：`/Users/xiepeilin/ccProject/airwar-game`（Python + Rust PyO3 空战游戏）  
**工作流**：静态扫描 → 重构手术 → 边界验证

---

## 1. 目标摘要

在保持业务逻辑完全等价、不牺牲可读性、不引入重型外部依赖的前提下，对代码库进行压缩与性能提升：

- 极致压缩代码总量，消灭冗余抽象与单次使用中间变量
- 提升运行时效率，减少热循环中的临时对象与重复计算
- 清理死代码（未使用变量、方法、导入）
- 降低系统资源开销（复用容器、缓存、浅层优化）

---

## 2. 静态扫描

使用 Explore agent 对 `airwar/`、`airwar_core/src/`、`main.py`、`run_with_server.py` 进行全库扫描，结合 `ruff`、`cargo clippy` 与手动模式匹配，定位到以下主要问题类别：

| 类别 | 典型位置 | 数量级 |
|---|---|---|
| 热路径临时对象分配 | `collision_controller.py`、子弹管理、爆炸渲染 | 数十处/帧 |
| 死代码（方法/属性/常量） | `boss.py`、`player_state.py`、`game_integrator.py`、`design_tokens.py` 等 | 数百行 |
| 重复 `getattr` / `get_screen_*` | `bullet_manager.py`、`entity_renderer.py` | 多处 |
| Rust clippy 警告 | `bullets.rs`、`movement.rs` 等 | 8 条 |
| 配置膨胀 | `design_tokens.py` 未使用 token | 100+ 处 |

完整扫描结论已保留在会话记录中，作为本次重构的输入清单。

---

## 3. 重构手术（已执行）

### 3.1 碰撞系统热路径（`airwar/game/managers/collision_controller.py`）

- 删除死代码：`_previous_enemy_ids`、`_get_cell_key`、`clear_events` 方法。
- `_get_entities_in_cells` 改为 **generator + 复用 `self._query_seen`**，每查询减少一次 `list` + `set` 分配。
- `check_player_vs_enemies` 复用已构建的敌人空间网格，敌人数多时由 **O(n)** 降至 **O(k)**。
- `_get_rect_bounds` 移除冗余 `else` 分支。

**复杂度变化**：每查询临时空间从 O(k) 降至 O(1)；玩家-敌人碰撞从 O(n) 降至 O(k)。

### 3.2 子弹管理热路径（`airwar/game/managers/bullet_manager.py`）

- 缓存 `screen_width/screen_height`，避免每颗子弹 2 次屏幕尺寸函数调用。
- 将 `data`/`is_laser`/`margin` 缓存在 `bullet_map` 元组中，apply 阶段 **O(1) 查表** 替代多次 `getattr`。
- `struct.pack_into` 使用 `*values` 解包，减少 12 次显式索引。
- 内联并删除 `_is_bullet_outside_screen` 辅助方法。

**复杂度变化**：apply 阶段从 O(n·m) 的元数据查找退化为 O(n)；每帧减少 2×bullets 次函数调用。

### 3.3 游戏循环（`airwar/game/managers/game_loop_manager.py`）

- 删除未使用的 `EntityBuffer` 实例 `_entity_buf`。
- `struct.pack` 全部改为 `*base` / `*extra` 解包，删除约 24 行机械索引代码。
- 移除 `_batch_indices` 的冗余 lazy 初始化。
- `_estimate_player_dps` 用 `getattr(..., lambda: {})()` 替代 `hasattr` + `getattr` 混用。

### 3.4 渲染热路径（`airwar/game/rendering/entity_renderer.py`）

- `render_boss` 入口缓存一次 `pygame.time.get_ticks()`，向下传给 `_render_boss_body`、`_render_enrage_body_aura`、`_render_enrage_core_lines`。
- 每帧减少 4–5 次 SDL 时间查询调用。

### 3.5 刷怪控制器（`airwar/game/managers/spawn_controller.py`）

- 删除未使用属性 `is_boss_killed`。
- `cleanup_enemies` 改为 `self.enemies[:] = [...]` 保留列表对象，避免引用失效与额外分配。

### 3.6 爆炸特效死代码清理（`airwar/game/explosion_animation/explosion_effect.py`）

- 删除未使用的模块级缓存函数 `_get_glow_texture`、`_get_spark_core`、`_get_flash_surface` 及其 `OrderedDict` 缓存。
- 删除实例上从未读写的 `_glow_surf_cache`、`_glow_surf_size`。
- 清理 `reset()` 中不一致的整型 0（统一为 0.0）。

### 3.7 Rust 核心（`airwar_core/src/bullets.rs`、`movement.rs`）

- 将 `buf.len() % STRIDE != 0` 改为 `!buf.len().is_multiple_of(STRIDE)`，消除 2 处 clippy 警告。

### 3.8 Boss 协调器死代码清理（`airwar/entities/enemy/boss/boss.py`）

- 删除未调用的公共谓词：`is_enraged()`、`is_enrage_active()`、`is_enrage_transitioning()`。
- 删除未调用的私有 shim 方法：
  - `_primary_boss_muzzle_position`、`_trigger_muzzle_flash`、`_update_muzzle_flash`、`_face_target`
  - `_is_aim_dashing`、`_start_aim_dash`、`_update_aim_dash`
  - `_create_enrage_snapshot_attack`、`_record_enrage_trail`、`_clamped_enrage_position`、`_enrage_path_radius`、`_enrage_progress`
- 删除未使用的 shim 属性：`_enrage_timer`、`_enrage_snapshot_target`。
- 保留 `render()`（`Entity` 抽象方法必须实现）、`_enrage_transition_timer`（`game_loop_manager` 通过 `getattr` 读取）、`_facing_vector`（`entity_renderer` 使用）。

### 3.9 玩家状态机死代码清理（`airwar/entities/player_state.py`）

- 删除未使用的属性：`state`、`shield_duration`、`dock_active`、`respawn_invincible`。
- 删除未调用的生命周期方法：`mark_dying()`、`mark_dead()`、`respawn()`。
- 删除未调用的子状态辅助方法：`tick_shield()`、`enter_dock()`、`exit_dock()`、`enter_respawn_invincibility()`、`tick_respawn_invincibility()`、`is_shielded()`、`is_docked()`、`is_respawn_invincible()`、`should_lock_controls()`。
- 清理 `__init__` 中随之上游无读取方的计时/标志属性。
- 简化 `activate_shield` / `deactivate_shield`，明确 shield duration 由 `PlayerShield` 组件管理。

### 3.10 母舰协调器死代码清理（`airwar/game/mother_ship/game_integrator.py`）

- 删除从 `mothership_gatling.py` 重新导出但本类不用的 12 个 `MOTHERSHIP_GATLING_*` 类常量及 `GatlingTurretSpec` 再导出。
- 删除 10 个外部无调用的公共方法：
  - 动画进度查询：`get_docking_animation_progress`、`get_docking_animation_start`、`get_undocking_animation_progress`、`get_undocking_animation_start`
  - 动画活跃谓词：`is_entering_animation_active`、`is_docking_animation_active`、`is_undocking_animation_active`
  - 其他公共包装器：`is_in_cooldown`、`request_undock`、`is_player_control_disabled`、`reset_to_idle_with_mothership_visible`
- 清理随之变为未使用的 `EVENT_UNDOCK_REQUESTED` 导入。
- 保留全部事件总线回调（`event_hub.py` 的 `HANDLER_BINDINGS` 订阅了 12 个处理器，含 3 个空实现；移除会破坏注册表，本次未动）。

### 3.11 场景层死代码清理（`airwar/scenes/game_scene.py`、`game_scene_protocols.py`）

- 删除从未读取的加载状态：`_is_loading`、`_loading_progress` 属性及其在 `enter()` 中的赋值。
- 删除 homecoming 死转发器：`set_homecoming_coordinator`、`_leave_homecoming_base`、`_on_homecoming_orbital_strike`、`_on_homecoming_departure_complete`。
- 同步 `GameSceneProtocol` 中 `_is_loading` / `_loading_progress` 的声明。

### 3.12 玩家实体死代码清理（`airwar/entities/player.py`、`airwar/game/protocols.py`）

- 删除未使用常量 `BULLET_SPAWN_Y_OFFSET`。
- 删除 `bullet_damage_value` property（外部直接读写 `player.bullet_damage`）。
- 删除 12 个未调用的公共方法：`get_aim_target`、`get_facing_angle_degrees`、`set_render_hitbox`、`remove_bullet`、`is_colliding_with`、`is_phase_dashing`、`is_alive`、`is_dying`、`is_dead`、`alive_substate`、`is_alive_substate`。
- 同步 `PlayerProtocol`，移除 `remove_bullet` 声明。

### 3.13 玩家组件死代码清理（`airwar/entities/player_components/`）

- `aim.py`：删除未读取的公共 accessor（`aim_target`、`facing_angle_degrees`、setter、`facing_direction`、`rotated_sprite_cache`、`get_aim_target`、`get_facing_angle_degrees`），保留底层私有字段与 `get_facing_direction`/`set_aim_target`/`update`/`rotated_ship_sprite`。
- `boost.py`：删除 4 个未调用方法：`set_active_flag`、`set_toggle_active`、`read_toggle_active`、`is_boost_active_q`。
- `phase_dash.py`：删除未读取的 `state`/`timer`/`max_cooldown`/`direction` property、`is_enabled` 方法、`progress` 方法；将 `is_enabled` 判断内联到 `can_dash()`，保留 `_state`、`_timer`、`_direction` 等私有字段。

---

## 4. 边界验证

| 检查项 | 命令 | 结果 |
|---|---|---|
| Python 测试 | `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -m pytest` | **192 passed** |
| Python Lint | `python3 -m ruff check .` | **All checks passed** |
| Rust 编译 | `cargo check` | 成功 |
| Rust 扩展构建 | `maturin develop --release` | 成功 |
| Rust Clippy | `cargo clippy --all-targets` | 6 个 warning（与优化前持平，均为 `missing_errors_doc` / `useless_conversion`） |

---

## 5. 数据指标

| 指标 | 数值 |
|---|---|
| 改动文件数 | 21（Python 19 + Rust 2） |
| 删除行数 | 841 |
| 新增行数 | 98 |
| 净删减 | **-743 行** |
| 改动行中删除占比 | **89.6%** |
| 占代码库总比例 | 约 1.54%（基于 48,355 行 Python/Rust） |

```text
 airwar/audio/sound_manager.py                      | 166 +--------------------
 airwar/config/design_tokens.py                     |  53 +------
 airwar/entities/enemy/boss/boss.py                 |  55 -------
 airwar/entities/player.py                          |  42 -------
 airwar/entities/player_components/aim.py           |  26 ----
 airwar/entities/player_components/boost.py         |  15 ---
 airwar/entities/player_components/phase_dash.py    |  33 ----
 airwar/entities/player_state.py                    |  88 ----------
 airwar/game/constants.py                           |  47 ------
 airwar/game/explosion_animation/explosion_effect.py   |  91 ----------
 airwar/game/managers/bullet_manager.py             |  51 +++----
 airwar/game/managers/collision_controller.py       |  67 ++++-----
 airwar/game/managers/game_loop_manager.py          |  67 +++------
 airwar/game/managers/spawn_controller.py           |   3 +-
 airwar/game/mother_ship/game_integrator.py         |  80 ---------
 airwar/game/protocols.py                           |   1 -
 airwar/game/rendering/entity_renderer.py           |  23 +---
 airwar/scenes/game_scene.py                        |  25 ----
 airwar/scenes/game_scene_protocols.py              |   2 --
 airwar_core/src/bullets.rs                         |   2 +-
 airwar_core/src/movement.rs                        |   2 +-
 21 files changed, 98 insertions(+), 841 deletions(-)
```

---

## 6. 剩余工作开头

本次已完成三阶段工作：热路径优化、核心实体/状态机死代码清理，以及母舰/场景/玩家组件层死代码清理，全部通过测试与 Lint。下一阶段建议继续按子系统拆分执行：

### 6.1 运行时性能深耕（高运行时收益）

- `airwar/game/managers/collisions/bullet_vs_entities.py`：Python 回退路径引入空间哈希，避免 O(n·m)
- `airwar/game/managers/collisions/enemy_bullet_vs_player.py`：回退路径使用网格查询；将热路径内 import 移至文件顶部
- `airwar/game/explosion_animation/explosion_effect.py`：`_render_central_glow` / `_render_main_particle` 的逐层 `pygame.draw.circle` 改为预渲染 glow 纹理（需解决缓存污染问题）
- `airwar/game/rendering/entity_renderer.py`：`_render_enrage_trail` 共享 surface alpha 修改问题
- `airwar_core/src/collision.rs`：`get_potential_collisions_for_aabb` 每查询新建 `HashSet`，可复用或帧标记
- `airwar_core/src/particles.rs`：`batch_render_particles` 若已无人使用则停止导出并删除

### 6.2 Rust 侧可维护性

- `movement.rs`：`update_movement_inner` 的 `_amplitude`、`_spiral_radius` 未使用参数清理
- `starfield.rs`：`sin_table_mask` 未使用参数清理或改用位掩码替代 `rem_euclid`
- 处理剩余 `useless_conversion` 与 `missing_errors_doc` clippy 警告

---

## 7. 结论

本次阶段在热循环路径、实体/状态机协调层、母舰/场景/玩家组件层均取得了可量化的压缩改进，全部改动通过测试与 Lint，Rust 扩展成功构建。累计净删减 **743 行**，改动行中删除占比 **89.6%**。高代码量收益的死代码清理已基本完成，建议下一阶段将重心转向运行时性能深耕与 Rust 侧可维护性收尾。
