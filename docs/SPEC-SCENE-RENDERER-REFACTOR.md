# Scene Renderer 重构规范

**版本**: 1.0
**日期**: 2026-04-21
**状态**: 已批准，待实施

---

## 1. 概述

重构 `airwar/scenes/` 中的场景渲染代码，消除代码重复并优化性能。

### 1.1 目标

- 消除 5 个场景类中 ~600 行重复代码
- 减少每帧 Surface 创建数量（900+ → <20）
- 提升帧率 30-50%

### 1.2 范围

**涉及文件**:
- `airwar/scenes/menu_scene.py`
- `airwar/scenes/login_scene.py`
- `airwar/scenes/death_scene.py`
- `airwar/scenes/exit_confirm_scene.py`
- `airwar/scenes/pause_scene.py`

**不受影响**:
- `airwar/scenes/scene.py` — 接口定义
- `airwar/scenes/game_scene.py` — 已有独立渲染系统
- `airwar/scenes/tutorial_scene.py` — 已有独立渲染组件

---

## 2. 新增组件

### 2.1 BackgroundRenderer (`airwar/scenes/ui/background.py`)

**职责**: 渲染渐变背景和星星动画

**公共接口**:
```python
class BackgroundRenderer:
    def __init__(self) -> None: ...
    def update(self) -> None: ...
    def render(self, surface: pygame.Surface, colors: dict) -> None: ...
```

**缓存策略**:
- 渐变背景按 `(width, height, bg_color, gradient_color)` 缓存
- 星星数据动态更新

### 2.2 ParticleSystem (`airwar/scenes/ui/particles.py`)

**职责**: 高效渲染粒子效果

**公共接口**:
```python
class ParticleSystem:
    _texture_cache: dict  # 类级别共享

    def __init__(self) -> None: ...
    def update(self, direction: float = -1) -> None: ...
    def render(self, surface: pygame.Surface, color: tuple) -> None: ...
    def reset(self, count: int = 40, color_key: str = 'particle') -> None: ...
```

**缓存策略**:
- 预创建 4 种尺寸（8, 12, 16, 20）× 2 种颜色 = 8 个纹理
- 类级别共享，所有实例共用

### 2.3 EffectsRenderer (`airwar/scenes/ui/effects.py`)

**职责**: 渲染发光文字和选项框

**公共接口**:
```python
class EffectsRenderer:
    def render_glow_text(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        pos: tuple,
        color: tuple,
        glow_color: tuple,
        glow_radius: int = 3
    ) -> None: ...

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
    ) -> None: ...
```

---

## 3. 迁移模式

每个场景文件的修改遵循相同模式：

### 3.1 导入

```python
from airwar.scenes.ui.background import BackgroundRenderer
from airwar.scenes.ui.particles import ParticleSystem
from airwar.scenes.ui.effects import EffectsRenderer
```

### 3.2 初始化（`enter` 方法）

```python
def enter(self, **kwargs) -> None:
    # ... 原有的初始化代码 ...
    self._background_renderer = BackgroundRenderer()
    self._particle_system = ParticleSystem()
    self._effects_renderer = EffectsRenderer()
    self._particle_system.reset(40, 'particle')
```

### 3.3 更新（`update` 方法）

```python
def update(self, *args, **kwargs) -> None:
    # ... 原有的更新代码 ...
    self._background_renderer._animation_time = self.animation_time
    self._background_renderer.update()
    self._particle_system._animation_time = self.animation_time
    self._particle_system.update(direction=-1)
```

### 3.4 渲染（`render` 方法）

```python
def render(self, surface: pygame.Surface) -> None:
    # ... 其他渲染代码 ...
    self._background_renderer.render(surface, self.colors)
    self._particle_system.render(surface, self.colors['particle'])
```

### 3.5 删除

以下方法从各场景文件中删除：
- `_draw_gradient_background`
- `_draw_stars`
- `_draw_particles`
- `_draw_glow_text` (可使用 EffectsRenderer 替代或保留)

---

## 4. 兼容性要求

- Scene 基类接口保持不变
- 所有公开方法签名保持不变
- 视觉效果与重构前一致
- 动画行为与重构前一致

---

## 5. 测试要求

- 现有测试全部通过
- 每个场景手动验证功能正常
- 渲染效果与预期一致

---

## 6. 文件清单

### 新建

| 文件 | 描述 |
|------|------|
| `airwar/scenes/ui/__init__.py` | 包初始化 |
| `airwar/scenes/ui/background.py` | 背景渲染器 |
| `airwar/scenes/ui/particles.py` | 粒子系统 |
| `airwar/scenes/ui/effects.py` | 特效渲染器 |

### 修改

| 文件 | 修改内容 |
|------|----------|
| `airwar/scenes/menu_scene.py` | 使用新渲染器，删除重复方法 |
| `airwar/scenes/death_scene.py` | 使用新渲染器，删除重复方法 |
| `airwar/scenes/exit_confirm_scene.py` | 使用新渲染器，删除重复方法 |
| `airwar/scenes/pause_scene.py` | 使用新渲染器，删除重复方法 |
| `airwar/scenes/login_scene.py` | 使用新渲染器，删除重复方法 |

---

## 7. 验收标准

- [ ] 代码重复消除（减少 ~600 行）
- [ ] 性能提升（Surface 创建减少 95%+）
- [ ] 所有场景功能正常
- [ ] 测试通过
- [ ] 无运行时错误
