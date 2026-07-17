# AirWar 项目类型接口错误审核报告

- 生成时间：2026-07-10T20:38:14.916493
- 扫描工具：mypy 2026（Python 3.12）
- 扫描范围：`airwar/`、`main.py`、`tests/`

## 1. 执行摘要

使用 `mypy` 对项目进行静态类型扫描，默认模式发现 **653 个类型错误**，分布在 **77 个文件**中；
启用 `--check-untyped-defs` 严格模式后，错误数上升至 **721 个**。

主要问题集中在以下几类：

1. **协议/适配器类型信息缺失**：大量 `object` 类型参数通过属性访问其它组件，导致 `attr-defined` 错误。
2. **颜色/UI 常量命名漂移**：代码引用大量不存在的 `SceneColors`、`SystemColors`、`SystemUI` 常量。
3. **Optional/None 处理缺失**：多处未对可能为 `None` 的对象进行判空，导致运行时 `AttributeError` 风险。
4. **函数签名不兼容**：子类覆盖父类方法时参数不一致。
5. **Rust 绑定存根缺失**：`airwar_core` 未提供类型存根，mypy 无法识别导出的函数。

## 2. 扫描方法与命令

```bash
# 默认模式
python3 -m mypy airwar main.py tests --ignore-missing-imports --show-error-codes --show-column-numbers

# 严格模式（同时检查未标注函数体）
python3 -m mypy airwar main.py tests --ignore-missing-imports --check-untyped-defs --show-error-codes --show-column-numbers
```

## 3. 错误分类统计

### 3.1 按 mypy 错误代码统计

| 错误代码 | 默认模式数量 | 严格模式数量 | 说明 |
| --- | --- | --- | --- |
| attr-defined | 423 | 447 | 访问未定义属性（协议/对象类型丢失） |
| arg-type | 73 | 81 | 函数参数类型不匹配 |
| assignment | 47 | 71 | 赋值类型不兼容 |
| union-attr | 40 | 48 | 对 Optional/Union 类型访问属性 |
| var-annotated | 33 | 34 | 变量缺少类型注解 |
| return-value | 10 | 10 | 返回值类型不匹配 |
| dict-item | 8 | 8 | 字典元素类型不匹配 |
| index | 6 | 8 | 对不可索引对象进行索引 |
| operator | 6 | 6 | 操作数类型不支持 |
| truthy-function | 2 | 2 | 函数在布尔上下文恒真 |
| override | 1 | 1 | 子类方法签名与父类不兼容 |
| has-type | 1 | 2 | 无法推断变量类型 |
| valid-type | 1 | 1 | 类型表达式无效 |
| abstract | 1 | 1 | 实例化抽象类 |
| method-assign | 1 | 1 | 给方法赋值 |

### 3.2 按文件统计（Top 30）

