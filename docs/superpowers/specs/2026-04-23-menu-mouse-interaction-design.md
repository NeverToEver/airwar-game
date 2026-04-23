# 菜单鼠标交互支持设计文稿

## 1. 背景与目标

### 1.1 问题陈述
当前游戏的大部分菜单场景仅支持键盘交互（↑/↓/Enter），缺乏鼠标点击支持，影响用户体验的直观性和便捷性。

### 1.2 目标
为所有菜单场景添加鼠标点击交互支持，使玩家可以通过鼠标直接点击选项完成选择。

### 1.3 范围
| 场景 | 文件 | 当前状态 | 目标状态 |
|------|------|----------|----------|
| 登录场景 | `login_scene.py` | ✅ 已支持 | 维持现状 |
| 难度选择 | `menu_scene.py` | ❌ 仅键盘 | 键盘 + 鼠标 |
| 死亡菜单 | `death_scene.py` | ❌ 仅键盘 | 键盘 + 鼠标 |
| 暂停菜单 | `pause_scene.py` | ❌ 仅键盘 | 键盘 + 鼠标 |
| 退出确认 | `exit_confirm_scene.py` | ❌ 仅键盘 | 键盘 + 鼠标 |
| 天赋选择 | `reward_selector.py` | ❌ 仅键盘 | 键盘 + 鼠标 |
| 教程场景 | `tutorial_scene.py` | ✅ 部分支持 | 完善支持 |

> **注**：关于"存档菜单"，经代码分析，游戏未设置独立的存档加载界面。存档功能集成在暂停菜单（Save And Quit）和退出确认菜单中。

---

## 2. 设计方案

### 2.1 统一交互模式

#### 2.1.1 鼠标交互规范
- **点击选中**：鼠标悬停时显示高亮效果，点击时触发选项确认
- **悬停反馈**：鼠标移动到选项上方时，自动切换选中状态
- **视觉提示**：底部提示文字从 "W/S or UP/DOWN to select" 改为 "Click or W/S to select"

#### 2.1.2 交互优先级
1. 鼠标悬停 > 键盘上下键（鼠标悬停时覆盖键盘选中状态）
2. 鼠标点击 > Enter键（直接确认当前悬停选项）
3. ESC键保持原有行为（返回/取消）

### 2.2 技术实现方案

#### 方案 A：集中式工具函数（推荐）

**思路**：在 `airwar/utils/` 下创建 `mouse_interaction.py`，提供通用的鼠标交互工具函数和混入类。

**优点**：
- 代码复用性高
- 保持各场景代码简洁
- 便于统一维护
- 符合 DRY 原则

**缺点**：
- 需要理解继承/混入模式

```python
# airwar/utils/mouse_interaction.py

class MouseSelectableMixin:
    """可鼠标选择的混入类"""

    def __init__(self):
        self._hovered_index: int = -1
        self._option_rects: list = []  # 存储选项矩形区域

    def _handle_mouse_hover(self, mouse_pos: tuple) -> bool:
        """检测鼠标悬停，返回是否改变了选中项"""
        for i, rect in enumerate(self._option_rects):
            if rect.collidepoint(mouse_pos):
                if self._hovered_index != i:
                    self._hovered_index = i
                    self._on_hover_change(i)
                return True
        return False

    def _handle_mouse_click(self, mouse_pos: tuple) -> bool:
        """处理鼠标点击，返回是否触发了选择"""
        for i, rect in enumerate(self._option_rects):
            if rect.collidepoint(mouse_pos):
                self._on_item_click(i)
                return True
        return False

    def _on_hover_change(self, index: int):
        """子类可重写：选中项变化时的回调"""
        pass

    def _on_item_click(self, index: int):
        """子类可重写：点击选项时的回调"""
        pass

    def get_selected_index(self) -> int:
        """获取当前选中项（优先返回悬停项）"""
        return self._hovered_index if self._hovered_index >= 0 else self.selected_index
```

#### 方案 B：各场景独立实现

**思路**：在每个场景中独立实现鼠标交互逻辑。

**优点**：
- 实现简单直观
- 无需理解额外抽象

**缺点**：
- 代码重复
- 维护成本高
- 容易产生不一致

### 2.3 推荐方案实施细节

#### 2.3.1 统一交互接口

每个需要鼠标支持的场景实现以下接口：

