# Air War 项目架构重构设计文档

**日期**: 2026-04-14  
**项目**: Air War (飞机大战游戏)  
**目标**: 完整重构，消除架构问题，提升代码质量

---

## 📋 目录

1. [重构概述](#1-重构概述)
2. [Phase 1: 输入层抽象](#2-phase-1-输入层抽象)
3. [Phase 2: GameScene 拆分](#3-phase-2-gamescene-拆分)
4. [Phase 3: Enemy/Boss 解耦](#4-phase-3-enemyboss-解耦)
5. [Phase 4: RewardSystem 重构](#5-phase-4-rewardsystem-重构)
6. [文件结构规划](#6-文件结构规划)
7. [实现优先级](#7-实现优先级)
8. [预期成果](#8-预期成果)

---

## 1. 重构概述

### 1.1 当前架构问题

| 问题 | 严重程度 | 描述 |
|------|----------|------|
| GameScene 上帝类 | 🔴 严重 | 524行，混合所有职责 |
| Enemy/Boss 循环依赖 | 🔴 严重 | 实体直接持有GameScene引用 |
| Player 直接操作pygame | 🟡 中等 | 违反解耦要求 |
| RewardSystem if-elif链 | 🟡 中等 | 违反开闭原则 |
| HUDRenderer 直接使用pygame | 🟢 轻微 | 渲染层未解耦 |

### 1.2 重构目标

- ✅ 消除上帝类 (God Class)
- ✅ 实现完全解耦
- ✅ 遵循开闭原则
- ✅ 提升可测试性
- ✅ 保持功能完全兼容

---

## 2. Phase 1: 输入层抽象

### 2.1 设计目标
消除 Player 对 pygame 的直接依赖，实现输入处理的解耦。

### 2.2 文件结构

```
airwar/
├── input/                          # 新增：输入模块
│   ├── __init__.py
│   └── input_handler.py
└── entities/
    └── player.py                   # 修改：接受InputHandler依赖
```

### 2.3 核心接口

```python
# airwar/input/input_handler.py

from abc import ABC, abstractmethod
from airwar.entities.base import Vector2
import pygame

class InputHandler(ABC):
    """输入处理抽象接口"""
    
    DEFAULT_BINDINGS = {
        'left': pygame.K_LEFT,
        'left_alt': pygame.K_a,
        'right': pygame.K_RIGHT,
        'right_alt': pygame.K_d,
        'up': pygame.K_UP,
        'up_alt': pygame.K_w,
        'down': pygame.K_DOWN,
        'down_alt': pygame.K_s,
        'fire': pygame.K_SPACE,
        'pause': pygame.K_ESCAPE,
    }
    
    @abstractmethod
    def get_movement_direction(self) -> Vector2:
        """获取移动方向，返回 (dx, dy)"""
        pass
    
    @abstractmethod
    def is_fire_pressed(self) -> bool:
        """检查是否按下开火键"""
        pass
    
    @abstractmethod
    def is_pause_pressed(self) -> bool:
        """检查是否按下暂停键"""
        pass

class PygameInputHandler(InputHandler):
    """Pygame实现"""
    
    def __init__(self, key_bindings: dict = None):
        self._bindings = key_bindings or self.DEFAULT_BINDINGS
    
    def get_movement_direction(self) -> Vector2:
        keys = pygame.key.get_pressed()
        dx = 0
        dy = 0
        
        if keys[self._bindings['left']] or keys[self._bindings['left_alt']]:
            dx = -1
        if keys[self._bindings['right']] or keys[self._bindings['right_alt']]:
            dx = 1
        if keys[self._bindings['up']] or keys[self._bindings['up_alt']]:
            dy = -1
        if keys[self._bindings['down']] or keys[self._bindings['down_alt']]:
            dy = 1
            
        return Vector2(dx, dy)
    
    def is_fire_pressed(self) -> bool:
        keys = pygame.key.get_pressed()
        return keys[self._bindings['fire']]
    
    def is_pause_pressed(self) -> bool:
        keys = pygame.key.get_pressed()
        return keys[self._bindings['pause']]
```

### 2.4 Player 重构

```python
# airwar/entities/player.py (修改后)

class Player(Entity):
    def __init__(self, x: float, y: float, input_handler: InputHandler):
        super().__init__(x, y, 50, 60)
        self._input_handler = input_handler
        self.health = 100
        self.max_health = 100
        self.score = 0
        self.fire_cooldown = 0
        self.bullet_damage = 50
        self._bullets: List[Bullet] = []
        self.hitbox_width = 20
        self.hitbox_height = 24
        self.hitbox_timer = 0
    
    def update(self, dt: float) -> None:
        from airwar.config import PLAYER_SPEED, get_screen_width, get_screen_height
        
        direction = self._input_handler.get_movement_direction()
        self.rect.x += direction.x * PLAYER_SPEED
        self.rect.y += direction.y * PLAYER_SPEED
        
        screen_width = get_screen_width()
        screen_height = get_screen_height()
        
        self.rect.x = max(0, min(self.rect.x, screen_width - self.rect.width))
        self.rect.y = max(0, min(self.rect.y, screen_height - self.rect.height))
        
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
        
        for bullet in self._bullets:
            bullet.update()
        
        self._bullets = [b for b in self._bullets if b.active]
        self.hitbox_timer += 1
```

### 2.5 优点

- ✅ 完全解耦 - Player 不再依赖 pygame
- ✅ 可测试性 - 可以注入 MockInputHandler 进行单元测试
- ✅ 可扩展 - 未来可以轻松添加手柄支持

---

## 3. Phase 2: GameScene 拆分

### 3.1 设计目标
将 524 行的 GameScene 拆分为多个职责明确的子系统。

### 3.2 拆分后的子系统架构

```
airwar/
├── scenes/
│   └── game_scene.py              # 精简后的GameScene (~150行)
│
├── game/
│   ├── controllers/               # 新增：游戏控制器层
│   │   ├── __init__.py
│   │   ├── game_controller.py    # 游戏主控制器
│   │   ├── spawn_controller.py    # 生成控制器
│   │   └── collision_controller.py  # 碰撞控制器
│   │
│   ├── systems/
│   │   ├── health_system.py       # 保留
│   │   ├── reward_system.py       # 重构
│   │   ├── hud_renderer.py        # 重构
│   │   └── notification_manager.py  # 新增：通知系统
│   │
│   └── rendering/                 # 新增：渲染层
│       ├── __init__.py
│       └── game_renderer.py       # 游戏渲染器
```

### 3.3 GameController - 游戏主控制器

```python
# airwar/game/controllers/game_controller.py

from dataclasses import dataclass, field
from typing import List, Optional
from airwar.config import DIFFICULTY_SETTINGS

@dataclass
class GameState:
    difficulty: str = 'medium'
    username: str = 'Player'
    score: int = 0
    score_multiplier: int = 1
    paused: bool = False
    running: bool = True
    player_invincible: bool = False
    invincibility_timer: int = 0
    ripple_effects: List[dict] = field(default_factory=list)
    notification: Optional[str] = None
    notification_timer: int = 0
    entrance_animation: bool = True
    entrance_timer: int = 0
    entrance_duration: int = 60

class GameController:
    """游戏主控制器 - 协调所有子系统"""
    
    def __init__(self, difficulty: str, username: str):
        settings = DIFFICULTY_SETTINGS[difficulty]
        self.state = GameState()
        self.state.difficulty = difficulty
        self.state.username = username
        self.state.score_multiplier = {'easy': 1, 'medium': 2, 'hard': 3}[difficulty]
        
        self.health_system = HealthSystem(difficulty)
        self.reward_system = RewardSystem()
        self.spawn_controller = SpawnController(settings)
        self.collision_controller = CollisionController()
        self.notification_manager = NotificationManager()
        
        self.cycle_count = 0
        self.milestone_index = 0
        self.max_cycles = 10
        self.base_thresholds = [1000, 2500, 5000, 10000, 20000]
        self.cycle_multiplier = 1.5
        self.difficulty_threshold_multiplier = {'easy': 1.0, 'medium': 1.5, 'hard': 2.0}[difficulty]
    
    def update(self, player: Player, dt: float) -> None:
        """更新所有子系统"""
        has_regen = 'Regeneration' in self.reward_system.unlocked_buffs
        self.health_system.update(player, has_regen)
        
        self.spawn_controller.update(
            self.state.score, 
            self.reward_system.slow_factor
        )
        
        self.notification_manager.update()
        
        if self.state.notification_timer > 0:
            self.state.notification_timer -= 1
        
        self._check_milestones()
    
    def _check_milestones(self) -> None:
        """检查是否达到里程碑"""
        if self.cycle_count >= self.max_cycles:
            return
        
        threshold = self._get_next_threshold()
        if self.state.score >= threshold:
            return threshold
        return None
    
    def _get_next_threshold(self) -> float:
        base = self.base_thresholds[self.milestone_index % len(self.base_thresholds)]
        cycle_bonus = self.milestone_index // len(self.base_thresholds)
        return base * (self.cycle_multiplier ** cycle_bonus) * self.difficulty_threshold_multiplier
```

### 3.4 SpawnController - 生成控制器

```python
# airwar/game/controllers/spawn_controller.py

import random
from typing import List, Optional
from airwar.entities import Enemy, Boss, EnemySpawner, BossData, EnemyData
from airwar.config import get_screen_width

class SpawnController:
    """管理敌人生成和Boss生成"""
    
    def __init__(self, settings: dict):
        self.enemy_spawner = EnemySpawner()
        self.enemy_spawner.set_params(
            health=settings['enemy_health'],
            speed=settings['enemy_speed'],
            spawn_rate=settings['spawn_rate']
        )
        
        self.enemies: List[Enemy] = []
        self.boss: Optional[Boss] = None
        self.boss_spawn_timer = 0
        self.boss_spawn_interval = 1800
        self.boss_killed = False
    
    def update(self, score: int, slow_factor: float) -> None:
        """更新生成逻辑"""
        self.enemy_spawner.update(self.enemies, slow_factor)
        
        self.boss_spawn_timer += 1
        if self.boss is None and self.boss_spawn_timer >= self.boss_spawn_interval / slow_factor:
            self.boss_spawn_timer = 0
            return True  # 需要生成Boss
        return False
    
    def spawn_boss(self, cycle_count: int, bullet_damage: int) -> Boss:
        """生成Boss"""
        screen_width = get_screen_width()
        base_health = 500 * (1 + cycle_count * 0.5)
        escape_time = int(base_health / bullet_damage * 2.5)
        escape_time = max(600, min(escape_time, 1800))
        
        boss_data = BossData(
            health=base_health,
            speed=1.5 + cycle_count * 0.1,
            score=5000 + cycle_count * 1000,
            width=120,
            height=100,
            fire_rate=60 - cycle_count * 3,
            phase=1,
            escape_time=escape_time
        )
        
        boss = Boss(screen_width // 2 - boss_data.width // 2, -100, boss_data)
        self.boss = boss
        return boss
    
    def cleanup(self) -> None:
        """清理不活跃的实体"""
        self.enemies = [e for e in self.enemies if e.active]
        if self.boss and not self.boss.active:
            self.boss = None
```

### 3.5 CollisionController - 碰撞控制器

```python
# airwar/game/controllers/collision_controller.py

from typing import List, Tuple
from airwar.entities import Player, Enemy, Boss, Bullet
from airwar.game.systems.reward_system import RewardSystem

@dataclass
class CollisionResult:
    player_damaged: bool = False
    enemies_killed: int = 0
    score_gained: int = 0
    boss_damaged: bool = False
    boss_killed: bool = False

class CollisionController:
    """集中管理所有碰撞检测逻辑"""
    
    def __init__(self):
        pass
    
    def update(self,
               player: Player,
               player_bullets: List[Bullet],
               enemies: List[Enemy],
               enemy_bullets: List[Bullet],
               boss: Boss,
               reward_system: RewardSystem,
               score_multiplier: int) -> CollisionResult:
        
        result = CollisionResult()
        
        self._check_player_bullets_vs_enemies(
            player_bullets, enemies, reward_system, score_multiplier, result)
        
        self._check_player_bullets_vs_boss(
            player_bullets, boss, reward_system, result)
        
        self._check_enemy_bullets_vs_player(
            enemy_bullets, player, reward_system, result)
        
        self._check_player_vs_enemies(
            player, enemies, reward_system, result)
        
        return result
    
    def _check_player_bullets_vs_enemies(self, ...):
        """玩家子弹 vs 敌人"""
        # 实现碰撞检测逻辑
    
    def _check_player_bullets_vs_boss(self, ...):
        """玩家子弹 vs Boss"""
        # 实现碰撞检测逻辑
    
    def _check_enemy_bullets_vs_player(self, ...):
        """敌人子弹 vs 玩家"""
        # 实现碰撞检测逻辑
    
    def _check_player_vs_enemies(self, ...):
        """玩家 vs 敌人"""
        # 实现碰撞检测逻辑
```

### 3.6 GameRenderer - 游戏渲染器

```python
# airwar/game/rendering/game_renderer.py

import pygame
from airwar.game.systems.hud_renderer import HUDRenderer
from airwar.game.controllers.game_controller import GameState
from typing import List

@dataclass
class GameEntities:
    player: Player
    enemies: List[Enemy]
    boss: Boss

class GameRenderer:
    """统一管理游戏渲染"""
    
    def __init__(self, hud_renderer: HUDRenderer = None):
        self.hud_renderer = hud_renderer or HUDRenderer()
    
    def render(self, surface: pygame.Surface, 
               state: GameState,
               entities: GameEntities) -> None:
        
        surface.fill((0, 0, 0))
        
        if state.entrance_animation:
            self._render_entrance(surface, state, entities)
        else:
            self._render_game(surface, state, entities)
    
    def _render_entrance(self, surface, state, entities):
        """渲染入场动画"""
        progress = state.entrance_timer / state.entrance_duration
        zoom_scale = 1.0 + (1.5 - 1.0) * (1 - progress)
        
        if not state.player_invincible or (state.invincibility_timer // 5) % 2 == 0:
            entities.player.render(surface)
        
        for enemy in entities.enemies:
            enemy.render(surface)
        
        if entities.boss:
            entities.boss.render(surface)
    
    def _render_game(self, surface, state, entities):
        """渲染正常游戏画面"""
        if not state.player_invincible or (state.invincibility_timer // 5) % 2 == 0:
            entities.player.render(surface)
        
        for enemy in entities.enemies:
            enemy.render(surface)
        
        if entities.boss:
            entities.boss.render(surface)
            self.hud_renderer.render_boss_health_bar(surface, entities.boss)
        
        self.hud_renderer.render_ripples(surface, state.ripple_effects)
        self.hud_renderer.render_hud(...)
```

### 3.7 NotificationManager - 通知系统

```python
# airwar/game/systems/notification_manager.py

import pygame
from typing import Optional

class NotificationManager:
    """管理游戏通知和提示"""
    
    def __init__(self, duration: int = 90):
        self.current_notification: Optional[str] = None
        self.timer: int = 0
        self.duration = duration
        self.notif_font = pygame.font.Font(None, 32)
    
    def show(self, message: str, duration: int = None) -> None:
        self.current_notification = message
        self.timer = duration or self.duration
    
    def update(self) -> None:
        if self.timer > 0:
            self.timer -= 1
    
    def render(self, surface: pygame.Surface) -> None:
        if self.timer > 0 and self.current_notification:
            alpha = min(255, self.timer * 4)
            color = (0, 255, 150) if alpha > 150 else (150, 255, 200)
            text = self.notif_font.render(self.current_notification, True, color)
            text.set_alpha(alpha)
            x = surface.get_width() // 2 - text.get_width() // 2
            y = 100
            surface.blit(text, (x, y))
```

### 3.8 简化后的 GameScene

```python
# airwar/scenes/game_scene.py (精简后)

class GameScene(Scene):
    def __init__(self):
        self.controller: Optional[GameController] = None
        self.renderer: Optional[GameRenderer] = None
        self.player: Optional[Player] = None
        self.input_handler: Optional[PygameInputHandler] = None
        
        self.enemies = []
        self.enemy_bullets = []
        self.boss = None
        self.cycle_count = 0
        self.kills = 0
    
    def enter(self, **kwargs) -> None:
        difficulty = kwargs.get('difficulty', 'medium')
        username = kwargs.get('username', 'Player')
        
        self.controller = GameController(difficulty, username)
        self.renderer = GameRenderer(HUDRenderer())
        
        from airwar.config import get_screen_width, get_screen_height
        self.input_handler = PygameInputHandler()
        self.player = Player(
            get_screen_width() // 2 - 25,
            get_screen_height() - 100,
            self.input_handler
        )
        
        settings = DIFFICULTY_SETTINGS[difficulty]
        self.player.bullet_damage = settings['bullet_damage']
        
        self.controller.spawn_controller.enemy_spawner.set_bullet_spawner(
            EnemyBulletSpawner(self.enemy_bullets)
        )
    
    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if not self.reward_selector.visible:
                    self.controller.state.paused = not self.controller.state.paused
            elif event.key == pygame.K_SPACE:
                if not self.controller.state.paused and not self.reward_selector.visible:
                    self.player.fire()
        
        self.reward_selector.handle_input(event)
    
    def update(self, *args, **kwargs) -> None:
        self.reward_selector.update()
        
        if self.controller.state.entrance_animation:
            self._update_entrance()
            return
        
        if self.controller.state.paused or self.reward_selector.visible:
            return
        
        self.player.update()
        self.player.auto_fire()
        
        self._update_game_logic()
    
    def _update_game_logic(self) -> None:
        """更新游戏逻辑"""
        # 更新敌人
        for enemy in self.enemies:
            enemy.update()
        
        # 检查Boss生成
        if self.controller.spawn_controller.update(
            self.controller.state.score,
            self.controller.reward_system.slow_factor
        ):
            boss = self.controller.spawn_controller.spawn_boss(
                self.cycle_count,
                self.player.bullet_damage
            )
            boss.set_bullet_spawner(
                EnemyBulletSpawner(self.enemy_bullets)
            )
            self.boss = boss
        
        # 碰撞检测
        # ...
    
    def render(self, surface: pygame.Surface) -> None:
        entities = GameEntities(
            player=self.player,
            enemies=self.enemies,
            boss=self.boss
        )
        self.renderer.render(surface, self.controller.state, entities)
```

---

## 4. Phase 3: Enemy/Boss 解耦

### 4.1 设计目标
消除 Enemy 和 Boss 对 GameScene 的直接引用，使用策略模式和事件系统实现完全解耦。

### 4.2 核心问题

```python
# 当前问题：Enemy 直接持有 GameScene 引用
class Enemy(Entity):
    def set_game_scene(self, game: 'GameScene') -> None:
        self.game_scene = game  # 循环依赖！
    
    def _fire(self) -> None:
        game.enemy_bullets.append(bullet)  # 直接访问容器
```

### 4.3 BulletSpawner 接口

```python
# airwar/entities/interfaces.py

from abc import ABC, abstractmethod
from typing import List
from .bullet import Bullet

class IBulletSpawner(ABC):
    """子弹生成器接口"""
    
    @abstractmethod
    def spawn_bullet(self, bullet: Bullet) -> None:
        """生成子弹"""
        pass
```

### 4.4 Enemy 重构

```python
# airwar/entities/enemy.py (修改后)

class Enemy(Entity):
    def __init__(self, x: float, y: float, data: EnemyData):
        super().__init__(x, y, 40, 40)
        self.data = data
        self.health = data.health
        self.max_health = data.health
        self.fire_timer = random.randint(0, data.fire_rate)
        
        self._bullet_spawner: IBulletSpawner = None
        self.entity_id = id(self)
    
    def set_bullet_spawner(self, spawner: IBulletSpawner) -> None:
        """设置子弹生成器 - 依赖注入"""
        self._bullet_spawner = spawner
    
    def _fire(self) -> None:
        """生成子弹并通过策略发射"""
        bullets = self._create_bullets()
        
        if self._bullet_spawner:
            for bullet in bullets:
                self._bullet_spawner.spawn_bullet(bullet)
    
    def _create_bullets(self) -> List[Bullet]:
        """根据子弹类型创建子弹"""
        bullets = []
        center_x = self.rect.centerx - 5
        
        if self.data.bullet_type == "spread":
            for angle in [-20, 0, 20]:
                bullet_data = BulletData(
                    damage=8,
                    speed=5.0,
                    owner="enemy",
                    bullet_type="spread"
                )
                bullet = Bullet(center_x + angle, self.rect.bottom, bullet_data)
                bullet.velocity = Vector2(angle * 0.1, 5)
                bullets.append(bullet)
        
        elif self.data.bullet_type == "laser":
            bullet_data = BulletData(
                damage=25,
                speed=5.0,
                owner="enemy",
                bullet_type="laser"
            )
            bullet = Bullet(center_x, self.rect.bottom, bullet_data)
            bullet.velocity = Vector2(0, 8)
            bullets.append(bullet)
        
        else:
            bullet_data = BulletData(
                damage=15,
                speed=5.0,
                owner="enemy",
                bullet_type="single"
            )
            bullet = Bullet(center_x, self.rect.bottom, bullet_data)
            bullets.append(bullet)
        
        return bullets
```

### 4.5 Boss 重构

```python
# airwar/entities/enemy.py (Boss部分修改后)

class Boss(Entity):
    def __init__(self, x: float, y: float, data: BossData):
        super().__init__(x, y, data.width, data.height)
        self.data = data
        self.health = data.health
        self.max_health = data.health
        self.fire_timer = 0
        self.phase_timer = 0
        self.move_direction = 1
        self.move_timer = 0
        self.attack_pattern = 0
        self.entering = True
        self.phase = data.phase
        self.survival_timer = 0
        self.escaped = False
        
        self._bullet_spawner: IBulletSpawner = None
        self.entity_id = id(self)
    
    def set_bullet_spawner(self, spawner: IBulletSpawner) -> None:
        self._bullet_spawner = spawner
    
    def _fire(self) -> None:
        """使用攻击策略发射子弹"""
        bullets = []
        
        if self.attack_pattern == 0:
            bullets = self._spread_attack()
        elif self.attack_pattern == 1:
            bullets = self._aim_attack()
        else:
            bullets = self._wave_attack()
        
        if self._bullet_spawner:
            for bullet in bullets:
                self._bullet_spawner.spawn_bullet(bullet)
        
        self.attack_pattern = (self.attack_pattern + 1) % 3
    
    def _spread_attack(self) -> List[Bullet]:
        """扩散攻击"""
        bullets = []
        center_x = self.rect.centerx
        bullet_count = 5 + self.phase
        
        for i in range(bullet_count):
            angle = -90 + (180 / (bullet_count - 1)) * i
            rad = math.radians(angle)
            speed = 5.0
            vx = math.cos(rad) * speed
            vy = math.sin(rad) * speed
            
            bullet_data = BulletData(
                damage=10 + self.phase * 2,
                speed=5.0,
                owner="enemy",
                bullet_type="spread"
            )
            bullet = Bullet(center_x, self.rect.bottom, bullet_data)
            bullet.velocity = Vector2(vx, vy)
            bullets.append(bullet)
        
        return bullets
    
    def _aim_attack(self, player_pos: Tuple[float, float] = None) -> List[Bullet]:
        """追踪攻击"""
        bullets = []
        
        if player_pos is None:
            player_pos = (self.rect.centerx, self.rect.bottom + 500)
        
        bullet_data = BulletData(
            damage=15 + self.phase * 3,
            speed=7.0,
            owner="enemy",
            bullet_type="laser"
        )
        
        dx = player_pos[0] - self.rect.centerx
        dy = player_pos[1] - self.rect.bottom
        dist = math.sqrt(dx * dx + dy * dy)
        
        for i in range(3):
            bullet = Bullet(
                self.rect.centerx - 30 + i * 30,
                self.rect.bottom,
                bullet_data
            )
            bullet.velocity = Vector2(dx / dist * 6, dy / dist * 6)
            bullets.append(bullet)
        
        return bullets
    
    def _wave_attack(self) -> List[Bullet]:
        """波浪攻击"""
        bullets = []
        center_x = self.rect.centerx
        
        for i in range(8):
            angle = -90 + 22.5 * i
            rad = math.radians(angle)
            speed = 4.0
            
            bullet_data = BulletData(
                damage=8,
                speed=speed,
                owner="enemy",
                bullet_type="single"
            )
            bullet = Bullet(center_x, self.rect.centery, bullet_data)
            bullet.velocity = Vector2(math.cos(rad) * speed, math.sin(rad) * speed)
            bullets.append(bullet)
        
        return bullets
```

### 4.6 BulletSpawner 实现

```python
# airwar/game/spawners/enemy_bullet_spawner.py

from typing import List
from airwar.entities.interfaces import IBulletSpawner
from airwar.entities.bullet import Bullet

class EnemyBulletSpawner(IBulletSpawner):
    """敌人子弹生成器实现"""
    
    def __init__(self, bullet_list: List[Bullet] = None):
        self.bullet_list = bullet_list if bullet_list else []
    
    def spawn_bullet(self, bullet: Bullet) -> None:
        self.bullet_list.append(bullet)
    
    def get_bullets(self) -> List[Bullet]:
        return self.bullet_list
    
    def clear_inactive(self) -> None:
        self.bullet_list = [b for b in self.bullet_list if b.active]
```

### 4.7 EnemySpawner 改造

```python
# airwar/entities/enemy.py (EnemySpawner修改后)

class EnemySpawner:
    def __init__(self):
        self.spawn_timer = 0
        self.health = 100
        self.speed = 3.0
        self.spawn_rate = 30
        self.bullet_type = "single"
        
        self._bullet_spawner: IBulletSpawner = None
    
    def set_bullet_spawner(self, spawner: IBulletSpawner) -> None:
        self._bullet_spawner = spawner
    
    def update(self, enemies: List[Enemy], slow_factor: float = 1.0) -> None:
        from airwar.config import get_screen_width
        screen_width = get_screen_width()
        
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_rate:
            self.spawn_timer = 0
            x = random.randint(0, screen_width - 40)
            
            bullet_types = ["single", "spread", "laser"]
            bullet_type = random.choice(bullet_types)
            
            data = EnemyData(
                health=self.health,
                speed=self.speed * slow_factor,
                bullet_type=bullet_type,
                fire_rate=90 if bullet_type == "laser" else 120
            )
            
            enemy = Enemy(x, -40, data)
            
            if self._bullet_spawner:
                enemy.set_bullet_spawner(self._bullet_spawner)
            
            enemies.append(enemy)
```

### 4.8 架构对比

```
【重构前】
Enemy ──→ GameScene (循环依赖!)
  ↓
  └── 直接访问 game_scene.enemy_bullets

【重构后】
Enemy ──→ IBulletSpawner (接口)
           ↑
           │
GameScene ─┘ (实现注入)
```

---

## 5. Phase 4: RewardSystem 重构

### 5.1 设计目标
将 if-elif 硬编码链重构为策略模式，消除违反开闭原则的问题。

### 5.2 核心问题

```python
# 当前问题：15个if-elif硬编码
def apply_reward(self, reward: Dict, player) -> str:
    if name == 'Extra Life':
        player.max_health += 50
    elif name == 'Regeneration':
        pass
    # ... 更多elif
```

### 5.3 Buff 基类

```python
# airwar/game/buffs/base_buff.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple

@dataclass
class BuffResult:
    name: str
    notification: str
    color: Tuple[int, int, int]

class Buff(ABC):
    """Buff基类 - 遵循开闭原则"""
    
    @abstractmethod
    def apply(self, player) -> BuffResult:
        """应用Buff效果"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        pass
    
    @abstractmethod
    def get_color(self) -> Tuple[int, int, int]:
        pass
```

### 5.4 具体 Buff 实现

```python
# airwar/game/buffs/health_buffs.py

from .base_buff import Buff, BuffResult

class ExtraLifeBuff(Buff):
    def apply(self, player) -> BuffResult:
        player.max_health += 50
        player.health += 30
        return BuffResult(
            name='Extra Life',
            notification='REWARD: Extra Life',
            color=(100, 255, 150)
        )
    
    def get_name(self) -> str:
        return 'Extra Life'
    
    def get_color(self) -> Tuple[int, int, int]:
        return (100, 255, 150)

class RegenerationBuff(Buff):
    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Regeneration',
            notification='REWARD: Regeneration',
            color=(150, 255, 100)
        )
    
    def get_name(self) -> str:
        return 'Regeneration'
    
    def get_color(self) -> Tuple[int, int, int]:
        return (150, 255, 100)

class LifestealBuff(Buff):
    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Lifesteal',
            notification='REWARD: Lifesteal',
            color=(255, 100, 150)
        )
    
    def get_name(self) -> str:
        return 'Lifesteal'
    
    def get_color(self) -> Tuple[int, int, int]:
        return (255, 100, 150)
```

```python
# airwar/game/buffs/offense_buffs.py

from .base_buff import Buff, BuffResult

class PowerShotBuff(Buff):
    def apply(self, player) -> BuffResult:
        player.bullet_damage = int(player.bullet_damage * 1.25)
        return BuffResult(
            name='Power Shot',
            notification='REWARD: Power Shot',
            color=(255, 80, 80)
        )
    
    def get_name(self) -> str:
        return 'Power Shot'
    
    def get_color(self) -> Tuple[int, int, int]:
        return (255, 80, 80)

class RapidFireBuff(Buff):
    def apply(self, player) -> BuffResult:
        player.fire_cooldown = max(1, int(player.fire_cooldown * 0.8))
        return BuffResult(
            name='Rapid Fire',
            notification='REWARD: Rapid Fire',
            color=(255, 200, 100)
        )
    
    def get_name(self) -> str:
        return 'Rapid Fire'
    
    def get_color(self) -> Tuple[int, int, int]:
        return (255, 200, 100)

class PiercingBuff(Buff):
    def __init__(self):
        self.level = 0
    
    def apply(self, player) -> BuffResult:
        self.level += 1
        return BuffResult(
            name='Piercing',
            notification='REWARD: Piercing',
            color=(200, 200, 100)
        )
    
    def get_name(self) -> str:
        return 'Piercing'
    
    def get_color(self) -> Tuple[int, int, int]:
        return (200, 200, 100)

class SpreadShotBuff(Buff):
    def __init__(self):
        self.level = 0
    
    def apply(self, player) -> BuffResult:
        self.level += 1
        return BuffResult(
            name='Spread Shot',
            notification='REWARD: Spread Shot',
            color=(255, 150, 100)
        )
    
    def get_name(self) -> str:
        return 'Spread Shot'
    
    def get_color(self) -> Tuple[int, int, int]:
        return (255, 150, 100)

class ExplosiveBuff(Buff):
    def __init__(self):
        self.level = 0
    
    def apply(self, player) -> BuffResult:
        self.level += 1
        return BuffResult(
            name='Explosive',
            notification='REWARD: Explosive',
            color=(255, 100, 50)
        )
    
    def get_name(self) -> str:
        return 'Explosive'
    
    def get_color(self) -> Tuple[int, int, int]:
        return (255, 100, 50)
```

### 5.5 Buff 注册表

```python
# airwar/game/buffs/buff_registry.py

from typing import Type, Dict
from .base_buff import Buff
from .health_buffs import ExtraLifeBuff, RegenerationBuff, LifestealBuff
from .offense_buffs import (
    PowerShotBuff, RapidFireBuff, PiercingBuff, 
    SpreadShotBuff, ExplosiveBuff
)

BUFF_REGISTRY: Dict[str, Type[Buff]] = {
    'Extra Life': ExtraLifeBuff,
    'Regeneration': RegenerationBuff,
    'Lifesteal': LifestealBuff,
    'Power Shot': PowerShotBuff,
    'Rapid Fire': RapidFireBuff,
    'Piercing': PiercingBuff,
    'Spread Shot': SpreadShotBuff,
    'Explosive': ExplosiveBuff,
}

def create_buff(name: str) -> Buff:
    buff_class = BUFF_REGISTRY.get(name)
    if buff_class:
        return buff_class()
    raise ValueError(f"Unknown buff: {name}")
```

### 5.6 重构后的 RewardSystem

```python
# airwar/game/systems/reward_system.py (重构后)

import random
from typing import List, Dict, Optional
from .buffs.buff_registry import BUFF_REGISTRY, create_buff
from .buffs.base_buff import Buff, BuffResult

class RewardSystem:
    def __init__(self):
        self.unlocked_buffs: List[str] = []
        self.active_buffs: Dict[str, Buff] = {}
        
        self.piercing_level: int = 0
        self.spread_level: int = 0
        self.explosive_level: int = 0
        self.armor_level: int = 0
        self.evasion_level: int = 0
        self.magnet_range: int = 0
        self.slow_factor: float = 1.0
    
    def generate_options(self, cycle_count: int, unlocked_buffs: list) -> List[Dict]:
        """生成奖励选项"""
        options = []
        categories = list(BUFF_REGISTRY.keys())
        
        for _ in range(3):
            name = random.choice(categories)
            
            if name in ['Spread Shot', 'Explosive'] and cycle_count > 2:
                continue
            
            reward = {
                'name': name,
                'desc': self._get_buff_description(name),
                'icon': self._get_buff_icon(name)
            }
            
            attempts = 0
            while reward in options and attempts < 10:
                name = random.choice(categories)
                reward = {
                    'name': name,
                    'desc': self._get_buff_description(name),
                    'icon': self._get_buff_icon(name)
                }
                attempts += 1
            
            options.append(reward)
        
        return options
    
    def apply_reward(self, reward: Dict, player) -> str:
        name = reward['name']
        
        if name in self.unlocked_buffs:
            return self._upgrade_buff(name, player)
        
        buff = create_buff(name)
        result = buff.apply(player)
        
        self.unlocked_buffs.append(name)
        self.active_buffs[name] = buff
        
        if name == 'Piercing':
            self.piercing_level += 1
        elif name == 'Spread Shot':
            self.spread_level += 1
        elif name == 'Explosive':
            self.explosive_level += 1
        elif name == 'Armor':
            self.armor_level += 1
        elif name == 'Evasion':
            self.evasion_level += 1
        elif name == 'Slow Field':
            self.slow_factor = 0.8
        
        return result.notification
    
    def _upgrade_buff(self, name: str, player) -> str:
        if name == 'Power Shot':
            player.bullet_damage = int(player.bullet_damage * 1.25)
        elif name == 'Rapid Fire':
            player.fire_cooldown = max(1, int(player.fire_cooldown * 0.8))
        elif name == 'Piercing':
            self.piercing_level += 1
        elif name == 'Spread Shot':
            self.spread_level += 1
        elif name == 'Explosive':
            self.explosive_level += 1
        
        return f"UPGRADED: {name}"
    
    def calculate_damage_taken(self, damage: int) -> int:
        if 'Armor' in self.unlocked_buffs:
            return int(damage * 0.85)
        return damage
    
    def try_dodge(self) -> bool:
        if 'Evasion' in self.unlocked_buffs:
            dodge_chance = 0.2
            if random.random() < dodge_chance:
                return True
        return False
    
    def apply_lifesteal(self, player, kill_value: int) -> None:
        if 'Lifesteal' in self.unlocked_buffs:
            heal = int(player.max_health * 0.1)
            player.health = min(player.health + heal, player.max_health)
    
    def do_explosive_damage(self, enemies: list, x: int, y: int, damage: int) -> None:
        if self.explosive_level <= 0:
            return
        
        for enemy in enemies:
            if enemy.active:
                dist = ((enemy.rect.centerx - x) ** 2 + (enemy.rect.centery - y) ** 2) ** 0.5
                if dist < 60:
                    enemy.take_damage(int(damage * 0.5))
    
    def get_buff_color(self, name: str) -> tuple:
        if name in self.active_buffs:
            return self.active_buffs[name].get_color()
        
        buff = create_buff(name)
        return buff.get_color()
    
    def _get_buff_description(self, name: str) -> str:
        descriptions = {
            'Extra Life': '+50 Max HP, +30 HP',
            'Regeneration': 'Passively heal 2 HP/sec',
            'Lifesteal': '+10% lifesteal on kill',
            'Power Shot': '+25% bullet damage',
            'Rapid Fire': '+20% fire rate',
            'Piercing': 'Bullets pierce 1 enemy',
            'Spread Shot': 'Fire 3 bullets at once',
            'Explosive': 'Bullets deal 30 AoE damage',
        }
        return descriptions.get(name, '')
    
    def _get_buff_icon(self, name: str) -> str:
        icons = {
            'Extra Life': 'HP',
            'Regeneration': 'REG',
            'Lifesteal': 'LST',
            'Power Shot': 'DMG',
            'Rapid Fire': 'RPD',
            'Piercing': 'PIR',
            'Spread Shot': 'SPD',
            'Explosive': 'EXP',
        }
        return icons.get(name, '?')
    
    def reset(self) -> None:
        self.unlocked_buffs = []
        self.active_buffs = {}
        self.piercing_level = 0
        self.spread_level = 0
        self.explosive_level = 0
        self.armor_level = 0
        self.evasion_level = 0
        self.magnet_range = 0
        self.slow_factor = 1.0
```

---

## 6. 文件结构规划

### 6.1 新增文件

```
airwar/
├── input/                              # 新增：输入模块
│   ├── __init__.py
│   └── input_handler.py
│
├── entities/
│   ├── interfaces.py                   # 新增：实体接口
│   ├── enemy.py                        # 修改：解耦重构
│   └── player.py                       # 修改：输入解耦
│
├── game/
│   ├── buffs/                          # 新增：Buff系统
│   │   ├── __init__.py
│   │   ├── base_buff.py
│   │   ├── buff_registry.py
│   │   ├── health_buffs.py
│   │   ├── offense_buffs.py
│   │   └── defense_buffs.py
│   │
│   ├── controllers/                   # 新增：游戏控制器
│   │   ├── __init__.py
│   │   ├── game_controller.py
│   │   ├── spawn_controller.py
│   │   └── collision_controller.py
│   │
│   ├── spawners/                       # 新增：生成器
│   │   ├── __init__.py
│   │   └── enemy_bullet_spawner.py
│   │
│   ├── rendering/                      # 新增：渲染层
│   │   ├── __init__.py
│   │   └── game_renderer.py
│   │
│   └── systems/
│       ├── health_system.py            # 保留
│       ├── reward_system.py            # 重构
│       ├── hud_renderer.py             # 重构
│       └── notification_manager.py     # 新增
│
└── scenes/
    └── game_scene.py                   # 重构：精简
```

### 6.2 修改文件

| 文件 | 修改内容 |
|------|----------|
| `entities/player.py` | 注入InputHandler依赖 |
| `entities/enemy.py` | 移除GameScene引用，使用IBulletSpawner |
| `game/systems/reward_system.py` | 重构为Buff策略模式 |
| `scenes/game_scene.py` | 拆分为子系统协调器 |

---

## 7. 实现优先级

### Phase 1: 基础设施 (预计2-3小时)
1. ✅ 创建 input 模块
2. ✅ 重构 Player 使用 InputHandler
3. ✅ 创建 entities/interfaces.py

### Phase 2: 解耦 Enemy/Boss (预计2-3小时)
4. ✅ 创建 EnemyBulletSpawner 实现
5. ✅ 重构 Enemy 移除 GameScene 引用
6. ✅ 重构 Boss 移除 GameScene 引用
7. ✅ 重构 EnemySpawner 使用依赖注入

### Phase 3: GameScene 拆分 (预计3-4小时)
8. ✅ 创建 GameController
9. ✅ 创建 SpawnController
10. ✅ 创建 CollisionController
11. ✅ 创建 GameRenderer
12. ✅ 创建 NotificationManager
13. ✅ 精简 GameScene

### Phase 4: RewardSystem 重构 (预计2-3小时)
14. ✅ 创建 Buff 基类和注册表
15. ✅ 实现所有 Buff 类
16. ✅ 重构 RewardSystem 使用 Buff 策略

### 总计预计时间: 9-13 小时

---

## 8. 预期成果

### 8.1 代码质量指标

| 指标 | 重构前 | 重构后 | 改进 |
|------|--------|--------|------|
| **GameScene 行数** | 524 行 | ~150 行 | -71% |
| **单一职责遵循** | ❌ 违反 | ✅ 遵循 | 完全符合 |
| **子系统数量** | 0 | 10+ | 显著增加 |
| **耦合度** | 高 | 低 | 显著降低 |
| **可测试性** | 困难 | 各子系统可独立测试 | 显著提升 |
| **可扩展性** | 困难 | 新Buff只需添加类 | 显著提升 |

### 8.2 架构对比

```
【重构前】
main.py
  └── Game
        ├── Window
        ├── SceneManager
        │     └── GameScene ⚠️ (524行, 职责过重)
        │           ├── Player ⚠️ (直接操作pygame)
        │           ├── Enemy/Boss ⚠️ (持有game_scene引用)
        │           └── RewardSystem ⚠️ (if-elif链)
        └── ...

【重构后】
main.py
  └── Game
        ├── Window ✓
        ├── SceneManager
        │     └── GameScene ✓ (150行, 仅协调)
        │           ├── GameController
        │           │     ├── SpawnController
        │           │     ├── CollisionController
        │           │     ├── HealthSystem
        │           │     ├── RewardSystem (Buff策略)
        │           │     └── NotificationManager
        │           ├── GameRenderer
        │           └── Player ✓ (InputHandler注入)
        │           └── Enemy/Boss ✓ (IBulletSpawner注入)
        └── ...
```

### 8.3 优点总结

- ✅ **消除上帝类** - GameScene 职责清晰
- ✅ **完全解耦** - 模块间通过接口通信
- ✅ **开闭原则** - 新增Buff只需添加类
- ✅ **可测试性** - 各子系统可独立测试
- ✅ **可扩展性** - 易于添加新功能
- ✅ **职责清晰** - 每个类都有明确职责

---

## 📝 备注

本文档为完整重构设计文档，包含所有四个阶段的设计方案。请在确认后开始实现。
