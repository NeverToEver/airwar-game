# 战机死亡动画设计方案

**版本**: 1.0
**创建日期**: 2026-04-21
**状态**: 已审查

## 1. 功能概述

为战机死亡添加视觉效果动画，包含三个阶段：
1. **闪烁效果**: 战机在死亡位置快速闪烁红/白色
2. **火花爆裂**: 从战机位置随机喷射火花粒子
3. **光晕扩散**: 白色光晕从中心向外扩散至全屏

动画持续约3.3秒（200帧），动画结束后触发原有死亡流程（Game Over）。

## 2. 视觉风格

保持赛博朋克/霓虹灯视觉风格，与游戏整体设计一致：
- 闪烁颜色: 红色 (255, 50, 50) 与 白色 (255, 255, 255) 交替
- 火花颜色: 黄色 (255, 200, 50) 到橙色 (255, 100, 0) 渐变
- 光晕颜色: 白色 (255, 255, 255, 150) 渐变至透明

## 3. 动画时间线

| 帧数 | 阶段 | 效果 |
|------|------|------|
| 0-60 | 阶段1: 闪烁 | 战机快速闪烁，每4帧切换一次透明度 |
| 0-180 | 阶段2: 火花 | 持续生成火花粒子，从中心向外喷射 |
| 60-180 | 阶段3: 光晕 | 光晕半径从0扩展到屏幕对角线 |
| 200 | 结束 | 动画完成，触发 Game Over |

## 4. 架构设计

### 4.1 组件结构

```
airwar/game/death_animation/
├── __init__.py
└── death_animation.py
    ├── SparkParticle (内部类)
    └── DeathAnimation (主类)
```

### 4.2 DeathAnimation 类

```python
class SparkParticle:
    """火花粒子数据类"""
    x: float           # x坐标
    y: float           # y坐标
    vx: float          # x方向速度
    vy: float          # y方向速度
    life: int          # 剩余生命周期
    max_life: int      # 最大生命周期
    size: float        # 粒子大小

class DeathAnimation:
    """死亡动画组件"""
    def trigger(self, x: int, y: int) -> None
        """在指定位置触发动画

        Args:
            x: 战机中心x坐标
            y: 战机中心y坐标
        """
    def update(self) -> bool
        """更新动画状态

        Returns:
            bool: True表示动画仍在进行，False表示动画已结束
        """
    def render(self, surface: pygame.Surface) -> None
        """渲染所有动画效果

        Args:
            surface: pygame渲染表面
        """
    def is_active(self) -> bool
        """检查动画是否在进行中

        Returns:
            bool: True表示正在进行
        """
```

### 4.3 渲染集成

为保持渲染层统一，将 DeathAnimation 集成到 GameRenderer 中：

```python
class GameRenderer:
    def __init__(self, ...):
        self.death_animation = DeathAnimation()
        ...

    def _render_game(self, surface, state, entities):
        # ... 现有逻辑 ...

        # 死亡动画渲染（在玩家渲染之后）
        if state.gameplay_state == GameplayState.DYING:
            if not self.death_animation.is_active():
                self.death_animation.trigger(
                    entities.player.rect.centerx,
                    entities.player.rect.centery
                )
            self.death_animation.render(surface)
```

## 5. 详细实现

### 5.1 闪烁效果

- **条件**: 帧0-60内
- **频率**: 每4帧切换透明度
- **透明度**: 255 ↔ 80
- **实现**: 重新渲染玩家精灵，应用透明度调整和红色叠加

### 5.2 火花粒子系统

- **生成频率**: 每3帧生成3-5个新粒子
- **粒子生命周期**: 60-90帧
- **初始速度**: 随机方向，速度2-5像素/帧
- **运动**: 简单直线运动，带轻微重力效果
- **颜色**: 根据剩余生命周期，从黄色渐变到橙色
- **大小**: 初始2-4像素，逐渐缩小

```python
def _generate_sparks(self) -> None:
    """生成新的火花粒子"""
    count = random.randint(3, 5)
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 5)
        self._sparks.append(SparkParticle(
            x=self._center_x,
            y=self._center_y,
            vx=math.cos(angle) * speed,
            vy=math.sin(angle) * speed,
            life=random.randint(60, 90),
            max_life=random.randint(60, 90),
            size=random.uniform(2, 4)
        ))

def _update_sparks(self) -> None:
    """更新所有火花粒子"""
    for spark in self._sparks:
        spark.x += spark.vx
        spark.y += spark.vy
        spark.vy += 0.05  # 轻微重力
        spark.life -= 1
    self._sparks = [s for s in self._sparks if s.life > 0]
```

### 5.3 光晕效果

- **起始帧**: 60
- **结束帧**: 180
- **起始半径**: 0
- **结束半径**: screen_diagonal（屏幕对角线长度）
- **透明度**: 从150渐变到0
- **颜色**: 白色 (255, 255, 255)

```python
def _render_glow(self, surface: pygame.Surface) -> None:
    """渲染扩散光晕"""
    if self._timer < 60:
        return

    progress = (self._timer - 60) / 120  # 60-180帧的进度
    max_radius = self._screen_diagonal

    radius = int(max_radius * progress)
    alpha = int(150 * (1 - progress))

    glow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (255, 255, 255, alpha), (radius, radius), radius)
    surface.blit(glow_surf, (self._center_x - radius, self._center_y - radius))
```

## 6. 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `airwar/game/death_animation/__init__.py` | 新建 | 模块导出 |
| `airwar/game/death_animation/death_animation.py` | 新建 | DeathAnimation 组件 |
| `airwar/game/controllers/game_controller.py` | 修改 | death_duration: 6 → 200 |
| `airwar/game/rendering/game_renderer.py` | 修改 | 集成 DeathAnimation |

## 7. 测试计划

### 7.1 单元测试

- `test_death_animation_trigger()`: 测试触发功能
- `test_death_animation_update()`: 测试更新逻辑
- `test_death_animation_spark_lifecycle()`: 测试火花粒子生命周期
- `test_death_animation_glow_progress()`: 测试光晕进度
- `test_death_animation_is_active()`: 测试激活状态

### 7.2 集成测试

- `test_death_animation_plays_on_player_death()`: 测试玩家死亡时动画触发
- `test_death_animation_duration_matches_game_over()`: 测试动画时长与 Game Over 匹配

## 8. 已知约束

1. 死亡动画期间玩家无敌（由 GameController.state.player_invincible 控制）
2. 动画时长 (200帧 ≈ 3.3秒) 必须与 GameController.state.death_duration 一致
3. 闪烁效果直接访问 Player 精灵，需要确保精灵资源已加载

## 9. 性能考虑

- 火花粒子数量上限: 100个（超出时停止生成）
- 使用对象池模式复用 SparkParticle（可选优化）
- 光晕使用单次绘制的圆形而非渐变复杂计算
