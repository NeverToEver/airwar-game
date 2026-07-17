# 代码审核:空间换时间 · 逻辑错误 · 循环漏洞

日期:2026-07-17
审核人:AI Agent(fresh context,配额受限下由主线程直接审核)
基线:`pytest tests/` → 200 passed

## 概要

- **审核范围**:每帧热路径(`game/managers`、`game/rendering`、`entities/`、`scenes/game_scene_updater.py`)、`core_bindings.py` 与 `airwar_core/src/bullets.rs` 的一致性、场景切换循环。
- **发现问题**:6(0 critical,1 major,5 minor)
- **修复状态**(2026-07-17):6/6 已修复并验证(爆炸计分 Major + 5 个 Minor 全部),全套 215 passed + ruff 绿。
- **总体结论**:空间换时间原则在渲染与碰撞层执行良好(LRU/bucket 缓存、buffer 复用、空间哈希);未发现迭代中修改集合或死循环类漏洞。主要问题是 Rust/Fallback 双实现之间的规则分叉隐患,以及爆炸 AoE 击杀不计分。

## Major Issues

- [x] **[LOGIC] 爆炸 AoE 击杀不计分、不计入击杀数(已修复,2026-07-17)** — `airwar/game/managers/collisions/bullet_vs_entities.py:260-272`
  修复:`_handle_explosive_damage` 新增 `score_multiplier`/`exclude` 参数并返回 `(killed, score)`,由 `_apply_player_bullet_hit` 累加;`exclude` 防止直接命中者被爆炸补刀时重复计分。新增 `tests/test_explosive_scoring.py` 5 个用例(两条碰撞路径 + 补刀去重 + 倍率),全套 205 passed。
  原问题:`_handle_explosive_damage` 对半径内敌人 `enemy.take_damage(explosion_damage)` 后,既不累加 `enemies_killed` 也不累加 `score_gained`(对比 242-244 行:只有被子弹直接命中的敌人才计分)。后果:爆炸天赋群杀一片敌人只按 1 个击杀给分,且击杀数/里程碑统计偏低。

## Minor Issues

- [x] **[LOGIC] `getattr` 默认值双陷阱:enrage 子弹释放速度(已修复,2026-07-17)** — `airwar/game/managers/bullet_manager.py:249`
  修复:改为 `bullet.enrage_release_speed or bullet.data.speed`,未设置(0.0)时回退基础速度,避免零向量悬停泄漏;同时消除 getattr 默认值立即求值的 `AttributeError` 隐患。新增 `tests/test_bullet_manager.py` 2 个用例(回退 + 显式速度优先,旧代码红验证)。

- [x] **[LOGIC/一致性] 子弹出界判定双标准(±10 vs ±80)(已简化,2026-07-17)** — `airwar_core/src/bullets.rs:24`、`airwar/core_bindings.py:703,719` vs `airwar/entities/bullet.py:35,89-96`
  处理:`_use_rust` 恒 True 问题按方案 A 修复——删除 `bullet_manager.py` 的 `_use_rust` 标志与永不执行的纯 Python 逐弹分支,batch 路径成为唯一路径(经 core_bindings 自动选 Rust 或 Python fallback);`_update_bullets_batch` docstring 已写明出界判定以 Python 层 `OFFSCREEN_MARGIN` 四方向检查为准、后端 ±10 垂直检查仅为提前禁用提示。`Bullet.update()`/`_is_offscreen()` 作为 `Entity` 接口实现保留。
  原问题:Rust 与 Python fallback 的 `batch_update_bullets*` 硬编码垂直边界 `±10`;`Bullet._is_offscreen()` 与 `_update_bullets_batch` 的 Python 二次检查用 `OFFSCREEN_MARGIN = 80` 四方向。且 `_use_rust = batch_update_bullets is not None` 恒为 True(core_bindings fallback 同样导出该函数,core_bindings.py:171 起),使 `bullet_manager.py:115-117` 的纯 Python 逐弹分支成为**事实死代码**。合成效果:非激光子弹在 `y ∈ [-80, -10)` 即被禁用,比文档化的 ±80 提前消失。

- [x] **[LOOP/设计风险] 空间哈希查询生成器共享 `_query_seen`,不可重入(已修复,2026-07-17)** — `airwar/game/managers/collision_controller.py:185-202`
  修复:`_get_entities_in_cells` 改用生成器内局部 `seen` set,每个查询实例持有自己的去重状态;删除 `__init__` 中共享的 `_query_seen`。新增 `tests/test_spatial_hash_reentrancy.py` 2 个用例(嵌套查询不破坏外层去重——旧代码会重复 yield、跨 cell 实体去重)。

