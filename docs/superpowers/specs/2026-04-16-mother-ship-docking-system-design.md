# 母舰停靠系统技术实现文档

**文档版本**: v1.0
**创建日期**: 2026-04-16
**状态**: 待审核
**架构方案**: 状态机 + 观察者模式

---

## 1. 概述

### 1.1 系统简介

母舰停靠系统是游戏"飞机大战"的核心功能之一，允许玩家通过持续按住"H"键3秒进入母舰停靠状态，实现游戏进度的安全保存与恢复。母舰采用呼出式设计（外形参考千年隼号），停靠期间游戏暂停，确保玩家可以随时中断游戏而不会丢失进度。

### 1.2 核心功能清单

| 功能模块 | 描述 |
|---------|------|
| 按键检测 | 检测"H"键按下/松开/持续状态 |
| 进度条UI | 实时显示3秒按住进度 |
| 状态机 | 管理IDLE/PRESSING/DOCKING/DOCKED/UNDOCKING五种状态 |
| 动画系统 | 飞机进出母舰的过渡动画 |
| 数据持久化 | JSON格式的游戏状态保存与恢复 |

### 1.3 技术选型

| 技术选型 | 选择 | 理由 |
|---------|------|------|
| 架构模式 | 状态机 + 观察者模式 | 符合SRP，职责清晰，扩展性好 |
| 数据格式 | JSON | 轻量级，易于调试，与现有数据库模块兼容 |
| UI渲染 | Pygame原生绘制 | 与现有UI系统一致，减少依赖 |
| 母舰外形 | 千年隼号风格 | 符合用户指定的视觉风格要求 |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MotherShipSystem                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────┐         ┌─────────────────────┐                        │
│   │  InputDetector │────────▶│ MotherShipStateMachine│                        │
│   │  (按键检测)      │         │     (状态流转)        │                        │
│   └─────────────────┘         └──────────┬──────────┘                        │
│                                           │                                    │
│                                           ▼                                    │
│   ┌─────────────────┐         ┌─────────────────────┐     ┌─────────────────┐ │
│   │ ProgressBarUI  │◀────────│     EventBus       │────▶│   GameScene     │ │
│   │  (进度条渲染)    │         │     (事件总线)      │     │   (游戏逻辑)    │ │
│   └─────────────────┘         └─────────────────────┘     └────────┬────────┘ │
│                                           │                          │         │
│                                           ▼                          ▼         │
│                              ┌─────────────────────┐    ┌─────────────────┐  │
│                              │ PersistenceManager │    │   MotherShip    │  │
│                              │   (数据持久化)      │    │   (母舰实体)    │  │
│                              └─────────────────────┘    └─────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 模块职责

| 模块 | 职责 | 依赖 |
|------|------|------|
| InputDetector | 检测H键状态变化，计算按住时长 | pygame |
| MotherShipStateMachine | 管理状态流转，触发状态转换事件 | EventBus |
| ProgressBarUI | 渲染进度条UI，处理动画效果 | pygame |
| EventBus | 模块间事件通信（发布-订阅模式） | 无 |
| PersistenceManager | 游戏状态JSON序列化/反序列化 | JSON文件 |
| GameScene | 集成母舰系统，处理游戏逻辑暂停/恢复 | InputDetector, EventBus |
| MotherShip | 母舰实体渲染（千年隼号风格） | pygame |

### 2.3 模块交互流程

```
1. 玩家按下H键
   └─▶ InputDetector检测到KEYDOWN
       └─▶ EventBus.publish('H_PRESSED')
           ├─▶ MotherShipStateMachine: IDLE → PRESSING
           │   └─▶ ProgressBarUI: 显示进度条
           └─▶ GameScene: 可选（暂停敌人生成）

2. 玩家持续按住H键
   └─▶ InputDetector每帧更新press_time
       └─▶ EventBus.publish('PROGRESS_UPDATE', progress=0.0~1.0)
           └─▶ ProgressBarUI: 更新进度条显示

3. 3秒完成
   └─▶ InputDetector检测到progress >= 1.0
       └─▶ EventBus.publish('DOCKING_COMPLETE')
           ├─▶ MotherShipStateMachine: PRESSING → DOCKING
           │   └─▶ ProgressBarUI: 完成动画
           └─▶ GameScene: 触发飞机飞向母舰动画

4. 动画完成
   └─▶ EventBus.publish('DOCKING_ANIMATION_COMPLETE')
       └─▶ MotherShipStateMachine: DOCKING → DOCKED
           ├─▶ PersistenceManager: 保存游戏状态
           └─▶ GameScene: 游戏暂停

5. 玩家再次按下H键
   └─▶ EventBus.publish('UNDOCK_REQUEST')
       └─▶ MotherShipStateMachine: DOCKED → UNDOCKING
           └─▶ GameScene: 飞机飞出动画

6. 动画完成
   └─▶ EventBus.publish('UNDOCKING_ANIMATION_COMPLETE')
       └─▶ MotherShipStateMachine: UNDOCKING → IDLE
           └─▶ GameScene: 游戏继续
```

