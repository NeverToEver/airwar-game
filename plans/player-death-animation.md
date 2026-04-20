# Plan: 战机死亡动画

> Source PRD: [docs/superpowers/specs/2026-04-21-player-death-animation-design.md](../docs/superpowers/specs/2026-04-21-player-death-animation-design.md)

## 架构决策

- **组件**: DeathAnimation 类，包含 SparkParticle 内部类
- **常量**: 所有动画参数提取为类常量（FLICKER_INTERVAL, SPARK_COUNT 等）
- **集成点**: GameRenderer._render_game() 方法
- **配置变更**: GameController.state.death_duration 从 6 改为 200

---

## Phase 1: 基础组件 + 火花粒子

**用户故事**: 战机死亡时产生火花粒子效果

### 构建内容

1. 创建 `airwar/game/death_animation/` 目录
2. 创建 `SparkParticle` 内部类（位置、速度、生命周期属性）
3. 创建 `DeathAnimation` 类基础结构：
   - `__init__()`: 初始化粒子列表、计时器
   - `trigger(x, y)`: 在指定位置触发动画
   - `update()`: 更新粒子状态
   - `is_active()`: 返回动画是否在进行
4. 实现 `_generate_sparks()`: 生成新火花粒子
5. 实现 `_update_sparks()`: 更新粒子位置和生命周期
6. 实现 `_render_sparks()`: 渲染火花粒子（黄-橙色渐变）

### 验收标准

- [ ] DeathAnimation 类可实例化
- [ ] `trigger()` 方法设置动画中心位置
- [ ] `update()` 返回 True 表示动画进行中
- [ ] 火花粒子从中心向外随机喷射
- [ ] 粒子生命周期结束自动移除
- [ ] 单元测试通过

---

## Phase 2: 闪烁效果

**用户故事**: 战机死亡时闪烁红/白色

### 构建内容

1. 实现 `_render_flicker()`: 闪烁效果渲染
2. 添加透明度切换逻辑（每4帧切换）
3. 添加红色叠加效果
4. 闪烁范围控制（0-60帧）

### 验收标准

- [ ] 战机在死亡位置快速闪烁
- [ ] 闪烁频率为每4帧一次
- [ ] 透明度在 255 和 80 之间切换
- [ ] 闪烁持续60帧后停止
- [ ] 单元测试通过

---

## Phase 3: 光晕效果

**用户故事**: 战机死亡时出现扩散至全屏的白色光晕

### 构建内容

1. 实现 `_render_glow()`: 光晕效果渲染
2. 计算屏幕对角线作为最大半径
3. 光晕从中心向外扩散
4. 透明度从150渐变到0
5. 光晕范围控制（60-180帧）

### 验收标准

- [ ] 光晕从战机位置开始
- [ ] 光晕半径从0扩展到屏幕对角线
- [ ] 光晕透明度从150渐变到0
- [ ] 光晕持续120帧（60-180帧）
- [ ] 单元测试通过

---

## Phase 4: 集成与测试

**用户故事**: 死亡动画与游戏流程完整集成

### 构建内容

1. 修改 `GameController.state.death_duration`: 6 → 200
2. 在 `GameRenderer.__init__()` 中初始化 DeathAnimation
3. 在 `GameRenderer._render_game()` 中添加死亡动画渲染逻辑
4. 创建集成测试验证动画与 Game Over 流程配合

### 验收标准

- [ ] GameController.death_duration = 200
- [ ] 玩家死亡时触发 DeathAnimation
- [ ] 死亡动画持续3.3秒后进入 Game Over
- [ ] 集成测试通过
- [ ] 所有现有测试继续通过

---

## 文件清单

| 文件 | Phase | 操作 |
|------|-------|------|
| `airwar/game/death_animation/__init__.py` | 1 | 新建 |
| `airwar/game/death_animation/death_animation.py` | 1-3 | 新建 |
| `airwar/game/controllers/game_controller.py` | 4 | 修改 |
| `airwar/game/rendering/game_renderer.py` | 4 | 修改 |
| `airwar/tests/test_death_animation.py` | 1-3 | 新建 |
| `airwar/tests/test_integration.py` | 4 | 修改 |

## 依赖关系

```
Phase 1 ──▶ Phase 2 ──▶ Phase 3 ──▶ Phase 4
  │            │            │           │
  └── 基础结构  ─┘            │           │
                    闪烁效果  ─┘           │
                              光晕效果  ──┘
                                        │
                              集成测试 ◄──┘
```