- [x] **[LOGIC/一致性] 敌方子弹命中结算:Rust 多弹 vs Python 单弹(已修复,2026-07-17)** — `airwar/game/managers/collisions/enemy_bullet_vs_player.py:100-108` vs `114-119`
  修复:Rust 路径改为首个 active 命中结算后即 `return True`,与 Python fallback 单弹语义对齐(该类 docstring 本就声明 first-hit),不再依赖场景清弹兜底;顺带修正"全部命中弹均 inactive 时误返回 True"的小偏差。新增 `tests/test_enemy_bullet_vs_player.py` 3 个用例(两路径参数化首弹语义 + inactive 命中跳过,旧 Rust 路径红验证)。

- [x] **[SPACE-TIME] `HUDRenderer` 每帧全量文本重渲染(仅兜底路径)(已修复,2026-07-17)** — `airwar/game/rendering/hud_renderer.py:109-133`
  修复:`render_hud` 的 6 处 `font.render` 全部改走已有的 `_render_value`/`render_cached_text` 缓存(文本不变时零重渲染;health 标签 key 含颜色,与 `render_notification` 模式一致)。新增 `tests/test_hud_renderer_cache.py` 3 个用例(全缓存命中、仅变更标签重渲染一次、危险色切换)。

## 正面确认(无需修改)

空间换时间运用良好的位置:

- 激光拖尾 Surface LRU 缓存:`entity_renderer.py:128-139`;enrage 旋转 sprite/ring 按 bucket 缓存:`181-258`;无敌光环缓存:`game_renderer.py:129-142`;警告文本缓存:`entity_renderer.py:59-66`;HUD 面板背景缓存:`integrated_hud.py:191-209`。
- 子弹二进制 buffer FFI(32B/颗)+ 复用 `bullet_map`:`bullet_manager.py:53-54,136-198`;struct 布局与 Rust 侧 `bullets.rs:44` 完全一致。
- 碰撞空间哈希网格与查询容器复用:`collision_controller.py:84-99`;子弹/敌人 data 缓冲复用避免每帧分配。
- 清理 fast-path(全 active 时跳过一次分配):`bullet_manager.py:258-261`、`spawn_controller.py:263-268`。
- 敌机波次生成一次性预计算 + deque 渐进释放:`enemy.py:693-779`。
- `core_bindings.py` 的 Rust 缺失检测与 ABI 签名校验(119-136 行)能在扩展过旧时整体回退,设计严谨。

循环安全性确认:

- `scene_switcher.py:447` 的 `while True`:所有分支均有 `return`/`continue`,退出条件完整,非死循环。
- 全库未发现迭代中修改同一集合的漏洞:删除均先标记 `active=False` 再统一过滤(`bullets[:] = [...]`)。
- hit_stop 历史死锁(暂停步骤短路导致计时器永不递减)已修复并留有详细注释:`game_scene_updater.py:111-133`。
- `batch_update_bullets_buf` 的 Python fallback 与 Rust 实现逐行一致(含 `ValueError` 校验)。

## 待确认

- ~~爆炸 AoE 击杀不计分~~ → 已确认为 bug 并修复。
- ~~`_use_rust` 恒 True 是否有意~~ → 已按方案 A 处理:删除标志与死代码分支,batch 为唯一路径。

## 审核覆盖(实际读完/扫过的文件)

`game/managers/bullet_manager.py`、`collision_controller.py`、`collisions/bullet_vs_entities.py`、`collisions/enemy_bullet_vs_player.py`、`collisions/collision_event_dispatcher.py`、`spawn_controller.py`、`entities/bullet.py`、`entities/player.py`(部分)、`entities/enemy/enemy.py`(update/spawner 段)、`entities/enemy/boss/boss.py`(enrage 段)、`entities/enemy/boss/boss_attack.py`(enrage 段)、`game/rendering/entity_renderer.py`、`game_renderer.py`、`integrated_hud.py`、`hud_renderer.py`(扫)、`scenes/game_scene_updater.py`、`scene_director_components/scene_switcher.py`(循环段)、`core_bindings.py`(fallback 段)、`airwar_core/src/bullets.rs`、`game/constants.py`(相关常量);全库 `for…remove/append/pop` 与 `while` 模式 grep 扫描。
