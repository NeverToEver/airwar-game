# 新手教程系统设计文档

> **文档版本**: 1.0
> **日期**: 2026-04-21
> **维护者**: AI Assistant (Trae IDE)
> **项目**: Air War 游戏新手教程系统

---

## 1. 概述

### 1.1 项目背景

当前 Air War 游戏缺少新手指引，玩家进入游戏后不清楚如何操作战斗机和母舰系统。为了提升用户体验，需要添加一个完整的新手教程系统，展示所有游戏操作。

### 1.2 目标

在游戏主菜单中添加独立的"新手教程"选项，通过静态展示页面向玩家介绍：
- 战斗机的移动和射击操作
- 母舰系统的使用（H键停靠）
- 其他功能（暂停ESC、放弃K键）

### 1.3 核心设计决策

- **展示方式**：静态页面（玩家阅读后返回主菜单）
- **布局设计**：按功能分类展示（基础控制、母舰系统、其他功能）
- **入口位置**：主菜单选项之一（与难度选择并列）

---

## 2. 系统架构

### 2.1 整体流程

```
登录界面 (LoginScene)
    ↓
主菜单 (MenuScene)  ← 新增"新手教程"选项
    ↓
┌─────────────────────────────────┐
│          分支选择               │
├─────────────────────────────────┤
│ [选择难度] → 游戏场景           │
│ 或                               │
│ [新手教程] → 教程页面           │
│              ↓                   │
│          返回主菜单              │
└─────────────────────────────────┘
```

### 2.2 菜单选项结构

**主菜单选项列表**：
1. `easy` - 简单难度
2. `medium` - 中等难度
3. `hard` - 困难难度
4. `tutorial` - **新增**：新手教程

### 2.3 场景交互

| 当前场景 | 操作 | 目标场景 | 返回状态 |
|---------|------|---------|---------|
| MenuScene | 选择 tutorial | TutorialScene | - |
| TutorialScene | 返回 | MenuScene | back_requested=True |

---

## 3. 界面设计

### 3.1 视觉风格

**配色方案**（沿用现有游戏风格）：
```python
colors = {
    'bg': (8, 8, 25),                    # 深蓝渐变起点
    'bg_gradient': (15, 15, 50),         # 深蓝渐变终点
    'title': (255, 255, 255),            # 标题白色
    'title_glow': (100, 200, 255),      # 标题光晕青色
    'selected': (0, 255, 150),           # 选中项绿色
    'selected_glow': (0, 200, 255),     # 选中项光晕青色
    'unselected': (90, 90, 130),        # 未选中项灰色
    'hint': (70, 70, 110),               # 提示文字
    'particle': (100, 180, 255),         # 粒子效果
    'panel': (15, 20, 40),              # 面板背景
    'panel_border': (50, 80, 140),       # 面板边框
}
```

### 3.2 页面布局

```
┌─────────────────────────────────────┐
│           ✦ AIR WAR ✦              │  ← 游戏标题（发光效果）
│         新手教程指南                │  ← 副标题
├─────────────────────────────────────┤
│                                     │
│  🎮 基础控制                        │  ← 分类标题
│  ┌───────────────────────────────┐ │
│  │ ↑/W  ↑ / S ↓  ←/A  →/D      │ │  ← 按键说明
│  │ 空格键：射击（自动射击）       │ │
│  └───────────────────────────────┘ │
│                                     │
│  🚀 母舰系统                        │
│  ┌───────────────────────────────┐ │
│  │ H（长按）：停靠/起飞           │ │
│  │ 母舰内可选择增益效果           │ │
│  └───────────────────────────────┘ │
│                                     │
│  ⚠️ 其他功能                        │
│  ┌───────────────────────────────┐ │
│  │ ESC：暂停游戏                 │ │
│  │ K（长按3秒）：放弃游戏         │ │
│  └───────────────────────────────┘ │
│                                     │
├─────────────────────────────────────┤
│         [ 返回主菜单 ]              │  ← 按钮
│                                     │
│    ↑↓ 选择    ENTER 确认          │  ← 底部提示
└─────────────────────────────────────┘
```

### 3.3 教程内容

**🎮 基础控制**
| 按键 | 功能 |
|------|------|
| ↑ / W | 向上移动 |
| ↓ / S | 向下移动 |
| ← / A | 向左移动 |
| → / D | 向右移动 |
| 空格键 | 射击（自动射击） |

**🚀 母舰系统**
| 按键 | 功能 |
|------|------|
| H (长按) | 停靠/进入母舰系统 |
| - | 母舰内可获得增益buff |
| - | 长按H键可重新起飞 |

**⚠️ 其他功能**
| 按键 | 功能 |
|------|------|
| ESC | 暂停游戏 |
| K (长按3秒) | 主动放弃游戏 |

---

## 4. 技术实现

### 4.1 文件结构