---

## 3. 状态机设计

### 3.1 状态图

```
                    ┌─────────────────────────────────────┐
                    │                                      │
                    │         ┌─────────────┐              │
                    │         │    IDLE     │◀─────────┐  │
                    │         └──────┬──────┘          │  │
                    │              │ H键按下           │  │
                    │              ▼                   │  │
                    │         ┌─────────────┐          │  │
                    │         │  PRESSING   │          │  │
                    │         └──────┬──────┘          │  │
                    │              │                  │  │
                    │    ┌─────────┴─────────┐        │  │
                    │    │                   │        │  │
                    │    ▼                   ▼        │  │
                    │  3秒完成           H键松开       │  │
                    │    │                   │        │  │
                    │    ▼                   │        │  │
                    │ ┌──────────┐           │        │  │
                    │ │ DOCKING  │           │        │  │
                    │ └────┬─────┘           │        │  │
                    │      │ 动画完成         │        │  │
                    │      ▼                 │        │  │
                    │ ┌──────────┐           │        │  │
                    │ │  DOCKED  │───────────┘        │  │
                    │ └────┬─────┘   H键按下(离开)     │  │
                    │      │                           │  │
                    │      │ H键按下(再次停靠)         │  │
                    │      ▼                           │  │
                    │ ┌───────────┐                    │  │
                    │ │ UNDOCKING │────────────────────┘  │
                    │ └─────┬─────┘    动画完成
                    │       ▼
                    └─────────────────────────────────────┘
```

### 3.2 状态说明

| 状态 | 描述 | 进入条件 | 退出条件 |
|------|------|---------|---------|
| IDLE | 默认状态，母舰不可见 | 初始化/动画完成 | H键按下 |
| PRESSING | 按住H键阶段，显示进度条 | H键按下 | 3秒完成/H键松开 |
| DOCKING | 飞机飞向母舰动画 | 3秒按住完成 | 动画完成 |
| DOCKED | 停靠状态，游戏暂停 | 动画完成 | H键按下 |
| UNDOCKING | 飞机飞出母舰动画 | H键按下(在DOCKED) | 动画完成 |

### 3.3 状态转换表

| 当前状态 | 事件 | 下一个状态 | 副作用 |
|---------|------|-----------|--------|
| IDLE | H_PRESSED | PRESSING | 显示母舰，进度条开始 |
| PRESSING | H_RELEASED | IDLE | 隐藏母舰，进度条消失 |
| PRESSING | PROGRESS_COMPLETE | DOCKING | 播放完成动画 |
| DOCKING | ANIMATION_COMPLETE | DOCKED | 保存游戏，暂停游戏 |
| DOCKED | H_PRESSED | UNDOCKING | 准备离开动画 |
| UNDOCKING | ANIMATION_COMPLETE | IDLE | 恢复游戏 |

---

## 4. 核心数据结构和接口

### 4.1 核心数据结构

