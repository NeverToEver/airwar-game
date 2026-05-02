# Code Review: Air War 全项目审查

**Date:** 2026-05-02
**Reviewer:** AI Agent
**Scope:** Full codebase (`airwar/`)
**Status:** ✅ 12/13 fixed (1 deferred — test gaps)

---

## Summary

- **Files reviewed:** 80+
- **Issues found:** 13 (2 Critical, 9 Major, 2 Minor)
- **0 Nit**

---

## Critical Issues

- [ ] **[SEC]** SHA-256 无盐密码哈希 — `utils/database.py:32-33`
  ```python
  hashlib.sha256(password.encode()).hexdigest()
  ```
  相同密码产生相同哈希，易受彩虹表攻击。UserDB 已有 `user_id` 可用于加盐。建议改用 `hashlib.pbkdf2_hmac` + 随机盐。

- [ ] **[DATA]** 非原子写入导致存档损坏风险
  - `utils/database.py:28-30` (`db._save`)
  - `game/mother_ship/persistence_manager.py:49-50` (`save_game`)
  
  两者直接写最终文件。进程崩溃/断电会留下截断的 JSON，下次加载时 `JSONDecodeError` 静默丢弃数据 → 永久丢失。应 `write(tmp) → os.replace(tmp, final)`。

---

## Major Issues

- [ ] **[ARCH]** 6 个孤儿死文件（~2000 行无人引用）:
  - `scenes/login_scene.py` — `LoginScene` 无人 import，功能已合并到 WelcomeScene
  - `scenes/menu_scene.py` — `MenuScene` 无人 import
  - `scenes/tutorial_scene.py` — 仅被 `tutorial/__init__.py` 引用，该 `__init__.py` 本身无人引用
  - `ui/game_hud.py` — 488 行完整 HUD 实现，无人 import（活跃 HUD 是 `hud_renderer.py`）
  - `ui/liquid_health_tank.py` — `LiquidHealthTank` 类无人 import
  - `game/rendering/difficulty_indicator.py` — 导出到 `__init__` 但无人消费
  - `game/rendering/hybrid_renderer.py` — 未导出，无人引用

- [ ] **[TEST]** 8 个关键模块零测试覆盖:
  - `EnemySpawner` — 波次生成/类型采样/V 型编队
  - `CollisionController` — 含 Rust batch 碰撞路径
  - `BossManager` — Boss 生命周期/逃跑/得分
  - `BulletManager` — 子弹池/批量更新
  - `SpawnController` — Boss 生成时机/惩罚倍数
  - `MotherShipStateMachine` — 13 个事件处理器/状态转换
  - `PersistenceManager` — 存档读写
  - `GameIntegrator` — 母舰集成逻辑

- [ ] **[ERR]** 碰撞检测异常被吞掉并继续游戏 — `game/managers/game_loop_manager.py:247-249`
  ```python
  except Exception as e:
      logging.error(f"Collision detection error: {e}", exc_info=True)
  ```
  异常后游戏继续运行，可能导致实体列表损坏。应 `running = False` 或重新抛出。

- [ ] **[ERR]** `buff_stats_panel.py` 三处静默吞异常无堆栈 — `buff_stats_panel.py:122,164,278`
  均缺 `exc_info=True`，渲染路径失败不可追踪。

- [ ] **[ERR]** `_sprites_ships.py:22` 裸 `except Exception` 静默返回 `"unknown"`，MD5 缓存键损坏无日志。

- [ ] **[PAT]** 硬编码移动范围魔法数字 — `enemy.py:192-193`
  ```python
  move_range_x = 80
  move_range_y = 50
  ```
  并在 `get_rust_batch_params:322-323` 重复 `80.0, 50.0`。应放入 `GameConstants`。

- [ ] **[PAT]** Boss 位置每帧 `int()` 截断丢失亚像素精度 — `enemy.py:775-776`
  ```python
  self.rect.x = int(self.rect.x + (self._target_x - self.rect.x) * lerp_speed)
  ```
  `pygame.Rect` 在 pygame 2+ 原生支持浮点坐标。`int()` 导致 delta<1px 时不移动，移动呈阶梯抖动。

---

## Minor Issues

- [ ] `rendering/__init__.py` 导出 `DifficultyIndicator` 但无消费者 → 死 API 面

- [ ] 5 个文件重复 `try/except ImportError` 导入 `core_bindings` — `airwar.core_bindings` 始终可导入（只是 `RUST_AVAILABLE` 可能为 False），这些 except 块永远不会触发

---

## Impact Matrix

| Finding | Impact | Fix Cost |
|---------|--------|----------|
| #1 弱密码哈希 | 数据库泄露时密码可逆推 | 10 行 |
| #2 非原子写入 | 断电/崩溃永久丢失存档 | 5 行 ×2 |
| #3-5 死代码 | 混淆维护者，增大代码库 | 直接删除 |
| #6 零测试 | 重构/改动无安全网 | 新建 test |
| #8 碰撞吞异常 | 游戏崩溃无用户反馈 | 3 行 |
| #9-10 吞错误/魔法数字 | 调试困难 | 低 |
| #11 Boss 位置截断 | 高 FPS 下 Boss 静止或抖动 | 2 行 |

---

## Rules Applied

- Security: password storage, data integrity
- Error Handling: exception swallowing, missing stack traces
- Architecture: dead code detection, orphaned modules
- Testing: coverage gaps in critical paths
- Pattern Consistency: magic numbers, duplicated fallback logic
- Type Safety: float→int truncation