**新增文件**：
```
airwar/scenes/
├── tutorial_scene.py      # 新手教程场景类
└── __init__.py           # 更新注册新场景
```

**修改文件**：
```
airwar/
├── scenes/
│   ├── menu_scene.py     # 添加教程选项
│   └── scene.py          # 添加场景类型常量
└── game/
    └── scene_director.py # 添加教程流程处理
```

### 4.2 TutorialScene 类设计

```python
class TutorialScene(Scene):
    """新手教程场景，展示游戏操作指南"""

    def __init__(self):
        self.running = True
        self.animation_time = 0
        self.back_requested = False
        self.particles = []
        self.stars = []
        self.selected_button = 0  # 0: 返回按钮
        self.button_hover = False
        
        # 布局参数
        self.base_panel_width = 700
        self.base_panel_height = 650
        
    def enter(self, **kwargs) -> None:
        """初始化教程场景"""
        self.running = True
        self.back_requested = False
        self._init_particles()
        self._init_stars()
        
    def exit(self) -> None:
        """退出教程场景"""
        pass
        
    def handle_events(self, event: pygame.event.Event) -> None:
        """处理输入事件"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.back_requested = True
                self.running = False
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.back_requested = True
                self.running = False
                
    def update(self, *args, **kwargs) -> None:
        """更新动画和粒子效果"""
        self.animation_time += 1
        self._update_particles()
        self._update_stars()
        
    def render(self, surface: pygame.Surface) -> None:
        """渲染教程页面"""
        self._draw_background(surface)
        self._draw_panel(surface)
        self._draw_title(surface)
        self._draw_content_sections(surface)
        self._draw_button(surface)
        self._draw_hints(surface)
        
    # 状态查询方法
    def is_back_requested(self) -> bool:
        return self.back_requested
        
    def is_ready(self) -> bool:
        return not self.running
        
    # 私有渲染方法
    def _draw_background(self, surface) -> None
    def _draw_panel(self, surface) -> None
    def _draw_title(self, surface) -> None
    def _draw_content_sections(self, surface) -> None
    def _draw_section(self, surface, title, items, y_pos) -> None
    def _draw_key_mapping(self, surface, key, desc, x, y) -> None
    def _draw_button(self, surface) -> None
    def _draw_hints(self, surface) -> None
    def _update_particles(self) -> None
    def _update_stars(self) -> None
```

### 4.3 MenuScene 改造

**修改内容**：
1. 添加第四个选项：`tutorial`
2. 更新选项列表：
```python
self.menu_options = ['easy', 'medium', 'hard', 'tutorial']
self.option_names = {
    'easy': 'EASY',
    'medium': 'MEDIUM',
    'hard': 'HARD',
    'tutorial': 'TUTORIAL'
}
```

3. 修改渲染逻辑，支持4个选项
4. 修改事件处理，支持选择教程选项

### 4.4 SceneDirector 修改

**添加教程流程处理**：
```python
def _run_menu_flow(self) -> bool:
    # 现有的菜单流程
    # 修改：在选择确认时检查是否选择了教程
    if isinstance(self._scene_manager.get_current_scene(), MenuScene):
        ms = self._scene_manager.get_current_scene()
        if ms.should_go_back():
            back_to_login = True
            break
        if ms.is_selection_confirmed():
            selected_option = ms.get_selected_option()
            if selected_option == 'tutorial':
                # 进入教程流程
                self._run_tutorial_flow()
                continue  # 返回菜单继续
            else:
                self._selected_difficulty = selected_option
                break
```

**新增教程流程方法**：
```python
def _run_tutorial_flow(self) -> None:
    """运行教程流程"""
    self._scene_manager.switch("tutorial")
    tutorial_scene = self._scene_manager.get_current_scene()
    
    while tutorial_scene.is_running():
        events = self._poll_events()
        if not self._check_quit(events):
            return
        self._handle_resize_if_needed(events)
        self._handle_scene_events(events)
        tutorial_scene.update()
        tutorial_scene.render(self._window.get_surface())
        self._window.flip()
        self._window.tick(60)
```

### 4.5 场景注册

**scenes/__init__.py** 更新：
```python
from .tutorial_scene import TutorialScene

def _init_scenes(scene_manager):
    scene_manager.register("login", LoginScene())
    scene_manager.register("menu", MenuScene())
    scene_manager.register("game", GameScene())
    scene_manager.register("pause", PauseScene())
    scene_manager.register("death", DeathScene())
    scene_manager.register("exit_confirm", ExitConfirmScene())
    scene_manager.register("tutorial", TutorialScene())  # 新增
```

---

## 5. 交互设计

### 5.1 用户操作流程

**进入教程**：
1. 玩家在主菜单使用 ↑/↓ 或 W/S 选择"教程"选项
2. 选中项显示绿色高亮和发光效果
3. 按 Enter 或点击选中项进入教程页面

