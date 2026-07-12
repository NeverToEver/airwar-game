# Air War 遗留问题修复路线图

> 本文档基于以下审计报告整理：
> - `docs/audits/review-findings-main-interfaces-2026-07-11-0422.md`（38 项发现）
> - `docs/audits/remediation-plan-main-interfaces-2026-07-11-0422.md`（修复计划）
> - `docs/audits/2026-07-10_runtime-error-remediation_P1-P15.md`（运行时修复记录）
>
> 目标：将分散的审计结论合并为一份**可逐项执行**的修复路线图。

---

## 1. 当前状态速览

| 类别 | 数量 | 状态 |
|------|------|------|
| Critical（数据/安全/崩溃） | 5 | **已修复 5/5** |
| Major（稳定性/架构/边界） | 16 | **已修复 10/16** |
| Minor（可维护性/模式） | 14 | **待修复 13/14**（1 项已修复） |
| Nit | 3 | **待修复 3/3** |

### 1.1 已完成的修复

以下问题在最近提交中已解决，无需重复处理：

| 编号 | 问题 | 验证位置 |
|------|------|----------|
| DATA-1 | `UserDB` 读取损坏 JSON 时直接抛错 | `airwar/utils/database.py:124-143` 已备份并重置 |
| DATA-2 | 持久化使用固定 `.tmp` 文件名，多进程冲突 | `database.py:147-162`、`persistence_manager.py:81-95` 已用 `mkstemp` |
| SEC-1 | 缺失 `salt` 时回退到 `user_id` | `database.py:233-236` 已拒绝验证 |
| SEC-2 | 服务端 CORS `allow_origins=["*"]` | `leaderboard/server.py:47-53` 已限制来源 |
| SEC-3 | `/leaderboard?limit=` 无上限 | `leaderboard/server.py:61` 已限制 `1–100` |
| CFG-1/2 | 排行榜 `timeout`/`URL` 非法值 | `leaderboard/config.py` 已校验 |
| PAT-13 | `submit_score` 对 `bool` 处理与注释不符 | `database.py` 已明确拒绝 |
| C1-C5 | 主循环与场景生命周期异常隔离 | `scene_switcher.py` / `scene.py` / `game_scene.py` / `game_scene_updater.py` 已加防御 |

### 1.2 待修复问题分布

```text
C 批次：主循环/场景生命周期  ──► 0 项 Major（已修复 5/5）
D 批次：LockManager          ──► 4 项 Major + 1 Minor
E 批次：帧时间/视口/输入     ──► 1 Major + 4 Minor
F 批次：实体/战斗系统        ──► 6 Major + 3 Minor + 1 Nit
G 批次：Rust ↔ Python 边界   ──► 0 项 Major（已修复 5/5）
H 批次：杂项/可维护性        ──► 4 Minor + 2 Nit
```

---

## 2. 通用修复原则

1. **最小改动**：只修当前问题，不借机重构无关逻辑。
2. **测试先行**：每个修复项必须伴随测试，或至少不破坏现有 `62 passed`。
3. **Rust/Python 同步**：修改 Rust 扩展时，同步更新 `airwar/core_bindings.py` fallback 与 `airwar_core.pyi` 存根。
4. **文档同步**：修改 `AGENTS.md` 相关约定时同步更新。
5. **独立提交**：每个批次一次独立 commit，便于回滚。

### 2.1 每次提交前必须执行

```bash
python3 -m pytest tests/ -v
python3 -m ruff check .
python3 -m compileall -q airwar main.py
```

若涉及 Rust 扩展：

```bash
cd airwar_core && python3 -m maturin develop --release && cd ..
```

---

## 3. 分批次修复指引

### 批次 C：主循环与场景生命周期异常隔离
**优先级：高** | **目标：让游戏在单帧异常时不直接退出**

