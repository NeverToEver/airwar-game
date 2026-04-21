# Scene Renderer 重构设计方案

**文档版本**: 1.0
**创建日期**: 2026-04-21
**状态**: 待实施
**实施者**: AI Agent

---

## 1. 背景与目标

### 1.1 问题描述

当前项目 `airwar/scenes/` 目录下的 5 个场景类（MenuScene、LoginScene、DeathScene、ExitConfirmScene、PauseScene）存在以下问题：

1. **严重的代码重复** — 4 个渲染方法在 5 个文件中几乎完全相同：
   - `_draw_gradient_background()`
   - `_draw_stars()`
   - `_draw_particles()`
   - `_draw_glow_text()`

2. **性能问题** — 每帧渲染时重复创建 Surface 对象：
   - 粒子效果：每个粒子每帧创建 3-5 层 Surface
   - 光晕效果：每帧重复渲染文字多次
   - 背景渐变：逐像素绘制（720p 需要 720 次循环）

### 1.2 重构目标

1. 消除代码重复（DRY 原则）
2. 优化渲染性能（Surface 缓存、预渲染）
3. 提高代码可维护性
4. 保持现有功能不变

---

## 2. 技术方案

### 2.1 目录结构

```
airwar/scenes/
├── base/
│   ├── __init__.py
│   └── base_scene.py          # 基础场景类 (可选，待评估)
├── ui/
│   ├── __init__.py
│   ├── background.py           # 背景渲染器 (渐变、星星)
│   ├── particles.py            # 粒子系统 (Flyweight 模式)
│   └── effects.py             # 特效渲染器 (发光文字等)
├── menu_scene.py               # 保持不变，使用新渲染器
├── game_scene.py               # 保持不变
├── death_scene.py              # 重构使用新渲染器
├── pause_scene.py              # 重构使用新渲染器
├── login_scene.py              # 重构使用新渲染器
├── exit_confirm_scene.py       # 重构使用新渲染器
├── tutorial_scene.py           # 保持不变
└── scene.py                    # 保持不变 (接口定义)
```

### 2.2 核心组件设计

#### 2.2.1 `BackgroundRenderer` (背景渲染器)

**位置**: `airwar/scenes/ui/background.py`

```python
class BackgroundRenderer:
    """背景渲染器 — 负责渐变背景和星星效果"""

    def __init__(self):
        self._stars = []
        self._animation_time = 0
        self._gradient_cache = {}  # 尺寸 -> Surface 缓存
        self._init_stars()

    def _init_stars(self):
        """初始化星星数据"""
        import random
        self._stars = []
        for _ in range(100):
            self._stars.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(0.5, 2.0),
                'brightness': random.randint(50, 150),
                'twinkle_speed': random.uniform(0.03, 0.08),
                'twinkle_offset': random.random() * math.pi * 2,
            })

    def _get_cached_gradient(self, surface: pygame.Surface, bg_color: tuple, gradient_color: tuple) -> pygame.Surface:
        """获取或创建渐变背景缓存"""
        width, height = surface.get_size()
        cache_key = (width, height, bg_color, gradient_color)

        if cache_key not in self._gradient_cache:
            gradient = pygame.Surface((width, height))
            for y in range(0, height, 3):
                ratio = y / height
                r = int(bg_color[0] * (1 - ratio) + gradient_color[0] * ratio)
                g = int(bg_color[1] * (1 - ratio) + gradient_color[1] * ratio)
                b = int(bg_color[2] * (1 - ratio) + gradient_color[2] * ratio)
                pygame.draw.line(gradient, (r, g, b), (0, y), (width, y))
            self._gradient_cache[cache_key] = gradient

        return self._gradient_cache[cache_key]

    def update(self):
        """更新动画状态"""
        self._animation_time += 1
        for star in self._stars:
            star['y'] += 0.008
            if star['y'] > 1:
                star['y'] = 0
                import random
                star['x'] = random.random()

    def render(self, surface: pygame.Surface, colors: dict):
        """渲染背景"""
        gradient = self._get_cached_gradient(
            surface,
            colors['bg'],
            colors.get('bg_gradient', colors['bg'])
        )
        surface.blit(gradient, (0, 0))

        # 渲染星星
        width, height = surface.get_size()
        import math
        for star in self._stars:
            x = int(star['x'] * width)
            y = int(star['y'] * height)
            twinkle = math.sin(self._animation_time * star['twinkle_speed'] + star['twinkle_offset'])
            brightness = int(star['brightness'] * (0.5 + 0.5 * twinkle))
            pygame.draw.circle(surface, (brightness, brightness, brightness + 30), (x, y), int(star['size']))
```

