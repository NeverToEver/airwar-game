# Tutorial Scene Bug Report & Technical Handoff Document

**Created:** 2026-04-21  
**Project:** Air War Game (Pygame)  
**Status:** BLOCKED - 需要进一步调试

---

## 问题概述

### 1. 主菜单 (MenuScene) 问题
- **问题描述**: 主菜单界面无法通过 ESC 键返回登录界面
- **用户反馈**: 界面布局不合理，内容被遮挡

### 2. 教程页面 (TutorialScene) 问题
- **问题描述**: 进入教程页面后，无法通过任何方式返回主菜单
- **严重程度**: CRITICAL - 用户只能关闭窗口才能退出游戏

### 3. 调试历史
- 添加了 KEYUP 事件处理（之前只处理 KEYDOWN）
- 完全重构了 TutorialScene 参照 LoginScene 架构
- 问题仍然存在

---

## 架构分析

### 场景流程图

```
LoginScene → MenuScene → TutorialScene
                 ↓
              GameScene
```

### SceneDirector 主循环 (`airwar/game/scene_director.py`)

```python
def run(self) -> None:
    self._running = True
    while self._running:
        login_result, save_data = self._run_login_flow()  # 返回用户信息
        if not login_result:
            break
        self._pending_save_data = save_data
        if not self._run_menu_flow():  # 返回 True=继续, False=返回登录
            continue
        result = self._run_game_flow()
        # ...
```

### MenuScene 流程 (`_run_menu_flow`)
- 检测到 TUTORIAL 选择时调用 `_run_tutorial_flow()`
- 教程结束后重置状态返回菜单

### TutorialScene 流程 (`_run_tutorial_flow`)
- 当前实现：
```python
while tutorial_scene.is_running():
    events = self._poll_events()
    if not self._check_quit(events):
        return
    self._handle_resize_if_needed(events)
    for event in events:
        tutorial_scene.handle_events(event)
    
    if tutorial_scene.should_quit():
        return
    
    tutorial_scene.update()
    tutorial_scene.render(self._window.get_surface())
    self._window.flip()
    self._window.tick(60)
```

---

## 已验证的信息

### Pygame 事件类型
```
pygame.KEYDOWN = 768 (0x300)
pygame.KEYUP = 769 (0x301)
pygame.K_ESCAPE = 27
```

### 调试日志显示
- 事件类型 769 (KEYUP) 被收到，但 KEYDOWN 没有被记录
- 可能是窗口焦点问题导致

### TutorialScene 当前实现
文件: `airwar/scenes/tutorial_scene.py`

**关键方法:**
- `handle_events()` - 处理键盘和鼠标事件
- `_handle_keyboard_event()` - ESC/ENTER/SPACE 设置 `want_to_quit = True` 和 `running = False`
- `_handle_mouse_event()` - 点击 BACK 按钮设置退出
- `should_quit()` - 返回 `want_to_quit`
- `is_running()` - 返回 `running`

### MenuScene 当前实现
文件: `airwar/scenes/menu_scene.py`

**关键方法:**
- `handle_events()` - 处理 ESC 返回登录，ENTER/SPACE 选择难度或教程
- `should_go_back()` - 返回 `back_requested`
- `is_selection_confirmed()` - 返回 `selection_confirmed`

---

## 待验证假设

### 假设 1: 窗口焦点问题
- **描述**: Pygame 窗口可能没有获得键盘焦点
- **证据**: 只有 KEYUP 事件被记录，没有 KEYDOWN
- **验证方法**: 添加 `pygame.event.set_grab(True)` 获取输入焦点

### 假设 2: 事件被其他场景消耗
- **描述**: MenuScene 在切换到 TutorialScene 前可能消耗了事件
- **验证方法**: 在 `_run_menu_flow` 中添加事件追踪

### 假设 3: SceneManager 事件处理问题
- **描述**: `scene_manager.handle_events()` 可能没有正确传递事件
- **验证方法**: 检查 SceneManager 的事件传递链

