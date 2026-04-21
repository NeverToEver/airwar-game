# Scene Renderer 重构任务清单

**设计文档**: `docs/REFACTOR-DESIGN-SCENE-RENDERER.md`

---

## 任务 1: 创建 UI 渲染组件目录

**文件**: `airwar/scenes/ui/__init__.py`

```python
"""Scene UI Components

提供场景共用的渲染组件，包括背景、粒子系统、特效渲染等。
使用 Flyweight 模式优化性能。
"""

from airwar.scenes.ui.background import BackgroundRenderer
from airwar.scenes.ui.particles import ParticleSystem
from airwar.scenes.ui.effects import EffectsRenderer

__all__ = [
    'BackgroundRenderer',
    'ParticleSystem',
    'EffectsRenderer',
]
```

**验证**: 文件创建成功，导入无错误

---

## 任务 2: 实现 BackgroundRenderer

**文件**: `airwar/scenes/ui/background.py`

**要求**:
1. 实现 `_get_cached_gradient()` 方法，支持渐变背景缓存
2. 实现 `_init_stars()` 方法，初始化 100 颗星星
3. 实现 `update()` 方法，更新星星位置
4. 实现 `render()` 方法，渲染渐变背景和星星
5. 缓存键: `(width, height, bg_color, gradient_color)`

**关键代码结构**:
```python
class BackgroundRenderer:
    def __init__(self):
        self._stars = []
        self._animation_time = 0
        self._gradient_cache = {}
        self._init_stars()

    def _init_stars(self):
        import random
        self._stars = [{...} for _ in range(100)]

    def _get_cached_gradient(self, surface, bg_color, gradient_color):
        cache_key = (width, height, bg_color, gradient_color)
        if cache_key not in self._gradient_cache:
            # 创建渐变并缓存
            pass
        return self._gradient_cache[cache_key]

    def update(self):
        self._animation_time += 1
        for star in self._stars:
            star['y'] += 0.008
            if star['y'] > 1:
                star['y'] = 0
                star['x'] = random.random()

    def render(self, surface, colors):
        gradient = self._get_cached_gradient(surface, colors['bg'], colors.get('bg_gradient'))
        surface.blit(gradient, (0, 0))
        # 渲染星星...
```

**验证**: 
- [ ] 渐变背景只创建一次，后续从缓存获取
- [ ] 星星动画流畅
- [ ] 缓存键正确生成

---

## 任务 3: 实现 ParticleSystem

**文件**: `airwar/scenes/ui/particles.py`

**要求**:
1. 实现 `_init_cache()` 方法，预创建 4 种尺寸的粒子纹理
2. 实现 `_init_particles()` 方法，初始化粒子数据
3. 实现 `update()` 方法，更新粒子位置
4. 实现 `render()` 方法，使用缓存纹理渲染
5. 实现 `reset()` 方法，重置粒子系统

**关键代码结构**:
```python
class ParticleSystem:
    _texture_cache = {}

    def __init__(self):
        self._particles = []
        self._animation_time = 0
        self._init_cache()

    def _init_cache(self):
        for base_size in [8, 12, 16, 20]:
            for color_key in ['particle', 'particle_alt']:
                key = (base_size, color_key)
                if key not in self._texture_cache:
                    # 创建纹理并缓存
                    pass

    def _init_particles(self, count=40, color_key='particle'):
        import random
        self._particles = [{...} for _ in range(count)]

    def update(self, direction=-1):
        self._animation_time += 1
        for p in self._particles:
            p['y'] += p['speed'] * 0.003 * direction
            # 边界检查...

    def render(self, surface, color):
        for p in self._particles:
            # 使用缓存纹理
            cache_key = (size, color_key)
            if cache_key in self._texture_cache:
                particle_surf = self._texture_cache[cache_key].copy()
                particle_surf.set_alpha(alpha)
                surface.blit(particle_surf, (...))
            else:
                # 回退：动态创建
                pass

    def reset(self, count=40, color_key='particle'):
        self._animation_time = 0
        self._init_particles(count, color_key)
```

**验证**:
- [ ] 粒子纹理缓存成功（4 种尺寸 × 2 种颜色 = 8 个纹理）
- [ ] 粒子动画流畅
- [ ] `reset()` 方法正确重置状态

---

## 任务 4: 实现 EffectsRenderer

**文件**: `airwar/scenes/ui/effects.py`

**要求**:
1. 实现 `render_glow_text()` 方法，渲染发光文字
2. 实现 `render_option_box()` 方法，渲染选项框

**验证**:
- [ ] 发光文字效果与原实现一致
- [ ] 选项框样式与原实现一致

---

## 任务 5: 重构 MenuScene

**文件**: `airwar/scenes/menu_scene.py`

**修改清单**:

1. **添加导入** (文件开头):
```python
from airwar.scenes.ui.background import BackgroundRenderer
from airwar.scenes.ui.particles import ParticleSystem
from airwar.scenes.ui.effects import EffectsRenderer
```

2. **删除属性初始化** (`enter` 方法中):
   - 删除 `self.particles = []`
   - 删除 `self.stars = []`
   - 删除 `self._init_particles()` 调用
   - 删除 `self._init_stars()` 调用

