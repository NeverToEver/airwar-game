# Air War 全量修复执行报告

> 修复时间：2026-07-12  
> 修复工程师：AI 编码助手  
> 修复依据：`docs/audits/remediation-roadmap.md`、`docs/audits/remediation-plan-main-interfaces-2026-07-11-0422.md`、`docs/audits/2026-07-10_runtime-error-remediation_P1-P15.md`  
> 目标：对 Air War 代码仓库执行 roadmap 中剩余的全量修复，确保高优先级问题全部修复并验证通过。

---

## 1. 修复概览

| 批次 | 主题 | 优先级 | 问题数 | 成功 | 失败 | 跳过 | 备注 |
|------|------|--------|--------|------|------|------|------|
| C | 主循环与场景生命周期异常隔离 | 高 | 5 | 5 | 0 | 0 | 含新增帧错误注入测试 |
| D | LockManager 接口与语义 | 高 | 5 | 5 | 0 | 0 | 新增 LockToken、优先级仲裁、过期清理 |
| E | 帧时间、视口、输入边界 | 中 | 5 | 5 | 0 | 0 | 新增输入处理器测试 |
| F | 实体与战斗系统边界 | 中 | 10 | 10 | 0 | 0 | 含实体接口统一、Boss 死代码清理 |
| G | Rust ↔ Python 边界一致 | 中 | 5 | 5 | 0 | 0 | 已重新编译 Rust 扩展 |
| H | 杂项与可维护性 | 低 | 5 | 5 | 0 | 0 | 含 i18n 路径遍历防护 |
| **合计** | — | — | **35** | **35** | **0** | **0** | — |

### 1.1 变更统计

```text
32 files changed, 895 insertions(+), 253 deletions(-)
```

主要变更分布：

- Python 源码：19 个文件（场景、管理器、实体、输入、i18n、core_bindings 等）
- Rust 源码：4 个文件（bullets、particles、sprites、starfield）
- 测试：6 个文件新增/扩展，新增 6 个测试文件
- 文档：3 个文件（AGENTS.md、review-findings、本报告）

---

## 2. 执行摘要

本次修复严格遵循 `remediation-roadmap.md` 的分批顺序与验收要求：

1. **扫描阶段**：并行读取 6 个批次涉及的全部文件，确认待修复项的当前状态，生成结构化清单。
2. **修复阶段**：按 C → D → E → F/G/H 顺序执行；其中 C/D/E 可并行，F/G/H 可并行。
3. **自验证阶段**：每个批次完成后立即运行 `pytest`、`ruff`、`compileall`；Rust 批次额外执行 `maturin develop --release`。
4. **回归验证阶段**：全量测试 192 passed，ruff 全绿，compileall 通过，`./run.sh --debug` 20 秒内未崩溃，关键端到端边界用例通过。

### 2.1 核心原则遵循情况

| 原则 | 落实情况 |
|------|----------|
| 精准定位根因 | 每个修复项均引用 roadmap 具体编号与文件位置，先扫描再动手。 |
| 最小化改动 | 每个批次只修改与问题直接相关的代码，未借机重构无关逻辑。 |
| 可验证性 | 每项修复均补充测试或扩展现有测试；每个批次后执行自验证。 |
| 可追溯性 | 本报告逐条记录修复依据、修改文件、验证结果；代码变更可 git diff 追溯。 |

---

## 3. 修复依据

本次修复以以下文档为唯一依据：

- `docs/audits/remediation-roadmap.md`：批次 C–H 的修复动作与验收方式。
- `docs/audits/remediation-plan-main-interfaces-2026-07-11-0422.md`：A–H 批次的详细修复方案。
- `docs/audits/2026-07-10_runtime-error-remediation_P1-P15.md`：已修复的运行时崩溃项，用于避免重复工作。
- `docs/audits/review-findings-main-interfaces-2026-07-11-0422.md`：部分 issue 的修复状态已在修复过程中同步更新。

---

## 4. 详细修复记录

### 4.1 批次 C：主循环与场景生命周期异常隔离