#### 2.2.2 `ParticleSystem` (粒子系统)

**位置**: `airwar/scenes/ui/particles.py`

```python
class ParticleSystem:
    """粒子系统 — 使用 Flyweight 模式缓存粒子纹理"""

    _texture_cache: dict = {}

    def __init__(self):
        self._particles = []
        self._animation_time = 0
        self._init_cache()

    def _init_cache(self):
        """预创建常用尺寸的粒子纹理"""
        for base_size in [8, 12, 16, 20]:
            for color_key in ['particle', 'particle_alt']:
                key = (base_size, color_key)
                if key not in self._texture_cache:
                    surf = pygame.Surface((base_size * 4, base_size * 4), pygame.SRCALPHA)
                    for i in range(base_size * 2, 0, -2):
                        layer_alpha = int(180 * (base_size * 2 - i) / (base_size * 2) * 0.4)
                        pygame.draw.circle(
                            surf,
                            (100, 180, 255, layer_alpha),
                            (base_size * 2, base_size * 2),
                            i
                        )
                    self._texture_cache[key] = surf

    def _init_particles(self, count: int = 40, color_key: str = 'particle'):
        """初始化粒子数据"""
        import random
        self._particles = []
        for _ in range(count):
            self._particles.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(1.5, 3.5),
                'speed': random.uniform(0.3, 0.9),
                'alpha': random.randint(80, 180),
                'pulse_speed': random.uniform(0.02, 0.05),
                'pulse_offset': random.random() * math.pi * 2,
                'color_key': color_key,
            })

    def update(self, direction: float = -1):
        """更新粒子状态

        Args:
            direction: 移动方向，-1 表示向上，1 表示向下
        """
        import random
        for p in self._particles[:]:
            p['y'] += p['speed'] * 0.003 * direction
            if p['y'] < -0.1:
                p['y'] = 1.1
                p['x'] = random.random()
                p['alpha'] = random.randint(80, 180)

    def render(self, surface: pygame.Surface, color: tuple):
        """渲染粒子

        Args:
            surface: 目标 surface
            color: 粒子颜色 (r, g, b)
        """
        width, height = surface.get_size()
        import math

        for p in self._particles:
            x = int(p['x'] * width)
            y = int(p['y'] * height)
            pulse = math.sin(self._animation_time * p['pulse_speed'] + p['pulse_offset'])
            alpha = int(p['alpha'] * (0.6 + 0.4 * pulse))
            size = int(p['size'] * (0.7 + 0.3 * pulse))

            # 使用缓存的纹理
            cache_key = (size, p.get('color_key', 'particle'))
            if cache_key in self._texture_cache:
                particle_surf = self._texture_cache[cache_key].copy()
                particle_surf.set_alpha(alpha)
                surface.blit(particle_surf, (x - size * 2, y - size * 2))
            else:
                # 回退：动态创建
                particle_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
                for i in range(size * 2, 0, -2):
                    layer_alpha = int(alpha * (size * 2 - i) / (size * 2) * 0.4)
                    pygame.draw.circle(particle_surf, (*color, layer_alpha),
                                     (size * 2, size * 2), i)
                surface.blit(particle_surf, (x - size * 2, y - size * 2))

    def reset(self, count: int = 40, color_key: str = 'particle'):
        """重置粒子系统"""
        self._animation_time = 0
        self._init_particles(count, color_key)
```

#### 2.2.3 `EffectsRenderer` (特效渲染器)

