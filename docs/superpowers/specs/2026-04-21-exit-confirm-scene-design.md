# ExitConfirmScene 设计文档

> **文档版本**: 1.0
> **日期**: 2026-04-21
> **状态**: 已批准

## 1. 功能概述

### 1.1 功能描述

在玩家选择"保存并退出"或"不保存退出"后，显示一个过渡性确认菜单（ExitConfirmScene），让玩家在真正退出游戏之前可以选择返回主菜单、开始新游戏或退出游戏。

### 1.2 触发条件

- 玩家在暂停菜单（PauseScene）中选择了 SAVE_AND_QUIT 或 QUIT_WITHOUT_SAVING 选项
- 对于 SAVE_AND_QUIT：先保存游戏进度，然后显示退出确认菜单
- 对于 QUIT_WITHOUT_SAVING：直接显示退出确认菜单

### 1.3 用户交互流程

```
游戏中按 ESC
    ↓
显示 PauseScene（暂停菜单）
    ↓
玩家选择 "SAVE AND QUIT"
    ↓
保存游戏进度
    ↓
显示 ExitConfirmScene
    ↓
┌──────────────────────────────────────┐
│         游戏已保存 ✓                  │
│                                      │
│    [1] 返回主菜单                    │
│    [2] 开始新游戏                    │
│    [3] 退出游戏                      │
│                                      │
│    使用 W/S 选择，Enter 确认         │
└──────────────────────────────────────┘
    ↓
玩家选择任一选项
```

## 2. 架构设计

### 2.1 设计模式

遵循现有 PauseScene 的设计模式，确保代码架构一致性：
- 相同的视觉效果（渐变背景、星光粒子、发光效果）
- 相同的交互方式（W/S 选择，Enter 确认）
- 相同的状态管理（running 标志，result 属性）

### 2.2 组件结构

```
airwar/
└── scenes/
    ├── __init__.py              # 导出 ExitConfirmScene
    ├── scene.py                  # 新增 ExitConfirmAction 枚举
    ├── pause_scene.py           # 现有
    ├── exit_confirm_scene.py    # 新增：退出确认场景
```

### 2.3 类设计

#### 2.3.1 ExitConfirmAction 枚举

**位置**: `airwar/scenes/scene.py`

**定义**:
```python
class ExitConfirmAction(Enum):
    RETURN_TO_MENU = "return_to_menu"      # 返回主菜单
    START_NEW_GAME = "start_new_game"     # 开始新游戏
    QUIT_GAME = "quit_game"               # 退出游戏
```

#### 2.3.2 ExitConfirmScene 类

**位置**: `airwar/scenes/exit_confirm_scene.py`

**职责**: 显示退出确认菜单，处理用户输入

**接口**:
```python
class ExitConfirmScene(Scene):
    def enter(self, **kwargs) -> None:
        """
        kwargs:
            - saved: bool - 是否已保存游戏
            - difficulty: str - 当前难度（用于开始新游戏）
        """
    def exit(self) -> None: ...
    def handle_events(self, event: pygame.event.Event) -> None: ...
    def update(self, *args, **kwargs) -> None: ...
    def render(self, surface: pygame.Surface) -> None: ...
    def get_result(self) -> ExitConfirmAction: ...
    def is_running(self) -> bool: ...
```

**状态管理**:
- `self.running`: 控制场景是否运行
- `self.result`: 存储用户选择的动作
- `self.selected_index`: 当前选中的选项索引
- `self.saved`: 是否已保存游戏（影响提示文本）

## 3. UI设计

### 3.1 布局

| 元素 | 位置 | 说明 |
|------|------|------|
| 标题文本 | 屏幕上方 1/3 处 | "GAME SAVED" 或 "EXIT GAME" |
| 选项列表 | 屏幕中央 | 垂直排列的三个选项 |
| 操作提示 | 屏幕底部 | 选择/确认控制说明 |

### 3.2 颜色配置

与 PauseScene 保持一致：

| 元素 | 颜色 | 说明 |
|------|------|------|
| 背景渐变起点 | (8, 8, 25) | 深蓝色 |
| 背景渐变终点 | (15, 15, 50) | 浅蓝色 |
| 标题文字 | (255, 255, 255) | 白色 |
| 标题光晕 | (100, 200, 255) | 青色光晕 |
| 选中选项 | (0, 255, 150) | 绿色高亮 |
| 未选中选项 | (90, 90, 130) | 灰色 |
| 成功提示 | (100, 255, 150) | 绿色确认 |

### 3.3 选项列表

```python
self.options = [
    "RETURN TO MENU",      # 返回主菜单
    "START NEW GAME",      # 开始新游戏
    "QUIT GAME"           # 退出游戏
]
```

### 3.4 视觉元素