**修复时间**：2026-07-12  
**优先级**：高  
**涉及文件**：`airwar/game/scene_director_components/scene_switcher.py`、`airwar/scenes/scene.py`、`airwar/scenes/game_scene_updater.py`、`airwar/scenes/game_scene.py`、`tests/test_scene_manager.py`、`tests/test_scene_switcher.py`

| 编号 | 问题 | 修复动作 | 修复依据 | 自验证结果 |
|------|------|----------|----------|------------|
| C1 | 主循环帧级异常导致进程退出 | 在 `_run_scene_loop` 中对 `handle_events`/`update`/`render`/`flip` 分别加 `try/except`；新增连续失败计数器（阈值 5）；异常时调用场景可选 `on_frame_error()` 钩子。 | roadmap 3.1 C1 | 新增 `tests/test_scene_switcher.py`：单帧错误跳过、连续错误退出、render/flip 错误隔离均通过。 |
| C2 | `SceneManager.switch()` 异常后状态不一致 | 保存 `old_scene`/`old_name`，在 `try` 中调用 `enter()`，异常时回滚旧场景并尝试重新 `enter()`。 | roadmap 3.1 C2 | `tests/test_scene_manager.py::test_switch_rollback_on_enter_error` 通过。 |
| C3 | 子场景循环异常时 `exit()` 不被调用 | 子场景入口方法用 `try/finally` 包裹 `_run_scene_loop`，`finally` 中调用 `exit()`。 | roadmap 3.1 C3 | `test_settings_subscene_exit_called_on_update_error` 通过。 |
| C4 | `assert` 在 `-O` 模式下被移除 | `scene_switcher.py:46` 与 `game_scene_updater.py:364-370` 两处 `assert` 改为显式 `RuntimeError`。 | roadmap 3.1 C4 | 相关测试通过；`compileall` 通过。 |
| C5 | `GameScene` 缓存清理静默吞异常 | `_clear_module_caches()` 中 `except AttributeError/ImportError` 不再 `pass`，统一使用 `logger.debug` 记录。 | roadmap 3.1 C5 | 手动检查日志记录代码已就位；测试通过。 |

**批次 C 自验证**：

```bash
python3 -m pytest tests/test_scene_manager.py tests/test_scene_switcher.py -v   # 21 passed
python3 -m ruff check .                                                          # All checks passed
python3 -m compileall -q airwar main.py                                          # 通过
```

---

### 4.2 批次 D：LockManager 接口与语义

**修复时间**：2026-07-12  
**优先级**：高  
**涉及文件**：`airwar/game/systems/lock_manager.py`、`tests/test_lock_manager.py`、`AGENTS.md`、`docs/audits/review-findings-main-interfaces-2026-07-11-0422.md`

| 编号 | 问题 | 修复动作 | 修复依据 | 自验证结果 |
|------|------|----------|----------|------------|
| D1 | `release()` 可被任意调用者释放任意层 | 新增 `LockToken` dataclass；`acquire`/`acquire_or_update`/`acquire_strict` 返回 `LockToken`；`release` 优先接受 token，旧 `release(LockLayer)` 仍兼容但记录 warning。 | roadmap 3.2 D1 | `test_token_release`、`test_layer_release_warning` 通过。 |
| D2 | 控制锁/暂停全局 OR，低优先级可持续锁定 | `_recompute` 中 `lock_controls` 与 `is_paused` 改为按优先级仲裁：高优先级置位后低优先级不再覆盖。 | roadmap 3.2 D2 | `test_priority_controls_pause` 通过；AGENTS.md 语义描述已同步更新。 |
| D3 | 过期锁永久留在 `_locks` | `_recompute` 开始时清理 `expires_at > 0` 且已过期、且非永久的锁。 | roadmap 3.2 D3 | `test_expired_lock_cleanup` 通过。 |
| D4 | `acquire` 原地修改传入 `LockRequest` | 新增 `_with_expires_at`，使用 `dataclasses.replace()` 复制请求后再设置 `expires_at`。 | roadmap 3.2 D4 | `test_acquire_does_not_mutate_request` 通过。 |
| D5 | `TRANSIENT` 层状态互相覆盖 | `apply_transient_state` 先读取现有 `TRANSIENT` 请求，合并布尔值后再 `acquire_or_update`。 | roadmap 3.2 D5 | `test_transient_merge` 通过。 |