```python
# mother_ship_state.py

from dataclasses import dataclass, field
from typing import Tuple, List, Dict, Optional
from enum import Enum
import time

class MotherShipState(Enum):
    IDLE = "idle"
    PRESSING = "pressing"
    DOCKING = "docking"
    DOCKED = "docked"
    UNDOCKING = "undocking"

@dataclass
class DockingProgress:
    is_pressing: bool = False
    press_start_time: float = 0.0
    current_progress: float = 0.0  # 0.0 ~ 1.0
    required_duration: float = 3.0  # 3秒

    def update_progress(self, current_time: float) -> None:
        if self.is_pressing:
            elapsed = current_time - self.press_start_time
            self.current_progress = min(elapsed / self.required_duration, 1.0)

    def reset(self) -> None:
        self.is_pressing = False
        self.press_start_time = 0.0
        self.current_progress = 0.0

@dataclass
class GameSaveData:
    score: int = 0
    cycle_count: int = 0
    kill_count: int = 0
    unlocked_buffs: List[str] = field(default_factory=list)
    buff_levels: Dict[str, int] = field(default_factory=dict)
    player_health: int = 100
    player_max_health: int = 100
    difficulty: str = "medium"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            'score': self.score,
            'cycle_count': self.cycle_count,
            'kill_count': self.kill_count,
            'unlocked_buffs': self.unlocked_buffs,
            'buff_levels': self.buff_levels,
            'player_health': self.player_health,
            'player_max_health': self.player_max_health,
            'difficulty': self.difficulty,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'GameSaveData':
        return cls(**data)
```

### 4.2 核心接口定义

```python
# interfaces.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Callable
from .mother_ship_state import MotherShipState, DockingProgress, GameSaveData

class IInputDetector(ABC):
    @abstractmethod
    def update(self) -> None:
        pass

    @abstractmethod
    def is_h_pressed(self) -> bool:
        pass

    @abstractmethod
    def get_progress(self) -> DockingProgress:
        pass

class IMotherShipUI(ABC):
    @abstractmethod
    def show(self) -> None:
        pass

    @abstractmethod
    def hide(self) -> None:
        pass

    @abstractmethod
    def update_progress(self, progress: float) -> None:
        pass

    @abstractmethod
    def play_complete_animation(self) -> None:
        pass

    @abstractmethod
    def render(self, surface: Any) -> None:
        pass

class IEventBus(ABC):
    @abstractmethod
    def subscribe(self, event: str, callback: Callable) -> None:
        pass

    @abstractmethod
    def unsubscribe(self, event: str, callback: Callable) -> None:
        pass

    @abstractmethod
    def publish(self, event: str, **kwargs) -> None:
        pass

class IPersistenceManager(ABC):
    @abstractmethod
    def save_game(self, data: GameSaveData) -> bool:
        pass

    @abstractmethod
    def load_game(self) -> Optional[GameSaveData]:
        pass

    @abstractmethod
    def has_saved_game(self) -> bool:
        pass

    @abstractmethod
    def delete_save(self) -> bool:
        pass

class IMotherShipStateMachine(ABC):
    @property
    @abstractmethod
    def current_state(self) -> MotherShipState:
        pass

    @abstractmethod
    def transition(self, event: str, **kwargs) -> None:
        pass

    @abstractmethod
    def update(self) -> None:
        pass
```

---

## 5. 详细实现

### 5.1 InputDetector 实现

```python
# input_detector.py

import pygame
from typing import Optional
from .interfaces import IInputDetector
from .mother_ship_state import DockingProgress

class InputDetector(IInputDetector):
    H_KEY = pygame.K_h

    def __init__(self, event_bus):
        self._event_bus = event_bus
        self._progress = DockingProgress()
        self._h_was_pressed = False
        self._last_update_time = 0.0

    def update(self) -> None:
        current_time = pygame.time.get_ticks() / 1000.0
        self._last_update_time = current_time

        is_h_currently_pressed = pygame.key.get_pressed()[self.H_KEY]

        if is_h_currently_pressed and not self._h_was_pressed:
            self._on_h_pressed(current_time)
        elif not is_h_currently_pressed and self._h_was_pressed:
            self._on_h_released()
        elif is_h_currently_pressed and self._progress.is_pressing:
            self._on_h_held(current_time)

        self._h_was_pressed = is_h_currently_pressed

    def _on_h_pressed(self, current_time: float) -> None:
        self._progress.is_pressing = True
        self._progress.press_start_time = current_time
        self._event_bus.publish('H_PRESSED', timestamp=current_time)

    def _on_h_released(self) -> None:
        was_complete = self._progress.current_progress >= 1.0
        self._progress.reset()

        if was_complete:
            self._event_bus.publish('DOCKING_COMPLETE')
        else:
            self._event_bus.publish('H_RELEASED')

    def _on_h_held(self, current_time: float) -> None:
        old_progress = self._progress.current_progress
        self._progress.update_progress(current_time)

        if old_progress < 1.0 and self._progress.current_progress >= 1.0:
            self._event_bus.publish('PROGRESS_COMPLETE')

    def is_h_pressed(self) -> bool:
        return pygame.key.get_pressed()[self.H_KEY]

    def get_progress(self) -> DockingProgress:
        return self._progress
```

