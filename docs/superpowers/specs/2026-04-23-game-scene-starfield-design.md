# 游戏场景星空背景重构设计

Date: 2026-04-23
Author: AI Agent
Last Updated: 2026-04-23

## 概述

将游戏场景（GameScene）的星空背景从现有简单实现重构为更具科幻感的分层视差星空效果，同时确保60fps性能目标。

## 设计选择

| 维度 | 选择 | 理由 |
|------|------|------|
| 视觉风格 | 科幻感 | 高对比度，明亮星星带辉光、闪烁效果 |
| 运动方式 | 视差多层 | 远慢近快的深度感 |
| 性能策略 | 平衡方案 | 预渲染+缓存，确保60fps |
| 特殊效果 | 全部 | 流星、星云、闪烁星星群 |

## 架构设计

### 分层结构

```
┌─────────────────────────────────┐
│  Layer 3: 前景星空 (最快)        │ 速度: 2.0 px/frame
│  - 大星星 (size: 2.5-4.0)      │ 数量: 30颗
│  - 明亮辉光效果                │ 颜色: 白/淡蓝
├─────────────────────────────────┤
│  Layer 2: 中景星空 (中速)        │ 速度: 1.0 px/frame  
│  - 中等星星 (size: 1.5-2.5)    │ 数量: 60颗
│  - 闪烁效果                    │ 颜色: 蓝/淡紫
├─────────────────────────────────┤
│  Layer 1: 远景星空 (最慢)        │ 速度: 0.3 px/frame
│  - 小星星 (size: 0.5-1.5)     │ 数量: 150颗
│  - 微弱闪烁                    │ 颜色: 深蓝
├─────────────────────────────────┤
│  Layer 0: 动态星云背景          │ 速度: 0.1 px/frame
│  - 3-5个缓慢移动的彩色星云       │ Alpha: 15-25
└─────────────────────────────────┘
```

### 特效系统

#### 1. 流星效果
- 触发频率: 随机间隔5-15秒
- 拖尾长度: 5-8个渐隐段
- 速度: 8-15 px/frame
- 角度: 30-60度斜向

#### 2. 闪烁星星群
- 组成: 每群5-10颗星星
- 同步闪烁周期: 2-4秒
- 闪烁类型: 亮度+大小同时变化

#### 3. 动态星云
- 数量: 3-5个
- 颜色: 深紫/深蓝/深红
- Alpha: 15-25（微弱）
- 半径: 150-300px
- 移动: 缓慢向上漂移

## 性能优化策略

### 1. 预渲染缓存
```python
# 每层的星星状态预渲染到Surface
class StarLayer:
    def __init__(self, star_count, speed, size_range, color_range):
        self._render_cache = None
        self._needs_update = True
        
    def _pre_render(self):
        """预渲染整个层到单个Surface"""
        if not self._needs_update:
            return
        # 渲染所有星星到缓存Surface
        self._render_cache = pygame.Surface(...)
        self._needs_update = False
```

### 2. 环形缓冲区滚动
```python
class ScrollingLayer:
    def __init__(self, texture_height):
        self._offset = 0
        
    def scroll(self, delta):
        self._offset = (self._offset + delta) % self._texture_height
        # 使用2x屏幕高度的纹理循环滚动
```

### 3. 闪烁预计算
```python
import math

class TwinkleController:
    def __init__(self, star_count):
        self._phases = [random.random() * math.tau for _ in range(star_count)]
        self._time = 0
        
    def update(self, delta_time):
        self._time += delta_time
        
    def get_brightness(self, star_index):
        return 0.5 + 0.5 * math.sin(self._time * 0.05 + self._phases[star_index])
```

## 核心类设计