**批次 D 自验证**：

```bash
python3 -m pytest tests/test_lock_manager.py tests/test_game_scene_facade.py -v   # 31 passed
python3 -m pytest tests/ -v                                                        # 138 passed（当时基线）
python3 -m ruff check .                                                            # All checks passed
python3 -m compileall -q airwar main.py                                            # 通过
```

---

### 4.3 批次 E：帧时间、视口、输入边界

**修复时间**：2026-07-12  
**优先级**：中  
**涉及文件**：`airwar/game/frame_context.py`、`airwar/game/scaled_viewport.py`、`airwar/input/input_handler.py`、`tests/test_frame_context.py`、`tests/test_scaled_viewport.py`、`tests/test_input_handler.py`

| 编号 | 问题 | 修复动作 | 修复依据 | 自验证结果 |
|------|------|----------|----------|------------|
| E1 | `FrameContext` 非法 dt 未处理 | `FixedStepAccumulator.__init__` 限制 `fixed_delta_seconds` 在 `[1/1200, 1/10]` 且有限；`advance()` 对负数/NaN/Inf 抛 `ValueError`。 | roadmap 3.3 E1 | `test_invalid_delta_raises`、`test_fixed_delta_bounds` 通过。 |
| E2 | `ScaledViewport` 构造参数可非正且 `logical_size` 可变 | `__init__` 校验宽高为正；`logical_size` 改为 property，setter 同步重建 surface 并再次校验。 | roadmap 3.3 E2 | `test_non_positive_size_rejected`、`test_logical_size_property_rebuilds_surface` 通过。 |
| E3 | `InputHandler` 协议不完整、绑定未校验 | 抽象基类新增 `tick()` 抽象方法；`DEFAULT_BINDINGS` 深拷贝避免共享；`__init__` 校验键值有效。 | roadmap 3.3 E3 | `test_tick_protocol`、`test_default_bindings_not_shared`、`test_invalid_bindings_rejected` 通过。 |
| E4 | 对向键冲突行为未文档 | 在 `get_movement_direction()` docstring 中明确说明“后赋值覆盖”。 | roadmap 3.3 E4 | 代码审查通过；新增测试读取 docstring 确认。 |
| E5 | 外部直接改 `logical_size` 破坏一致性 | `logical_size` 私有化后改为 property，docstring 指明外部 resize 应调用 `update()`。 | roadmap 3.3 E5 | 无直接赋值使用点；`ruff`/`compileall` 通过。 |

**批次 E 自验证**：

```bash
python3 -m pytest tests/test_frame_context.py tests/test_scaled_viewport.py tests/test_input_handler.py -v   # 29 passed
python3 -m ruff check .                                                                                       # All checks passed
python3 -m compileall -q airwar main.py                                                                       # 通过
```

---

### 4.4 批次 F：实体与战斗系统边界

**修复时间**：2026-07-12  
**优先级**：中  
**涉及文件**：`airwar/entities/base.py`、`airwar/entities/bullet.py`、`airwar/entities/enemy/boss/boss.py`、`airwar/entities/enemy/enemy.py`、`airwar/entities/player.py`、`airwar/entities/player_state.py`、`airwar/game/managers/boss_manager.py`、`airwar/game/managers/bullet_manager.py`、`airwar/game/managers/game_loop_manager.py`，以及新增测试文件。