- 渐变星空背景（与 PauseScene 相同）
- 上升粒子效果（与 PauseScene 相同）
- 选项发光边框（与 PauseScene 相同）
- 成功勾选图标（如已保存，显示 ✓ 图标）

## 4. 行为规范

### 4.1 选项行为

| 选项 | 行为 | 返回值 |
|------|------|--------|
| RETURN TO MENU | 清除存档，返回主菜单 | `ExitConfirmAction.RETURN_TO_MENU` |
| START NEW GAME | 清除存档，保留难度，重新开始 | `ExitConfirmAction.START_NEW_GAME` |
| QUIT GAME | 真正退出游戏程序 | `ExitConfirmAction.QUIT_GAME` |

### 4.2 键盘交互

| 按键 | 行为 |
|------|------|
| W / ↑ | 向上选择选项 |
| S / ↓ | 向下选择选项 |
| Enter / Space | 确认选择 |
| ESC | 取消并返回（等同于返回主菜单）|

### 4.3 状态显示

- 如果 `saved=True`：显示 "GAME SAVED ✓"
- 如果 `saved=False`：显示 "EXIT GAME"

## 5. 数据流设计

### 5.1 SceneDirector 集成

**修改**: `airwar/game/scene_director.py`

```python
def _run_game_flow(self) -> str:
    # ... 现有的暂停逻辑 ...
    
    # 修改 _handle_pause_toggle 返回值处理
    elif result == "save_and_quit":
        return self._show_exit_confirm(current_scene, saved=True)
    elif result == "quit_without_saving":
        return self._show_exit_confirm(current_scene, saved=False)

def _show_exit_confirm(self, game_scene: GameScene, saved: bool) -> str:
    """显示退出确认菜单"""
    exit_scene = self._scene_manager._scenes.get("exit_confirm")
    if not exit_scene:
        return "quit"
    
    exit_scene.enter(saved=saved, difficulty=self._selected_difficulty)
    
    while exit_scene.is_running():
        # 事件处理循环...
        pass
    
    result = exit_scene.get_result()
    
    if result == ExitConfirmAction.RETURN_TO_MENU:
        self._clear_saved_game()
        return "main_menu"
    elif result == ExitConfirmAction.START_NEW_GAME:
        self._clear_saved_game()
        return "restart"
    else:  # QUIT_GAME
        return "quit"
```

### 5.2 Game 类集成

**修改**: `airwar/game/game.py`

```python
# 注册新场景
from airwar.scenes import ExitConfirmScene

def _setup_scenes(self):
    # ... 现有代码 ...
    self._scene_manager.register("exit_confirm", ExitConfirmScene())
```

## 6. 测试计划

### 6.1 单元测试

| 测试项 | 说明 |
|--------|------|
| 场景初始化 | 验证 enter() 正确设置状态 |
| 选项选择 | 验证 W/S 键正确切换选项 |
| 选项确认 | 验证 Enter 键返回正确动作 |
| ESC 处理 | 验证 ESC 返回主菜单 |
| 渲染测试 | 验证 UI 元素正确绘制 |
| 已保存状态 | 验证 saved=True 显示正确文本 |
| 未保存状态 | 验证 saved=False 显示正确文本 |

### 6.2 集成测试

| 测试项 | 说明 |
|--------|------|
| 保存退出流程 | SAVE_AND_QUIT → 显示确认 → 选择返回主菜单 |
| 不保存退出流程 | QUIT_WITHOUT_SAVING → 显示确认 → 选择退出游戏 |
| 开始新游戏流程 | 保存退出 → 选择开始新游戏 → 验证难度保留 |
| SceneDirector 集成 | 验证场景正确注册和切换 |

## 7. 验收标准

- [ ] ExitConfirmScene 正确创建并显示
- [ ] 视觉效果与 PauseScene 保持一致
- [ ] 三个选项正确显示并可选
- [ ] W/S 键正确切换选项
- [ ] Enter 键确认选择
- [ ] ESC 键返回主菜单
- [ ] 已保存状态显示 "GAME SAVED ✓"
- [ ] 未保存状态显示 "EXIT GAME"
- [ ] 返回主菜单选项正确清除存档
- [ ] 开始新游戏选项正确重置游戏
- [ ] 退出游戏选项正确关闭程序
- [ ] 所有单元测试通过
- [ ] 集成测试通过

## 8. 实施顺序

1. 在 `airwar/scenes/scene.py` 中新增 `ExitConfirmAction` 枚举
2. 创建 `airwar/scenes/exit_confirm_scene.py` 实现 `ExitConfirmScene` 类
3. 修改 `airwar/scenes/__init__.py` 导出新场景
4. 修改 `airwar/game/game.py` 注册新场景
5. 修改 `airwar/game/scene_director.py` 添加 `_show_exit_confirm` 方法
6. 编写单元测试
7. 编写集成测试
8. 验证完整功能
