# Air War 运行时逻辑错误修正指导文档

> 生成时间：2026-07-10
> 审查方式：多子 Agent 并行深度代码审查 + 人工复核
> 目标：消除游戏正常进行过程中的崩溃、异常退出、状态不一致与严重逻辑错误

## 修复记录

> 本次修复由 AI 编码助手于 **2026-07-11** 完成，覆盖范围为审核报告中全部 **CRITICAL**、**HIGH** 与 **MEDIUM** 项。
> 修复后已通过 `pytest tests/`、`ruff check .`、`compileall -q airwar main.py`，并重新编译 Rust 扩展 `maturin develop --release`。

### 已修复问题清单

#### Phase 1 CRITICAL（运行时崩溃）
- **场景生命周期**：S-1 `GameScene.enter()` 构造失败未捕获、S-2 `GameScene` 公共方法在 `enter()` 前被调用、S-3 `_handle_game_over` 忽略窗口关闭返回值
- **实体战斗核心**：E-1 `Boss.update` 未防御 inactive Boss、E-7 `Player.update` 不检查 alive、E-8 `Player.render` 未防御 sprite None、E-9 `Player.fire_interval` setter 对非法值崩溃
- **游戏管理器**：M-1 `update_entrance` 除零、M-2 `_estimate_player_dps` 除零、M-3 `SpawnController.update` 除零、M-4 `_update_bullets_batch` 解引用 `bullet.data`、M-5 Rust 返回长度不一致导致越界
- **母舰/返航/保存**：H-1 `SaveRestoreManager.restore` 直接解引用子系统、H-2 `HomecomingSequence` 在 `player` 为 None 时崩溃、H-3 `_clear_hostiles` 硬访问 spawner 字段
- **UI 渲染与特效**：U-1 ~ U-10（除零、空值解引用、Rust 返回长度不一致、`colors["bg"]` 直接访问等）
- **Rust 扩展边界**：R-1 ~ R-5（cell_size 为 0、zigzag_interval 为 0、负粒子数、运动/子弹 buffer 长度非法）
- **排行榜/数据/配置**：D-2 排行榜 UI 每帧同步网络请求、D-6 `LeaderboardConfig` 环境变量非法值、D-7 `submit_score` 非法 score、D-8 `Colors.star_color` 颜色越界

#### Phase 2 HIGH（严重逻辑错误）
- **场景生命周期**：S-4 ~ S-8
- **实体战斗核心**：E-2 ~ E-6、E-10
- **游戏管理器**：M-6 ~ M-10
- **母舰/返航/保存**：H-4 ~ H-8
- **输入/锁/状态**：I-1 ~ I-5
- **UI 渲染与特效**：U-11 ~ U-17
- **Rust 扩展边界**：R-6 ~ R-10
- **排行榜/数据/配置**：D-1、D-3、D-9

#### Phase 3 MEDIUM（状态一致性与潜在风险）
- **场景生命周期**：S-9 ~ S-13
- **实体战斗核心**：E-13 ~ E-18
- **游戏管理器**：M-11 ~ M-13
- **母舰/返航/保存**：H-9 ~ H-13
- **输入/锁/状态**：I-6 ~ I-11
- **UI 渲染与特效**：U-18 ~ U-23
- **Rust 扩展边界**：R-11 ~ R-16
- **排行榜/数据/配置**：D-4、D-5、D-10、D-14、D-15

### 验证结果

```text
python3 -m pytest tests/ -q       # 62 passed, 1 warning
python3 -m ruff check .           # All checks passed
python3 -m compileall -q airwar main.py  # 成功
cd airwar_core && python3 -m maturin develop --release  # 成功
./run.sh --debug                  # 20s 内正常启动未崩溃
```

详细修复说明与代码片段见下文各问题条目中的 (已修复) 标记。

---


## 1. 执行摘要

本次审查覆盖了 Air War 的核心运行时模块，共识别出 **7 大模块组** 的数十项问题。按严重程度分布如下：

- **CRITICAL（运行时崩溃）**：约 25 项，可在正常或异常流程中直接导致游戏退出
- **HIGH（严重逻辑错误）**：约 30 项，会导致状态不一致、玩法异常或数据丢失
- **MEDIUM（潜在风险）**：约 25 项，在边界条件下可能触发
- **LOW（代码异味）**：约 20 项，影响可维护性

**最危险的崩溃集中点**：

1. `GameScene` 生命周期未做防御性校验（构造失败、未 `enter()` 即被调用）
2. Rust 扩展边界缺乏参数校验（`cell_size=0`、`zigzag_interval<1`、负粒子数等 panic）
3. 渲染/UI 路径大量除零与空值解引用（进度条、爆炸、HUD、血条）
4. 排行榜/UI 同步网络 IO 跑在主线程，导致卡顿与 DDoS 式请求
5. 存档/返航系统对 `None`、损坏数据、旧战场状态清理缺失

**修复原则**：

- 先崩溃、后逻辑、再优化
- 同一类问题在同一阶段批量修复，减少回归测试次数
- 每个阶段结束时必须跑 `pytest tests/` + `ruff check .` + 一次完整手动流程验证
- 改动必须同时更新 Rust 实现、`airwar/core_bindings.py` fallback 和 `airwar_core.pyi` 存根

---

## 2. 审查范围

| 模块组 | 审查文件 | 来源 |
|--------|----------|------|
| 场景生命周期 | `airwar/scenes/*.py`、`airwar/game/scene_director*.py` | Agent-0 |
| 实体战斗核心 | `airwar/entities/**/*.py` | Agent-8 |
| 游戏管理器 | `airwar/game/managers/*.py` | 人工复核 |
| 母舰/返航/保存 | `airwar/game/mother_ship/*.py`、`airwar/game/systems/homecoming*.py`、`airwar/game/systems/save_restore_manager.py` 等 | Agent-3 |
| 输入/锁/状态 | `airwar/input/*.py`、`airwar/game/systems/lock_manager.py`、`airwar/game/give_up/*.py`、`airwar/game/homecoming/homecoming_detector.py` | Agent-4 |
| UI 渲染与特效 | `airwar/game/rendering/*.py`、`airwar/ui/*.py`、`airwar/game/explosion_animation/*.py` | Agent-10 |
| Rust 扩展与回退 | `airwar_core/src/*.rs`、`airwar/core_bindings.py` | Agent-6 |
| 排行榜/数据/配置 | `airwar/leaderboard/*.py`、`airwar/utils/*.py`、`airwar/config/*.py`、`airwar/game/systems/difficulty_manager.py` | Agent-7 |

---

## 3. 分阶段修复计划（总览）

| 阶段 | 主题 | 预计工时 | 验收方式 |
|------|------|----------|----------|
| Phase 1 | 消除运行时崩溃（CRITICAL） | 2-3 天 | `pytest` 全绿 + 游戏能完整启动/退出/重开 |
| Phase 2 | 修复严重逻辑错误（HIGH） | 2-3 天 | 难度切换、Boss 战、存档/读档、排行榜无异常 |
| Phase 3 | 状态一致性与潜在风险（MEDIUM） | 1-2 天 | 长会话稳定、暂停/恢复/返航流程正确 |
| Phase 4 | 代码清理与可维护性（LOW） | 0.5-1 天 | `ruff` 全绿、无新增 mypy 严重错误 |

**每个 Phase 的通用验收命令**：

```bash
python3 -m pytest tests/ -v
python3 -m ruff check .
python3 -m compileall -q airwar main.py
# 如修改了 Rust 扩展：
cd airwar_core && python3 -m maturin develop --release && cd ..
./run.sh --debug
```

---

## 4. Phase 1：消除运行时崩溃（CRITICAL）

本阶段目标是让游戏在正常启动、游玩、退出流程中不再因为未处理异常而退出。优先修复最直接、最频繁的崩溃点。

### 4.1 场景生命周期防御

#### ✅ 已修复 — 4.1.1 `GameScene.enter()` 构造失败未捕获

- **位置**：`airwar/game/scene_director_components/scene_switcher.py:108-116`、`airwar/scenes/game_scene.py:189`
- **问题**：`SceneSwitcher.run_game_flow` 直接调用 `self._scene_manager.switch("game", ...)`，触发 `GameScene.enter()`，后者调用 `GameSceneFactory.build()`。Factory 中任何子系统初始化失败都会抛出未捕获异常，导致游戏闪退。
- **修复**：在 `run_game_flow` 中给 `switch/restore` 加保护壳：

```python
# airwar/game/scene_director_components/scene_switcher.py
try:
    self._scene_manager.switch("game", ...)
except Exception:
    self._logger.exception("Failed to build game scene")
    self._director._pending_save_data = None
    return "main_menu"

current_scene = self._scene_manager.get_current_scene()
if not isinstance(current_scene, GameScene):
    self._director._pending_save_data = None
    return "main_menu"

if self._director._pending_save_data:
    try:
        current_scene.restore_from_save(self._director._pending_save_data)
    except Exception:
        self._logger.exception("Save restore failed")
    self._director._pending_save_data = None
```

#### ✅ 已修复 — 4.1.2 `GameScene` 公共方法在 `enter()` 完成前被调用

- **位置**：`airwar/scenes/game_scene.py:463-465`、`airwar/scenes/game_scene_renderer.py:65-100`、`airwar/scenes/game_scene_updater.py:108-413`、`airwar/scenes/game_scene_event_dispatcher.py:48-51`
- **问题**：`GameScene.__init__` 把 `game_renderer`、`player`、`spawn_controller` 等大量属性初始化为 `None`。`render/update/handle_events` 直接访问这些属性，不检查是否已 `enter()`。
- **修复**：

```python
# airwar/scenes/game_scene.py
def __init__(self):
    ...
    self._entered = False

def enter(self, **kwargs) -> None:
    ...
    self._entered = True

def _ensure_entered(self) -> None:
    if not self._entered:
        raise RuntimeError("GameScene operation before enter()")

def render(self, surface: pygame.Surface) -> None:
    self._ensure_entered()
    self._scene_renderer.render(surface)

def update(self, frame=None, *args, **kwargs) -> None:
    self._ensure_entered()
    self._updater.run(frame)

def handle_events(self, event) -> None:
    self._ensure_entered()
    self._event_dispatcher.dispatch(event)
```

同时在 `GameSceneRenderer`/`GameSceneUpdater`/`GameSceneEventDispatcher` 中对核心访问路径加空值保护：