### StarLayer 类
```python
from typing import List, Optional, Tuple

class StarLayer:
    """单层星空渲染器"""
    
    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        star_count: int,
        speed: float,
        size_range: Tuple[float, float],
        color_base: Tuple[int, int, int],
        twinkle_enabled: bool = True
    ):
        self._stars = []
        self._scroll_offset = 0.0
        self._speed = speed
        self._screen_height = screen_height
        self._twinkle_enabled = twinkle_enabled
        self._twinkle = TwinkleController(star_count) if twinkle_enabled else None
        self._init_stars(screen_width, star_count, size_range, color_base)
        
    def _init_stars(self, screen_width, count, size_range, color_base):
        """初始化星星数据"""
        for _ in range(count):
            self._stars.append(Star(screen_width, self._screen_height, size_range, color_base))
            
    def update(self, delta_time: float = 1.0):
        """更新滚动偏移 - 与现有API兼容"""
        self._scroll_offset += self._speed * delta_time
        if self._twinkle:
            self._twinkle.update(delta_time)
        
    def render(self, surface: pygame.Surface):
        """渲染整层星星 - 与现有API兼容"""
        for i, star in enumerate(self._stars):
            y = (star.base_y + self._scroll_offset) % self._screen_height
            brightness = self._twinkle.get_brightness(i) if self._twinkle else 1.0
            star.draw(surface, y, brightness)
```

### NebulaLayer 类
```python
class NebulaLayer:
    """动态星云层"""
    
    def __init__(self, screen_width, screen_height, nebula_count: int = 4):
        self._nebulas = []
        self._scroll_offset = 0.0
        self._speed = 0.1
        
    def update(self, delta_time: float = 1.0):
        self._scroll_offset += self._speed * delta_time
        
    def render(self, surface: pygame.Surface):
        for nebula in self._nebulas:
            y = (nebula.base_y + self._scroll_offset) % self._screen_height
            nebula.draw(surface, y)
```

### MeteorSystem 类
```python
class MeteorSystem:
    """流星效果系统"""
    
    def __init__(self):
        self._meteors = []
        self._next_spawn_time = random.uniform(5, 15)
        
    def update(self, delta_time: float = 1.0):
        self._next_spawn_time -= delta_time
        if self._next_spawn_time <= 0:
            self._spawn_meteor()
            self._next_spawn_time = random.uniform(5, 15)
            
        for meteor in self._meteors:
            meteor.update(delta_time)
        self._meteors = [m for m in self._meteors if m.is_alive]
        
    def render(self, surface: pygame.Surface):
        for meteor in self._meteors:
            meteor.draw(surface)
```

## 数据结构

### Star
```python
class Star:
    """单个星星"""
    _glow_cache = {}
    
    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        size_range: Tuple[float, float],
        color_base: Tuple[int, int, int]
    ):
        self.base_x = random.randint(0, screen_width)
        self.base_y = random.randint(0, screen_height)
        self.size = random.uniform(size_range[0], size_range[1])
        self.speed = random.uniform(0.5, 2.0)
        self.brightness = random.randint(100, 255)
        self.twinkle_speed = random.uniform(0.02, 0.08)
        self.twinkle_offset = random.uniform(0, math.tau)
        self.color = color_base
        self._cached_glow = None
```

### Nebula
```python
class Nebula:
    """星云效果"""
    _nebula_cache = {}
    
    def __init__(self, screen_width, screen_height):
        self.x = random.randint(-200, screen_width + 200)
        self.base_y = random.randint(0, screen_height)
        self.radius = random.randint(100, 250)
        self.color = random.choice([
            (60, 20, 80),
            (20, 40, 80),
            (40, 60, 80),
            (80, 30, 60),
            (30, 60, 80)
        ])
        self.alpha = random.randint(15, 35)
        self.speed = random.uniform(0.1, 0.3)
        self._cached_surface = None
```

### Meteor
```python
class Meteor:
    """流星效果"""
    
    def __init__(self, screen_width, screen_height):
        self.x = random.randint(0, screen_width)
        self.y = random.randint(-50, 0)
        self.speed = random.uniform(8, 15)
        self.angle = math.radians(random.uniform(30, 60))
        self.trail = []
        self.life = random.randint(30, 60)
        self.max_life = self.life
```

## API接口 - 与现有代码兼容