3. **添加渲染器初始化** (`enter` 方法末尾):
```python
self._background_renderer = BackgroundRenderer()
self._particle_system = ParticleSystem()
self._effects_renderer = EffectsRenderer()
self._particle_system.reset(40, 'particle')
```

4. **修改 `reset` 方法**:
   - 添加渲染器重置代码

5. **修改 `update` 方法**:
   - 删除星星和粒子更新逻辑
   - 添加:
```python
self._background_renderer._animation_time = self.animation_time
self._background_renderer.update()
self._particle_system._animation_time = self.animation_time
self._particle_system.update(direction=-1)
```

6. **修改 `render` 方法**:
   - 删除 `_draw_gradient_background(surface)`
   - 删除 `_draw_stars(surface)`
   - 删除 `_draw_particles(surface)`
   - 添加:
```python
self._background_renderer.render(surface, self.colors)
self._particle_system.render(surface, self.colors['particle'])
```

7. **删除以下方法**:
   - `_init_particles`
   - `_init_stars`
   - `_init_colors`
   - `_draw_gradient_background`
   - `_draw_stars`
   - `_draw_particles`

**验证**:
- [ ] MenuScene 渲染效果与重构前一致
- [ ] 动画流畅
- [ ] 无运行时错误

---

## 任务 6: 重构 DeathScene

**文件**: `airwar/scenes/death_scene.py`

**修改清单**:
- 与 MenuScene 类似
- **保留** `_draw_ripples()` 方法（DeathScene 特有）
- **保留** `_draw_decorative_lines()` 方法
- **保留** `_draw_icon_decoration()` 方法

**颜色键**: DeathScene 使用 `self.colors['particle']` (红色系)

**验证**:
- [ ] DeathScene 渲染效果与重构前一致
- [ ] Ripple 效果正常
- [ ] 无运行时错误

---

## 任务 7: 重构 ExitConfirmScene

**文件**: `airwar/scenes/exit_confirm_scene.py`

**修改清单**:
- 与 MenuScene 类似
- **保留** `_draw_decorative_lines()` 方法
- **保留** `_draw_icon_decoration()` 方法
- **保留** `_draw_success_indicator()` 方法

**颜色键**: ExitConfirmScene 使用 `self.colors['particle']` (蓝色系)

**验证**:
- [ ] ExitConfirmScene 渲染效果与重构前一致
- [ ] 保存成功指示器正常
- [ ] 无运行时错误

---

## 任务 8: 重构 PauseScene

**文件**: `airwar/scenes/pause_scene.py`

**修改清单**:
- 与 MenuScene 类似
- **保留** `_draw_decorative_lines()` 方法
- **保留** `_draw_icon_decoration()` 方法

**颜色键**: PauseScene 使用 `self.colors['particle']` (蓝色系)

**验证**:
- [ ] PauseScene 渲染效果与重构前一致
- [ ] 无运行时错误

---

## 任务 9: 重构 LoginScene

**文件**: `airwar/scenes/login_scene.py`

**修改清单**:
- 与 MenuScene 类似
- **保留** `_render_panel()` 方法
- **保留** `_render_title()` 方法
- **保留** `_render_inputs()` 方法
- **保留** `_render_buttons()` 方法
- **保留** `_render_hints()` 方法
- **保留** `_render_message()` 方法
- **保留** `_render_input_box()` 及相关辅助方法

**颜色键**: LoginScene 使用 `self.colors['particle']` (蓝色系)

**验证**:
- [ ] LoginScene 渲染效果与重构前一致
- [ ] 输入框和按钮交互正常
- [ ] 无运行时错误

---

## 任务 10: 整体验证

**检查项**:

1. **功能验证**:
   - [ ] 所有场景可以正常启动
   - [ ] 菜单场景显示正确
   - [ ] 登录场景输入正常
   - [ ] 暂停场景显示正确
   - [ ] 死亡场景显示正确
   - [ ] 退出确认场景显示正确

2. **性能验证** (可选):
   - [ ] Surface 创建数量显著减少
   - [ ] 帧率稳定或提升

3. **代码质量**:
   - [ ] 无导入错误
   - [ ] 无未使用的变量
   - [ ] 代码风格一致

4. **测试运行**:
   - [ ] 运行 `pytest airwar/tests/test_scenes.py`
   - [ ] 所有测试通过

---

## 任务 11: 运行测试套件

**命令**:
```bash
pytest airwar/tests/ -v --tb=short
```

**重点测试文件**:
- `test_scenes.py`
- `test_menu_scene.py` (如果存在)
- `test_death_scene.py` (如果存在)
- `test_exit_confirm_scene.py` (如果存在)

**验证**: 所有测试通过

---

## 完成标准

所有任务完成后，确认：

1. [ ] 新建文件存在且代码完整
2. [ ] 5 个场景文件重构完成
3. [ ] 删除了所有重复的渲染方法
4. [ ] 所有场景功能正常
5. [ ] 测试套件全部通过
6. [ ] 无运行时警告或错误