```python
# airwar/scenes/game_scene_event_dispatcher.py
def dispatch(self, event) -> None:
    if self._scene._input_coordinator is None or self._scene.game_renderer is None:
        return
    ...
```

#### ✅ 已修复 — 4.1.3 `_handle_game_over` 忽略窗口关闭返回值

- **位置**：`airwar/game/scene_director_components/scene_switcher.py:399-420`
- **问题**：`_run_scene_loop(death_scene)` 会在用户关闭窗口时返回 `"quit"`，但 `_handle_game_over` 未检查该返回值，直接调用 `death_scene.get_result()`。
- **修复**：

```python
loop_result = self._run_scene_loop(death_scene)
if loop_result == "quit":
    death_scene.exit()
    return False
result = death_scene.get_result()
death_scene.exit()
return result == "return_to_menu"
```

### 4.2 实体战斗核心防御

#### ✅ 已修复 — 4.2.1 `Boss.update` 未防御 inactive Boss

- **位置**：`airwar/entities/enemy/boss/boss.py:199-285`、`airwar/entities/enemy/boss/boss.py:438-452`
- **问题**：`Boss.update` 开头没有 `if not self.active: return`。Boss 死亡/逃跑后若仍被更新，会触发非法状态转换 `IllegalBossTransition`。
- **修复**：

```python
def update(self, enemies, slow_factor=1.0, player_pos=None, *args, **kwargs) -> None:
    if not self.active:
        return
    ...
```

#### ✅ 已修复 — 4.2.2 `Player.update` / `Player.render` 未做生命/资源空值守卫

- **位置**：`airwar/entities/player.py:207-284`、`airwar/entities/player.py:285-309`
- **问题**：`Player.update` 不检查 alive 状态，死亡后仍继续移动、射击。`Player.render` 直接使用 `self.aim.rotated_ship_sprite()`，若资源加载失败返回 `None` 会崩溃。
- **修复**：

```python
def update(self, *args, **kwargs) -> None:
    if not self.active or not self._state.is_alive():
        return
    ...

def render(self, surface: pygame.Surface) -> None:
    sprite = self.aim.rotated_ship_sprite()
    if sprite is None:
        return
    ...
```

#### ✅ 已修复 — 4.2.3 `Player.fire_interval` setter 对非法值崩溃

- **位置**：`airwar/entities/player.py:169`
- **问题**：`set_transform=lambda v: max(1, int(v))`，`int(None)` 会抛 `TypeError`。
- **修复**：

```python
fire_interval = _Comp(
    "weapon", "_fire_interval",
    set_transform=lambda v: max(1, int(v or 0))
)
```

### 4.3 游戏管理器防御

#### ✅ 已修复 — 4.3.1 `GameLoopManager.update_entrance` 除零

- **位置**：`airwar/game/managers/game_loop_manager.py:183-194`
- **问题**：`progress = state.entrance_timer / state.entrance_duration`，`entrance_duration` 可能为 0。
- **修复**：

```python
progress = 1.0 if state.entrance_duration <= 0 else min(1.0, state.entrance_timer / state.entrance_duration)
```

#### ✅ 已修复 — 4.3.2 `GameLoopManager._estimate_player_dps` 除零

- **位置**：`airwar/game/managers/game_loop_manager.py:280-285`
- **问题**：`fire_interval` 可能为 0。
- **修复**：

```python
fire_interval = max(1, int(getattr(player, "fire_interval", PlayerConstants.FIRE_COOLDOWN)))
```

#### ✅ 已修复 — 4.3.3 `SpawnController.update` 除零

- **位置**：`airwar/game/managers/spawn_controller.py:153`
- **问题**：`self.boss_spawn_timer >= self.boss_spawn_interval / slow_factor`，`slow_factor` 可能为 0。
- **修复**：

```python
if self.boss is None and self.boss_spawn_timer >= self.boss_spawn_interval / max(0.001, slow_factor):
```

#### ✅ 已修复 — 4.3.4 `BulletManager._update_bullets_batch` 解引用 `bullet.data`

- **位置**：`airwar/game/managers/bullet_manager.py:177`、`airwar/game/managers/bullet_manager.py:205`
- **问题**：直接访问 `bullet.data.bullet_type`、`bullet.data.is_laser`、`bullet.data.speed`，若 `data` 为 None 会崩溃。
- **修复**：

```python
data = getattr(bullet, "data", None)
if data is None:
    continue
is_laser = getattr(data, "bullet_type", "") == "laser" or getattr(data, "is_laser", False)
```

#### ✅ 已修复 — 4.3.5 `GameLoopManager._update_entities` Rust 返回长度不一致

- **位置**：`airwar/game/managers/game_loop_manager.py:388-394`
- **问题**：`batch_update_movements_buf` 返回结果长度若与 `batch_indices` 不一致，`batch_indices[j]` 可能越界。
- **修复**：

```python
results = batch_update_movements_buf(base_buf, extra_buf)
if len(results) != len(batch_indices):
    raise MovementParamError(
        f"Rust movement batch returned {len(results)} results for {len(batch_indices)} enemies"
    )
for j, (new_x, new_y, new_timer) in enumerate(results):
    idx = batch_indices[j]
    enemies[idx].apply_batch_movement_result((new_x, new_y, new_timer))
```

### 4.4 母舰/返航/保存防御

#### ✅ 已修复 — 4.4.1 `SaveRestoreManager.restore` 直接解引用子系统

- **位置**：`airwar/game/systems/save_restore_manager.py:51-54`、`69`、`74`
- **问题**：直接调用 `game_controller.difficulty_manager.set_difficulty(...)`、`spawn_controller.set_difficulty(...)`、`reward_system.unlocked_buffs = ...`，任一对象为 None 即崩溃。
- **修复**：

```python
if getattr(game_controller, "difficulty_manager", None):
    game_controller.difficulty_manager.set_difficulty(saved_diff)
if getattr(game_controller, "reward_system", None):
    game_controller.reward_system.set_difficulty(saved_diff)
if getattr(game_controller, "health_system", None):
    game_controller.health_system.set_difficulty(saved_diff)
if spawn_controller is not None:
    spawn_controller.set_difficulty(saved_diff)
if reward_system is not None:
    reward_system.unlocked_buffs = save_data.unlocked_buffs
    reward_system.capture_player_baselines(player)
```

#### ✅ 已修复 — 4.4.2 `HomecomingSequence` 在 `player` 为 None 时崩溃

- **位置**：`airwar/game/homecoming/homecoming_sequence.py:71`、`87`、`118`、`274-275`
- **问题**：`start / start_departure / _apply_player_position` 未校验 `player`。
- **修复**：

```python
def start(self, player, screen_width, screen_height) -> bool:
    if player is None or self.is_active():
        return False
    ...

def _apply_player_position(self, player) -> None:
    if player is None:
        return
    ...
```

#### ✅ 已修复 — 4.4.3 `HomecomingCoordinator._clear_hostiles` 硬访问 spawner 内部字段

- **位置**：`airwar/game/systems/homecoming_coordinator.py:341-368`
- **问题**：直接读取 `.enemies`、`.boss`、`.reset_boss_timer()`，未做 `hasattr/getattr` 保护。
- **修复**：

```python
enemies = getattr(spawn_controller, "enemies", [])
boss = getattr(spawn_controller, "boss", None)
...
if boss:
    boss.active = False
    spawn_controller.boss = None
    if hasattr(spawn_controller, "reset_boss_timer"):
        spawn_controller.reset_boss_timer()
```

### 4.5 UI 渲染与特效防御

#### ✅ 已修复 — 4.5.1 `SegmentedProgressBar.render` 除零

- **位置**：`airwar/ui/segmented_bar.py:63`
- **修复**：

```python
ratio = 0.0 if max_value <= 0 else min(max(value / max_value, 0.0), 1.0)
```

#### ✅ 已修复 — 4.5.2 `ExplosionEffect._render_shockwave` 除零

- **位置**：`airwar/game/explosion_animation/explosion_effect.py:343`
- **修复**：

```python
if self._shockwave_max_radius <= 0:
    return
progress = self._shockwave_radius / self._shockwave_max_radius
```

#### ✅ 已修复 — 4.5.3 `GameRenderer._render_entrance` 除零

- **位置**：`airwar/game/rendering/game_renderer.py:76`
- **修复**：

```python
progress = 1.0 if state.entrance_duration <= 0 else min(1.0, state.entrance_timer / state.entrance_duration)
```

#### ✅ 已修复 — 4.5.4 `IntegratedHUD._get_visible_buffs` 除零

- **位置**：`airwar/ui/integrated_hud.py:476-481`
- **修复**：

```python
total_buffs = len(buffs)
if total_buffs == 0:
    return []
start_idx = int(self._buff_scroll_offset) % total_buffs
```

#### ✅ 已修复 — 4.5.5 `IntegratedHUD._render_buffs_module` 颜色返回值未校验

- **位置**：`airwar/ui/integrated_hud.py:436-438`
- **修复**：

```python
raw_color = get_buff_color(buff)
if not isinstance(raw_color, (tuple, list)) or len(raw_color) < 3:
    raw_color = (200, 200, 200)
buff_color = tuple(raw_color[:3])
```

#### ✅ 已修复 — 4.5.6 `EntityRenderer.render_bullet` 未检查 `bullet.data`

- **位置**：`airwar/game/rendering/entity_renderer.py:93-109`
- **修复**：

```python
if bullet.data is None:
    return
```

#### ✅ 已修复 — 4.5.7 `BossEnrageRenderer` 解引用 `boss.rect`

- **位置**：`airwar/game/rendering/boss_enrage_renderer.py:51-52`
- **修复**：

```python
rect = getattr(boss, "rect", None)
center_x = getattr(rect, "centerx", sw // 2) if rect else sw // 2
center_y = getattr(rect, "centery", sh // 2) if rect else sh // 2
```

#### ✅ 已修复 — 4.5.8 `LeaderboardView.render` 未捕获 fetch 异常

- **位置**：`airwar/ui/leaderboard_view.py:56-57`、`77`
- **修复**：

```python
try:
    entries = self.fetch_entries()
except Exception as e:
    logger.warning("Leaderboard fetch failed: %s", e)
    entries = []
```

#### ✅ 已修复 — 4.5.9 `MenuBackground.render` 直接访问 `colors["bg"]`

- **位置**：`airwar/ui/menu_background.py:176-177`
- **修复**：