```python
class MenuScene(Scene, MouseSelectableMixin):
    def __init__(self):
        # ... 原有初始化
        MouseSelectableMixin.__init__(self)

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._handle_keyboard_event(event)
        elif event.type == pygame.MOUSEMOTION:
            self._handle_mouse_hover(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse_click(event.pos)

    def _handle_mouse_hover(self, mouse_pos: tuple) -> None:
        """检测悬停并更新选中状态"""
        for i, rect in enumerate(self._option_rects):
            if rect.collidepoint(mouse_pos):
                self.selected_index = i
                break
        else:
            pass  # 鼠标不在任何选项上，保持当前选中

    def _handle_mouse_click(self, mouse_pos: tuple) -> None:
        """检测点击并触发选择"""
        for i, rect in enumerate(self._option_rects):
            if rect.collidepoint(mouse_pos):
                self.selected_index = i
                self._confirm_selection()  # 触发确认逻辑
                break

    def render(self, surface: pygame.Surface) -> None:
        # ... 渲染逻辑中存储每个选项的矩形区域
        self._option_rects = []
        for i, option in enumerate(self.options):
            # ... 渲染选项
            box_rect = pygame.Rect(...)
            self._option_rects.append(box_rect)
```

#### 2.3.2 视觉反馈增强

悬停时的视觉变化：
```python
def _draw_option_box(self, surface, ...):
    is_highlighted = (i == self.selected_index)

    # 悬停时添加额外高亮效果
    if is_highlighted:
        # 使用已有的选中样式
        self._draw_selected_style(box_rect)
    else:
        self._draw_unselected_style(box_rect)
```

#### 2.3.3 底部提示文字更新

| 场景 | 更新后提示 |
|------|-----------|
| MenuScene | "Click or ENTER to start" |
| DeathScene | "Click or ENTER to confirm" |
| PauseScene | "Click or ESC to resume" |
| ExitConfirmScene | "Click or ESC to return" |
| RewardSelector | "Click or ENTER to select" |

---

## 3. 各场景详细设计

### 3.1 MenuScene (难度选择)

**选项列表**：
- EASY
- MEDIUM (默认选中)
- HARD
- TUTORIAL

**交互行为**：
- 鼠标悬停：自动选中该选项
- 鼠标点击：
  - 非 TUTORIAL：确认选择，切换到游戏
  - TUTORIAL：确认选择，切换到教程
- 键盘：↑/↓ 切换，Enter 确认

### 3.2 DeathScene (死亡菜单)

**选项列表**：
- RETURN TO MAIN MENU
- QUIT GAME

**交互行为**：
- 鼠标悬停：自动选中
- 鼠标点击：确认选择
- 键盘：↑/↓ 切换，Enter 确认

### 3.3 PauseScene (暂停菜单)

**选项列表**：
- RESUME
- MAIN MENU
- SAVE AND QUIT
- QUIT WITHOUT SAVING

**交互行为**：
- 鼠标悬停：自动选中
- 鼠标点击：确认选择
- 键盘：↑/↓ 切换，Enter 确认，ESC 恢复游戏

### 3.4 ExitConfirmScene (退出确认)

**选项列表**：
- RETURN TO MENU
- START NEW GAME
- QUIT GAME

**交互行为**：
- 鼠标悬停：自动选中
- 鼠标点击：确认选择
- 键盘：↑/↓ 切换，Enter 确认，ESC 返回菜单

### 3.5 RewardSelector (天赋选择)

**选项列表**：
- 天赋选项 1 (动态生成)
- 天赋选项 2 (动态生成)
- 天赋选项 3 (动态生成)

**交互行为**：
- 鼠标悬停：自动选中
- 鼠标点击：确认选择
- 键盘：↑/↓ 切换，Enter 确认

**特殊考虑**：
- 动态生成选项，需要在渲染时更新 `_option_rects`

---

## 4. 实施计划

### 阶段一：基础设施
1. 创建 `airwar/utils/mouse_interaction.py` 工具模块
2. 定义 `MouseSelectableMixin` 混入类

### 阶段二：场景改造
1. MenuScene - 添加鼠标交互
2. DeathScene - 添加鼠标交互
3. PauseScene - 添加鼠标交互
4. ExitConfirmScene - 添加鼠标交互
5. RewardSelector - 添加鼠标交互

### 阶段三：验证与优化
1. 视觉反馈测试
2. 键盘/鼠标切换一致性测试
3. 响应式布局测试（窗口大小变化）

---

## 5. 验收标准

### 5.1 功能验收
- [ ] 所有目标场景支持鼠标悬停高亮
- [ ] 所有目标场景支持鼠标点击选择
- [ ] 键盘和鼠标交互可以无缝切换
- [ ] ESC 键行为保持不变

### 5.2 视觉验收
- [ ] 悬停状态有明显的视觉反馈
- [ ] 点击反馈即时生效
- [ ] 底部提示文字已更新

### 5.3 兼容性验收
- [ ] 不同窗口尺寸下交互正常
- [ ] 全屏/窗口模式切换后交互正常

---

## 6. 风险与注意事项

### 6.1 潜在风险
1. **响应式布局**：选项位置随窗口大小变化，需要动态计算矩形区域
2. **动画状态**：部分场景有动画效果，需要确保鼠标状态不受动画干扰

### 6.2 注意事项
1. 不要破坏现有的键盘交互逻辑
2. 保持与现有视觉风格的一致性
3. 复用 LoginScene 中已有的鼠标处理代码模式