**浏览教程**：
1. 显示完整的操作指南
2. 包含星空背景动画
3. 底部显示"返回主菜单"按钮

**返回主菜单**：
1. 按 ESC 或 Enter
2. 点击"返回主菜单"按钮
3. 返回主菜单继续选择难度或重新查看教程

### 5.2 视觉反馈

- **选中状态**：绿色边框发光 + 背景色变化
- **按钮悬停**：鼠标悬停时按钮颜色变亮
- **标题动画**：柔和的发光脉动效果
- **背景动画**：星空闪烁 + 粒子飘动

---

## 6. 实现步骤

### 步骤 1：创建 TutorialScene 类
- [ ] 创建 `airwar/scenes/tutorial_scene.py`
- [ ] 实现基础框架（enter, exit, handle_events, update, render）
- [ ] 实现星空和粒子背景
- [ ] 实现教程内容绘制
- [ ] 实现按钮和交互

### 步骤 2：注册新场景
- [ ] 更新 `scenes/__init__.py` 注册 TutorialScene
- [ ] 更新 `scenes/scene.py` 添加场景类型常量

### 步骤 3：修改 MenuScene
- [ ] 添加 tutorial 选项到菜单列表
- [ ] 修改渲染逻辑支持4个选项
- [ ] 修改事件处理
- [ ] 添加选项名称映射

### 步骤 4：集成到 SceneDirector
- [ ] 修改 `_run_menu_flow()` 方法
- [ ] 添加 `_run_tutorial_flow()` 方法
- [ ] 测试流程跳转

### 步骤 5：测试和优化
- [ ] 功能测试：所有交互正常工作
- [ ] 视觉测试：界面美观流畅
- [ ] 边界测试：不同分辨率下正常显示

---

## 7. 测试计划

### 7.1 功能测试

| 测试项 | 测试内容 | 预期结果 |
|--------|---------|----------|
| 菜单导航 | 在主菜单选择教程选项 | 能够选中并高亮 |
| 教程入口 | 选择教程后进入教程页面 | 正常显示教程内容 |
| 返回功能 | 按ESC或Enter返回主菜单 | 正常返回并可继续操作 |
| 按钮点击 | 鼠标点击返回按钮 | 能够触发返回 |
| 键盘导航 | 使用方向键选择选项 | 能够上下切换 |

### 7.2 视觉测试

| 测试项 | 检查内容 | 预期结果 |
|--------|---------|----------|
| 背景效果 | 星空闪烁和粒子飘动 | 动画流畅无卡顿 |
| 布局适配 | 不同窗口尺寸下显示 | 正确适配无溢出 |
| 色彩一致性 | 与游戏整体风格一致 | 赛博朋克风格统一 |
| 文字清晰度 | 所有文字清晰可读 | 字体大小适中 |

### 7.3 集成测试

| 测试项 | 测试内容 | 预期结果 |
|--------|---------|----------|
| 完整流程 | 登录→主菜单→教程→返回→选难度→开始游戏 | 全流程无错误 |
| 多次访问 | 反复进入教程页面 | 每次都正常显示 |
| 状态重置 | 从教程返回后重新进入 | 状态正确重置 |

---

## 8. 风险评估

### 8.1 潜在风险

1. **布局适配风险**：不同分辨率下教程内容可能溢出
   - **缓解措施**：使用 ResponsiveHelper 进行适配
   - **测试**：在多种分辨率下测试

2. **菜单逻辑复杂性**：添加新选项可能影响现有菜单逻辑
   - **缓解措施**：最小化修改，尽量复用现有逻辑
   - **测试**：充分测试所有菜单选项

3. **场景切换稳定性**：频繁切换场景可能导致状态不一致
   - **缓解措施**：确保 enter/exit 方法正确重置状态
   - **测试**：多次切换场景测试稳定性

### 8.2 预防措施

- ✅ 使用现有的 Scene 基类
- ✅ 复用 MenuScene 的视觉风格和动画效果
- ✅ 使用 ResponsiveHelper 确保适配性
- ✅ 编写完整的测试用例

---

## 9. 附录

### 9.1 代码规范

- 所有代码遵循现有代码风格
- 使用中文注释关键逻辑
- 函数和变量命名遵循现有规范
- 保持代码简洁，避免过度设计

### 9.2 性能考虑

- 粒子数量控制在合理范围（40-60个）
- 星空数量控制在合理范围（100-120个）
- 避免不必要的重复渲染
- 使用缓存优化静态内容

### 9.3 后续扩展

未来可能的扩展方向：
- 添加具体的游戏演示视频/动画
- 添加可交互的教程练习关卡
- 添加成就系统（首次完成教程）
- 支持多语言教程内容

---

**文档结束**

*设计文档已通过审核，可进入实现阶段。*
