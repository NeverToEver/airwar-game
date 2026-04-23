# Military HUD UI Implementation Plan

## Phase 1: Foundation - Extend Design Tokens
**文件**: `airwar/config/design_tokens.py`

添加军事风格颜色常量：
- `AMBER_PRIMARY`, `AMBER_DIM`, `MILITARY_GREEN`
- `BG_PRIMARY`, `BG_PANEL`, `BORDER_GLOW`
- `DANGER_RED`, `TEXT_PRIMARY`, `TEXT_DIM`

添加尺寸常量：
- `CHAMFER_DEPTH = 12`
- `CHAMFER_BORDER_WIDTH = 2`
- `SCANLINE_ALPHA = 12`

---

## Phase 2: Core Primitive - ChamferedPanel
**新建**: `airwar/ui/chamfered_panel.py`

创建切角矩形组件：
- `__init__(self, width, height, chamfer_depth=12)`
- `render(surface, x, y, bg_color, border_color, glow_color=None)`
- 内部缓存机制

---

## Phase 3: Effects Extension
**修改**: `airwar/ui/effects.py`

添加方法到 `EffectsRenderer`：
```python
def render_chamfered_rect(self, surface, rect, color, border_color=None, glow_color=None)
```

---

## Phase 4: Scanline Overlay
**新建**: `airwar/ui/scanline_overlay.py`

创建扫描线效果组件：
- 静态扫描线 surface 缓存
- 垂直移动动画

---

## Phase 5: Segmented Progress Bar
**新建**: `airwar/ui/segmented_bar.py`

创建分段进度条：
- 支持分段数量配置
- 用于血条、里程碑、Boss血条

---

## Phase 6: Hexagon Icon
**新建**: `airwar/ui/hex_icon.py`

创建六边形图标组件：
- 绘制六边形方法
- 支持发光状态（激活/满级）

---

## Phase 7: Military HUD Renderer
**新建**: `airwar/ui/military_hud.py`

创建军事风格 HUD：
- `render_top_bar()` - 顶部信息条
- `render_health_panel()` - 左下生命值
- `render_difficulty_panel()` - 右下难度

---

## Phase 8: Menu Military Styling
**修改**: `menu_scene.py`, `menu_background.py`

- 添加网格背景
- 应用切角边框
- 军事配色方案

---

## Phase 9: Boss Health Bar
**修改**: `airwar/game/rendering/hud_renderer.py`

- 切角边框 + 分段血条
- Phase 指示器
- 阶段切换动画

---

## Phase 10: Buff Panel Military
**修改**: `airwar/ui/buff_stats_panel.py`

- 六边形图标
- 军事配色
- 满级发光效果

---

## Phase 11: Milestone Progress
**新建/修改**: `military_hud.py`

- 切角面板包裹
- 分段进度条
- 到达100%时闪烁动画

---

## Phase 12: Integration & Polish

- 确保测试通过
- 性能优化
- 添加开关切换（兼容性）