#### C1 — 主循环帧级异常隔离 ✅
- **问题**：`_run_scene_loop` 中 `update/render/flip/handle_events` 任一异常直接退出进程。
- **文件**：`airwar/game/scene_director_components/scene_switcher.py`
- **修复动作**：
  1. 在帧循环中把 `handle_events`、`update`、`render`、`flip` 分别包 `try/except`。
  2. 维护连续失败计数器，超过阈值（5 帧）再退出循环。
  3. 异常时调用场景可选的 `on_frame_error()` 钩子。
- **验收方式**：注入一个会抛异常的 `update()`，确认游戏跳过坏帧并记录日志；连续异常超过阈值后退出。

#### C2 — `SceneManager.switch()` 异常回滚 ✅
- **问题**：先设置 `_current_scene` 再调用 `enter()`，异常后状态不一致。
- **文件**：`airwar/scenes/scene.py`
- **修复动作**：
  1. 保存 `old_scene` / `old_name`。
  2. `try` 中调用 `enter()`。
  3. 异常时恢复旧场景，并尝试重新 `enter()` 旧场景。
- **验收方式**：注册一个 `enter()` 会抛异常的场景，切换时确认原场景恢复。

#### C3 — 子场景 enter/exit 使用 try/finally ✅
- **问题**：子场景循环异常时 `exit()` 可能不被调用。
- **文件**：`airwar/game/scene_director_components/scene_switcher.py`
- **修复动作**：在 `_show_settings_menu` / `_show_pause_menu` / `_show_exit_confirm` / `_handle_game_over` 中用 `try/finally` 包裹 `_run_scene_loop`，确保 `exit()` 被调用。
- **验收方式**：注入异常到子场景 `update()`，确认 `exit()` 仍被调用。

#### C4 — 替换 assert 为显式检查 ✅
- **问题**：`assert` 在 `-O` 模式下被移除。
- **文件**：
  - `airwar/game/scene_director_components/scene_switcher.py:46`
  - `airwar/scenes/game_scene_updater.py:364-370`
- **修复动作**：改为显式 `if ...: raise RuntimeError(...)`。

#### C5 — `game_scene.py` 缓存清理异常处理 ✅
- **问题**：使用 `except AttributeError/ImportError: pass` 静默吞异常。
- **文件**：`airwar/scenes/game_scene.py:703-747`
- **修复动作**：至少记录 `logger.debug`，区分预期清理失败与意外错误。

---

### 批次 D：LockManager 接口与语义
**优先级：高** | **目标：锁系统符合优先级仲裁语义**

#### D1 — `release()` 增加 owner/cookie 校验
- **问题**：任何调用者都能释放任意层。
- **文件**：`airwar/game/systems/lock_manager.py`
- **修复动作**：
  1. 新增 `LockToken` dataclass。
  2. `acquire` / `acquire_or_update` / `acquire_strict` 返回 `LockToken`。
  3. `release` 优先接受 `LockToken`，兼容旧 layer 调用但记录 warning。
- **验收方式**：用 token 释放成功；用 layer 释放时记录 warning。

#### D2 — 控制锁/暂停按优先级仲裁
- **问题**：当前控制锁和暂停是全局 OR，低优先级层可持续锁定。
- **文件**：`airwar/game/systems/lock_manager.py`
- **修复动作**：`_recompute` 中只取最高优先级层的 `lock_controls` 和 `is_paused`。
- **验收方式**：高优先级层存在时压制低优先级层；高优先级释放后低优先级生效。

#### D3 — 自动清理过期锁
- **问题**：`expires_at` 只用于计算 timer，锁对象永久留在 `_locks`。
- **修复动作**：`_recompute` 遍历前移除已过期且非永久的锁。
- **验收方式**：创建带 `expires_at` 的锁，时间到后调用 `refresh()`，确认 `is_locked` 为 `False`。

#### D4 — `acquire` 不原地修改传入的 `LockRequest`
- **问题**：设置 `expires_at` 时修改了调用者传入的实例。
- **修复动作**：先用 `dataclasses.replace()` 复制再修改。