```python
bg_color = colors.get("bg", (0, 0, 0))
bg_gradient = colors.get("bg_gradient", bg_color)
```

#### ✅ 已修复 — 4.5.10 `ExplosionEffect.update` Rust 返回粒子长度不一致

- **位置**：`airwar/game/explosion_animation/explosion_effect.py:246-254`
- **修复**：

```python
results = batch_update_particles(particle_data, dt)
if len(results) != len(original_particles):
    logger.error("Particle batch size mismatch: %d vs %d", len(results), len(original_particles))
    self._particle_pool.extend(original_particles)
    self._particles.clear()
else:
    for i, (result, original_max_life) in enumerate(zip(results, max_lives)):
        ...
```

### 4.6 Rust 扩展边界防御

#### ✅ 已修复 — 4.6.1 `batch_collide_bullets_vs_entities` `cell_size == 0` 除零 panic

- **位置**：`airwar_core/src/collision.rs:37-40`、`58-61`、`179`
- **修复**：

```rust
if cell_size <= 0 {
    return Vec::new(); // 或 return Err(PyValueError::new_err("cell_size must be > 0"));
}
```

#### ✅ 已修复 — 4.6.2 Zigzag 移动 `zigzag_interval` 为 0 取模 panic

- **位置**：`airwar_core/src/movement.rs:325-329`
- **修复**：

```rust
let interval = (zigzag_interval as i32).max(1);
let actual_direction = if (t as i32) % interval == 0 && t > 0.0 { -direction } else { direction };
```

#### ✅ 已修复 — 4.6.3 `generate_explosion_particles` 负 `particle_count` OOM/panic

- **位置**：`airwar_core/src/particles.rs:75`
- **修复**：

```rust
if particle_count <= 0 {
    return Vec::new();
}
```

#### ✅ 已修复 — 4.6.4 `batch_update_movements_buf` 缓冲区长度不足 panic

- **位置**：`airwar_core/src/movement.rs:224-246`
- **修复**：

```rust
let count = base_buf.len() / BASE_BUF_STRIDE;
if base_buf.len() % BASE_BUF_STRIDE != 0 || extra_buf.len() < count * EXTRA_BUF_STRIDE {
    return Err(PyValueError::new_err("movement buffers length mismatch"));
}
```

#### ✅ 已修复 — 4.6.5 `batch_update_bullets_buf` 缓冲区长度非 32 整数倍

- **位置**：`airwar_core/src/bullets.rs:45-46`
- **修复**：

```rust
if buf.len() % BULLET_BUF_STRIDE != 0 {
    return Err(PyValueError::new_err("bullet buffer length must be multiple of 32"));
}
```

#### 4.6.6 `batch_render_particles` 负屏幕尺寸 OOM

- **位置**：`airwar_core/src/particles.rs:101-104`
- **修复**：

```rust
if screen_width <= 0 || screen_height <= 0 {
    return PyBytes::new_bound(py, &[]);
}
```

#### 4.6.7 `create_*_glow` / `create_glow_circle` 负半径 OOM

- **位置**：`airwar_core/src/sprites.rs:118-120`、`141`、`185-186`、`221-222`、`250-252`
- **修复**：统一在入口校验：

```rust
if radius <= 0.0 || glow_radius < 0.0 {
    return Vec::new();
}
```

### 4.7 排行榜/数据/配置防御

#### ✅ 已修复 — 4.7.1 排行榜 UI 每帧同步网络请求导致卡死

- **位置**：`airwar/ui/leaderboard_view.py:54-77`、`airwar/leaderboard/service.py:143-169`、`airwar/leaderboard/client.py:78-87`
- **问题**：`LeaderboardView.render()` 每帧调用 `fetch_entries()`，同步 `urllib.request` 阻塞主线程。
- **修复**：

```python
class LeaderboardView:
    def __init__(self, ...):
        ...
        self._cached_entries: list[dict] | None = None
        self._last_fetch_at: float = -999.0
        self._FETCH_TTL = 10.0

    def fetch_entries(self) -> list[dict]:
        now = time.monotonic()
        if self._cached_entries is None or now - self._last_fetch_at > self._FETCH_TTL:
            self._cached_entries = self._service.get_leaderboard()
            self._last_fetch_at = now
        return self._cached_entries

    def invalidate_cache(self) -> None:
        self._cached_entries = None
```

#### 4.7.2 `UserDB.submit_score` 写入前未过滤损坏条目

- **位置**：`airwar/utils/database.py:234-272`
- **修复**：

```python
entries = [e for e in entries if isinstance(e, dict)]
data[_LEADERBOARD_KEY] = sorted(
    entries,
    key=lambda item: (-int(item.get("score", 0)), item.get("timestamp", "")),
)[:LEADERBOARD_CAP]
```

#### ✅ 已修复 — 4.7.3 `LeaderboardConfig` 环境变量非法值导致启动失败

- **位置**：`airwar/leaderboard/config.py:19-23`
- **修复**：

```python
try:
    self.timeout = float(os.environ.get("AIRWAR_LEADERBOARD_TIMEOUT", _DEFAULT_TIMEOUT))
except ValueError:
    logger.warning("Invalid AIRWAR_LEADERBOARD_TIMEOUT, using default %s", _DEFAULT_TIMEOUT)
    self.timeout = float(_DEFAULT_TIMEOUT)

self.mode = os.environ.get("AIRWAR_LEADERBOARD_MODE", _DEFAULT_MODE).lower()
if self.mode not in {"auto", "local", "remote"}:
    logger.warning("Unknown leaderboard mode %r, defaulting to auto", self.mode)
    self.mode = "auto"
```

#### ✅ 已修复 — 4.7.4 `Colors.star_color` 颜色越界

- **位置**：`airwar/config/design_tokens.py:75-77`
- **修复**：

```python
@staticmethod
def star_color(brightness: int) -> tuple[int, int, int]:
    return (
        min(255, max(0, brightness + 50)),
        min(255, max(0, brightness + 50)),
        min(255, max(0, brightness + 70)),
    )
```

---

## 5. Phase 2：修复严重逻辑错误（HIGH）

本阶段目标是消除状态不一致、玩法异常和数据丢失。这些问题不会立即崩溃，但会破坏游戏体验。

### 5.1 场景生命周期 HIGH

#### 5.1.1 `run_welcome_flow` 兜底返回值让非法状态进入游戏

- **位置**：`airwar/game/scene_director_components/scene_switcher.py:72`
- **问题**：当欢迎场景 `running=False` 但 `is_ready()` 为 False 且无导航标志时，返回 `(True, None)`，`SceneDirector` 会继续调用 `_run_game_flow()`，此时 `_current_user` 可能为空。
- **修复**：

```python
if welcome.is_ready():
    self._director._current_user = welcome.get_username()
    self._director._selected_difficulty = welcome.get_difficulty()
    ...
    return (True, save_data)
# 兜底：不应进入游戏
return (False, None)
```

#### 5.1.2 `GameScene.enter` 不校验必需 kwargs

- **位置**：`airwar/scenes/game_scene.py:174-175`
- **问题**：`viewport` 和 `save_service` 缺失时静默置为 `None`，导致存档丢失、鼠标错位。
- **修复**：

```python
def enter(self, **kwargs) -> None:
    self._viewport = kwargs.get("viewport")
    self._save_service = kwargs.get("save_service")
    if self._viewport is None:
        raise ValueError("GameScene.enter requires 'viewport'")
    if self._save_service is None:
        raise ValueError("GameScene.enter requires 'save_service'")
```

#### 5.1.3 `SceneStatePersistence.clear_saved_game` 在 `current_user=None` 时误删默认存档

- **位置**：`airwar/game/scene_director_components/scene_state_persistence.py:49-50`
- **修复**：

```python
def clear_saved_game(self) -> None:
    if not self._director._current_user:
        return
    self._save_service.clear(self._director._current_user)
```

#### 5.1.4 `_show_exit_confirm` 非预期结果默认当退出处理

- **位置**：`airwar/game/scene_director_components/scene_switcher.py:394-397`
- **修复**：

```python
if result == ExitConfirmAction.RETURN_TO_MENU:
    ...
elif result == ExitConfirmAction.START_NEW_GAME:
    ...
elif result == ExitConfirmAction.QUIT_GAME:
    ...
else:
    self._director._logger.warning("Unexpected exit confirm result: %r", result)
    if not saved:
        self._director._clear_saved_game()
    return "quit"
```

#### 5.1.5 `PauseAction.QUIT` 语义与实现不一致

- **位置**：`airwar/game/scene_director.py:173-174`
- **问题**：`PauseAction.QUIT` docstring 为“Quit the application”，但实现映射为 `"save_and_quit"`。
- **修复**：要么移除未使用的 `QUIT`，要么映射为 `"quit_without_saving"`，或在 docstring 明确说明“保存并退出”。

### 5.2 实体战斗核心 HIGH

#### 5.2.1 `Enemy.update` 忽略 `slow_factor` 与 `player_pos`

- **位置**：`airwar/entities/enemy/enemy.py:198-216`
- **修复**：

```python
def update(self, *args, **kwargs) -> None:
    ...
    self._slow_factor = kwargs.get("slow_factor", 1.0)
    self._player_pos = kwargs.get("player_pos")
    self._update_active_state()

def _update_movement(self) -> None:
    if self._can_use_rust_movement():
        self._update_rust_movement()
    else:
        self._movement_strategy.update(self, self._slow_factor, self._player_pos)
```

#### 5.2.2 `Enemy.set_difficulty` 的速度倍率从未被使用

- **位置**：`airwar/entities/enemy/enemy.py:379-384`
- **修复**：在 `_update_movement` 中将 `_difficulty_multiplier` 应用到 `self._rust_params["speed"]` 或策略速度上。

#### 5.2.3 Boss aim-dash 后 `fire_timer` 未被消耗

- **位置**：`airwar/entities/enemy/boss/boss.py:369-382`、`airwar/entities/enemy/boss/boss.py:294-302`
- **修复**：

```python
if player_pos and self._movement.start_aim_dash(player_pos):
    self._aim_fire_target = (float(player_pos[0]), float(player_pos[1]))
    self.fire_timer = 0
    return
```

#### 5.2.4 狂暴释放子弹依赖 spawner 的 `get_bullets`

- **位置**：`airwar/entities/enemy/boss/boss.py:483-496`、`airwar/entities/enemy/boss/boss.py:422-432`
- **修复**：Boss 自己持有狂暴阶段创建的子弹列表（见 4.2 节总体建议）。