| 文件 | 默认模式错误数 | 严格模式错误数 |
| --- | --- | --- |
| `airwar/scenes/game_scene_updater.py` | 78 | 78 |
| `airwar/scenes/game_scene_protocol_adapter.py` | 51 | 52 |
| `airwar/scenes/scene_homecoming_dispatcher.py` | 45 | 45 |
| `airwar/scenes/welcome_scene.py` | 39 | 45 |
| `airwar/core_bindings.py` | 29 | 29 |
| `airwar/scenes/settings_scene.py` | 22 | 29 |
| `airwar/scenes/exit_confirm_scene.py` | 19 | 19 |
| `airwar/scenes/welcome/login_panel.py` | 17 | 29 |
| `airwar/scenes/game_scene_event_dispatcher.py` | 16 | 16 |
| `airwar/scenes/pause_scene.py` | 16 | 16 |
| `airwar/entities/enemy/boss/boss_attack.py` | 15 | 15 |
| `airwar/game/rendering/game_rendering_background.py` | 14 | 14 |
| `airwar/ui/leaderboard_view.py` | 13 | 13 |
| `airwar/scenes/themed_scene_mixin.py` | 13 | 13 |
| `airwar/ui/hex_icon.py` | 11 | 11 |
| `airwar/utils/_sprites_common.py` | 10 | 10 |
| `airwar/ui/buff_stats_panel.py` | 10 | 12 |
| `airwar/ui/reward/reward_card_renderer.py` | 10 | 10 |
| `airwar/entities/enemy/boss/boss.py` | 10 | 10 |
| `airwar/game/mother_ship/mothership_animations.py` | 10 | 10 |
| `airwar/scenes/tutorial_scene.py` | 10 | 10 |
| `airwar/game/rendering/boss_enrage_renderer.py` | 9 | 9 |
| `airwar/ui/game_over_screen.py` | 9 | 9 |
| `airwar/ui/scene_rendering_utils.py` | 8 | 8 |
| `airwar/scenes/welcome/welcome_modals.py` | 8 | 8 |
| `airwar/ui/reward_selector.py` | 8 | 8 |
| `airwar/entities/enemy/enemy.py` | 8 | 8 |
| `airwar/ui/difficulty_coefficient_panel.py` | 7 | 7 |
| `airwar/game/mother_ship/mother_ship_renderer.py` | 7 | 7 |
| `airwar/entities/enemy/enemy_movement_batch.py` | 7 | 7 |

## 4. 高风险问题详细说明

以下问题具有较高运行时风险，建议优先修复。

### 4.1 协议适配器持有 `object` 类型而非具体协议

多个适配器类将 scene 标注为 `object`，导致 mypy 无法识别任何属性，同时运行时若传入错误对象也难以发现。

#### 4.1.1 `airwar/scenes/game_scene_protocol_adapter.py`

- 位置：`__init__` 第 23 行；属性访问集中在第 30–187 行
- 问题：`self._scene: object`，后续访问 `game_controller`、`player`、`spawn_controller` 等 51 个属性均无类型保障
- 风险：调用方传入非 GameScene 对象时，错误只能在运行时发现
- 修复建议：定义 `IGameScene` Protocol，将参数类型改为该协议；或在 `TYPE_CHECKING` 块中引入前向引用

#### 4.1.2 `airwar/scenes/game_scene_event_dispatcher.py`

- 位置：第 43–60 行
- 问题：内部 `scene` 为 `object` 类型，访问 `_input_coordinator`、`game_renderer`、`_aim_assist` 等 16 处

#### 4.1.3 `airwar/scenes/game_scene_updater.py`

- 位置：第 136–395 行
- 问题：该类包含 78 处 `attr-defined` 错误，是项目中最严重的单文件类型盲区
- 代表位置：
  - 第 151 行：`object` 访问 `_homecoming_coordinator`
  - 第 160 行：`object` 访问 `game_renderer`
  - 第 183 行：`object` 访问 `_game_loop_manager`
  - 第 289 行：`object` 访问 `AUTO_SAVE_INTERVAL_SECONDS`

#### 4.1.4 `airwar/scenes/scene_homecoming_dispatcher.py`

- 位置：第 80–169 行
- 问题：45 处 `attr-defined` 错误，同样因 scene 为 `object`

### 4.2 颜色/UI 常量命名漂移（运行时 AttributeError 风险）

大量代码引用了 `design_tokens.py` 中不存在的颜色常量。这些错误在运行时直接抛出 `AttributeError`，是显性 bug。

#### 缺失常量清单

- `SceneColors.GOLD_PRIMARY`、`GOLD_GLOW`、`GOLD_BRIGHT`、`GOLD_DIM`、`FOREST_GREEN`
- `SystemColors.AMBER_GLOW`、`AMBER_PRIMARY`、`AMBER_BRIGHT`、`AMBER_DIM`
- `SystemUI.MILITARY_LABEL_SIZE`、`MILITARY_SMALL_SIZE`

#### 高频引用位置

