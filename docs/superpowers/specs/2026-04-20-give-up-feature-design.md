# Give Up 功能设计文档

> **文档版本**: 1.0
> **日期**: 2026-04-20
> **状态**: 已批准

## 1. 功能概述

### 1.1 功能描述

实现玩家主动放弃功能：持续按住K键3秒后触发角色死亡，显示红色进度条UI作为视觉反馈。

### 1.2 触发条件

- 玩家存活且游戏进行中
- 非暂停状态
- 非死亡/游戏结束状态

### 1.3 用户交互流程

```
玩家按下K键
    ↓
显示红色进度条UI（屏幕顶部）
    ↓
进度条从0%填充到100%（3秒）
    ↓
进度条完成
    ↓
触发角色死亡 → 显示死亡菜单
```

## 2. 架构设计

### 2.1 设计模式

采用与母舰系统(H键)相同的输入检测模式，确保代码架构一致性。

### 2.2 组件结构

```
airwar/
├── game/
│   └── give_up/
│       ├── __init__.py
│       ├── give_up_detector.py  # K键输入检测
│       └── give_up_ui.py        # 红色进度条UI
```

### 2.3 类设计

#### 2.3.1 GiveUpDetector

**职责**: 检测K键长按状态，计算进度

**接口**:
```python
class GiveUpDetector:
    def __init__(self, on_complete_callback: Callable): ...
    def update(self, delta_time: float) -> None
    def get_progress(self) -> float
    def is_active(self) -> bool
    def reset(self) -> None
```

**状态机**:
- `IDLE`: 等待K键按下
- `PRESSING`: K键按住，进度累加
- `COMPLETE`: 进度达到100%，触发回调

#### 2.3.2 GiveUpUI

**职责**: 渲染红色进度条和提示文本

**接口**:
```python
class GiveUpUI:
    def __init__(self, screen_width: int, screen_height: int): ...
    def show(self) -> None
    def hide(self) -> None
    def update_progress(self, progress: float) -> None
    def render(self, surface: pygame.Surface) -> None
```

## 3. UI设计

### 3.1 布局

| 元素 | 位置 | 说明 |
|------|------|------|
| "GIVE UP" 文本 | 屏幕顶部居中，y=30 | 闪烁效果 |
| 进度条 | 屏幕顶部居中，y=60 | 红色警告风格 |
| 进度条尺寸 | 250×16像素 | 带圆角边框 |

### 3.2 颜色配置

| 元素 | 颜色 | 说明 |
|------|------|------|
| 背景 | (40, 10, 10) | 深红色半透明 |
| 进度 | (255, 60, 60) | 亮红色 |
| 边框 | (200, 80, 80) | 红色边框 |
| 文本 | (255, 100, 100) | 浅红色，带闪烁 |

### 3.3 动画效果

- 文本闪烁: alpha值在180-255之间周期性变化
- 进度条填充: 从左到右平滑增长
- 高亮效果: 进度条顶部有高亮线条

## 4. 数据流设计

### 4.1 游戏集成点

**GameScene集成**:
```python
class GameScene:
    def __init__(self):
        self._give_up_detector = GiveUpDetector(self._on_give_up_complete)
        self._give_up_ui = GiveUpUI(screen_width, screen_height)

    def update(self):
        # 在游戏进行中更新
        if self._can_use_give_up():
            self._give_up_detector.update(delta_time)
            self._give_up_ui.update_progress(self._give_up_detector.get_progress())

    def render(self, surface):
        if self._give_up_detector.is_active():
            self._give_up_ui.render(surface)

    def _can_use_give_up(self) -> bool:
        return (self.game_controller.state.gameplay_state == GameplayState.PLAYING
                and not self.game_controller.state.paused)

    def _on_give_up_complete(self) -> None:
        self.game_controller.on_player_hit(9999, self.player)
```

### 4.2 状态检查逻辑

```python
def _can_use_give_up(self) -> bool:
    return (
        self.game_controller.state.gameplay_state == GameplayState.PLAYING
        and not self.game_controller.state.paused
        and not self.reward_selector.visible
    )
```

## 5. 测试计划

### 5.1 单元测试

| 测试项 | 说明 |
|--------|------|
| GiveUpDetector进度计算 | 验证3秒内进度正确累加 |
| GiveUpDetector重置 | 松开K键后进度归零 |
| GiveUpDetector完成触发 | 进度达到100%时调用回调 |
| GiveUpUI显示/隐藏 | 验证可见性控制 |
| GiveUpUI渲染 | 验证UI正确绘制 |

### 5.2 集成测试

| 测试项 | 说明 |
|--------|------|
| 游戏进行中可用 | PLAYING状态下K键有效 |
| 暂停时不可用 | PAUSED状态下K键无效 |
| 死亡后不可用 | GAME_OVER状态下K键无效 |
| 完成触发死亡 | 3秒后正确触发死亡逻辑 |

## 6. 验收标准

- [ ] 持续按住K键3秒后角色死亡
- [ ] 进度条显示在屏幕顶部
- [ ] 进度条为红色警告风格
- [ ] 文本"GIVE UP"闪烁效果
- [ ] 松开K键进度条消失
- [ ] 暂停状态下无法触发
- [ ] 所有单元测试通过
- [ ] 集成测试通过

## 7. 实施顺序

1. 创建 `airwar/game/give_up/` 目录结构
2. 实现 `GiveUpDetector` 类
3. 实现 `GiveUpUI` 类
4. 集成到 `GameScene`
5. 编写单元测试
6. 编写集成测试
7. 验证完整功能