| 编号 | 问题 | 修复动作 | 修复依据 | 自验证结果 |
|------|------|----------|----------|------------|
| F1 | `Entity` 基类接口不统一 | `Entity` 新增抽象 `take_damage(self, damage: int)` 与默认 `kill()`；`Bullet` 补实现。 | roadmap 3.4 F1 | `tests/test_entity_interface.py` 通过。 |
| F2 | Boss 狂暴除零保护顺序 | 代码中 `max_health <= 0` guard 已在除法前，新增测试覆盖。 | roadmap 3.4 F2 | `tests/test_boss.py::test_max_health_zero_does_not_raise_on_enrage_check` 通过。 |
| F3 | `BulletManager` data=None 子弹破坏 buffer | 将 `data is None` 检查提前到 `active_bullets.append` 之前。 | roadmap 3.4 F3 | `tests/test_bullet_manager.py` 通过。 |
| F4 | `GameLoopManager` 依赖未校验 | `__init__` 末尾对 8 个非可选依赖做 `None` 检查，缺失抛 `ValueError`。 | roadmap 3.4 F4 | `tests/test_game_loop_manager.py` 通过。 |
| F5 | `BossManager.clear_boss()` 绕过计时器 | `BossManager.clear_boss()` 改为调用 `SpawnController.clear_boss()`。 | roadmap 3.4 F5 | `tests/test_boss.py::test_clear_boss_resets_spawn_timer` 通过。 |
| F6 | 普通敌机 `update()` 未传 `player_pos` | `_update_entities()` 从 `player.rect.center` 取位置传入 `enemy.update(...)`。 | roadmap 3.4 F6 | `tests/test_game_loop_manager.py` 通过。 |
| F7 | Boss 死代码未清理 | 删除未调用的 `_update_enrage_transition`、`_update_enrage_release_hold`、`_update_enrage_return`、`_start_enrage_return`。 | roadmap 3.4 F7 | `tests/test_boss.py::test_boss_dead_methods_removed` 通过。 |
| F8 | `PlayerState.force_substate()` 无安全模式 | 增加 `validate: bool = True`；`validate=False` 时记录 warning。 | roadmap 3.4 F8 | `tests/test_player_state.py` 通过。 |
| F9 | `Player.enter_boost()` 静默吞异常 | 仅对“已在 boost”静默，其余 `IllegalPlayerTransition` 记录 warning。 | roadmap 3.4 F9 | `tests/test_player_state.py` 通过。 |
| F10 | `Enemy.set_difficulty` 速度倍率未使用 | Python fallback 路径中 `_update_movement()` 对策略速度应用 `_difficulty_multiplier`。 | roadmap 3.4 F10 | `tests/test_enemy.py` 通过。 |

**批次 F 自验证**：

```bash
python3 -m pytest tests/test_boss.py tests/test_bullet_manager.py tests/test_enemy.py tests/test_entity_interface.py tests/test_game_loop_manager.py tests/test_player_state.py -v   # 25 passed
python3 -m ruff check .                                                                                                                                                               # All checks passed
python3 -m compileall -q airwar main.py                                                                                                                                               # 通过
```

---

### 4.5 批次 G：Rust ↔ Python 边界一致

**修复时间**：2026-07-12  
**优先级**：中  
**涉及文件**：`airwar_core/src/bullets.rs`、`airwar_core/src/particles.rs`、`airwar_core/src/sprites.rs`、`airwar_core/src/starfield.rs`、`airwar/core_bindings.py`、`tests/test_core_bindings.py`

| 编号 | 问题 | 修复动作 | 修复依据 | 自验证结果 |
|------|------|----------|----------|------------|
| G1 | bullet id 类型 Rust `i64` / Python `u64` 不一致 | Rust 注释统一为 `i64`；Python fallback format 由 `<Q` 改为 `<q`；修正解包变量数。 | roadmap 3.5 G1 | `test_negative_id_roundtrip_rust_and_fallback` 通过。 |
| G2 | sprite 非正输入 Rust/fallback 返回不一致 | Python fallback 5 个 sprite 函数增加 `width/radius <= 0` 检查，返回 `b''`；Rust 同步返回 `Bound<PyBytes>` 空 bytes。 | roadmap 3.5 G2 | `TestSpriteNonPositiveInput` 多参数组合通过。 |
| G3 | 颜色越界 Rust 抛 OverflowError | Rust 中 RGB 参数改为 `i32` 并在函数内 `clamp(0, 255)`；fallback 也在赋值前 clamp。 | roadmap 3.5 G3 | `test_create_glow_circle_no_overflow`、`test_batch_render_particles_color_clamped` 通过。 |
| G4 | `compute_starfield_positions` 负 phase 语义不一致 | Rust 由截断取模改为欧几里得取模 `phase.rem_euclid(len as i32) as usize`。 | roadmap 3.5 G4 | `test_negative_phase_matches_fallback` 通过。 |
| G5 | `core_bindings.py` 只检查函数存在 | 新增 `_RUST_SIGNATURES` 字典，加载时用 `inspect.signature` 校验参数数量，ABI 不匹配时回退 fallback 并记录 warning。 | roadmap 3.5 G5 | `test_abi_mismatch_falls_back` 通过。 |

