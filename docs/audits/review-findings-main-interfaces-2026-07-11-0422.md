# Code Review: Air War 主要函数接口与行为健壮性

Date: 2026-07-11
Reviewer: AI Agent (fresh context)

## Summary

- **Files reviewed:** 约 60 个核心文件（架构组件、场景生命周期、实体/Boss、碰撞/子弹管理、持久化、排行榜、Rust 扩展与 Python fallback）
- **Issues found:** 38（5 critical, 16 major, 14 minor, 3 nit）
- **Verification:** `pytest tests/` 62 passed、`ruff check .` 全绿、`compileall -q airwar main.py` 通过

> 本次为静态代码审查，未运行实际游戏流程。所有行号基于审查时 HEAD 状态。

---

## Critical Issues

- [x] **[DATA]** `UserDB` 读取损坏 JSON 时直接抛出 `DatabaseError`，不会自动备份或重置，玩家可能因一次写入中断就无法登录。 — [`airwar/utils/database.py:80-81`](airwar/utils/database.py:80)
- [x] **[DATA]** 持久化使用固定 `.tmp` 文件名且无文件锁，多进程/多实例同时保存时会互相覆盖临时文件，导致数据丢失。 — [`airwar/utils/database.py:86-99`](airwar/utils/database.py:86)、[`airwar/game/mother_ship/persistence_manager.py:80-91`](airwar/game/mother_ship/persistence_manager.py:80)
- [x] **[SEC]** 排行榜服务端 `CORSMiddleware` 配置 `allow_origins=["*"]`、`allow_methods=["*"]`，若服务被意外暴露到公网，任意来源均可调用提交/查询接口。 — [`airwar/leaderboard/server.py:46-52`](airwar/leaderboard/server.py:46)
- [x] **[SEC]** `/leaderboard?limit=` 仅校验为 `int`，未限制最大值，请求 `limit=100000000` 会导致全表扫描与内存耗尽。 — [`airwar/leaderboard/server.py:60`](airwar/leaderboard/server.py:60)
- [x] **[SEC]** `verify_user` 在账户缺失 `salt` 时回退到 `user_id` 作为 salt，大幅降低离线破解难度。 — [`airwar/utils/database.py:149`](airwar/utils/database.py:149)

---

## Major Issues

### 错误处理与稳定性

- [ ] **[ERR]** 主循环对 `update()` / `render()` / `handle_events()` 没有帧级异常隔离，任一帧失败即退出整个游戏进程。 — [`airwar/game/scene_director.py:76-88`](airwar/game/scene_director.py:76)、[`airwar/game/scene_director_components/scene_switcher.py:182-225`](airwar/game/scene_director_components/scene_switcher.py:182)
- [ ] **[ERR]** `SceneManager.switch()` 先设置 `_current_scene` 再调用 `enter()`；若 `enter()` 抛异常，场景管理器会指向一个未完全初始化的场景。 — [`airwar/scenes/scene.py:225-229`](airwar/scenes/scene.py:225)
- [ ] **[ERR]** 子场景（Pause/Settings/Death/ExitConfirm）手动调用 `enter()` / `exit()`，但无 `try/finally`；异常时 `exit()` 不会被调用，资源与状态可能泄漏。 — [`airwar/game/scene_director_components/scene_switcher.py:320-426`](airwar/game/scene_director_components/scene_switcher.py:320)
- [x] **[ERR]** `LockManager.release()` 无 owner/cookie 校验，任何持有 `LockManager` 引用的代码都能释放任意层，存在误释放风险。 — [`airwar/game/systems/lock_manager.py:162-166`](airwar/game/systems/lock_manager.py:162)（已修复：新增 `LockToken`，`release` 支持 token 并校验 cookie，兼容 layer 调用但记录 warning）
- [ ] **[ERR]** `FrameContext` / `FixedStepAccumulator` 对负数 `delta_seconds` 静默取 0，对 `NaN/Inf` 未做校验；极小的 `fixed_delta_seconds` 可能导致单帧步数爆炸。 — [`airwar/game/frame_context.py:66-72`](airwar/game/frame_context.py:66)
- [ ] **[ERR]** `Boss._trigger_enrage_if_needed` 中 `max_health <= 0` 的 guard 位于除法比较之后，仍可能触发除零。 — [`airwar/entities/enemy/boss/boss.py:486-489`](airwar/entities/enemy/boss/boss.py:486)
- [ ] **[ERR]** `BulletManager._update_bullets_batch` 在把子弹加入 `active_bullets` 后才检查 `data is None` 并 `continue`，导致 buffer 索引与 `active_bullets` 不同步，未初始化槽位被 Rust 读取。 — [`airwar/game/managers/bullet_manager.py:174-192`](airwar/game/managers/bullet_manager.py:174)
- [ ] **[OBS]** `game_scene.py` 的模块缓存清理多处使用 `except AttributeError/ImportError: pass` 静默吞异常；`game_scene_updater.py` 使用 `assert bus is not None`，在 `-O` 模式下失效。 — [`airwar/scenes/game_scene.py:703-747`](airwar/scenes/game_scene.py:703)、[`airwar/scenes/game_scene_updater.py:364-370`](airwar/scenes/game_scene_updater.py:364)

