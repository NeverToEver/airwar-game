# Code Review: 弹药指示器 + 警告横幅 + 离散血量 + Boost表缩小 + 母舰弹药系统
Date: 2026-04-29
Reviewer: AI Agent (fresh context)
基线：master @ 6e4a843

## Summary
- **Files reviewed:** 36 (4 新增 UI 组件, 13 核心游戏文件, 3 Rust 扩展, 3 构建脚本, 文档/杂项)
- **Issues found:** 14 (0 critical, 5 major, 4 minor, 5 nit)
- **Tests:** 695 passed, 1 skipped, 0 regression

## Critical Issues
*无*

## Major Issues

- [ ] **[ARCH]** GameScene 绕过封装访问私有成员 — [`game_scene.py:352`](../../../airwar/scenes/game_scene.py#L352)
  `self._mother_ship_integrator._event_bus` — GameScene 通过 GameIntegrator 的私有 `_event_bus` 发布 `UNDOCK_REQUESTED`，破坏了两层封装。应在 GameIntegrator 上暴露 `request_undock()` 公共方法，由 GameIntegrator 内部调用自己的 event_bus。

- [ ] **[ARCH]** GameIntegrator 直接操作子对象私有状态 — [`game_integrator.py:654,660`](../../../airwar/game/mother_ship/game_integrator.py#L654)
  `force_docked_state()` 写 `self._state_machine._current_state`，`reset_to_idle_with_mothership_visible()` 操作 `self._input_detector._progress`，绕过了 StateMachine 和 InputDetector 的公共接口。应通过状态机的合法转换方法或事件总线实现。

- [ ] **[TEST]** 四个新 UI 组件缺单元测试
  - `airwar/ui/ammo_magazine.py` — 弹药格填充算法、缓存失效、隐藏条件
  - `airwar/ui/warning_banner.py` — 状态机生命周期、回调触发、定时逻辑
  - `airwar/ui/discrete_battery.py` — 分段计算、颜色映射、方向切换
  - `airwar/ui/liquid_health_tank.py` — 弹簧物理收敛、液体颜色插值、气泡系统
  核心逻辑未覆盖，仅通过集成测试（游戏截图对比）间接验证。

- [ ] **[RES]** 缓存 Surface 的每帧 fill+blit 模式 — [`liquid_health_tank.py:202`](../../../airwar/ui/liquid_health_tank.py#L202)
  `self._liquid_surf.fill((0,0,0,0))` 对缓存的 `_liquid_surf` 每帧清空再绘制液体，实质仍是每帧重新生成。可考虑直接创建每帧局部 Surface，避免缓存语义歧义。

- [ ] **[OBS]** WarningBanner.activate() 静默忽略重复调用 — [`warning_banner.py:51-52`](../../../airwar/ui/warning_banner.py#L51)
  banner 已在活动状态时 `activate()` 直接 return，无日志、无返回值、无异常。调用者（`_update_mothership_ammo_warning`）虽然做了 `is_active` 预检，但该防御性屏障仅在 GameScene 内部。如果未来有其他调用者忘记检查，静默忽略会导致 bug 难以排查。

## Minor Issues

- [ ] **[PAT]** 类常量位置不一致 — [`game_integrator.py:580`](../../../airwar/game/mother_ship/game_integrator.py#L580)
  `AMMO_CELL_COUNT = 10.0` 定义在类底部（紧邻 `get_status_data()`），而其他类常量（`MOTHSHIP_BULLET_DAMAGE`, `MOTHSHIP_FIRE_RATE` 等）在第 25-30 行。应移到类常量区域。

- [ ] **[PAT]** `hasattr` 防御性检查引入隐式契约 — [`game_scene.py:413`](../../../airwar/scenes/game_scene.py#L413)
  `if hasattr(self, '_boost_gauge'):` — `_boost_gauge` 在 `enter()` 中总是被赋值，此检查掩盖了 `enter()` 未调用时的初始化 bug。如果 `_boost_gauge` 是可选属性，应显式初始化为 `None` 并检查 `is not None`。

- [ ] **[PAT]** 开火计时使用帧计数 — [`game_integrator.py:155`](../../../airwar/game/mother_ship/game_integrator.py#L155)
  `self._mothership_fire_timer += 1` 帧计数而非 delta-time。与项目其余部分一致（60fps 设计），但帧率下降时开火速度随之下降。CLAUDE.md 中标注 ~3.3 shots/sec 的假设建立在稳定 60fps 上。

- [ ] **[PAT]** 魔法数字 `3` — [`ammo_magazine.py:144,154`](../../../airwar/ui/ammo_magazine.py#L144)
  `if (is_warning and i < 3)` — 低弹警告时最后 3 格变红的条件使用字面量 `3`。应提取为 `WARNING_CELL_THRESHOLD = 3` 常量，与 `CELL_COUNT = 10` 同区域定义。

## Nit

- [ ] `ammo_magazine.py:38` — `_pulse_phase += 0.05` 永远递增，极长时间运行后浮点精度退化。无明显影响，但可通过 `% (2 * math.pi)` 或周期重置来规范化。

- [ ] `ammo_magazine.py:42-43,45-48` — `frame_width` 和 `frame_height` 是简单计算属性，频繁调用（每帧 render 中访问 `frame_width`/`frame_height` 各一次）影响微小，但可改为缓存计算或赋值给局部变量。

- [ ] `game_scene.py:295-297` — `_warning_banner.update()` 被注释说明为 "even during pause"，但 `warning_banner.update()` 使用 `pygame.time.get_ticks()` 作为时间源，暂停期间 ticks 继续推进，这是正确的（注释与实际行为匹配）。注释本身可以更精确说明 "使用真实时间而非游戏帧时间"。

- [ ] `game_integrator.py:251` — `hasattr(self._game_scene, 'trigger_explosion')` 检查：`trigger_explosion` 是 `IGameScene` 接口的一部分，但此处未通过 TYPE_CHECKING 确保类型安全。可考虑在 `attach_game_scene` 时做一次接口验证。

- [ ] `collision_controller.py:269` — Boss 碰撞检测未使用 Rust batch_collide 加速而子弹-敌人碰撞已使用。这是合理的设计选择（通常只有一个 Boss），但缺少注释说明为什么只有这个路径走纯 Python。

## Dimensions Covered (Zero Critical/Major Guard 补充)

为满足 Code Review Skill 第 9 节 "Zero-Findings Guard" 要求（虽然本次有 findings，但为审查完整性列出所有检查维度）：

| 维度 | 检查内容 | 结论 |
|------|----------|------|
| Security | 无网络通信、无数据库查询、无用户输入注入点。游戏为纯客户端。 | 通过 |
| Data integrity | JSON 序列化通过 PersistenceManager，save_data 字段齐全，legacy key 兼容处理完善。 | 通过 |
| Resource leaks | Surface 缓存模式正确，frame/bg cache 在 resize 时重建。Bullet 列表 `[:]` 清理。 | 通过 |
| Circular dependencies | 新 UI 组件单向依赖 pygame + design_tokens，无循环导入。GameIntegrator↔GameScene 通过 IGameScene 接口解耦，层级清晰。 | 通过 |
| Configuration | 构建脚本（.sh/.bat）硬编码 Python 版本（3.12）和 venv 路径，符合文档要求。 | 通过 |
| Dependency health | `requirements.txt` 无新增依赖，Rust Cargo.toml 无新增 crate。 | 通过 |
| Test coverage | 695/696 测试通过。新 UI 组件缺单元测试（已在 Major 中指出）。 | 部分通过 |

## Rules Applied
- CLAUDE.md — 架构分层、导入规范、接口驱动设计
- Code Review Skill (`.agents/rules/` 规则集不存在，使用内联标准)
- Security checklist: passed (纯客户端游戏，无网络/认证/数据库)
- Language anti-patterns: Python 无红线违规（无本地方法导入、无裸 except）
- OWASP Top 10: N/A (无服务端)
