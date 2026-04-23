# 鼠标交互统一管理重构工作日志

**日期**: 2026-04-23  
**任务**: 将所有场景的鼠标交互逻辑集中管理  
**状态**: ✅ 已完成

---

## 一、修改的逻辑

### 1.1 问题背景

根据设计文档 `2026-04-23-menu-mouse-interaction-design.md`，游戏中的菜单场景存在鼠标交互不一致的问题：
- 部分场景仅支持键盘交互
- 各场景的鼠标处理逻辑分散，未统一管理
- 难以维护和扩展

### 1.2 解决方案

创建统一的鼠标交互模块 `mouse_interaction.py`，提供两个 Mixin 类：

#### MouseSelectableMixin（列表选择模式）

用于菜单选项列表场景（如 MenuScene、DeathScene 等）：
- `handle_mouse_motion()` - 检测鼠标悬停，更新选中状态
- `handle_mouse_click()` - 处理鼠标点击
- `get_effective_selected_index()` - 获取有效选中索引（鼠标优先于键盘）
- `append_option_rect()` - 注册选项矩形区域
- `clear_option_rects()` - 清空选项矩形区域
- `is_hovered()` - 检查是否悬停
- `clear_hover()` - 清空悬停状态

#### MouseInteractiveMixin（按钮点击模式）

用于按钮式交互场景（如 LoginScene、TutorialScene）：
- `register_button()` - 注册按钮（名称 + 矩形）
- `unregister_button()` - 注销按钮
- `handle_mouse_motion()` - 检测鼠标悬停
- `handle_mouse_click()` - 处理鼠标点击
- `is_button_hovered()` - 检查按钮是否悬停
- `get_hovered_button()` - 获取当前悬停的按钮名称
- `clear_hover()` - 清空悬停状态

### 1.3 交互优先级

1. **鼠标悬停 > 键盘上下键**（鼠标悬停时覆盖键盘选中状态）
2. **鼠标点击 > Enter键**（直接确认当前悬停选项）
3. **ESC键保持原有行为**（返回/取消）

---

## 二、改动的文件

### 2.1 新增文件

| 文件路径 | 说明 |
|----------|------|
| `airwar/utils/mouse_interaction.py` | 鼠标交互统一模块（两个 Mixin 类） |
| `airwar/tests/test_mouse_interaction.py` | 鼠标交互模块单元测试（23个测试用例） |

### 2.2 修改文件

#### 核心模块

| 文件路径 | 修改内容 |
|----------|----------|
| `airwar/utils/mouse_interaction.py` | 添加类文档（docstring） |

#### 场景文件

| 文件路径 | 使用的 Mixin | 主要修改 |
|----------|--------------|----------|
| `airwar/scenes/menu_scene.py` | `MouseSelectableMixin` | 添加鼠标事件处理、选项矩形管理、底部提示更新 |
| `airwar/scenes/death_scene.py` | `MouseSelectableMixin` | 添加鼠标事件处理、选项矩形管理、底部提示更新 |
| `airwar/scenes/pause_scene.py` | `MouseSelectableMixin` | 添加鼠标事件处理、选项矩形管理、底部提示更新 |
| `airwar/scenes/exit_confirm_scene.py` | `MouseSelectableMixin` | 添加鼠标事件处理、选项矩形管理、底部提示更新 |
| `airwar/scenes/login_scene.py` | `MouseInteractiveMixin` | 添加鼠标事件处理、按钮注册、输入框悬停反馈 |
| `airwar/scenes/tutorial_scene.py` | `MouseInteractiveMixin` | 添加鼠标事件处理、按钮注册、按钮注册时机优化 |
| `airwar/scenes/game_scene.py` | `MouseInteractiveMixin` | 添加鼠标点击处理框架 |

#### UI组件

| 文件路径 | 使用的 Mixin | 主要修改 |
|----------|--------------|----------|
| `airwar/ui/reward_selector.py` | `MouseSelectableMixin` | 添加鼠标事件处理、选项矩形管理、底部提示更新 |

### 2.3 修改详情

#### 2.3.1 mouse_interaction.py

```
新增：
- MouseSelectableMixin 类（列表选择模式）
- MouseInteractiveMixin 类（按钮点击模式）
- 完整的类文档（docstring）
```

#### 2.3.2 menu_scene.py

```
新增：
- __init__ 方法中初始化 MouseSelectableMixin
- handle_events 中处理 pygame.MOUSEMOTION 和 pygame.MOUSEBUTTONDOWN
- _confirm_selection() 方法（从原 handle_events 提取）
- _draw_option_item 中调用 append_option_rect()
- render 中调用 clear_option_rects() 和 get_effective_selected_index()

修改：
- 底部提示更新为 "Click or W/S to select"
```

#### 2.3.3 death_scene.py

```
新增：
- __init__ 方法中初始化 MouseSelectableMixin
- handle_events 中处理 pygame.MOUSEMOTION 和 pygame.MOUSEBUTTONDOWN
- _draw_option_box 中调用 append_option_rect()
- render 中调用 clear_option_rects() 和 get_effective_selected_index()

修改：
- 底部提示更新为 "Click or W/S to select"
```

#### 2.3.4 pause_scene.py

```
新增：
- __init__ 方法中初始化 MouseSelectableMixin
- handle_events 中处理 pygame.MOUSEMOTION 和 pygame.MOUSEBUTTONDOWN
- _draw_option_box 中调用 append_option_rect()
- render 中调用 clear_option_rects() 和 get_effective_selected_index()

修改：
- 底部提示更新为 "Click or W/S to select"
```