### 架构与设计

- [x] **[ARCH]** `LockManager` 仅“无敌”按优先级仲裁；控制锁与暂停是全局 OR 组合，低优先级层（如 `GAME_PAUSE`）可继续锁定控制/暂停，与 `AGENTS.md` 中“按优先级统一仲裁”的描述不一致。 — [`airwar/game/systems/lock_manager.py:221-234`](airwar/game/systems/lock_manager.py:221)（已修复：`_recompute` 中 `lock_controls` / `is_paused` 按最高优先级置位仲裁，并自动清理过期锁）
- [ ] **[ARCH]** `Entity` 基类未统一 `take_damage` / `kill` 接口，玩家、敌机、Boss 签名与返回值不一致，调用方无法多态替换。 — [`airwar/entities/base.py:199-234`](airwar/entities/base.py:199)
- [ ] **[ARCH]** `GameLoopManager` 构造时未校验 8 个依赖，运行时 `None` 会触发 `AttributeError` 而非清晰的 `ValueError`。 — [`airwar/game/managers/game_loop_manager.py:123-141`](airwar/game/managers/game_loop_manager.py:123)
- [ ] **[ARCH]** `BossManager.clear_boss()` 直接修改 `SpawnController.boss`，绕过 `SpawnController` 自身的清理与计时器逻辑，易导致下一只 Boss 出现时机异常。 — [`airwar/game/managers/boss_manager.py:143-145`](airwar/game/managers/boss_manager.py:143)
- [ ] **[PAT]** 普通敌机 `update()` 未传入 `player_pos`，依赖玩家位置的移动策略（如 aggressive 追踪）在当前主循环里拿不到玩家位置。 — [`airwar/game/managers/game_loop_manager.py:424`](airwar/game/managers/game_loop_manager.py:424)

### 集成契约（Rust ↔ Python）

- [ ] **[INT]** `batch_update_bullets` 中 bullet id 的 Rust 注释声明为 `u64`，但实现使用 `i64::from_le_bytes`；Python fallback 使用 `<Q`（u64），三者不一致。 — [`airwar_core/src/bullets.rs:34,56`](airwar_core/src/bullets.rs:34)、[`airwar/core_bindings.py:641`](airwar/core_bindings.py:641)
- [ ] **[INT]** sprite 函数对非正宽度/半径的处理不一致：Rust 返回空 bytes，Python fallback 继续生成极小 surface。 — [`airwar_core/src/sprites.rs:118-124,143-147,190-194,228-232,262-265`](airwar_core/src/sprites.rs:118)、[`airwar/core_bindings.py:542,560,577,590,609`](airwar/core_bindings.py:542)
- [ ] **[INT]** 颜色参数越界处理不一致：`batch_render_particles` / `create_glow_circle` 等 Rust 抛 `OverflowError`，fallback 静默截断或写入越界。 — [`airwar_core/src/particles.rs:109-118`](airwar_core/src/particles.rs:109)、[`airwar/core_bindings.py:485-487`](airwar/core_bindings.py:485)
- [ ] **[INT]** `compute_starfield_positions` 对负 `phase` 的取模语义不一致：Rust 截断为 `usize` 后取模，Python 使用数学取模。 — [`airwar_core/src/starfield.rs:68`](airwar_core/src/starfield.rs:68)、[`airwar/core_bindings.py:253`](airwar/core_bindings.py:253)
- [ ] **[INT]** `core_bindings.py` 只检查 Rust 模块中函数是否存在，无法检测 ABI/签名不匹配。 — [`airwar/core_bindings.py:81-123`](airwar/core_bindings.py:81)