#### D5 — 拆分 `TRANSIENT` 层语义
- **问题**：`apply_transient_state(paused=True)` 可能被 `apply_transient_state(invincible=True)` 覆盖。
- **修复动作**：更新前读取现有 `TRANSIENT` 请求，合并布尔值后再 `acquire_or_update`。

---

### 批次 E：帧时间、视口、输入边界
**优先级：中** | **目标：边界输入不导致异常或状态不一致**

#### [x] E1 — `FrameContext` 校验非法 dt
- **问题**：负数 dt 静默取 0；`NaN/Inf` 未处理；极小 `fixed_delta` 可导致步数爆炸。
- **文件**：`airwar/game/frame_context.py`
- **修复动作**：
  1. `advance` 中校验 `delta_seconds` 为有限非负数，否则抛 `ValueError`。
  2. `__init__` 中限制 `fixed_delta_seconds` 范围（如 `1/1200 ~ 1/10`）。
- **验收方式**：传入 `-0.1`、`nan`、`inf` 均抛 `ValueError`。

#### [x] E2 — `ScaledViewport` 参数保护与不可变 logical_size
- **问题**：`logical_size` 是公开可变属性；构造参数可非正。
- **文件**：`airwar/game/scaled_viewport.py`
- **修复动作**：
  1. `__init__` 校验宽高为正。
  2. `logical_size` 改为 property，setter 同步重建 surface。
- **验收方式**：构造 `ScaledViewport(0, 1080)` 抛 `ValueError`。

#### [x] E3 — `InputHandler` 协议与绑定校验
- **问题**：`tick()` 不在协议中；默认绑定是可变类属性；绑定值未校验。
- **文件**：`airwar/input/input_handler.py`
- **修复动作**：
  1. 抽象基类加入 `tick()` 抽象方法。
  2. `DEFAULT_BINDINGS` 改为不可变副本或每次复制。
  3. `__init__` 校验键值在 `pygame.key.get_pressed()` 范围内。
- **验收方式**：非法绑定抛 `ValueError`。

#### [x] E4 — 对向键冲突行为文档化
- **问题**：`PygameInputHandler` 对向键采用"后赋值覆盖"，无文档。
- **修复动作**：在 `get_movement_direction()` 注释中说明行为，或改为对向键归零。

#### [x] E5 — `ScaledViewport` 外部 resize 统一走 `update()`
- **问题**：外部直接改 `logical_size` 破坏一致性。
- **修复动作**：将 `logical_size` 设为 property 后，外部 resize 必须调用 `update(display_w, display_h)`。

---

### 批次 F：实体与战斗系统边界
**优先级：中** | **目标：统一接口、消除边界除零与不同步**

#### F1 — 统一 `Entity` 基类接口
- **问题**：`take_damage` / `kill` 未在基类统一，多态调用困难。
- **文件**：`airwar/entities/base.py`
- **修复动作**：在 `Entity` 中声明 `take_damage` 抽象方法和默认 `kill()` 实现。
- **验收方式**：未实现抽象方法的子类无法实例化；`Player/Enemy/Boss` 签名统一。

#### F2 — Boss 狂暴除零保护顺序
- **问题**：`max_health <= 0` 的 guard 在除法之后。
- **文件**：`airwar/entities/enemy/boss/boss.py:486-489`
- **修复动作**：将 `max_health <= 0` 判断提前到除法之前。
- **验收方式**：构造 `max_health=0` 的 Boss，调用 `_trigger_enrage_if_needed` 不抛异常。

#### F3 — `BulletManager` batch buffer 同步
- **问题**：`data is None` 检查在 `active_bullets.append` 之后。
- **文件**：`airwar/game/managers/bullet_manager.py:174-192`
- **修复动作**：将 `data is None` 检查提前到 append 之前。
- **验收方式**：构造 `data=None` 的子弹，确认不加入 `active_bullets`，buffer 索引正确。