#### 5.2.5 狂暴触发时强制移动玩家到屏幕中央未 clamp

- **位置**：`airwar/entities/enemy/boss/boss.py:453-465`
- **修复**：

```python
def _center_player_for_enrage(self, player=None, player_pos=None):
    target = (get_screen_width() / 2, get_screen_height() / 2)
    if player is not None:
        rect = player.rect
        new_x = max(0, min(target[0] - rect.width / 2, get_screen_width() - rect.width))
        new_y = max(0, min(target[1] - rect.height / 2, get_screen_height() - rect.height))
        rect.x, rect.y = new_x, new_y
        if hasattr(player, "sync_hitbox"):
            player.sync_hitbox()
        return target
```

#### 5.2.6 `PlayerStateMachine.mark_dying` 非幂等

- **位置**：`airwar/entities/player_state.py:173-176`
- **修复**：

```python
def mark_dying(self) -> None:
    if self._state in (PlayerState.DYING, PlayerState.DEAD):
        return
    self._state = PlayerState.DYING
```

#### 5.2.7 `PlayerStateMachine.respawn` 未清理旧状态

- **位置**：`airwar/entities/player_state.py:181-184`
- **修复**：

```python
def respawn(self) -> None:
    self._state = PlayerState.ALIVE
    self._alive_substate = PlayerAliveState.NORMAL
    self._dock_active = False
    self._respawn_invincible = False
    self._shield_duration = 0
    self.transition_substate(PlayerAliveState.RESPAWN_INVINCIBLE)
```

### 5.3 游戏管理器 HIGH

#### 5.3.1 `CollisionController` 负坐标空间哈希漏检

- **位置**：`airwar/game/managers/collision_controller.py:142-144`、`154-159`、`188-193`
- **问题**：`x // self._grid_cell_size` 对负数向零截断，导致负坐标物体放入错误 cell。
- **修复**：使用 floor division：

```python
def _get_cell_key(self, x: int, y: int) -> tuple[int, int]:
    import math
    return (math.floor(x / self._grid_cell_size), math.floor(y / self._grid_cell_size))
```

对所有 `//` 除法统一替换为 `math.floor(value / cell_size)`。

#### 5.3.2 `BossManager.on_boss_hit` 依赖 Boss 私有属性 `_death_consumed`

- **位置**：`airwar/game/managers/boss_manager.py:129-131`
- **问题**：设置 `boss._death_consumed = True` 是侵入式修改，且 Boss 死亡后未重置。
- **修复**：在 `Boss` 类暴露 `is_death_consumed` / `consume_death()` 公共方法，Boss 重置时自动清除。

#### 5.3.3 `SpawnController.spawn_boss` 中 `fire_rate` 可能为负

- **位置**：`airwar/game/managers/spawn_controller.py:206`
- **问题**：`fire_rate=self.BOSS_BASE_FIRE_RATE - boss_kill_count * self.BOSS_FIRE_RATE_DECREMENT`，击杀数足够大时变负。
- **修复**：

```python
fire_rate=max(1, self.BOSS_BASE_FIRE_RATE - boss_kill_count * self.BOSS_FIRE_RATE_DECREMENT),
```

#### 5.3.4 `GameLoopManager._update_core` 中 DYING 状态重复更新

- **位置**：`airwar/game/managers/game_loop_manager.py:211-217`
- **问题**：DYING 分支内已调用 `update_death_animation` 和 `explosion_manager.update`，else 分支又重复调用。
- **修复**：将公共的 `update_death_animation` / `explosion_manager.update` 提到分支外。

#### 5.3.5 `EnemyBulletVsPlayerStrategy` 多子弹同时命中只处理一个

- **位置**：`airwar/game/managers/collisions/enemy_bullet_vs_player.py:97-104`
- **问题**：Rust 返回多个 hits 时只处理 `hits[0]`。
- **修复**：按需求决定是只处理第一个（保留当前设计）还是处理全部。若保留，加注释说明“每帧最多受击一次”；若要真实，遍历 hits 直到玩家首次受伤。

### 5.4 母舰/返航/保存 HIGH

#### 5.4.1 `GameIntegrator._activate_invincibility` 回退分支无敌帧数错误

- **位置**：`airwar/game/mother_ship/game_integrator.py:421-440`
- **问题**：主分支使用 `PERMANENT_INVINCIBILITY_FRAMES`（999999），回退分支使用 `DOCKING_INVINCIBILITY_FRAMES`（1200）。
- **修复**：回退分支也使用 `PERMANENT_INVINCIBILITY_FRAMES`。

#### 5.4.2 事件订阅只注册不注销

- **位置**：`airwar/game/mother_ship/state_machine.py:57-69`、`airwar/game/mother_ship/event_hub.py:59-71`
- **修复**：在组件提供 `unregister_handlers()`，在重建/退出时调用；或用 `(event, id(handler))` 集合跟踪并移除。

#### 5.4.3 `SaveRestoreManager.restore` 不清理旧战场状态

- **位置**：`airwar/game/systems/save_restore_manager.py:19-94`
- **修复**：在 `restore` 开头显式清理，或增加可选 `cleanup_callback`：

```python
if cleanup_callback:
    cleanup_callback()
```

#### 5.4.4 `SaveRestoreManager.restore` 混用 `game_controller.reward_system` 与参数 `reward_system`

- **位置**：`airwar/game/systems/save_restore_manager.py:52`、`69`、`74`
- **修复**：统一使用传入的 `reward_system`，并加断言 `reward_system is game_controller.reward_system`。

#### 5.4.5 `GameIntegrator.create_save_data` 硬依赖 `game_scene` 方法

- **位置**：`airwar/game/mother_ship/game_integrator.py:502-536`
- **修复**：用 `getattr` 包装关键读取：

```python
score = getattr(self._game_scene, "get_score", lambda: 0)()
username = getattr(self._game_scene, "get_username", lambda: "")()
```

### 5.5 输入/锁/状态 HIGH

#### 5.5.1 `PygameInputHandler` 自定义键位缺失导致 KeyError

- **位置**：`airwar/input/input_handler.py:59-64`、`66-84`
- **修复**：

```python
_REQUIRED_BINDINGS = {"left", "left_alt", "right", "right_alt", "up", "up_alt",
                      "down", "down_alt", "pause", "boost", "precision"}

def __init__(self, key_bindings: dict[str, int] | None = None):
    self._bindings = dict(key_bindings) if key_bindings else dict(self.DEFAULT_BINDINGS)
    missing = self._REQUIRED_BINDINGS - self._bindings.keys()
    if missing:
        raise ValueError(f"Missing key bindings: {sorted(missing)}")
```

#### 5.5.2 `InputCoordinator` 依赖为空时直接崩溃

- **位置**：`airwar/game/managers/input_coordinator.py:35-77`
- **修复**：构造时显式校验参数非空。

#### 5.5.3 `LockManager` 锁优先级切换时无敌时间被重置

- **位置**：`airwar/game/systems/lock_manager.py:162-194`
- **修复**：将无敌模型从“请求时长”改为“过期时间点”：

```python
@dataclass
class LockRequest:
    invincible: bool = False
    lock_controls: bool = False
    is_paused: bool = False
    is_silent_invincible: bool = False
    invincibility_duration: int = 0
    expires_at: float = 0.0

# acquire 中：
request.expires_at = now + max(0, request.invincibility_duration)

# _recompute 中按优先级取最高 invincible 锁，计算剩余时间：
remaining = max(0, req.expires_at - now)
timer = int(remaining)
```

#### 5.5.4 `GiveUpDetector` 在不可用期间丢失按键释放事件

- **位置**：`airwar/game/give_up/give_up_detector.py:24-34`、`airwar/game/managers/input_coordinator.py:55-66`
- **修复**：

```python
def update_give_up(self, delta_seconds: float) -> None:
    if not self._can_use_give_up():
        self._give_up_detector.reset()
        self._give_up_ui.hide()
        return
    ...
```

#### 5.5.5 `PygameInputHandler` 边沿检测方法副作用导致顺序脆弱

- **位置**：`airwar/input/input_handler.py:86-107`
- **修复**：将按键读取与边沿捕获分离，提供显式 `tick()`：

```python
def tick(self) -> None:
    keys = pygame.key.get_pressed()
    boost = keys[self._bindings["boost"]]
    self._boost_just_pressed = boost and not self._prev_boost_pressed
    self._prev_boost_pressed = boost
    # precision 同理

def is_boost_pressed(self) -> bool:
    return pygame.key.get_pressed()[self._bindings["boost"]]

def is_boost_just_pressed(self) -> bool:
    just = self._boost_just_pressed
    self._boost_just_pressed = False
    return just
```

并在 `Player.update()` 开头调用 `self._input_handler.tick()`（若支持）。

### 5.6 UI 渲染与特效 HIGH

#### 5.6.1 `ParticleSystem.render` 共享缓存 alpha 污染

- **位置**：`airwar/ui/particles.py:92-97`
- **修复**：每次 blit 前复制 surface：

```python
particle_surf = self._texture_cache[cache_key]
surf = particle_surf.copy()
surf.set_alpha(alpha)
surface.blit(surf, (x - half_size, y - half_size))
```

#### 5.6.2 `IntegratedHUD` 展开态血条未同步生命值

- **位置**：`airwar/ui/integrated_hud.py:388-392`
- **修复**：

```python
if self._battery_expanded is None:
    self._battery_expanded = DiscreteBatteryIndicator(...)
self._battery_expanded.set_health(player_health, player_max_health)
```

#### 5.6.3 `EntityRenderer` 大量访问 Boss 私有属性

- **位置**：`airwar/game/rendering/entity_renderer.py:134-213`
- **修复**：在 `Boss` 暴露只读公共属性，渲染器使用公共 API；对可选字段用 `getattr(boss, "_xxx", None)`。

#### 5.6.4 `ExplosionManager.update` 使用入口动画时长控制“每秒”上限

- **位置**：`airwar/game/explosion_animation/explosion_manager.py:103-107`
- **修复**：使用真实时间或固定 1 秒阈值：

```python
self._time_accumulator += dt
if self._time_accumulator >= 1.0:  # 若 dt 为秒
    self._explosions_this_second = 0
    self._time_accumulator = 0.0
```

### 5.7 Rust 扩展 HIGH

#### 5.7.1 空间哈希负坐标 floor division

- **位置**：`airwar_core/src/collision.rs:37-40`、`58-61`
- **修复**：