### 5.2 EventBus 实现

```python
# event_bus.py

from typing import Dict, List, Callable, Any
from .interfaces import IEventBus

class EventBus(IEventBus):
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event: str, callback: Callable) -> None:
        if event not in self._subscribers:
            self._subscribers[event] = []
        if callback not in self._subscribers[event]:
            self._subscribers[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable) -> None:
        if event in self._subscribers:
            self._subscribers[event] = [
                cb for cb in self._subscribers[event] if cb != callback
            ]

    def publish(self, event: str, **kwargs) -> None:
        if event in self._subscribers:
            for callback in self._subscribers[event]:
                try:
                    callback(**kwargs)
                except Exception as e:
                    print(f"Event callback error [{event}]: {e}")
```

### 5.3 MotherShipStateMachine 实现

```python
# state_machine.py

from typing import Optional
from .interfaces import IMotherShipStateMachine
from .mother_ship_state import MotherShipState, DockingProgress
from .event_bus import EventBus

class MotherShipStateMachine(IMotherShipStateMachine):
    VALID_TRANSITIONS = {
        MotherShipState.IDLE: [MotherShipState.PRESSING],
        MotherShipState.PRESSING: [MotherShipState.IDLE, MotherShipState.DOCKING],
        MotherShipState.DOCKING: [MotherShipState.DOCKED],
        MotherShipState.DOCKED: [MotherShipState.UNDOCKING],
        MotherShipState.UNDOCKING: [MotherShipState.IDLE],
    }

    def __init__(self, event_bus: EventBus):
        self._current_state = MotherShipState.IDLE
        self._event_bus = event_bus
        self._animation_timer = 0
        self._register_handlers()

    def _register_handlers(self) -> None:
        self._event_bus.subscribe('H_PRESSED', self._on_h_pressed)
        self._event_bus.subscribe('H_RELEASED', self._on_h_released)
        self._event_bus.subscribe('PROGRESS_COMPLETE', self._on_progress_complete)
        self._event_bus.subscribe('DOCKING_ANIMATION_COMPLETE', self._on_docking_animation_complete)
        self._event_bus.subscribe('UNDOCKING_ANIMATION_COMPLETE', self._on_undocking_animation_complete)

    @property
    def current_state(self) -> MotherShipState:
        return self._current_state

    def transition(self, event: str, **kwargs) -> None:
        pass

    def _on_h_pressed(self, **kwargs) -> None:
        if self._can_transition_to(MotherShipState.PRESSING):
            self._change_state(MotherShipState.PRESSING)
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)

    def _on_h_released(self, **kwargs) -> None:
        if self._can_transition_to(MotherShipState.IDLE):
            self._change_state(MotherShipState.IDLE)
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)
            self._event_bus.publish('UNDOCK_CANCELLED')

    def _on_progress_complete(self, **kwargs) -> None:
        if self._can_transition_to(MotherShipState.DOCKING):
            self._change_state(MotherShipState.DOCKING)
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)
            self._event_bus.publish('START_DOCKING_ANIMATION')

    def _on_docking_animation_complete(self, **kwargs) -> None:
        if self._can_transition_to(MotherShipState.DOCKED):
            self._change_state(MotherShipState.DOCKED)
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)
            self._event_bus.publish('SAVE_GAME_REQUEST')

    def _on_undocking_animation_complete(self, **kwargs) -> None:
        if self._can_transition_to(MotherShipState.IDLE):
            self._change_state(MotherShipState.IDLE)
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)
            self._event_bus.publish('GAME_RESUME')

    def _can_transition_to(self, target_state: MotherShipState) -> bool:
        return target_state in self.VALID_TRANSITIONS.get(self._current_state, [])

    def _change_state(self, new_state: MotherShipState) -> None:
        self._current_state = new_state

    def update(self) -> None:
        pass
```

### 5.4 ProgressBarUI 实现