#### F4 — `GameLoopManager` 依赖校验
- **问题**：构造时未校验 8 个依赖，运行时才抛 `AttributeError`。
- **文件**：`airwar/game/managers/game_loop_manager.py:123-141`
- **修复动作**：`__init__` 末尾对非可选依赖做 `None` 检查，缺失时抛 `ValueError`。
- **验收方式**：传入 `None` 依赖时构造即抛 `ValueError`。

#### F5 — `BossManager.clear_boss()` 走 `SpawnController` 清理路径
- **问题**：直接修改 `SpawnController.boss`，绕过计时器逻辑。
- **文件**：`airwar/game/managers/boss_manager.py:143-145`
- **修复动作**：在 `SpawnController` 提供 `clear_boss()` 方法，`BossManager` 调用它。
- **验收方式**：调用后确认 `_boss_spawn_timer` 被重置。

#### F6 — 普通敌机 `update()` 传入 `player_pos`
- **问题**：追踪类敌机拿不到玩家位置。
- **文件**：`airwar/game/managers/game_loop_manager.py:424`
- **修复动作**：从 `player.rect.center` 获取位置并传入 `enemy.update(...)`。
- **验收方式**：运行 aggressive 敌机策略，确认能追踪玩家。

#### F7 — 清理 Boss 死代码
- **问题**：`_update_enrage_transition`、`_update_enrage_release_hold`、`_update_enrage_return` 未被调用。
- **文件**：`airwar/entities/enemy/boss/boss.py:584-606`
- **修复动作**：确认无调用点后删除。

#### F8 — `PlayerState.force_substate()` 增加安全模式
- **问题**：完全绕过合法边检查，损坏存档可置玩家于非法状态。
- **文件**：`airwar/entities/player_state.py:209-211`
- **修复动作**：增加 `validate: bool = True` 参数，存档恢复时 `validate=False` 并记录 warning。

#### F9 — `Player.enter_boost()` 不静默吞异常
- **问题**：对所有 `IllegalPlayerTransition` 静默处理。
- **文件**：`airwar/entities/player.py:269-274`
- **修复动作**：仅对已知可忽略条件（如已在 boost）静默处理，其他情况记录 warning。

#### F10 — `Enemy.set_difficulty` 速度倍率未使用
- **问题**：`_difficulty_multiplier` 设置后未应用到移动。
- **文件**：`airwar/entities/enemy/enemy.py`
- **修复动作**：在 `_update_movement` 中将倍率应用到 `self._rust_params["speed"]` 或策略速度。

---

### 批次 G：Rust ↔ Python 边界一致
**优先级：中** | **目标：Rust 与 Python fallback 行为一致**

#### G1 — 统一 bullet id 类型 ✅
- **问题**：Rust 注释 `u64`，实现 `i64`，Python fallback `<Q`（u64）。
- **文件**：`airwar_core/src/bullets.rs`、`airwar/core_bindings.py:641`
- **修复动作**：统一为 `i64`；Rust 注释与读取改为 `i64`；Python fallback 改为 `<q`。
- **验收方式**：Rust 与 fallback 对同一 buffer 返回相同 id。

#### G2 — sprite 非正输入统一返回空 bytes ✅
- **问题**：Rust 返回空 bytes，fallback 仍生成极小 surface。
- **文件**：`airwar_core/src/sprites.rs`、`airwar/core_bindings.py`
- **修复动作**：Python fallback 对每个 sprite 函数在 `width/radius <= 0` 时返回 `b''`；Rust 侧改为返回 `PyBytes` 以保证类型一致。
- **验收方式**：参数 `width=-5` 时两者均返回 `b''`。

#### G3 — 颜色越界统一 clamp ✅
- **问题**：Rust 抛 `OverflowError`，fallback 静默截断。
- **文件**：`airwar_core/src/particles.rs`、`airwar_core/src/sprites.rs`、`airwar/core_bindings.py`
- **修复动作**：Rust 侧对 sprite/particle 颜色参数改为 `i32` 并 `clamp(0, 255)`；Python fallback 在 `_set_pixel` 与 `batch_render_particles` 中同步 clamp。
- **验收方式**：传入 `r=300` 不抛异常且结果为 255。