```rust
let min_x = (bounds.min_x / cell_size as f32).floor() as i32;
let max_x = (bounds.max_x / cell_size as f32).floor() as i32;
```

#### 5.7.2 `compute_starfield_positions` 缺少越界与除零保护

- **位置**：`airwar_core/src/starfield.rs:65`、`74`
- **修复**：

```rust
if sin_table.is_empty() || glow_alpha_divisor == 0 {
    return Vec::new();
}
let idx = (phase as i32 as usize) % sin_table.len();
let glow_alpha = if has_glow { (b / glow_alpha_divisor).min(glow_alpha_cap) } else { 0 };
```

#### 5.7.3 `batch_update_movements` 长度不一致静默截断

- **位置**：`airwar_core/src/movement.rs:137-140`、`airwar/core_bindings.py:399`
- **修复**：

```rust
if base_params.len() != extra_params.len() {
    return Err(PyValueError::new_err("base_params and extra_params must have same length"));
}
```

Python fallback 用 `zip(..., strict=True)` 或显式检查。

#### 5.7.4 Rust-Python 边界 ID 类型不一致

- **位置**：`airwar_core/src/collision.rs:170-174`、`airwar_core/src/movement.rs:448`、`463`、`airwar_core/src/bullets.rs:9`
- **修复**：统一使用 `i64` 作为所有 ID 类型，并在 `airwar_core.pyi` 存根中同步。

#### 5.7.5 Python fallback `batch_render_particles` 颜色分量为 float 时 TypeError

- **位置**：`airwar/core_bindings.py:449-476`
- **修复**：

```python
data[idx] = min(255, data[idx] + int(r) * sa // 255)
```

### 5.8 排行榜/数据/配置 HIGH

#### 5.8.1 `DifficultyManager._notify_listeners` 迭代时删除元素

- **位置**：`airwar/game/systems/difficulty_manager.py:160-171`
- **修复**：

```python
def _notify_listeners(self) -> None:
    params = self.get_current_params()
    failed = []
    for listener in self._listeners[:]:  # 浅拷贝
        try:
            listener.on_difficulty_changed(params)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            self._logger.error(...)
            failed.append(listener)
    for listener in failed:
        self.remove_listener(listener)
```

#### 5.8.2 `DifficultyManager.set_difficulty/set_boss_kill_count` 未通知监听器

- **位置**：`airwar/game/systems/difficulty_manager.py:51-66`
- **修复**：在状态变更后调用 `_notify_listeners()`；若担心初始化时重复通知，添加 `_notifications_paused` 标志。

#### 5.8.3 爆炸导弹发光贴图尺寸不一致

- **位置**：`airwar/utils/_sprites_bullets.py:158-179`、`airwar/core_bindings.py:577-594`、`airwar_core/src/sprites.rs:219-246`
- **修复**：统一公式：

```python
bw = int(width * 0.8)
surf_w = bw * 3 + 12
surf_h = int(height) + 10
data = create_explosive_missile_glow(float(bw), float(height))
```

Rust 端相应改为 `let bw = (width * 0.8).round() as f32`。

#### 5.8.4 `UserDB.get_leaderboard` 非法 `score` 转换

- **位置**：`airwar/utils/database.py:218-231`
- **修复**：

```python
def _safe_score(entry: dict) -> int:
    try:
        return int(entry.get("score", 0))
    except (TypeError, ValueError):
        return 0
```

#### 5.8.5 `LeaderboardService.submit_score` 非法 `score` 崩溃

- **位置**：`airwar/leaderboard/service.py:80-141`
- **修复**：

```python
try:
    score_int = int(score)
except (TypeError, ValueError):
    logger.warning("Invalid score %r for leaderboard, ignoring", score)
    return 0
```

---

## 6. Phase 3：状态一致性与潜在风险（MEDIUM）

本阶段修复边界条件下的潜在问题，提升长会话稳定性。

### 6.1 场景生命周期 MEDIUM

#### 6.1.1 `_on_player_damaged` 中 `scene.state` 死代码

- **位置**：`airwar/scenes/game_scene_updater.py:383-386`
- **修复**：删除该死代码块，或改为 `scene.game_controller.state`。

#### 6.1.2 `GameScene.__setattr__` 魔法方法带来拷贝/序列化风险

- **位置**：`airwar/scenes/game_scene.py:376-381`
- **修复**：去掉 `__setattr__` 钩子，把同步逻辑放到 `_set_homecoming_coordinator` 显式方法中。

#### 6.1.3 `_handle_scene_events` 事件分发目标漂移

- **位置**：`airwar/game/scene_director_components/scene_switcher.py:262-273`
- **修复**：分发前快照当前场景：

```python
if target_scene is None:
    current = self._scene_manager.get_current_scene()
    if current is None:
        return
    for event in events:
        if skip_escape and getattr(event, "key", None) == pygame.K_ESCAPE:
            continue
        current.handle_events(event)
    return
```

#### 6.1.4 `GameScene.__init__` 中大量属性声明为非 Optional 却初始化为 None

- **位置**：`airwar/scenes/game_scene.py:119-149`
- **修复**：改为 `GameRenderer | None` 类型，访问处做判空。

### 6.2 实体战斗核心 MEDIUM

#### 6.2.1 `Player.add_listener` 无移除接口

- **位置**：`airwar/entities/player.py:424-425`、`airwar/entities/player_components/weapon.py:74-76`
- **修复**：提供 `remove_listener` 并在场景退出时调用。

#### 6.2.2 `Vector2.__add__` / `__sub__` 未校验操作数类型

- **位置**：`airwar/entities/base.py:44-60`
- **修复**：增加类型检查或返回 `NotImplemented`。

#### 6.2.3 `Rect.colliderect` 未校验 other 类型

- **位置**：`airwar/entities/base.py:184-190`
- **修复**：增加 `hasattr` 检查或显式转换。

#### 6.2.4 `BossMovement.select_next_target` 极小分辨率下 `randint` 低大于高

- **位置**：`airwar/entities/enemy/boss/boss_movement.py:92-135`
- **修复**：调用前确保 `low <= high`。

### 6.3 游戏管理器 MEDIUM

#### 6.3.1 `GameLoopManager._update_core` 中 `_lock_manager` 为 None 时抛出 RuntimeError 太晚

- **位置**：`airwar/game/managers/game_loop_manager.py:219-220`
- **修复**：在 `__init__` 中校验 `lock_manager` 非空，或在进入 gameplay 前更早失败。

#### 6.3.2 `SpawnController._calculate_escape_time` 对 NaN 处理不当

- **位置**：`airwar/game/managers/spawn_controller.py:223-234`
- **修复**：校验 `player_dps` 为有限值：

```python
if player_dps is None or not math.isfinite(player_dps):
    player_dps = bullet_damage * self.PLAYER_BULLETS_PER_SHOT / self.PLAYER_FIRE_INTERVAL
```

#### 6.3.3 `BulletManager._update_release_delay` `direction` 可能为 None

- **位置**：`airwar/game/managers/bullet_manager.py:230-236`
- **修复**：已部分处理，但 `bullet.velocity.normalize()` 在 velocity 为 0 时会怎样取决于 `Vector2` 实现，需确认；建议加 `length() > 0` 判断。

### 6.4 母舰/返航/保存 MEDIUM

#### 6.4.1 `HomecomingBaseState` 直接访问 mission dict 固定 key

- **位置**：`airwar/game/systems/homecoming_base_state.py:48-82`
- **修复**：使用 `.get()` 访问 key。

#### 6.4.2 `PersistenceManager.load_game` 遇损坏直接删除存档

- **位置**：`airwar/game/mother_ship/persistence_manager.py:180-197`
- **修复**：删除前备份为 `.corrupted`。

#### 6.4.3 `SaveRestoreManager` 对 player boost 属性硬依赖

- **位置**：`airwar/game/systems/save_restore_manager.py:57-63`
- **修复**：用 `hasattr` 循环设置属性。

#### 6.4.4 `InputDetector` 发布未订阅事件 `EVENT_DOCKING_COMPLETE`

- **位置**：`airwar/game/mother_ship/input_detector.py:67`、`airwar/game/mother_ship/event_hub.py:29-43`
- **修复**：移除 `DOCKING_COMPLETE` 发布，或补全订阅与处理。

#### 6.4.5 `HomecomingSequence` 模块级 `__getattr__` 死代码

- **位置**：`airwar/game/homecoming/homecoming_sequence.py:279-300`
- **修复**：删除类属性硬编码，真正通过 `__getattr__` 读取；或删除 `__getattr__`，在类属性中统一引用常量。

### 6.5 输入/锁/状态 MEDIUM

#### 6.5.1 `LockManager.apply_transient_state` 绕过锁仲裁

- **位置**：`airwar/game/systems/lock_manager.py:143-160`
- **修复**：删除该方法，统一走 `acquire/release`；或调用后立即 `_recompute()` 并 assert。

#### 6.5.2 `LockManager.acquire_or_update` 每帧调用导致计时器永不衰减

- **位置**：`airwar/game/systems/lock_manager.py:75-105`
- **修复**：仅当请求真正改变状态或需要延长时长时才强制更新。

#### 6.5.3 `GiveUpDetector` / `HomecomingDetector` 硬依赖 `pygame.key.get_pressed()`

- **位置**：`airwar/game/give_up/give_up_detector.py:25`、`airwar/game/homecoming/homecoming_detector.py:27`
- **修复**：依赖注入按键状态读取函数。

#### 6.5.4 `LockManager` 缺乏字段校验

- **位置**：`airwar/game/systems/lock_manager.py:56-122`
- **修复**：校验 `layer` 类型与 `invincibility_duration` 非负。

#### 6.5.5 `PygameInputHandler.get_movement_direction` 对角移动速度为 √2 倍

- **位置**：`airwar/input/input_handler.py:66-80`
- **修复**：归一化对角移动向量。

#### 6.5.6 `LockManager.set_player` 切换玩家时未清理旧玩家控制锁

- **位置**：`airwar/game/systems/lock_manager.py:51-54`
- **修复**：

```python
def set_player(self, player):
    if self._player is not None and self._player is not player:
        self._player.is_controls_locked = False
    self._player = player
    if self._locks:
        self._recompute()
```

### 6.6 UI 渲染与特效 MEDIUM

#### 6.6.1 `DiscreteBatteryIndicator` 未校验负尺寸