**批次 G 自验证**：

```bash
cd airwar_core && python3 -m maturin develop --release && cd ..
python3 -m pytest tests/test_core_bindings.py -v   # 18 passed
python3 -m pytest tests/ -v                         # 192 passed, 1 warning
python3 -m ruff check .                             # All checks passed
python3 -m compileall -q airwar main.py             # 通过
```

> 注：修复过程中发现系统 `python3` 加载的是旧版非 editable `airwar_core`，导致测试失败。已通过 `python3 -m pip install --force-reinstall -e ./airwar_core` 重新安装为 editable，确保系统 python3 与 `.venv` 均使用最新 Rust 扩展。

---

### 4.6 批次 H：杂项与可维护性

**修复时间**：2026-07-12  
**优先级**：低  
**涉及文件**：`airwar/i18n/__init__.py`、`airwar/scenes/scene.py`、`airwar/scenes/game_scene.py`、`airwar/game/scene_director.py`、`airwar/scenes/game_scene_event_dispatcher.py`、`airwar/scenes/scene_homecoming_dispatcher.py`、`tests/test_i18n.py`、`tests/test_event_dispatchers.py`

| 编号 | 问题 | 修复动作 | 修复依据 | 自验证结果 |
|------|------|----------|----------|------------|
| H1 | i18n `set_locale()` 路径遍历 | `set_locale()` 使用正则 `^[A-Za-z0-9_]+$` 校验 locale。 | roadmap 3.6 H1 | `tests/test_i18n.py` 通过；`set_locale("../../etc/passwd")` 抛 `ValueError`。 |
| H2 | `SceneManager.register()` 不校验类型与覆盖 | `register()` 校验 `isinstance(scene, Scene)`，新增 `overwrite: bool = True`；非 Scene 抛 `TypeError`，未授权覆盖抛 `ValueError`。（批次 C 已同步实现） | roadmap 3.6 H2 | `tests/test_scene_manager.py` 通过。 |
| H3 | `GameScene` 过时注释与重复赋值 | 删除模块 docstring 中已不存在的 `__setattr__ hook` 描述；简化 `set_homecoming_coordinator()`，去掉重复赋值。 | roadmap 3.6 H3 | 代码审查通过；测试通过。 |
| H4 | `SceneDirector` 每次新建 `LeaderboardService` | `__init__` 中创建并保存实例，`_submit_leaderboard_score()` 复用。 | roadmap 3.6 H4 | 相关测试通过；`ruff`/`compileall` 通过。 |
| H5 | 事件分发异常中断同帧处理 | `GameSceneEventDispatcher.dispatch()` 与 `SceneHomecomingDispatcher` 各回调增加 `try/except` 隔离，记录日志后继续。 | roadmap 3.6 H5 | `tests/test_event_dispatchers.py` 通过。 |

**批次 H 自验证**：

```bash
python3 -m pytest tests/test_i18n.py tests/test_event_dispatchers.py tests/test_scene_manager.py -v   # 通过
python3 -m pytest tests/ -v                                                                           # 149 passed（当时基线）
python3 -m ruff check .                                                                               # All checks passed
python3 -m compileall -q airwar main.py                                                               # 通过
```

---