### 安全与配置

- [ ] **[SEC]** `airwar.i18n.set_locale()` 直接把 `locale` 拼接到文件名，存在路径遍历风险（如 `../../etc/passwd`）。 — [`airwar/i18n/__init__.py:108`](airwar/i18n/__init__.py:108)
- [x] **[CFG]** 排行榜 `timeout` 可配置为 `0` 或 `inf`，分别导致立即超时或无限挂起游戏线程。 — [`airwar/leaderboard/config.py:24-31`](airwar/leaderboard/config.py:24)
- [x] **[CFG]** 排行榜 URL 环境变量为空字符串时未被拒绝，会构造出无效请求 URL。 — [`airwar/leaderboard/config.py:22`](airwar/leaderboard/config.py:22)

---

## Minor Issues

- [ ] **[PAT]** `Scene` 抽象基类的 `enter(**kwargs)` / `update(*args, **kwargs)` 过度宽松，子类签名不一致时只能在运行时发现。 — [`airwar/scenes/scene.py:105-144`](airwar/scenes/scene.py:105)
- [ ] **[PAT]** `SceneManager.register()` 不校验 `scene` 是否为 `Scene` 实例，也不阻止覆盖已注册场景。 — [`airwar/scenes/scene.py:202-203`](airwar/scenes/scene.py:202)
- [ ] **[PAT]** `InputHandler` 抽象基类未定义 `tick()`，调用者使用 `hasattr()` 判断，边沿检测不是协议的一部分。 — [`airwar/input/input_handler.py`](airwar/input/input_handler.py)、[`airwar/entities/player.py:226-227`](airwar/entities/player.py:226)
- [ ] **[PAT]** `PygameInputHandler` 对向按键冲突采用“后赋值覆盖”，结果不是归零，且缺少文档说明。 — [`airwar/input/input_handler.py:80-87`](airwar/input/input_handler.py:80)
- [ ] **[PAT]** `PygameInputHandler.DEFAULT_BINDINGS` 是可变类属性，实例间共享。 — [`airwar/input/input_handler.py:13-25`](airwar/input/input_handler.py:13)
- [ ] **[PAT]** `PygameInputHandler` 绑定值未校验是否为合法 pygame 键常量，可能引发 `IndexError`/`TypeError`。 — [`airwar/input/input_handler.py:67-69`](airwar/input/input_handler.py:67)
- [ ] **[PAT]** `ScaledViewport.logical_size` 是公开可变属性，外部只修改尺寸不重建 surface 会导致坐标变换与 surface 尺寸不一致。 — [`airwar/game/scaled_viewport.py:16`](airwar/game/scaled_viewport.py:16)
- [ ] **[PAT]** `Game` 与 `SceneSwitcher` 将 `logical_size` 始终维持为实际窗口尺寸，使 `ScaledViewport` 作为固定逻辑分辨率抽象的设计意图被削弱。 — [`airwar/game/game.py:54-55`](airwar/game/game.py:54)、[`airwar/game/scene_director_components/scene_switcher.py:287-298`](airwar/game/scene_director_components/scene_switcher.py:287)
- [ ] **[PAT]** `PlayerState.force_substate()` 完全绕过合法边检查，存档恢复损坏的 substate 可能把玩家置于非法组合状态。 — [`airwar/entities/player_state.py:209-211`](airwar/entities/player_state.py:209)
- [ ] **[PAT]** `Player.enter_boost()` 对非法转换 `try/except IllegalPlayerTransition: pass` 静默吞掉，掩盖状态机逻辑错误。 — [`airwar/entities/player.py:269-274`](airwar/entities/player.py:269)
- [ ] **[PAT]** `Boss` 中 `_update_enrage_transition`、`_update_enrage_release_hold`、`_update_enrage_return` 已定义但未被调用，属于死代码。 — [`airwar/entities/enemy/boss/boss.py:584-606`](airwar/entities/enemy/boss/boss.py:584)
- [ ] **[OBS]** 事件分发采用硬编码方法调用链，任意分支异常都会中断同帧后续事件处理并向上传播。 — [`airwar/scenes/game_scene_event_dispatcher.py:39-68`](airwar/scenes/game_scene_event_dispatcher.py:39)、[`airwar/scenes/scene_homecoming_dispatcher.py:75-171`](airwar/scenes/scene_homecoming_dispatcher.py:75)
- [x] **[PAT]** `UserDB.submit_score` 对 `bool` 的处理与注释不符：`bool` 是 `int` 子类，会被转换为 `0/1` 而非拒绝。 — [`airwar/utils/database.py:257-263`](airwar/utils/database.py:257)
- [ ] **[PAT]** `SceneDirector._submit_leaderboard_score()` 每次调用都新建 `LeaderboardService` 实例，属于不必要的开销。 — [`airwar/game/scene_director.py:248-256`](airwar/game/scene_director.py:248)