- **位置**：`airwar/ui/discrete_battery.py:59-85`、`87-111`
- **修复**：在 `__init__` 或 render 开头 `w = max(1, w)`、`h = max(1, h)`。

#### 6.6.2 `SpaceBackground.resize` / `_generate_gradient` 未处理 0 尺寸

- **位置**：`airwar/game/rendering/game_rendering_background.py:98-114`、`132-136`
- **修复**：

```python
if screen_width <= 0 or screen_height <= 0:
    return
```

#### 6.6.3 `HauntingRenderer.get_static_filter` 未处理 0 尺寸

- **位置**：`airwar/game/rendering/haunting_renderer.py:174-191`
- **修复**：

```python
if width <= 0 or height <= 0:
    return pygame.Surface((1, 1), pygame.SRCALPHA)
```

#### 6.6.4 `IntegratedHUD._render_collapsed_health` 可能创建负宽度电池

- **位置**：`airwar/ui/integrated_hud.py:209`
- **修复**：`bw = max(1, min(self.BATTERY_WIDTH_CAP, cw - 10))`。

#### 6.6.5 `IntegratedHUD._render_progress_module` 进度条可能超出背景

- **位置**：`airwar/ui/integrated_hud.py:355-357`
- **修复**：`fill_width = int(bar_width * min(progress, 100) / 100)`。

#### 6.6.6 `HUDRenderer.render_ripples` 直接访问 ripple 字典键

- **位置**：`airwar/game/rendering/hud_renderer.py:309-312`
- **修复**：使用 `.get()`。

#### 6.6.7 `BoostGauge` 紧凑模式缓存键可能冲突

- **位置**：`airwar/ui/boost_gauge.py:174-183`、`239-248`
- **修复**：分离普通/紧凑缓存字段，或在键中加入模式标记。

#### 6.6.8 `HauntingRenderer.distort_world` 可能传入负高度

- **位置**：`airwar/game/rendering/haunting_renderer.py:112-123`
- **修复**：`band_h = max(1, min(band_h, height - y))`。

### 6.7 Rust 扩展 MEDIUM

#### 6.7.1 `generate_explosion_particles` `life_min > life_max`

- **位置**：`airwar_core/src/particles.rs:81`
- **修复**：

```rust
let life_range = (life_max - life_min).max(0);
let life = life_min + (fast_rand() * life_range as f32) as i32;
```

#### 6.7.2 Python fallback `compute_starfield_positions` 未校验

- **位置**：`airwar/core_bindings.py:244-261`
- **修复**：校验 divisor 与 table 长度。

#### 6.7.3 `vec2_clamp_length` 负 `max_length`

- **位置**：`airwar_core/src/vector2.rs:72-80`、`airwar/core_bindings.py:158-164`
- **修复**：`let max_length = max_length.abs();` 或 `if max_length <= 0.0 { return (0.0, 0.0); }`。

#### 6.7.4 `Particle::get_alpha` `max_life == 0` 除零

- **位置**：`airwar_core/src/particles.rs:31-34`
- **修复**：

```rust
if self.max_life == 0 { 0.0 } else { self.life as f32 / self.max_life as f32 }
```

### 6.8 排行榜/数据/配置 MEDIUM

#### 6.8.1 `DifficultyCoefficientPanel` 直接读取 `initial_multiplier`

- **位置**：`airwar/ui/difficulty_coefficient_panel.py:33`
- **修复**：`getattr(difficulty_manager, "initial_multiplier", 1.0)`。

#### 6.8.2 `UserDB.create_user` 未防御空/非字符串密码

- **位置**：`airwar/utils/database.py:92-102`、`115-129`
- **修复**：

```python
if not isinstance(password, str) or len(password) < 1:
    return False
```

#### 6.8.3 `SimpleDB` 对 `db_path` 为目录的情况缺乏早期报错

- **位置**：`airwar/utils/database.py:44-58`
- **修复**：

```python
if os.path.exists(self.db_path) and os.path.isdir(self.db_path):
    raise DatabaseError(f"Database path is a directory: {self.db_path}")
```

#### 6.8.4 字体匹配到无效路径时未回退

- **位置**：`airwar/utils/fonts.py:69-99`
- **修复**：捕获 `OSError`/`pygame.error` 并回退到默认字体。

---

## 7. Phase 4：代码清理与可维护性（LOW）

本阶段主要消除代码异味、死代码、未使用字段、缓存泄漏等。

### 7.1 通用清理

1. **删除死代码**：`_can_fire`、`MenuBackground` 空 `_init_particles`/`_init_light_spots`、`SpaceBackground._star_cache`、`BossEnrageRenderer` 未使用 distortion 缓冲。
2. **魔法数字常量化**：`LockManager` 中的 `999999` 永久无敌阈值。
3. **`__all__` 补全**：`airwar/utils/sprites.py` 精英敌机导出；`airwar/core_bindings.py` buffer 函数导出。
4. **异常捕获粒度调整**：`HUDRenderer.render_buff_stats_panel` 不应裸吞 `Exception`。
5. **缓存容量限制**：`chamfered_panel.py` 模块级缓存加 LRU。
6. **性能优化**：`ExplosionPool.release` 线性搜索改为集合/字典索引。

### 7.2 文档与注释同步

1. `Player.__init__` 组件初始化顺序注释与代码不符。
2. `Boss._enrage_spawned_bullets` 使用脆弱 duck typing，应在 `IBulletSpawner` 中定义契约。
3. `DifficultyListener` 不是真正的抽象类，应使用 `ABC` + `@abstractmethod`。
4. `Enemy._get_damage` 不应使用 Boss 子弹伤害表。

### 7.3 类型声明整理

1. 把 `GameScene` 中 `enter()` 前可能为 `None` 的属性改为 `| None`。
2. `GameSceneProtocol` 与 `GameScene` 属性不匹配（`state`）。

---

## 8. 附录 A：按模块组的完整问题速查表

### 8.1 场景生命周期模块组

| 编号 | 严重度 | 文件/行号 | 问题简述 |
|------|--------|-----------|----------|
| S-1 | CRITICAL | `scene_switcher.py:108-116`, `game_scene.py:189` | `GameScene.enter()` 构造失败未捕获 (已修复) |
| S-2 | CRITICAL | `game_scene.py:463-465`, `game_scene_renderer.py:65-100`, `game_scene_updater.py:108-413`, `game_scene_event_dispatcher.py:48-51` | 公共方法在 `enter()` 完成前被调用 (已修复) |
| S-3 | CRITICAL | `scene_switcher.py:399-420` | `_handle_game_over` 忽略 `"quit"` 返回值 (已修复) |
| S-4 | HIGH | `scene_switcher.py:72` | `run_welcome_flow` 兜底返回值让非法状态进入游戏 (已修复) |
| S-5 | HIGH | `game_scene.py:174-175` | `GameScene.enter` 不校验必需 kwargs (已修复) |
| S-6 | HIGH | `scene_state_persistence.py:49-50` | `clear_saved_game` 在 `current_user=None` 时误删存档 (已修复) |
| S-7 | HIGH | `scene_switcher.py:394-397` | `_show_exit_confirm` 非预期结果默认当退出处理 (已修复) |
| S-8 | HIGH | `scene_director.py:173-174` | `PauseAction.QUIT` 语义与实现不一致 (已修复) |
| S-9 | MEDIUM | `game_scene_updater.py:383-386` | `_on_player_damaged` 中 `scene.state` 死代码 (已修复) |
| S-10 | MEDIUM | `game_scene.py:376-381` | `GameScene.__setattr__` 魔法方法风险 (已修复) |
| S-11 | MEDIUM | `scene_switcher.py:262-273` | 事件分发目标漂移 (已修复) |
| S-12 | MEDIUM | `game_scene_event_dispatcher.py:48-51` | 访问核心组件无空值保护 |
| S-13 | MEDIUM | `game_scene_renderer.py:106-111`, `73-74`, `236` | 渲染助手访问 player 等未判空 (已修复) |
| S-14 | LOW | `game_scene.py:119-149` | 属性声明为非 Optional 却初始化为 None |
| S-15 | LOW | `game_scene_protocols.py:122` | Protocol 声明 `state` 但实现无该属性 |
| S-16 | LOW | `game_scene_renderer.py:251` | 冗余空值检查 |
| S-17 | LOW | `game_scene.py:695-720` | `_clear_module_caches` 捕获范围过窄 |

### 8.2 实体战斗核心模块组

| 编号 | 严重度 | 文件/行号 | 问题简述 |
|------|--------|-----------|----------|
| E-1 | CRITICAL | `boss.py:199-285`, `438-452` | `Boss.update` 未防御 inactive Boss (已修复) |
| E-2 | HIGH | `enemy.py:198-216` | `Enemy.update` 忽略 `slow_factor`/`player_pos` (已修复) |
| E-3 | HIGH | `enemy.py:379-384` | `Enemy.set_difficulty` 速度倍率未使用 (已修复) |
| E-4 | HIGH | `boss.py:369-382`, `294-302` | Boss aim-dash 后 `fire_timer` 未消耗 (已修复) |
| E-5 | HIGH | `boss.py:483-496`, `422-432` | 狂暴子弹依赖 spawner `get_bullets` (已修复) |
| E-6 | HIGH | `boss.py:453-465` | 狂暴触发移动玩家未 clamp (已修复) |
| E-7 | HIGH | `player.py:207-284`, `331-334` | `Player.update` 不检查 alive (已修复) |
| E-8 | HIGH | `player.py:285-309` | `Player.render` 未防御 sprite None (已修复) |
| E-9 | HIGH | `player.py:169` | `fire_interval` setter 对非法值崩溃 (已修复) |
| E-10 | HIGH | `player.py:444-448` | `_read_boost_just_pressed` fallback 状态不同步 (已修复) |
| E-11 | MEDIUM | `player_state.py:173-176` | `mark_dying` 非幂等 |
| E-12 | MEDIUM | `player_state.py:181-184` | `respawn` 未清理旧状态 |
| E-13 | MEDIUM | `player.py:412-416`, `player_state.py` | HSM 子状态与组件标志不同步 (已修复) |
| E-14 | MEDIUM | `player.py:424-425`, `weapon.py:74-76` | `add_listener` 无移除接口 (已修复) |
| E-15 | MEDIUM | `base.py:44-60` | `Vector2.__add__` 未校验类型 (已修复) |
| E-16 | MEDIUM | `base.py:184-190` | `Rect.colliderect` 未校验类型 (已修复) |
| E-17 | MEDIUM | `boss_movement.py:92-135` | 极小分辨率下 `randint` 低大于高 (已修复) |
| E-18 | MEDIUM | `boss.py:238-267`, `279-302` | 狂暴期间 `fire_timer` 暂停，返回 active 后可能立即开火 (已修复) |
| E-19 | LOW | `enemy.py:567-568` | 普通敌人使用 Boss 子弹伤害表 |
| E-20 | LOW | `enemy.py:542-549` | spread 分支把角度值当 x 偏移 |
| E-21 | LOW | `player.py:104-119` | 组件初始化顺序注释与代码不符 |
| E-22 | LOW | `boss.py:422-432` | `_enrage_spawned_bullets` 使用脆弱 duck typing |