```python
# progress_bar_ui.py

import pygame
from typing import Optional
from .interfaces import IMotherShipUI

class ProgressBarUI(IMotherShipUI):
    def __init__(self, screen_width: int, screen_height: int):
        self._visible = False
        self._progress = 0.0
        self._screen_width = screen_width
        self._screen_height = screen_height

        self._bar_width = 300
        self._bar_height = 20
        self._corner_radius = 10
        self._border_width = 2

        self._bg_color = (30, 30, 50, 200)
        self._progress_color_inactive = (80, 80, 120)
        self._progress_color_active = (60, 180, 255)
        self._progress_color_complete = (80, 255, 120)
        self._border_color = (120, 120, 160)

        self._completion_animation_progress = 0.0
        self._is_playing_complete_animation = False

        pygame.font.init()
        self._font = pygame.font.Font(None, 24)

    def show(self) -> None:
        self._visible = True
        self._progress = 0.0
        self._is_playing_complete_animation = False

    def hide(self) -> None:
        self._visible = False
        self._progress = 0.0
        self._is_playing_complete_animation = False

    def update_progress(self, progress: float) -> None:
        if self._visible:
            self._progress = progress

    def play_complete_animation(self) -> None:
        self._is_playing_complete_animation = True
        self._completion_animation_progress = 0.0

    def render(self, surface: pygame.Surface) -> None:
        if not self._visible:
            return

        center_x = self._screen_width // 2
        center_y = self._screen_height - 150

        bar_x = center_x - self._bar_width // 2
        bar_y = center_y - self._bar_height // 2

        self._render_mothership_icon(surface, center_x, center_y - 60)

        if self._is_playing_complete_animation:
            self._render_complete_animation(surface, center_x, center_y, bar_x, bar_y)
        else:
            self._render_progress_bar(surface, bar_x, bar_y)
            self._render_progress_text(surface, center_x, center_y)

    def _render_progress_bar(self, surface: pygame.Surface, bar_x: int, bar_y: int) -> None:
        bg_rect = pygame.Rect(bar_x, bar_y, self._bar_width, self._bar_height)

        bg_surface = pygame.Surface((self._bar_width, self._bar_height), pygame.SRCALPHA)
        pygame.draw.rect(
            bg_surface, self._bg_color,
            (0, 0, self._bar_width, self._bar_height),
            border_radius=self._corner_radius
        )
        surface.blit(bg_surface, (bar_x, bar_y))

        pygame.draw.rect(
            surface, self._border_color,
            (bar_x, bar_y, self._bar_width, self._bar_height),
            self._border_width,
            border_radius=self._corner_radius
        )

        progress_width = int(self._bar_width * self._progress)
        if progress_width > 0:
            progress_color = self._get_progress_color()
            progress_rect = pygame.Rect(bar_x, bar_y, progress_width, self._bar_height)
            progress_surface = pygame.Surface((progress_width, self._bar_height), pygame.SRCALPHA)
            pygame.draw.rect(
                progress_surface, (*progress_color, 200),
                (0, 0, progress_width, self._bar_height),
                border_radius=self._corner_radius
            )
            surface.blit(progress_surface, (bar_x, bar_y))

            highlight_rect = pygame.Rect(bar_x + 2, bar_y + 2, progress_width - 4, 4)
            highlight_surface = pygame.Surface((progress_width - 4, 4), pygame.SRCALPHA)
            pygame.draw.rect(highlight_surface, (*progress_color, 100), (0, 0, progress_width - 4, 4))
            surface.blit(highlight_surface, (bar_x + 2, bar_y + 2))

    def _render_progress_text(self, surface: pygame.Surface, center_x: int, center_y: int) -> None:
        seconds = int(self._progress * 3)
        text = self._font.render(f"HOLD {seconds}/3", True, (200, 200, 220))
        text_rect = text.get_rect(center=(center_x, center_y + 30))
        surface.blit(text, text_rect)

    def _render_mothership_icon(self, surface: pygame.Surface, center_x: int, center_y: int) -> None:
        points = [
            (center_x, center_y - 20),
            (center_x + 25, center_y + 15),
            (center_x + 15, center_y + 10),
            (center_x + 15, center_y + 20),
            (center_x - 15, center_y + 20),
            (center_x - 15, center_y + 10),
            (center_x - 25, center_y + 15),
        ]

        mothership_surface = pygame.Surface((60, 50), pygame.SRCALPHA)
        pygame.draw.polygon(mothership_surface, (180, 180, 220, 200), [
            (p[0] - center_x + 30, p[1] - center_y + 25) for p in points
        ])
        pygame.draw.polygon(mothership_surface, (100, 100, 140, 255), [
            (p[0] - center_x + 30, p[1] - center_y + 25) for p in points
        ], 2)
        surface.blit(mothership_surface, (center_x - 30, center_y - 25))

    def _render_complete_animation(self, surface: pygame.Surface, center_x: int, center_y: int,
                                   bar_x: int, bar_y: int) -> None:
        self._completion_animation_progress += 0.05

        if self._completion_animation_progress >= 1.0:
            self._is_playing_complete_animation = False
            return

        scale = 1.0 + 0.1 * (1.0 - self._completion_animation_progress)
        alpha = 255 - int(255 * self._completion_animation_progress)

        original_bar_width = self._bar_width
        original_bar_height = self._bar_height

        scaled_bar_width = int(original_bar_width * scale)
        scaled_bar_height = int(original_bar_height * scale)

        scaled_x = center_x - scaled_bar_width // 2
        scaled_y = center_y - scaled_bar_height // 2

        progress_surface = pygame.Surface((scaled_bar_width, scaled_bar_height), pygame.SRCALPHA)
        pygame.draw.rect(
            progress_surface, (*self._progress_color_complete, alpha),
            (0, 0, scaled_bar_width, scaled_bar_height),
            border_radius=self._corner_radius
        )
        surface.blit(progress_surface, (scaled_x, scaled_y))

    def _get_progress_color(self) -> tuple:
        if self._progress >= 1.0:
            return self._progress_color_complete
        elif self._progress >= 0.8:
            t = (self._progress - 0.8) / 0.2
            return self._lerp_color(self._progress_color_active, self._progress_color_complete, t)
        return self._progress_color_active

    def _lerp_color(self, color1: tuple, color2: tuple, t: float) -> tuple:
        return tuple(int(c1 + (c2 - c1) * t) for c1, c2 in zip(color1, color2))
```