```python
class GameSceneBackground:
    """游戏场景星空背景主控制器 - 兼容现有API"""
    
    def __init__(self, screen_width: int = 800, screen_height: int = 600):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.time = 0
        
        # 三层视差星空
        self._layer_far = StarLayer(screen_width, screen_height, 150, 0.3, (0.5, 1.5), (100, 150, 200))
        self._layer_mid = StarLayer(screen_width, screen_height, 60, 1.0, (1.5, 2.5), (150, 180, 255))
        self._layer_near = StarLayer(screen_width, screen_height, 30, 2.0, (2.5, 4.0), (200, 220, 255))
        
        # 星云层
        self._nebula_layer = NebulaLayer(screen_width, screen_height)
        
        # 流星系统
        self._meteor_system = MeteorSystem()
        
        # 粒子效果（保留用于爆炸等）
        self.particles = []
        
        # 渐变缓存
        self._cached_gradient = None
        self._generate_gradient()
        
    def update(self, delta_time: float = 1.0):
        """更新 - 与现有GameSceneBackground.update()兼容"""
        self.time += delta_time
        self._layer_far.update(delta_time)
        self._layer_mid.update(delta_time)
        self._layer_near.update(delta_time)
        self._nebula_layer.update(delta_time)
        self._meteor_system.update(delta_time)
        self.particles = [p for p in self.particles if self._update_particle(p)]
        
    def draw(self, surface: pygame.Surface):
        """渲染 - 与现有GameSceneBackground.draw()兼容"""
        if self._cached_gradient:
            surface.blit(self._cached_gradient, (0, 0))
        
        self._nebula_layer.render(surface)
        self._layer_far.render(surface)
        self._meteor_system.render(surface)
        self._layer_mid.render(surface)
        self._layer_near.render(surface)
        
        for particle in self.particles:
            self._draw_particle(surface, particle)
            
    def resize(self, screen_width: int, screen_height: int):
        """窗口大小改变时重新初始化 - 与现有API兼容"""
        self.screen_width = screen_width
        self.screen_height = screen_height
        self._layer_far = StarLayer(screen_width, screen_height, 150, 0.3, (0.5, 1.5), (100, 150, 200))
        self._layer_mid = StarLayer(screen_width, screen_height, 60, 1.0, (1.5, 2.5), (150, 180, 255))
        self._layer_near = StarLayer(screen_width, screen_height, 30, 2.0, (2.5, 4.0), (200, 220, 255))
        self._nebula_layer = NebulaLayer(screen_width, screen_height)
        self._meteor_system = MeteorSystem()
        self._generate_gradient()
        
    def spawn_particle(self, x: float, y: float, color: tuple):
        """生成粒子 - 保留现有API"""
        for _ in range(5):
            self.particles.append({
                'x': x,
                'y': y,
                'vx': random.uniform(-1, 1),
                'vy': random.uniform(-2, 0),
                'size': random.uniform(1, 3),
                'life': random.randint(20, 40),
                'color': color
            })
```

## 性能目标

| 指标 | 目标 | 测量方法 |
|------|------|----------|
| FPS | 60fps稳定 | delta_time约16.67ms |
| CPU占用 | <5% | profile测试 |
| 内存占用 | <20MB | tracemalloc |

## 实现步骤

1. 创建 `TwinkleController` 类实现闪烁预计算
2. 实现 `Star` 和 `StarLayer` 类
3. 实现 `Nebula` 和 `NebulaLayer` 类
4. 创建 `Meteor` 和 `MeteorSystem` 类
5. 重构 `GameSceneBackground` 主控制器
6. 替换 `GameScene` 中的背景引用
7. 添加性能测试验证

## 文件结构

保持单文件结构，重构现有文件：

```
airwar/game/rendering/
└── game_rendering_background.py  # 重构此文件
    ├── class TwinkleController (新增)
    ├── class Star (重构)
    ├── class StarLayer (新增)
    ├── class Nebula (重构)
    ├── class NebulaLayer (新增)
    ├── class Meteor (新增)
    ├── class MeteorSystem (新增)
    └── class GameSceneBackground (重构)
```

## 兼容性说明

- ✅ `update()` - 添加delta_time参数但保持向后兼容
- ✅ `draw()` - 无参数变化
- ✅ `resize()` - 保持现有签名
- ✅ `spawn_particle()` - 保留用于爆炸粒子

---

*设计状态: 已修正，可实施*