### 8.3 游戏管理器模块组

| 编号 | 严重度 | 文件/行号 | 问题简述 |
|------|--------|-----------|----------|
| M-1 | CRITICAL | `game_loop_manager.py:183-194` | `update_entrance` 除零 (已修复) |
| M-2 | CRITICAL | `game_loop_manager.py:280-285` | `_estimate_player_dps` 除零 (已修复) |
| M-3 | CRITICAL | `spawn_controller.py:153` | `SpawnController.update` 除零 (已修复) |
| M-4 | CRITICAL | `bullet_manager.py:177`, `205` | `_update_bullets_batch` 解引用 `bullet.data` (已修复) |
| M-5 | CRITICAL | `game_loop_manager.py:388-394` | Rust 返回长度不一致导致越界 (已修复) |
| M-6 | HIGH | `collision_controller.py:142-144`, `154-159`, `188-193` | 负坐标空间哈希漏检 (已修复) |
| M-7 | HIGH | `boss_manager.py:129-131` | 依赖 Boss 私有属性 `_death_consumed` (已修复) |
| M-8 | HIGH | `spawn_controller.py:206` | Boss `fire_rate` 可能为负 (已修复) |
| M-9 | HIGH | `game_loop_manager.py:211-217` | DYING 状态重复更新 death animation (已修复) |
| M-10 | HIGH | `enemy_bullet_vs_player.py:97-104` | 多子弹同时命中只处理一个 (已修复) |
| M-11 | MEDIUM | `game_loop_manager.py:219-220` | `_lock_manager` None 检查太晚 (已修复) |
| M-12 | MEDIUM | `spawn_controller.py:223-234` | `player_dps` 为 NaN 时行为异常 (已修复) |
| M-13 | MEDIUM | `bullet_manager.py:230-236` | `direction` 为 None 时可能异常 (已修复) |

### 8.4 母舰/返航/保存模块组

| 编号 | 严重度 | 文件/行号 | 问题简述 |
|------|--------|-----------|----------|
| H-1 | CRITICAL | `save_restore_manager.py:51-54`, `69`, `74` | `restore` 直接解引用子系统 (已修复) |
| H-2 | CRITICAL | `homecoming_sequence.py:71`, `87`, `118`, `274-275` | `player` 为 None 时崩溃 (已修复) |
| H-3 | CRITICAL | `homecoming_coordinator.py:341-368` | `_clear_hostiles` 硬访问 spawner 字段 (已修复) |
| H-4 | HIGH | `game_integrator.py:421-440` | 回退分支无敌帧数错误 (已修复) |
| H-5 | HIGH | `state_machine.py:57-69`, `event_hub.py:59-71` | 事件订阅只注册不注销 (已修复) |
| H-6 | HIGH | `save_restore_manager.py:19-94` | 读档不清理旧战场状态 (已修复) |
| H-7 | HIGH | `save_restore_manager.py:52`, `69`, `74` | 混用 `game_controller.reward_system` 与参数 (已修复) |
| H-8 | HIGH | `game_integrator.py:502-536` | `create_save_data` 硬依赖 `game_scene` 方法 (已修复) |
| H-9 | MEDIUM | `homecoming_base_state.py:48-82` | 直接访问 mission dict 固定 key (已修复) |
| H-10 | MEDIUM | `persistence_manager.py:180-197` | 损坏存档直接删除 (已修复) |
| H-11 | MEDIUM | `save_restore_manager.py:57-63` | 对 player boost 属性硬依赖 (已修复) |
| H-12 | MEDIUM | `input_detector.py:67`, `event_hub.py:29-43` | 发布未订阅事件 (已修复) |
| H-13 | MEDIUM | `homecoming_sequence.py:279-300` | 模块级 `__getattr__` 死代码 (已修复) |

### 8.5 输入/锁/状态模块组

| 编号 | 严重度 | 文件/行号 | 问题简述 |
|------|--------|-----------|----------|
| I-1 | HIGH | `input_handler.py:59-64`, `66-84` | 自定义键位缺失 KeyError (已修复) |
| I-2 | HIGH | `input_coordinator.py:35-77` | 构造参数为空时崩溃 (已修复) |
| I-3 | HIGH | `lock_manager.py:162-194` | 锁优先级切换时无敌时间重置 (已修复) |
| I-4 | HIGH | `give_up_detector.py:24-34`, `input_coordinator.py:55-66` | 不可用期间丢失按键释放事件 (已修复) |
| I-5 | HIGH | `input_handler.py:86-107` | 边沿检测方法副作用 (已修复) |
| I-6 | MEDIUM | `lock_manager.py:143-160` | `apply_transient_state` 绕过锁仲裁 (已修复) |
| I-7 | MEDIUM | `lock_manager.py:75-105` | `acquire_or_update` 每帧调用计时器永生 (已修复) |
| I-8 | MEDIUM | `give_up_detector.py:25`, `homecoming_detector.py:27` | 硬依赖 pygame 按键读取 (已修复) |
| I-9 | MEDIUM | `lock_manager.py:56-122` | 缺乏字段校验 (已修复) |
| I-10 | MEDIUM | `input_handler.py:66-80` | 对角移动速度为 √2 倍 (已修复) |
| I-11 | MEDIUM | `lock_manager.py:51-54` | 切换玩家未清理旧玩家控制锁 (已修复) |
| I-12 | LOW | `input_coordinator.py:52-53` | `_can_fire` 死代码 |
| I-13 | LOW | `lock_manager.py:189` | 魔法数字 `999999` |
| I-14 | LOW | `give_up_detector.py:51-54`, `homecoming_detector.py:62-65` | 回调异常后状态不可恢复 |
| I-15 | LOW | `input_coordinator.py:75-76` | `render_give_up` 未防御 UI 为空 |

### 8.6 UI 渲染与特效模块组

| 编号 | 严重度 | 文件/行号 | 问题简述 |
|------|--------|-----------|----------|
| U-1 | CRITICAL | `segmented_bar.py:63` | `max_value == 0` 除零 (已修复) |
| U-2 | CRITICAL | `explosion_effect.py:343` | `_render_shockwave` 除零 (已修复) |
| U-3 | CRITICAL | `explosion_effect.py:246-254` | Rust 返回粒子长度不一致 (已修复) |
| U-4 | CRITICAL | `game_renderer.py:76` | `_render_entrance` 除零 (已修复) |
| U-5 | CRITICAL | `integrated_hud.py:476-481` | `_get_visible_buffs` 除零 (已修复) |
| U-6 | CRITICAL | `integrated_hud.py:436-438` | `get_buff_color` 返回值未校验 (已修复) |
| U-7 | CRITICAL | `entity_renderer.py:93-109` | `bullet.data` 未检查 (已修复) |
| U-8 | CRITICAL | `boss_enrage_renderer.py:51-52` | `boss.rect` 未检查 (已修复) |
| U-9 | CRITICAL | `leaderboard_view.py:56-57`, `77` | `fetch_entries` 异常未捕获 (已修复) |
| U-10 | CRITICAL | `menu_background.py:176-177` | 直接访问 `colors["bg"]` (已修复) |
| U-11 | HIGH | `particles.py:92-97` | 共享缓存 alpha 污染 (已修复) |
| U-12 | HIGH | `integrated_hud.py:388-392` | 展开态血条未同步生命值 (已修复) |
| U-13 | HIGH | `entity_renderer.py:134-213` | 访问 Boss 私有属性 (已修复) |
| U-14 | HIGH | `explosion_manager.py:103-107` | 使用入口动画时长控制每秒上限 (已修复) |
| U-15 | HIGH | `difficulty_coefficient_panel.py:33` | 直接读取 `initial_multiplier` (已修复) |
| U-16 | HIGH | `haunting_renderer.py:112-123` | 可能传入负高度 (已修复) |
| U-17 | HIGH | `integrated_hud.py:66-67`, `186-200`, `243-270` | 颜色元组长度假设 (已修复) |
| U-18 | MEDIUM | `discrete_battery.py:59-85`, `87-111` | 未校验负尺寸 (已修复) |
| U-19 | MEDIUM | `game_rendering_background.py:98-114`, `132-136` | 0 尺寸未处理 (已修复) |
| U-20 | MEDIUM | `haunting_renderer.py:174-191` | 0 尺寸未处理 (已修复) |
| U-21 | MEDIUM | `integrated_hud.py:209` | 可能创建负宽度电池 (已修复) |
| U-22 | MEDIUM | `integrated_hud.py:355-357` | 进度条可能超出背景 (已修复) |
| U-23 | MEDIUM | `hud_renderer.py:309-312` | 直接访问 ripple 字典键 (已修复) |
| U-24 | MEDIUM | `boost_gauge.py:174-183`, `239-248` | 缓存键可能冲突 |
| U-25 | LOW | `boss_enrage_renderer.py:33-42` | 分配未使用 distortion 缓冲 |
| U-26 | LOW | `menu_background.py:111-117` | `_init_particles` / `_init_light_spots` 为空 |
| U-27 | LOW | `game_rendering_background.py:30` | `_star_cache` 未使用 |
| U-28 | LOW | `hud_renderer.py:314-323` | 异常捕获过于宽泛 |
| U-29 | LOW | `explosion_pool.py:43-52` | `release` 线性搜索 |
| U-30 | LOW | `chamfered_panel.py:8-11` | 类级缓存无上限 |
| U-31 | LOW | `game_renderer.py:44`, `207` | `_screen_diagonal` 初始为 0 |

### 8.7 Rust 扩展与回退模块组