- `airwar/ui/scene_rendering_utils.py`：第 350、351、361、486、498、506 行
- `airwar/ui/leaderboard_view.py`：第 86、87、91、137 行
- `airwar/ui/game_over_screen.py`：第 166、188、197、298、324 行
- `airwar/ui/buff_stats_panel.py`：第 404、413、433、436、460、461、530 行
- `airwar/scenes/settings_scene.py`：第 247、255、271、317、377、382、394、437 行
- `airwar/ui/reward_selector.py`：第 79–93 行
- `airwar/ui/reward/reward_card_renderer.py`：第 126、135、202、336、353、356、366、369、375 行

- 修复建议：统一命名——要么在 `design_tokens.py` 中补齐缺失常量，要么全局替换为已存在的对应名称（如 `ACCENT_PRIMARY`）

### 4.3 父类方法签名覆盖错误

- 文件：`airwar/game/mother_ship/state_machine.py` 第 174 行
- 问题：`MotherShipStateMachine.update(self, current_time: float)` 与接口 `IMotherShipStateMachine.update(self) -> None` 签名不一致
- 风险：多态调用时可能因参数数量不一致触发 `TypeError`
- 修复建议：统一接口与实现签名；若必须传参，修改接口或在实现中移除参数

### 4.4 Optional/None 未处理导致运行时崩溃

- 文件：`airwar/scenes/welcome_scene.py`
  - 位置：第 203、206、214、216、270、272、282–301、309–323、378–412、589–604 行
  - 问题：`self._login_panel`、`self._difficulty_panel`、`self._modals`、`self._leaderboard_overlay` 等声明为 `Optional`，但大量调用未判空
  - 风险：组件未初始化时事件分发直接触发 `AttributeError`

- 文件：`airwar/game/mother_ship/mothership_animations.py`
  - 位置：第 115–147 行
  - 问题：`self._game_state` 等变量可能为 `None`，但直接访问 `.player`

- 文件：`airwar/game/managers/spawn_controller.py`
  - 位置：第 84–88 行
  - 问题：字典 `object` 类型取值后未判断即索引/调用 `.get()`

### 4.5 Rust 绑定 `airwar_core` 类型存根缺失

- 文件：`airwar/core_bindings.py` 第 51 行
- 问题：`from airwar_core import (...)` 的 29 个函数 mypy 无法识别
- 影响：调用这些 Rust 加速函数的所有位置均无类型检查
- 修复建议：
  1. 为 `airwar_core` 生成或手写 `airwar_core.pyi` 类型存根；
  2. 或在 `core_bindings.py` 中显式重新声明函数签名，使用 `if TYPE_CHECKING` 引入存根签名

### 4.6 isinstance 参数类型错误

- 文件：`airwar/game/mother_ship/persistence_manager.py` 第 133 行
- 问题：`isinstance(data[key], expected_type)` 中 `expected_type` 被推断为 `object`
- 原因：`type_checks` 字典值类型混合了 `type` 与 `tuple[int, float]`，导致整体推断为 `object`
- 修复建议：将 `type_checks` 注解为 `dict[str, type | tuple[type, ...]]`，并对元组形式单独处理

### 4.7 pygame.Rect 与项目内 Rect 类型混用

- 文件：`airwar/game/managers/collisions/enemy_bullet_vs_player.py` 第 109 行
- 问题：`pygame.rect.Rect` 与 `airwar.entities.base.Rect` 被视为不同类型
- 修复建议：统一使用 `pygame.Rect` 或在基类中显式声明兼容类型

## 5. 中低风险问题

### 5.1 缺少类型注解的类变量

多个模块类级/模块级缓存字典缺少泛型注解，例如：

- `airwar/utils/_sprites_common.py` 第 20–25 行：`_glow_circle_cache` 等 6 个缓存
- `airwar/utils/_sprites_ships.py` 第 13–16 行：`_player_sprite_cache` 等 4 个缓存
- `airwar/ui/chamfered_panel.py` 第 8–11 行：`_panel_surface_cache` 等 4 个缓存
- `airwar/ui/menu_background.py` 第 45–48 行：`_gradient_cache` 等 4 个缓存
- `airwar/ui/segmented_bar.py` 第 26 行：`_rendered_cache`
- `airwar/game/managers/bullet_manager.py` 第 52–53 行：`_batch_bullet_data`、`_batch_bullet_map`
- `airwar/game/systems/talent_balance_manager.py` 第 102 行：`locked`
- `airwar/scenes/death_scene.py` 第 40 行：`ripples`
- `tests/test_scene_manager.py` 第 20、22 行：`enter_calls`、`events`