#### G4 — `compute_starfield_positions` 负 phase 语义一致 ✅
- **问题**：Rust 截断为 `usize` 后取模，Python 使用数学取模。
- **文件**：`airwar_core/src/starfield.rs:68`、`airwar/core_bindings.py:253`
- **修复动作**：Rust 中使用欧几里得取模 `rem_euclid`。
- **验收方式**：负 phase 时 Rust 与 Python 返回相同索引。

#### G5 — `core_bindings.py` 签名/ABI 校验 ✅
- **问题**：只检查函数是否存在，无法检测签名不匹配。
- **文件**：`airwar/core_bindings.py:81-123`
- **修复动作**：维护 `_RUST_SIGNATURES` 字典，加载时用 `inspect.signature` 粗略校验参数数量。
- **验收方式**：用 mock 模拟 ABI 不匹配，确认切到 fallback。

---

### 批次 H：杂项与可维护性
**优先级：低** | **目标：清理代码异味、补全测试**

#### H1 — i18n `set_locale()` 路径遍历防护
- **问题**：直接把 locale 拼接到文件名。
- **文件**：`airwar/i18n/__init__.py:108`
- **修复动作**：校验 locale 只含字母、数字、下划线。
- **验收方式**：`set_locale("../../etc/passwd")` 抛 `ValueError`。

#### H2 — `Scene` 接口收紧
- **问题**：`register()` 不校验 scene 类型，也不阻止覆盖。
- **文件**：`airwar/scenes/scene.py`
- **修复动作**：`register()` 校验 scene 为 `Scene` 实例，并可选 `overwrite=True`。

#### H3 — `GameScene` 注释与死代码
- **问题**：注释提到已不存在的 `__setattr__` hook。
- **文件**：`airwar/scenes/game_scene.py:15,373-396`
- **修复动作**：删除过时注释；检查 `set_homecoming_coordinator` 中重复赋值。

#### H4 — `SceneDirector` 复用 `LeaderboardService`
- **问题**：每次调用都新建实例。
- **文件**：`airwar/game/scene_director.py:248-256`
- **修复动作**：在 `__init__` 中创建实例并复用。

#### H5 — 事件分发异常隔离
- **问题**：硬编码方法调用链，任一分支异常会中断同帧后续事件处理。
- **文件**：`airwar/scenes/game_scene_event_dispatcher.py`、`scene_homecoming_dispatcher.py`
- **修复动作**：在分发循环中捕获并记录异常，不中断同帧其他事件。

---

## 4. 推荐执行顺序

```
批次 C（主循环异常隔离）
  │
  ▼
批次 D（LockManager）
  │
  ▼
批次 E（帧时间/输入） ── 可并行 ──► 批次 F（实体/战斗）
  │                                  │
  ▼                                  ▼
批次 G（Rust/Python 边界）           批次 H（杂项）
  │                                  │
  └──────────────┬───────────────────┘
                 ▼
            全量回归测试
```

**为什么这样排**：
- C 批次直接影响"游戏会不会闪退"，收益最高。
- D 批次影响暂停/无敌/控制锁等核心玩法状态。
- E/F 批次相互独立，可并行。
- G 批次需要改动 Rust，测试成本最高，放在后面。
- H 批次是代码清理，最后做。

---

## 5. 测试补全清单

每个批次应新增/更新对应测试：