### 5.5 PersistenceManager 实现

```python
# persistence_manager.py

import json
import os
from typing import Optional
from .interfaces import IPersistenceManager
from .mother_ship_state import GameSaveData

class PersistenceManager(IPersistenceManager):
    SAVE_FILE_NAME = "user_docking_save.json"
    SAVE_DIRECTORY = "airwar/data"

    def __init__(self):
        self._save_path = os.path.join(self.SAVE_DIRECTORY, self.SAVE_FILE_NAME)

    def save_game(self, data: GameSaveData) -> bool:
        try:
            os.makedirs(self.SAVE_DIRECTORY, exist_ok=True)

            save_dict = data.to_dict()
            save_dict['timestamp'] = __import__('time').time()

            with open(self._save_path, 'w', encoding='utf-8') as f:
                json.dump(save_dict, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Failed to save game: {e}")
            return False

    def load_game(self) -> Optional[GameSaveData]:
        if not self.has_saved_game():
            return None

        try:
            with open(self._save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return GameSaveData.from_dict(data)
        except Exception as e:
            print(f"Failed to load game: {e}")
            return None

    def has_saved_game(self) -> bool:
        return os.path.exists(self._save_path)

    def delete_save(self) -> bool:
        try:
            if os.path.exists(self._save_path):
                os.remove(self._save_path)
            return True
        except Exception as e:
            print(f"Failed to delete save: {e}")
            return False
```

### 5.6 MotherShip 实体实现

```python
# mother_ship.py

import pygame
from typing import Optional

class MotherShip:
    def __init__(self, screen_width: int, screen_height: int):
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._visible = False
        self._position = (screen_width // 2, 100)
        self._target_position = (screen_width // 2, 100)
        self._animation_progress = 0.0

    def show(self) -> None:
        self._visible = True
        self._animation_progress = 0.0

    def hide(self) -> None:
        self._visible = False

    def is_visible(self) -> bool:
        return self._visible

    def render(self, surface: pygame.Surface) -> None:
        if not self._visible:
            return

        cx, cy = self._position

        body_points = [
            (cx, cy - 40),
            (cx + 80, cy + 20),
            (cx + 60, cy + 30),
            (cx + 50, cy + 60),
            (cx - 50, cy + 60),
            (cx - 60, cy + 30),
            (cx - 80, cy + 20),
        ]

        wing_points = [
            (cx - 60, cy + 10),
            (cx - 120, cy + 40),
            (cx - 100, cy + 50),
            (cx - 50, cy + 30),
        ]

        wing2_points = [
            (cx + 60, cy + 10),
            (cx + 120, cy + 40),
            (cx + 100, cy + 50),
            (cx + 50, cy + 30),
        ]

        pygame.draw.polygon(surface, (80, 80, 100), body_points)
        pygame.draw.polygon(surface, (100, 100, 130), body_points, 2)

        pygame.draw.polygon(surface, (70, 70, 90), wing_points)
        pygame.draw.polygon(surface, (90, 90, 110), wing_points, 2)

        pygame.draw.polygon(surface, (70, 70, 90), wing2_points)
        pygame.draw.polygon(surface, (90, 90, 110), wing2_points, 2)

        engine_glow = (40, 80, 120)
        for offset_y in [15, 25]:
            glow_pos = (cx, cy + offset_y)
            glow_radius = 8
            pygame.draw.circle(surface, engine_glow, glow_pos, glow_radius)
            pygame.draw.circle(surface, (60, 100, 150), glow_pos, glow_radius, 1)
```