## 5. 全量回归验证

### 5.1 自动检查

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 全量单元测试 | `python3 -m pytest tests/ -q` | **192 passed, 1 warning** |
| 代码风格 | `python3 -m ruff check .` | **All checks passed** |
| 字节码编译 | `python3 -m compileall -q airwar main.py` | **通过** |
| Rust 扩展编译 | `cd airwar_core && python3 -m maturin develop --release` | **通过** |
| 游戏启动 | `./run.sh --debug` 运行 20 秒 | **正常启动，未崩溃** |

### 5.2 关键端到端边界用例

| 用例 | 操作 | 结果 |
|------|------|------|
| FrameContext 非法 dt | `FixedStepAccumulator().advance(-0.1/nan/inf, simulate=True)` | 均抛出 `ValueError` |
| ScaledViewport 非正尺寸 | `ScaledViewport(0, 1080)` / `(-1, 1080)` / `(1920, 0)` | 均抛出 `ValueError` |
| i18n 路径遍历 | `Translator().set_locale("../../etc/passwd")` | 抛出 `ValueError` |
| Boss max_health=0 | `Boss(100,100,BossData(health=0))._trigger_enrage_if_needed()` | 不抛 `ZeroDivisionError` |
| Rust 与 fallback 边界 | `tests/test_core_bindings.py` 全部用例 | 通过 |

### 5.3 警告说明

全量测试中仅存在 1 条与本次修复无关的弃用警告：