### 5.2 数值类型隐式转换

多个位置将 `float` 赋值给声明为 `int` 的变量，或相反。典型位置：

- `airwar/game/mother_ship/mother_ship_motion.py` 第 124、152 行
- `airwar/game/explosion_animation/explosion_effect.py` 第 162、267 行
- `airwar/entities/enemy/enemy.py` 第 513、514 行
- `airwar/entities/movement_strategies.py` 第 78 行
- `airwar/scenes/death_scene.py` 第 109 行

### 5.3 `Optional` 默认参数未显式声明

现代 mypy 默认启用 `no_implicit_optional`，以下位置需要将默认值 `None` 改为 `Optional[T]`：

- `airwar/game/rendering/game_renderer.py` 第 38 行：`hud_renderer: HUDRenderer = None`
- `airwar/game/scene_director.py` 第 50 行：`viewport: ScaledViewport = None`
- `airwar/ui/segmented_bar.py` 第 211 行：`font: Font = None`
- `airwar/ui/effects.py` 第 157 行：`rect: Rect = None`

### 5.4 返回值类型与实现不符

- `airwar/ui/reward/reward_layout.py` 第 92、110 行：返回 `float` 元素但声明为 `int`
- `airwar/game/explosion_animation/explosion_pool.py` 第 41 行：可能返回 `None` 但声明为 `ExplosionEffect`
- `airwar/game/rendering/entity_renderer.py` 第 310 行：分支返回 `None` 但函数声明返回 `Surface`
- `airwar/window/window.py` 第 111、114 行：返回 `Surface | None` / `Clock | None` 但声明为非 Optional
- `airwar/scenes/scene.py` 第 261 行：返回 `Scene | None` 但声明为 `Scene`

### 5.5 实体接口与实现不一致

- `airwar/entities/enemy/boss/boss.py`
  - 第 247、248 行：`tuple[float, float] | None` 传给要求非 Optional 的参数
  - 第 421、423、425 行：未处理 `IBulletSpawner | None` 的 `None` 分支
  - 第 529 行：坐标元组类型不兼容
  - 第 530 行：访问不存在的 `_enrage_snapshot_target`（应为 `enrage_snapshot_target`）
- `airwar/entities/enemy/boss/boss_attack.py`
  - 第 218–220、255–256、285–287、485–487 行：`Bullet` 类型缺少 `held`、`clear_immune`、`enrage_release_delay`、`release_direction`、`enrage_release_speed` 等属性
- `airwar/entities/enemy/enemy_movement_batch.py`
  - 第 85、86、128–135 行：`Enemy` 类型缺少 `_rust_params`、`_timer_attr`、`_rust_move_type_code`
  - 修复建议：在 `Enemy` 类中声明这些属性，或将 `encode_rust_movement_params` 接收更具体的协议类型

## 6. 修复优先级与建议

### P0（立即修复，运行时崩溃风险）

1. 补齐 `design_tokens.py` 缺失的颜色/UI 常量，或全局替换引用。
2. 修复 `welcome_scene.py` 中 `Optional` 组件未判空的问题。
3. 修复 `persistence_manager.py` 中 `isinstance` 参数类型错误。
4. 修复 `state_machine.py` 中 `update` 方法签名覆盖错误。
5. 修复 `boss.py` 第 530 行对 `_enrage_snapshot_target` 的引用错误。

### P1（高优先级，接口健壮性）