### 5.7 GameScene 集成

```python
# 集成到 GameScene 的伪代码

class GameScene:
    def __init__(self):
        # ... 现有初始化 ...

        # 母舰系统组件
        self._event_bus = EventBus()
        self._input_detector = InputDetector(self._event_bus)
        self._state_machine = MotherShipStateMachine(self._event_bus)
        self._persistence_manager = PersistenceManager()
        self._progress_bar_ui = None
        self._mother_ship = None

        # 注册事件处理器
        self._register_mother_ship_handlers()

    def _register_mother_ship_handlers(self) -> None:
        self._event_bus.subscribe('STATE_CHANGED', self._on_state_changed)
        self._event_bus.subscribe('SAVE_GAME_REQUEST', self._on_save_game_request)
        self._event_bus.subscribe('GAME_RESUME', self._on_game_resume)
        self._event_bus.subscribe('START_DOCKING_ANIMATION', self._on_start_docking_animation)
        self._event_bus.subscribe('UNDOCK_CANCELLED', self._on_undock_cancelled)

    def enter(self, **kwargs) -> None:
        # ... 现有逻辑 ...

        screen_width = get_screen_width()
        screen_height = get_screen_height()

        self._progress_bar_ui = ProgressBarUI(screen_width, screen_height)
        self._mother_ship = MotherShip(screen_width, screen_height)

    def handle_events(self, event: pygame.event.Event) -> None:
        # ... 现有逻辑 ...

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_h:
                pass

        self._input_detector.update()

    def _on_state_changed(self, state, **kwargs) -> None:
        if state == MotherShipState.PRESSING:
            self._mother_ship.show()
            self._progress_bar_ui.show()
        elif state == MotherShipState.IDLE:
            self._mother_ship.hide()
            self._progress_bar_ui.hide()

    def _on_save_game_request(self, **kwargs) -> None:
        save_data = GameSaveData(
            score=self.game_controller.state.score,
            cycle_count=self.cycle_count,
            kill_count=self.game_controller.state.kill_count,
            unlocked_buffs=self.reward_system.unlocked_buffs,
            buff_levels=self._get_buff_levels(),
            player_health=self.player.health,
            player_max_health=self.player.max_health,
            difficulty=self.game_controller.state.difficulty
        )
        self._persistence_manager.save_game(save_data)
        self.game_controller.state.paused = True

    def _on_game_resume(self, **kwargs) -> None:
        self.game_controller.state.paused = False

    def _on_start_docking_animation(self, **kwargs) -> None:
        self._docking_animation_active = True
        self._docking_animation_start = self.player.rect.topleft

    def _on_undock_cancelled(self, **kwargs) -> None:
        self._progress_bar_ui.hide()

    def update(self, *args, **kwargs) -> None:
        if hasattr(self, '_progress_bar_ui') and self._progress_bar_ui:
            progress = self._input_detector.get_progress()
            self._progress_bar_ui.update_progress(progress.current_progress)

        if hasattr(self, '_docking_animation_active') and self._docking_animation_active:
            self._update_docking_animation()
            return

        # ... 现有逻辑 ...

    def render(self, surface: pygame.Surface) -> None:
        # ... 现有渲染逻辑 ...

        if hasattr(self, '_mother_ship') and self._mother_ship:
            self._mother_ship.render(surface)

        if hasattr(self, '_progress_bar_ui') and self._progress_bar_ui:
            self._progress_bar_ui.render(surface)

    def _get_buff_levels(self) -> Dict[str, int]:
        return {
            'piercing_level': self.reward_system.piercing_level,
            'spread_level': self.reward_system.spread_level,
            'explosive_level': self.reward_system.explosive_level,
            'armor_level': self.reward_system.armor_level,
            'evasion_level': self.reward_system.evasion_level,
            'rapid_fire_level': self.reward_system.rapid_fire_level,
        }
```