#### 2.3.5 exit_confirm_scene.py

```
新增：
- __init__ 方法中初始化 MouseSelectableMixin
- handle_events 中处理 pygame.MOUSEMOTION 和 pygame.MOUSEBUTTONDOWN
- _draw_option_box 中调用 append_option_rect()
- render 中调用 clear_option_rects() 和 get_effective_selected_index()

修改：
- 底部提示更新为 "Click or W/S to select"
```

#### 2.3.6 login_scene.py

```
新增：
- __init__ 方法中初始化 MouseInteractiveMixin
- enter() 中调用 clear_hover() 和 clear_buttons()
- handle_events 中处理 pygame.MOUSEMOTION 和 pygame.MOUSEBUTTONDOWN
- _update_input_active_from_hover() 方法
- _handle_button_click() 方法
- _render_inputs 中注册 username 和 password 按钮
- _render_buttons 中传递 button_name 参数
- _render_button 中使用 is_button_hovered() 检查悬停
- _draw_input_bg 中添加悬停时的视觉反馈

修改：
- 删除原有的 _handle_mouse_event() 方法
- 添加空按钮名称检查（_handle_button_click 中的 None 检查）
```

#### 2.3.7 tutorial_scene.py

```
新增：
- __init__ 方法中初始化 MouseInteractiveMixin
- enter() 和 reset() 中调用 clear_hover() 和 clear_buttons()
- handle_events 中添加 _ensure_buttons_registered() 调用
- _ensure_buttons_registered() 方法
- _handle_button_click() 方法
- _register_buttons() 方法（接受屏幕尺寸参数）

修改：
- 删除原有的 _handle_mouse() 和 _rect_contains_point() 方法
- 移除冗余的 self._hovered_button = None 定义
```

#### 2.3.8 game_scene.py

```
新增：
- __init__ 方法中初始化 MouseInteractiveMixin
- handle_events 中添加鼠标点击处理框架
- _handle_mouse_click() 空方法（预留扩展点）
```

#### 2.3.9 reward_selector.py

```
新增：
- __init__ 方法中初始化 MouseSelectableMixin
- handle_input 中处理 pygame.MOUSEMOTION 和 pygame.MOUSEBUTTONDOWN
- _draw_option_item 中调用 append_option_rect()
- render 中调用 clear_option_rects() 和 get_effective_selected_index()

修改：
- 底部提示更新为 "Click or W/S to select, ENTER to confirm"
```

---

## 三、仍在的问题

### 3.1 已知问题

| # | 严重程度 | 问题描述 | 影响 | 建议处理 |
|---|----------|----------|------|----------|
| 1 | Low | GameScene 中的 `_handle_mouse_click()` 是空方法 | 目前游戏主场景没有实际的鼠标交互 | 未来可根据需要扩展，如点击暂停按钮等 |
| 2 | Info | 测试文件 test_death_animation.py 中的一个无关测试失败 | 与本次改动无关，是预先存在的问题 | 建议单独跟进 |

### 3.2 未来可优化项

| # | 优化项 | 优先级 | 说明 |
|---|--------|--------|------|
| 1 | 视觉反馈增强 | Medium | 可为按钮添加更明显的悬停动画效果 |
| 2 | 触摸支持 | Low | 可扩展支持移动端触摸交互 |
| 3 | 手柄支持 | Low | 可添加游戏手柄的按钮导航支持 |

---

## 四、测试结果

```
============================= test session starts ==============================
platform darwin -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0
collected 643 items

新增测试：
airwar/tests/test_mouse_interaction.py
  - TestMouseSelectableMixin: 11 passed
  - TestMouseInteractiveMixin: 12 passed

总计：642 passed, 1 failed (预先存在问题)
```

---

## 五、使用示例

### 5.1 列表选择模式（MenuScene）

```python
class MenuScene(Scene, MouseSelectableMixin):
    def __init__(self):
        Scene.__init__(self)
        MouseSelectableMixin.__init__(self)

    def handle_events(self, event):
        # 原有键盘处理...
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.handle_mouse_click(event.pos):
                self._confirm_selection()

    def render(self, surface):
        self.clear_option_rects()
        effective_index = self.get_effective_selected_index(self.selected_index)
        for i, option in enumerate(self.options):
            self._draw_option(surface, option, i, i == effective_index)

    def _draw_option(self, surface, option, index, is_selected):
        rect = pygame.Rect(...)
        self.append_option_rect(rect)  # 注册矩形区域
        # 渲染逻辑...
```

### 5.2 按钮点击模式（LoginScene）

```python
class LoginScene(Scene, MouseInteractiveMixin):
    def __init__(self):
        Scene.__init__(self)
        MouseInteractiveMixin.__init__(self)

    def handle_events(self, event):
        # 原有键盘处理...
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.handle_mouse_click(event.pos):
                self._handle_button_click(self.get_hovered_button())

    def _render_button(self, surface, rect, text, button_name):
        self.register_button(button_name, rect)  # 注册按钮
        if self.is_button_hovered(button_name):
            # 悬停时的视觉反馈
        # 渲染逻辑...
```

---

## 六、变更统计

| 统计项 | 数量 |
|--------|------|
| 新增文件 | 2 |
| 修改文件 | 8 |
| 新增测试用例 | 23 |
| 删除代码行数 | ~80 |
| 新增代码行数 | ~150 |