1. 为 `IGameSceneAdapter`、`game_scene_event_dispatcher`、`game_scene_updater`、`scene_homecoming_dispatcher` 引入具体协议类型，替换 `object`。
2. 为 `airwar_core` 生成 `.pyi` 类型存根。
3. 统一 `pygame.Rect` 与项目内 `Rect` 的使用。
4. 处理 `spawn_controller.py`、`boss.py` 中的 `None`/字典 `object` 分支。

### P2（中优先级，代码可维护性）

1. 为缓存字典、集合、列表添加完整泛型类型注解。
2. 将 `hud_renderer`、`viewport`、`font`、`rect` 等默认 `None` 改为 `Optional[T]`。
3. 修正 `return-value` 与 `assignment` 类型不一致问题。
4. 为 `Enemy`/`Bullet` 补充 Rust/狂暴相关的属性声明。

### P3（低优先级，工程规范）

1. 在 `pyproject.toml` 中增加 `[tool.mypy]` 配置，约定目标版本与忽略规则。
2. 将 mypy 加入 CI/本地检查流程。
3. 清理 `truthy-function`、`abstract`、`method-assign` 等边缘问题。

## 7. 工作指引（后续行动清单）

1. **每次改动后执行**：
   ```bash
   python3 -m mypy airwar main.py tests --ignore-missing-imports --show-error-codes
   ```
2. **新增文件要求**：所有新增模块至少为公共函数/类添加类型签名；类属性使用泛型容器注解。
3. **修改既有文件时**：若改动涉及 `Optional` 组件、scene 转发、颜色常量，优先修复相关 mypy 错误，避免引入新的 `attr-defined`/`union-attr`。
4. **协议扩展流程**：新增 scene 能力时，先在 `airwar/scenes/game_scene_protocols.py`（或同类文件）更新 Protocol，再同步修改 adapter/updater/dispatcher。
5. **Rust 函数新增/变更**：同步更新 `airwar_core` 的 `.pyi` 存根与 `core_bindings.py` 的 fallback 实现签名。
6. **颜色常量新增**：统一在 `airwar/config/design_tokens.py` 的 `SystemColors`、`SceneColors`、`SystemUI` 中注册，禁止在业务代码中硬编码颜色元组。

## 8. 处理完成情况

> 由 Kimi Code 于 2026-07-10 完成 P0 / P1 全量修复后更新。

### 8.1 P0（立即修复）

- [x] 补齐 `design_tokens.py` 缺失的颜色/UI 常量（`AMBER_*`、`GOLD_*`、`FOREST_GREEN_*`、`MILITARY_*` 等）。
- [x] 修复 `welcome_scene.py` 中 `Optional` 组件未判空的问题。
- [x] 修复 `persistence_manager.py` 中 `isinstance` 参数类型错误。
- [x] 修复 `state_machine.py` 中 `update` 方法签名覆盖错误。
- [x] 修复 `boss.py` 第 530 行对 `_enrage_snapshot_target` 的引用错误。

### 8.2 P1（高优先级）

- [x] 为 `IGameSceneAdapter`、`game_scene_event_dispatcher`、`game_scene_updater`、`scene_homecoming_dispatcher` 引入 `GameSceneProtocol`，替换 `object`。
- [x] 为 `airwar_core` 生成 `.pyi` 类型存根，并在 `core_bindings.py` / `pyproject.toml` 中配置 mypy 识别路径。
- [x] 统一 `pygame.Rect` 与项目内 `Rect` 的使用（`base.Rect.colliderect` 接受 `_RectLike`）。
- [x] 处理 `spawn_controller.py`、`boss.py` 中的 `None`/字典 `object` 分支。

### 8.3 验证数据

| 模式 | 修复前 | 修复后 | 减少 |
|------|--------|--------|------|
| mypy 默认模式 | 653 | 277 | 376 |
| mypy 严格模式（`--check-untyped-defs`） | 721 | 312 | 409 |

测试：`pytest tests/` 全部通过（61 passed）。

## 9. 附录：原始扫描输出

- 默认模式完整输出：`/tmp/mypy_report_default.txt`
- 严格模式完整输出：`/tmp/mypy_report_strict.txt`

---
报告结束