---

## Nit

- [ ] `assert welcome is not None` 在 `-O` 模式下被移除。 — [`airwar/game/scene_director_components/scene_switcher.py:46`](airwar/game/scene_director_components/scene_switcher.py:46)
- [ ] `GameScene` 注释中提到已不存在的 `__setattr__` hook，注释与实现不一致。 — [`airwar/scenes/game_scene.py:15,373-396`](airwar/scenes/game_scene.py:15)
- [ ] `airwar_core.pyi` stub 文件包含不必要的 `__all__` 列表。 — [`airwar_core/airwar_core/airwar_core.pyi:157-187`](airwar_core/airwar_core/airwar_core.pyi:157)

---

## Positive Findings

以下做法值得保留：

1. **原子写入**：`database.py` 与 `persistence_manager.py` 均使用 `f.flush()` → `os.fsync()` → `os.replace()`，是防止掉电损坏的正确做法。
2. **存档损坏恢复**：`PersistenceManager` 加载失败时自动备份为 `.corrupted.{timestamp}.bak` 并删除损坏文件。
3. **密码安全**：PBKDF2-SHA256、100k 迭代、随机 128-bit salt、`secrets.compare_digest` 防时序攻击。
4. **SQL 注入防护**：排行榜服务端全程参数化查询。
5. **远程降级**：`LeaderboardService` 在 remote 不可用时自动回退本地，失败被日志记录，不中断游戏循环。
6. **Rust 加载回退**：`core_bindings.py` 捕获 `ImportError`/`OSError` 并校验函数存在性，缺失时自动切到纯 Python fallback。

---

## Rules Applied

本次审查综合应用了以下规则维度（项目未提供 `.agents/rules/` 文件，故使用 skill 通用规则与项目自身 `AGENTS.md` 约定）：

- `security-principles.md` — 认证、输入验证、数据保护、CORS、依赖安全
- `error-handling-principles.md` — 异常隔离、空 except、assert 误用、状态回滚
- `architectural-pattern.md` — 接口一致性、层间访问、依赖注入、状态机 guards
- `api-design-principles.md` — 参数校验、类型契约、异常行为一致性
- `database-design-principles.md` — 原子写入、并发安全、损坏恢复
- `configuration-management-principles.md` — 环境变量校验、默认值合理性
- `resources-and-memory-management-principles.md` — 资源释放、锁泄漏、池管理
- `logging-and-observability-mandate.md` — 关键路径日志、异常可见性

---

## Recommended Priority

| 优先级 | 问题 | 建议改动 |
|--------|------|----------|
| 高 | 用户数据库损坏无法恢复 | 损坏时备份并重置为空数据库 |
| 高 | 并发写入冲突 | 使用唯一临时文件名 + 文件锁 |
| 高 | 主循环单点崩溃 | 增加帧级 `try/except` 降级或日志后退出 |
| 高 | Rust/Python sprite 非正输入不一致 | fallback 与 Rust 统一返回空 bytes |
| 中 | CORS `*` 与 limit 无上限 | 限制来源、Pydantic 限制 `1 <= limit <= 100` |
| 中 | 缺失 salt 回退到 user_id | 强制重新生成 salt 或要求重置密码 |
| 中 | LockManager release 无 owner | 增加 cookie/owner 校验或调用栈日志 |
| 中 | BulletManager buffer 不同步 | 将 `data is None` 检查提前到 append 前 |
| 低 | FrameContext 负 dt / NaN | 增加校验或日志 |
| 低 | i18n 路径遍历 | 校验 locale 白名单 |