**位置**: `airwar/scenes/ui/effects.py`

```python
class EffectsRenderer:
    """特效渲染器 — 负责发光文字等视觉效果"""

    def __init__(self):
        self._glow_cache = {}  # (text, font_size, color) -> Surface

    def render_glow_text(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        pos: tuple,
        color: tuple,
        glow_color: tuple,
        glow_radius: int = 3
    ):
        """渲染发光文字

        Args:
            surface: 目标 surface
            text: 文字内容
            font: pygame 字体对象
            pos: 位置 (x, y)
            color: 主颜色
            glow_color: 发光颜色
            glow_radius: 发光半径
        """
        for i in range(glow_radius, 0, -1):
            alpha = int(100 / i)
            glow_surf = font.render(text, True, glow_color)
            glow_surf.set_alpha(alpha)
            glow_rect = glow_surf.get_rect(center=(pos[0], pos[1] + i))
            surface.blit(glow_surf, glow_rect)

        main_text = font.render(text, True, color)
        surface.blit(main_text, main_text.get_rect(center=pos))

    def render_option_box(
        self,
        surface: pygame.Surface,
        text: str,
        y: int,
        is_selected: bool,
        colors: dict,
        option_width: int = 350,
        option_height: int = 60,
        scale: float = 1.0
    ):
        """渲染选项框

        Args:
            surface: 目标 surface
            text: 选项文字
            y: Y 坐标 (中心点)
            is_selected: 是否选中
            colors: 颜色字典
            option_width: 选项宽度
            option_height: 选项高度
            scale: 缩放因子
        """
        from airwar.utils.responsive import ResponsiveHelper

        width = surface.get_width()
        center_x = width // 2

        box_width = ResponsiveHelper.scale(option_width, scale)
        box_height = ResponsiveHelper.scale(option_height, scale)
        box_rect = pygame.Rect(center_x - box_width // 2, y - box_height // 2, box_width, box_height)

        if is_selected:
            glow_color = colors.get('selected_glow', (0, 200, 255))
            for i in range(4, 0, -1):
                glow_rect = box_rect.inflate(i * 4, i * 4)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*glow_color, 50 // i), glow_surf.get_rect())
                surface.blit(glow_surf, glow_rect)

            pygame.draw.rect(surface, (25, 35, 65), box_rect, border_radius=12)
            pygame.draw.rect(surface, colors.get('selected', (0, 255, 150)), box_rect, 3, border_radius=12)
        else:
            pygame.draw.rect(surface, (18, 20, 40), box_rect, border_radius=12)
            pygame.draw.rect(surface, colors.get('unselected', (90, 90, 130)), box_rect, 2, border_radius=12)

        arrow = ">> " if is_selected else "   "
        option_text = pygame.font.Font(None, 48).render(f"{arrow}{text}", True,
            colors.get('selected', (0, 255, 150)) if is_selected else colors.get('unselected', (90, 90, 130)))
        text_rect = option_text.get_rect(center=(center_x, y))
        surface.blit(option_text, text_rect)
```

---

## 3. 迁移指南

### 3.1 MenuScene 重构

**文件**: `airwar/scenes/menu_scene.py`

**修改点**:

1. 添加导入：
```python
from airwar.scenes.ui.background import BackgroundRenderer
from airwar.scenes.ui.particles import ParticleSystem
from airwar.scenes.ui.effects import EffectsRenderer
```

2. 在 `__init__` 中替换：
```python
# 删除 self.particles, self.stars 初始化
# 删除 _init_particles, _init_stars 方法

# 添加：
self._background_renderer = BackgroundRenderer()
self._particle_system = ParticleSystem()
self._effects_renderer = EffectsRenderer()
self._particle_system.reset(40, 'particle')
```

3. 修改 `update` 方法：
```python
def update(self, *args, **kwargs) -> None:
    import random
    self.animation_time += 1
    self.glow_offset = math.sin(self.animation_time * 0.05) * 12

    self._background_renderer._animation_time = self.animation_time
    self._background_renderer.update()

    self._particle_system._animation_time = self.animation_time
    self._particle_system.update(direction=-1)
```