### 假设 4: Pygame 版本或 SDL 兼容性问题
- **描述**: 特定环境下 pygame.KEYDOWN 可能不工作
- **环境**: macOS 上 pygame 2.6.1
- **验证方法**: 测试其他键盘事件

---

## 建议的修复方案

### 方案 1: 添加事件获取模式
```python
# 在 scene_director 中
def _poll_events(self) -> List[pygame.event.Event]:
    pygame.event.set_grab(True)  # 获取输入焦点
    return pygame.event.get()
```

### 方案 2: 同时监听 KEYDOWN 和 KEYUP
```python
def handle_events(self, event):
    if event.type in (pygame.KEYDOWN, pygame.KEYUP):
        if event.key == pygame.K_ESCAPE:
            self.exit()
```

### 方案 3: 检查窗口是否获得焦点
```python
def is_window_focused() -> bool:
    return pygame.mouse.get_focused()  # 检查是否有输入焦点
```

---

## 相关文件列表

| 文件路径 | 说明 |
|---------|------|
| `airwar/scenes/tutorial_scene.py` | 教程场景 - 需要修复退出逻辑 |
| `airwar/scenes/menu_scene.py` | 主菜单 - 需要修复 ESC 返回 |
| `airwar/scenes/login_scene.py` | 登录场景 - 参考架构 |
| `airwar/scenes/scene.py` | Scene 基类定义 |
| `airwar/game/scene_director.py` | 场景流程控制器 |
| `airwar/game/game.py` | 游戏主入口 |
| `main.py` | 启动文件 |

---

## 测试步骤

### 基础测试
1. 运行 `python3 main.py`
2. 登录（任意用户名/密码如 test/test）
3. 在菜单界面按 ESC - 应该返回登录页
4. 选择 TUTORIAL 进入教程
5. 按 ESC/ENTER/SPACE - 应该返回主菜单
6. 点击 BACK 按钮 - 应该返回主菜单

### 调试测试
1. 添加打印语句追踪事件流
2. 检查 `pygame.mouse.get_focused()` 返回值
3. 检查 `event.type` 的实际值

---

## MenuScene 布局问题

### 当前问题
- 面板尺寸可能不足以显示所有选项
- 4个选项 (EASY/MEDIUM/HARD/TUTORIAL) 可能溢出

### 当前尺寸
```python
base_panel_width = 400
base_panel_height = 460  # 之前是 360
base_option_height = 70
base_option_gap = 12
```

### MenuScene 的布局计算
```python
option_section_height = option_height * 3 + option_gap * 2
start_y = panel_y + (panel_height - option_section_height) // 2
```

### 建议
- 保持与 LoginScene 一致的视觉风格
- 验证 4 个选项是否正确显示
- 检查 ResponsiveHelper 是否正确处理多分辨率

---

## 参考: LoginScene 架构

LoginScene 使用以下架构成功实现了退出功能：

```python
def enter(self, **kwargs) -> None:
    self.running = True
    self.want_to_quit = False
    # ...

def handle_events(self, event):
    if event.type == pygame.KEYDOWN:
        self._handle_keyboard_event(event)
    elif event.type == pygame.MOUSEBUTTONDOWN:
        self._handle_mouse_event(event)

def _handle_keyboard_event(self, event):
    if event.key == pygame.K_ESCAPE:
        self.want_to_quit = True
        self.running = False

def should_quit(self) -> bool:
    return self.want_to_quit
```

---

## 下一步行动

1. **添加诊断代码**: 在 `_poll_events()` 中添加 `pygame.mouse.get_focused()` 检查
2. **验证焦点问题**: 尝试 `pygame.event.set_grab(True)`
3. **检查事件类型**: 打印所有收到的事件类型
4. **简化测试**: 创建一个最小化测试用例验证事件处理

---

## 备注

- 项目使用 pygame 2.6.1
- Python 3.12.3
- macOS 环境
- SceneManager 使用单例模式管理场景
- 所有场景共享同一个 pygame display surface