| 批次 | 测试文件 | 覆盖内容 |
|------|----------|----------|
| C | `tests/test_scene_manager.py` | switch 异常回滚、register 类型校验 |
| C | 新增帧错误注入测试 | 单帧异常跳过、连续异常退出 |
| D | `tests/test_lock_manager.py` | owner token、优先级仲裁、过期清理、TRANSIENT 合并 |
| E | `tests/test_frame_context.py` | 非法 dt、NaN/Inf、fixed_delta 边界 |
| E | `tests/test_scaled_viewport.py` | 非正构造、logical_size 不可变 |
| E | 新增 `tests/test_input_handler.py` | 绑定校验、默认绑定不可变 |
| F | 新增 `tests/test_entity_interface.py` | `Entity` 抽象方法 |
| F | 新增 `tests/test_bullet_manager.py` | `data=None` 子弹跳过 |
| F | 新增 `tests/test_boss.py` | `max_health=0`、clear_boss 计时器重置 |
| G | 新增 `tests/test_core_bindings.py` | Rust/fallback 边界行为一致、ABI 不匹配回退 |
| H | 新增 `tests/test_i18n.py` | locale 路径遍历防护 |

---

## 6. 验收清单（每次批次完成后检查）

- [ ] `python3 -m pytest tests/ -v` 全绿
- [ ] `python3 -m ruff check .` 全绿
- [ ] `python3 -m compileall -q airwar main.py` 通过
- [ ] 若改 Rust：`cd airwar_core && maturin develop --release` 通过
- [ ] 启动 `./run.sh --debug`，20 秒内不崩溃
- [ ] 本次修改的审计条目在 `review-findings-main-interfaces-2026-07-11-0422.md` 中标记 `[x]`

### 6.1 全部完成后的端到端验证

- [ ] 构造损坏 `users.json`，启动游戏能自动恢复
- [ ] 多进程同时写入 `users.json`，数据不丢失
- [ ] 启动排行榜服务端，`limit=101` 返回 422
- [ ] 非允许来源的 CORS preflight 被拒绝
- [ ] 主循环中注入单帧异常，游戏不崩溃
- [ ] 子场景 `update()` 异常，`exit()` 仍被调用
- [ ] `LockManager` 高优先级控制锁压制低优先级暂停
- [ ] 过期锁自动清理
- [ ] `FrameContext` 传入 NaN 抛出 `ValueError`
- [ ] `ScaledViewport(0, 0)` 抛出 `ValueError`
- [ ] 非法 pygame 键绑定抛出 `ValueError`
- [ ] `Boss.max_health=0` 不触发除零
- [ ] `BulletManager` 遇到 `data=None` 子弹不破坏 buffer
- [ ] Rust 与 Python fallback 对非法 sprite 输入均返回空 bytes
- [ ] `set_locale("../../etc/passwd")` 抛出 `ValueError`

---

## 7. 风险与回滚策略

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 修改 `LockManager` 优先级语义影响玩法 | 中 | 先新增可选行为，通过特性开关切换；测试通过后再默认启用 |
| 收紧 `FrameContext` 校验暴露现有非法 dt 调用点 | 中 | 先改为记录 warning 不抛异常，观察日志后再升级 |
| Rust 颜色 clamp 改变性能或视觉效果 | 低 | 在 sprite 渲染基准测试中对比帧率；视觉差异需人工确认 |
| 数据库损坏自动重置丢失玩家数据 | 中 | 必须先备份到 `.corrupted.{ts}.bak`，并通知玩家 |
| CORS 限制导致本地开发调试失败 | 低 | 提供 `AIRWAR_LEADERBOARD_CORS_ORIGINS=*` 开发模式 |

### 回滚策略

- 每个批次独立 commit。
- 若某批次引入回归，直接 revert 该 commit。
- 关键修复先合并到 `main`，其他批次可在 feature 分支并行开发。

---

## 8. 文档更新清单

修复过程中如涉及以下约定，请同步更新：

- [ ] `AGENTS.md` 中 `LockManager` 优先级语义描述
- [ ] `README.md` / `README.en.md` 中增加排行榜环境变量说明
- [ ] `.env.example` 中增加新环境变量示例
- [ ] `docs/audits/review-findings-main-interfaces-2026-07-11-0422.md` 中各 issue 修复状态
- [ ] 本文件 `remediation-roadmap.md` 中对应条目标记为已完成