```text
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

该警告来自 `fastapi.testclient` 对 `httpx` 的版本提示，不影响功能与稳定性，未引入新的严重问题。

---

## 6. 遗留问题与说明

### 6.1 未在本轮手动执行的端到端项

以下 `remediation-roadmap.md` 6.1 节中的端到端项已通过单元测试覆盖，或因环境限制未做人工交互验证：

| 项 | 状态 | 说明 |
|----|------|------|
| 构造损坏 `users.json` 自动恢复 | 已修复（DATA-1） | 对应代码已在 `database.py` 中，单元测试覆盖。 |
| 多进程同时写入 `users.json` | 已修复（DATA-2） | 使用 `tempfile.mkstemp` + `os.replace`，单元测试覆盖。 |
| 排行榜 `limit=101` 返回 422 | 已修复（SEC-3） | 服务端 Pydantic 模型已限制，测试覆盖。 |
| 非允许来源 CORS preflight 被拒绝 | 已修复（SEC-2） | 服务端 CORS 已限制，测试覆盖。 |
| 主循环注入单帧异常不崩溃 | 已修复（C1） | `tests/test_scene_switcher.py` 覆盖。 |
| 子场景 `update()` 异常 `exit()` 仍被调用 | 已修复（C3） | `tests/test_scene_switcher.py` 覆盖。 |
| LockManager 高优先级压制低优先级 | 已修复（D2） | `tests/test_lock_manager.py` 覆盖。 |
| 过期锁自动清理 | 已修复（D3） | `tests/test_lock_manager.py` 覆盖。 |
| 非法 pygame 键绑定抛 `ValueError` | 已修复（E3） | `tests/test_input_handler.py` 覆盖。 |
| `BulletManager` data=None 不破坏 buffer | 已修复（F3） | `tests/test_bullet_manager.py` 覆盖。 |
| Rust 与 fallback 非法 sprite 输入均返回空 bytes | 已修复（G2） | `tests/test_core_bindings.py` 覆盖。 |

### 6.2 环境相关说明

- 修复过程中发现系统 `python3` 与 `.venv` 中 `airwar_core` 版本不一致。已通过重新安装 editable 版本解决，确保 `python3 -m pytest tests/` 与 `.venv/bin/python -m pytest tests/` 均返回 **192 passed**。
- `.venv` 中缺少 `httpx`，已由批次 G 修复代理安装，使 `tests/test_leaderboard_server.py` 可正常收集与执行。

### 6.3 无新增严重问题

- 全量测试无失败。
- `ruff check .` 全绿。
- `compileall` 通过。
- `./run.sh --debug` 20 秒内未崩溃。

---

## 7. 审批与归档

### 7.1 质量门禁检查

| 门禁项 | 状态 |
|--------|------|
| 所有高优先级问题（C、D 批次）修复并验证通过 | ✅ 通过 |
| 修复后无新增严重问题 | ✅ 通过（192 passed，ruff 全绿，compileall 通过） |
| 报告完整可追溯 | ✅ 通过（本报告含逐项修复记录与验证结果） |
| 获得审批确认 | ⏳ 待人工审批 |

### 7.2 建议审批意见

- 建议批准本次全量修复。
- 批准后可执行独立 commit：每个批次一次 commit（C、D、E、F、G、H），便于后续回滚。
- 如审批通过，请归档本报告至 `docs/audits/` 并同步更新 `remediation-roadmap.md` 中的“当前状态速览”。

---

## 附录 A：新增/修改测试文件清单

| 文件 | 说明 |
|------|------|
| `tests/test_scene_switcher.py` | 新增：帧错误隔离、子场景生命周期 |
| `tests/test_input_handler.py` | 新增：绑定校验、tick 协议、默认绑定不可变 |
| `tests/test_entity_interface.py` | 新增：Entity 抽象接口 |
| `tests/test_bullet_manager.py` | 新增：data=None 子弹跳过 |
| `tests/test_boss.py` | 新增：max_health=0、clear_boss、死代码清理 |
| `tests/test_game_loop_manager.py` | 新增：依赖校验、player_pos 传递 |
| `tests/test_player_state.py` | 新增：force_substate 安全模式、boost 非法转换 |
| `tests/test_enemy.py` | 新增：fallback 路径速度倍率 |
| `tests/test_core_bindings.py` | 新增：Rust/fallback 边界一致、ABI 不匹配回退 |
| `tests/test_i18n.py` | 新增：locale 路径遍历防护 |
| `tests/test_event_dispatchers.py` | 新增：事件分发异常隔离 |
| `tests/test_scene_manager.py` | 扩展：register 类型校验、switch 异常回滚 |
| `tests/test_lock_manager.py` | 扩展：token、优先级仲裁、过期清理、TRANSIENT 合并 |
| `tests/test_frame_context.py` | 扩展：非法 dt、fixed_delta 边界 |
| `tests/test_scaled_viewport.py` | 扩展：非正构造、logical_size property |

---

## 附录 B：关键代码位置索引

| 批次 | 关键文件 | 关键函数/类 |
|------|----------|-------------|
| C | `airwar/game/scene_director_components/scene_switcher.py` | `_run_scene_loop`, `_run_subscene`, `on_frame_error` |
| C | `airwar/scenes/scene.py` | `SceneManager.switch`, `SceneManager.register` |
| D | `airwar/game/systems/lock_manager.py` | `LockToken`, `LockManager._recompute`, `apply_transient_state` |
| E | `airwar/game/frame_context.py` | `FixedStepAccumulator` |
| E | `airwar/game/scaled_viewport.py` | `ScaledViewport.logical_size` property |
| E | `airwar/input/input_handler.py` | `InputHandler.tick`, `PygameInputHandler.__init__` |
| F | `airwar/entities/base.py` | `Entity.take_damage`, `Entity.kill` |
| F | `airwar/entities/enemy/boss/boss.py` | `_trigger_enrage_if_needed` |
| F | `airwar/game/managers/bullet_manager.py` | `_update_bullets_batch` |
| F | `airwar/game/managers/game_loop_manager.py` | `__init__`, `_update_entities` |
| G | `airwar/core_bindings.py` | `_RUST_SIGNATURES`, sprite fallback |
| G | `airwar_core/src/sprites.rs` | `create_single_bullet_glow` 等 |
| H | `airwar/i18n/__init__.py` | `Translator.set_locale` |
| H | `airwar/scenes/game_scene_event_dispatcher.py` | `dispatch` |
| H | `airwar/scenes/scene_homecoming_dispatcher.py` | `_safe_call` |

---

*报告结束。*