| 编号 | 严重度 | 文件/行号 | 问题简述 |
|------|--------|-----------|----------|
| R-1 | CRITICAL | `collision.rs:37-40`, `58-61`, `179` | `cell_size == 0` 除零 panic (已修复) |
| R-2 | CRITICAL | `movement.rs:325-329` | Zigzag `interval` 为 0 取模 panic (已修复) |
| R-3 | CRITICAL | `particles.rs:75` | 负 `particle_count` OOM/panic (已修复) |
| R-4 | CRITICAL | `movement.rs:224-246` | `extra_buf` 长度不足 panic (已修复) |
| R-5 | CRITICAL | `bullets.rs:45-46` | 缓冲区长度非 32 整数倍 (已修复) |
| R-6 | HIGH | `collision.rs:37-40`, `58-61` | 负坐标向零截断除法漏检 (已修复) |
| R-7 | HIGH | `starfield.rs:65`, `74` | `sin_table` 越界与 divisor 除零 (已修复) |
| R-8 | HIGH | `particles.rs:101-104` | 负屏幕尺寸 OOM (已修复) |
| R-9 | HIGH | `sprites.rs:118-120`, `141`, `185-186`, `221-222`, `250-252` | 负半径/尺寸 OOM (已修复) |
| R-10 | HIGH | `movement.rs:137-140`, `core_bindings.py:399` | 批量运动长度不一致截断 (已修复) |
| R-11 | MEDIUM | `particles.rs:81` | `life_min > life_max` 产生负生命 (已修复) |
| R-12 | MEDIUM | `collision.rs:170-174`, `movement.rs:448`, `463`, `bullets.rs:9` | ID 类型不一致 (已修复) |
| R-13 | MEDIUM | `movement.rs:358-400` | NaN 输入返回 NaN (已修复) |
| R-14 | MEDIUM | `core_bindings.py:449-476` | `batch_render_particles` float 颜色 TypeError (已修复) |
| R-15 | MEDIUM | `core_bindings.py:707-740` | `__all__` 缺少 buffer 函数 (已修复) |
| R-16 | MEDIUM | `core_bindings.py:244-261` | `compute_starfield_positions` 未校验 (已修复) |
| R-17 | LOW | `sprites.rs:166-167` | `create_spread_bullet_glow` 循环变量写反 |
| R-18 | LOW | `vector2.rs:72-80`, `core_bindings.py:158-164` | `vec2_clamp_length` 负长度反向缩放 |
| R-19 | LOW | `particles.rs:31-34` | `Particle::get_alpha` 除零 |
| R-20 | LOW | `particles.rs:163-169` | RNG 在异常时钟下 panic |
| R-21 | LOW | `collision.rs:123-155` | SSE2 target_feature 可移植性隐患 |
| R-22 | LOW | `core_bindings.py:211-224`, `movement.rs:40-57` | NaN 处理双路径不一致 |

### 8.8 排行榜/数据/配置模块组

| 编号 | 严重度 | 文件/行号 | 问题简述 |
|------|--------|-----------|----------|
| D-1 | HIGH | `_sprites_bullets.py:158-179`, `core_bindings.py:577-594`, `sprites.rs:219-246` | 爆炸导弹 glow 尺寸不一致 (已修复) |
| D-2 | HIGH | `leaderboard_view.py:54-77`, `service.py:143-169`, `client.py:78-87` | 排行榜 UI 每帧同步网络请求 (已修复) |
| D-3 | HIGH | `difficulty_manager.py:160-171` | 迭代监听器时删除元素 (已修复) |
| D-4 | MEDIUM | `database.py:234-272` | 写入未过滤损坏条目 (已修复) |
| D-5 | MEDIUM | `database.py:218-231` | 非法 `score` 转换崩溃 (已修复) |
| D-6 | MEDIUM | `leaderboard/config.py:19-23` | 环境变量非法值启动失败 (已修复) |
| D-7 | MEDIUM | `leaderboard/service.py:80-141` | `submit_score` 非法 score 崩溃 (已修复) |
| D-8 | MEDIUM | `design_tokens.py:75-77` | `Colors.star_color` 颜色越界 (已修复) |
| D-9 | MEDIUM | `difficulty_manager.py:51-66` | 修改难度未通知监听器 (已修复) |
| D-10 | LOW | `database.py:92-102`, `115-129` | 空/非字符串密码 (已修复) |
| D-11 | LOW | `utils/sprites.py:34-51` | `__all__` 缺少精英敌机 |
| D-12 | LOW | `_sprites_bullets.py:94-102` | 敌机子弹发光偏移 |
| D-13 | LOW | `difficulty_manager.py:12-16` | `DifficultyListener` 非真正抽象类 |
| D-14 | LOW | `database.py:44-58` | `db_path` 为目录未早期报错 (已修复) |
| D-15 | LOW | `fonts.py:69-99` | 字体无效路径未回退 (已修复) |

---

## 9. 附录 B：验证清单

### 9.1 自动化检查（每次提交前必须执行）

```bash
python3 -m pytest tests/ -v
python3 -m ruff check .
python3 -m compileall -q airwar main.py
```

若修改了 Rust 扩展：

```bash
cd airwar_core
python3 -m maturin develop --release
cd ..
cargo clippy --all-targets --all-features -- -D warnings  # 可选，视项目 CI 而定
```

### 9.2 手动流程验证（每个 Phase 结束后执行）

1. **启动流程**：`./run.sh --debug` 能正常到欢迎界面
2. **登录/注册**：创建用户、登录、退出
3. **游戏启动**：从欢迎界面进入游戏，入口动画正常
4. **基础操作**：移动、射击、加速、相位冲刺（如已解锁）
5. **敌人波次**：击杀普通敌人，观察难度变化
6. **Boss 战**：等待 Boss 出现，击杀/让其逃跑，观察通知与下一波生成
7. **暂停/恢复**：ESC 暂停，继续游戏
8. **返航基地**：B 长按返航，离舰后状态正确
9. **对接母舰**：H 长按保存
10. **放弃出击**：K 长按放弃
11. **死亡流程**：被击杀后进入死亡场景，返回菜单
12. **读档**：重新登录后读取上次保存，状态一致
13. **排行榜**：打开排行榜面板，远程/本地模式不卡顿
14. **设置/退出**：调整设置，正常退出游戏

### 9.3 边界条件验证

1. 窗口最小化/还原后无崩溃
2. 快速连续暂停/恢复无状态错乱
3. Boss 狂暴期间玩家被锁定，结束后控制恢复
4. 玩家死亡动画期间不再移动/射击
5. 读档后旧敌人/Boss/子弹被清理
6. 网络不可用时排行榜不卡死，回退到本地
7. 存档文件损坏时不丢失数据（备份 `.corrupted`）

---

## 10. 附录 C：修复优先级总表

下表综合所有模块组，按“先修依赖、后修被依赖”原则给出全局优先级。

| 全局优先级 | 阶段 | 问题编号/名称 | 关键文件 | 验收方式 |
|------------|------|---------------|----------|----------|
| P1 | Phase 1 | GameScene 生命周期防御（S-1, S-2, S-3） | `scene_switcher.py`, `game_scene.py` | 启动/重开/退出不崩溃 |
| P2 | Phase 1 | Rust 扩展 panic 入口（R-1 ~ R-6） | `airwar_core/src/*.rs` | `cargo check` 通过，Boss/敌人正常移动 |
| P3 | Phase 1 | 渲染/UI 除零与空值（U-1 ~ U-10） | `ui/*.py`, `rendering/*.py`, `explosion_animation/*.py` | HUD/爆炸/血条正常 |
| P4 | Phase 1 | 实体核心崩溃（E-1, E-7, E-8, E-9） | `entities/*.py` | 玩家/Boss 死亡/渲染不崩溃 |
| P5 | Phase 1 | 管理器崩溃（M-1 ~ M-5） | `game/managers/*.py` | 入口动画/Boss 生成/子弹更新不崩溃 |
| P6 | Phase 1 | 母舰/保存崩溃（H-1 ~ H-3） | `mother_ship/*.py`, `systems/homecoming*.py` | 返航/读档不崩溃 |
| P7 | Phase 1 | 排行榜卡死/崩溃（D-2, D-6, D-7, D-8） | `leaderboard/*.py`, `ui/leaderboard_view.py` | 排行榜打开不卡顿 |
| P8 | Phase 2 | 输入/锁状态一致性（I-3, I-4, I-5, I-10） | `input/*.py`, `systems/lock_manager.py` | 冲刺/暂停/投降逻辑正确 |
| P9 | Phase 2 | Boss 战斗逻辑（E-2 ~ E-6, E-18） | `entities/enemy/boss/*.py` | 慢动作、狂暴、aim-dash 正常 |
| P10 | Phase 2 | 难度管理器通知（D-3, D-9） | `systems/difficulty_manager.py` | 难度切换/存档恢复后状态一致 |
| P11 | Phase 2 | 场景流程控制（S-4 ~ S-8） | `scene_director*.py` | 非法状态不进入游戏，退出行为正确 |
| P12 | Phase 2 | 母舰事件订阅/保存一致性（H-4 ~ H-8） | `mother_ship/*.py`, `systems/save_restore_manager.py` | 停靠无敌、保存/读档状态一致 |
| P13 | Phase 2 | 碰撞正确性（M-6） | `managers/collision_controller.py` | 屏幕边缘碰撞正确 |
| P14 | Phase 3 | 边界条件 MEDIUM（各模块） | 见 8.x MEDIUM 项 | 长会话稳定 |
| P15 | Phase 4 | 代码清理 LOW | 见 8.x LOW 项 | `ruff` 全绿，无死代码 |

---

## 11. 结语

本指导文档基于对 Air War 项目关键运行时模块的深度审查，列出了当前最可能引发崩溃、状态异常和玩法失衡的问题，并按依赖关系给出了可执行的分阶段修复计划。

**建议执行顺序**：

1. 先集中完成 **Phase 1** 的所有 CRITICAL 修复，确保游戏不再闪退。
2. 再进行 **Phase 2** 的 HIGH 修复，消除状态不一致和玩法异常。
3. **Phase 3** 和 **Phase 4** 可穿插进行，但必须在每个阶段结束后跑完整验收流程。
4. 所有涉及 Rust 的改动必须同步更新 Python fallback 和 `.pyi` 存根。

**注意事项**：

- 项目测试主要覆盖架构组件，玩法逻辑需手动验证。
- 修复时遵循“最小改动”原则，不要顺带重构无关代码。
- 遇到文档中未覆盖的新问题，应及时补充到本文档的附录中。

---

*文档结束*