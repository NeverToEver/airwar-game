# 快速修复指南 - 教程场景和主菜单退出问题

## 核心问题

**症状**: 进入 TutorialScene 后，无法通过 ESC/ENTER/SPACE 返回主菜单，只能关闭窗口退出。

**调试发现**: 事件类型 769 (KEYUP) 被收到，但 768 (KEYDOWN) 没有被记录。

---

## 立即尝试的修复

### 修复 1: 添加输入焦点获取

**文件**: `airwar/game/scene_director.py`

```python
def _poll_events(self) -> List[pygame.event.Event]:
    pygame.event.set_grab(True)  # 添加这行
    return pygame.event.get()
```

### 修复 2: 在进入教程前清除事件队列

```python
def _run_tutorial_flow(self) -> None:
    # 清除之前的事件
    pygame.event.clear()
    
    self._scene_manager.switch("tutorial")
    tutorial_scene = self._scene_manager.get_current_scene()
    
    while tutorial_scene.is_running():
        events = self._poll_events()
        # ...
```

### 修复 3: 添加窗口焦点检查

```python
def _run_tutorial_flow(self) -> None:
    self._scene_manager.switch("tutorial")
    tutorial_scene = self._scene_manager.get_current_scene()
    
    # 确保窗口获得焦点
    pygame.display.set_mode((800, 600), pygame.RESIZABLE)
    
    while tutorial_scene.is_running():
        # 检查焦点
        if not pygame.mouse.get_focused():
            print("WARNING: Window lost focus!")
        
        events = self._poll_events()
        # ...
```

---

## 验证步骤

1. 在终端运行 `python3 main.py`
2. 登录后选择 TUTORIAL
3. 观察是否能通过 ESC 返回
4. 如果不能，检查终端输出是否有警告信息

---

## 替代方案

如果以上修复无效，考虑：

1. **简化退出机制**: 只使用窗口关闭事件退出
2. **重构事件处理**: 创建一个统一的事件处理器
3. **使用 pygame.KEYUP**: 只监听 KEYUP 事件（因为它能被收到）

```python
def handle_events(self, event):
    if event.type == pygame.KEYUP:  # 改用 KEYUP
        if event.key == pygame.K_ESCAPE:
            self.exit()
```