---

## 6. 文件结构

```
airwar/
├── game/
│   └── mother_ship/
│       ├── __init__.py
│       ├── interfaces.py          # 接口定义
│       ├── mother_ship_state.py   # 状态和数据结构
│       ├── event_bus.py           # 事件总线
│       ├── input_detector.py      # 按键检测
│       ├── state_machine.py        # 状态机
│       ├── progress_bar_ui.py     # 进度条UI
│       ├── persistence_manager.py # 数据持久化
│       ├── mother_ship.py          # 母舰实体
│       └── game_integrator.py     # GameScene集成逻辑
├── scenes/
│   └── game_scene.py              # 修改：集成母舰系统
└── data/
    └── user_docking_save.json      # 保存文件
```

---

## 7. 关键技术难点及解决方案

### 7.1 按键状态精确检测

**难点**：Pygame的`pygame.key.get_pressed()`需要在每帧调用，且KEYDOWN事件可能丢失

**解决方案**：
- 使用`get_pressed()`作为主检测方式
- 记录上一帧的H键状态，对比状态变化检测按下/松开
- 在`InputDetector.update()`中处理状态对比逻辑

### 7.2 进度条与状态机同步

**难点**：进度条动画和状态机状态需要严格同步

**解决方案**：
- 通过EventBus事件驱动，避免直接耦合
- ProgressBarUI订阅PROGRESS_UPDATE事件被动更新
- 状态转换由StateMachine统一管理

### 7.3 游戏暂停时机

**难点**：需要在正确时机暂停游戏，避免敌人继续生成

**解决方案**：
- DOCKING状态时开始飞机动画，但不暂停游戏
- DOCKED状态时才调用`game_controller.state.paused = True`
- UNDOCKING动画时设置标志位阻止敌人更新

### 7.4 数据一致性

**难点**：游戏状态复杂，保存/恢复需要完整

**解决方案**：
- 定义GameSaveData dataclass，统一数据结构
- 保存时收集所有必要字段
- 恢复时通过RewardSystem方法重新应用buff

### 7.5千年隼号风格视觉

**难点**：需要绘制符合千年隼号风格的母舰

**解决方案**：
- 使用多边形绘制主体和双侧翼
- 添加引擎发光效果
- 参考星球大战千年隼号特征：碟形舱+双侧翼+尾部推进器

---

## 8. 测试计划

### 8.1 单元测试

| 模块 | 测试用例 |
|------|---------|
| InputDetector | H键按下检测、松开检测、进度计算 |
| StateMachine | 状态转换、非法转换拒绝 |
| PersistenceManager | 保存、加载、文件不存在处理 |
| ProgressBarUI | 显示/隐藏、进度更新、动画触发 |

### 8.2 集成测试

| 场景 | 验证点 |
|------|--------|
| 正常停靠流程 | 3秒按住 → 动画 → 暂停 → 保存 |
| 中断流程 | 按住1秒松开 → 进度条消失 |
| 恢复流程 | 重新按下H → 动画 → 游戏继续 |
| 存档覆盖 | 多次停靠只保留最新存档 |

### 8.3 性能测试

- 进度条更新：确保60FPS下无卡顿
- 文件IO：保存/加载 < 100ms
- 内存占用：新增模块 < 1MB

---

## 9. 潜在风险及缓解

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| 存档损坏 | 中 | 加载前验证JSON格式，损坏时删除重建 |
| 状态机死锁 | 低 | 定义明确的转换表，禁止非法转换 |
| 进度条与动画不同步 | 低 | 通过事件驱动，保证执行顺序 |
| 多存档冲突 | 低 | 单一存档文件，覆盖式写入 |

---

## 10. 后续扩展建议

1. **多存档槽位**：支持多个存档位置
2. **自动存档**：每30秒自动保存一次
3. **母舰升级**：使用存档的分数升级母舰
4. **视觉增强**：添加母舰引擎光晕动画
5. **声音反馈**：添加按住时的音效

---

**文档结束**