4. 修改 `render` 方法：
```python
def render(self, surface: pygame.Surface) -> None:
    width, height = surface.get_size()
    scale = ResponsiveHelper.get_scale_factor(width, height)
    self._init_fonts(scale)

    # 使用新的渲染器
    self._background_renderer.render(surface, self.colors)
    self._particle_system.render(surface, self.colors['particle'])

    self._draw_title_section(surface)
    self._draw_panel(surface)
    # ... 其余代码保持不变
```

5. **删除以下方法**：
   - `_draw_gradient_background`
   - `_draw_stars`
   - `_draw_particles`

### 3.2 DeathScene 重构

**文件**: `airwar/scenes/death_scene.py`

类似 MenuScene 的修改，但注意：
- DeathScene 有额外的 `_draw_ripples` 方法，需要保留
- 颜色方案略有不同，使用 `self.colors`

### 3.3 其他场景

ExitConfirmScene、PauseScene、LoginScene 按照相同模式重构。

---

## 4. 性能优化预期

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| Surface 创建/帧 | ~900+ | <20 | **95%+** |
| 渐变背景绘制 | 720 次/帧 | 1 次 (缓存) | **显著** |
| 粒子纹理创建 | 每帧 200+ 次 | 4 次 (预缓存) | **95%+** |
| 重复代码行数 | ~600 行 | 0 行 | **消除** |

---

## 5. 注意事项

### 5.1 兼容性

- 保持 `Scene` 基类接口不变
- 所有场景的公开方法签名保持不变
- 动画效果保持一致

### 5.2 缓存管理

- `BackgroundRenderer._gradient_cache` 会在首次创建后永久保留
- 如果内存成为问题，可以添加 LRU 淘汰策略
- 粒子纹理缓存为类级别共享

### 5.3 测试建议

1. 重构后运行所有现有测试
2. 手动测试每个场景的视觉效果
3. 对比优化前后的帧率（如果可测量）

---

## 6. 实施步骤

| 步骤 | 任务 | 依赖 |
|------|------|------|
| 1 | 创建 `airwar/scenes/ui/` 目录 | - |
| 2 | 实现 `background.py` | 1 |
| 3 | 实现 `particles.py` | 1 |
| 4 | 实现 `effects.py` | 1 |
| 5 | 重构 `menu_scene.py` | 2, 3, 4 |
| 6 | 重构 `death_scene.py` | 2, 3, 4 |
| 7 | 重构 `exit_confirm_scene.py` | 2, 3, 4 |
| 8 | 重构 `pause_scene.py` | 2, 3, 4 |
| 9 | 重构 `login_scene.py` | 2, 3, 4 |
| 10 | 验证所有场景功能 | 5, 6, 7, 8, 9 |
| 11 | 运行测试套件 | 10 |

---

## 7. 文件清单

### 新建文件

| 文件路径 | 描述 |
|----------|------|
| `airwar/scenes/ui/__init__.py` | 包初始化 |
| `airwar/scenes/ui/background.py` | 背景渲染器 |
| `airwar/scenes/ui/particles.py` | 粒子系统 |
| `airwar/scenes/ui/effects.py` | 特效渲染器 |

### 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `airwar/scenes/menu_scene.py` | 使用新渲染器，删除重复方法 |
| `airwar/scenes/death_scene.py` | 使用新渲染器，删除重复方法 |
| `airwar/scenes/exit_confirm_scene.py` | 使用新渲染器，删除重复方法 |
| `airwar/scenes/pause_scene.py` | 使用新渲染器，删除重复方法 |
| `airwar/scenes/login_scene.py` | 使用新渲染器，删除重复方法 |

### 保持不变

| 文件路径 | 原因 |
|----------|------|
| `airwar/scenes/scene.py` | 接口定义，无需修改 |
| `airwar/scenes/game_scene.py` | 已有独立的渲染系统 |
| `airwar/scenes/tutorial_scene.py` | 已有独立的渲染组件 |

---

**文档结束**
