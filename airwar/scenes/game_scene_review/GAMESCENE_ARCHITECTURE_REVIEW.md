# GameScene Architecture Review Report

**File**: `/Users/xiepeilin/TRAE1/AIRWAR/airwar/scenes/game_scene.py`
**Review Date**: 2025-09-19
**Reviewer**: Architecture Enforcer

---

## Part 1: Executive Summary

| Aspect | Current State | Target State | Effort |
|--------|---------------|--------------|--------|
| **Class Size** | 530 lines | < 300 lines | Medium |
| **Method Count** | 25+ methods | < 15 methods | High |
| **Nesting Depth** | Max 5 levels | ≤ 3 levels | Medium |
| **Property Count** | 23 properties | < 10 properties | Low |
| **Magic Numbers** | 10+ instances | 0 instances | Low |
| **Testability** | Medium | High | Medium |

### Risk Assessment

| Category | Rating | Description |
|----------|--------|-------------|
| **Single Responsibility** | ⚠️ Medium Risk | 单一类承担过多职责 |
| **Coupling** | ⚠️ Medium Risk | 直接依赖多个具体实现类 |
| **Complexity** | ⚠️ Medium Risk | 方法过长，嵌套过深 |
| **Maintainability** | ⚠️ Medium Risk | 属性委托过多，反射访问私有成员 |
| **Testability** | ✅ Low Risk | 依赖注入模式，接口较清晰 |

**Overall Assessment**: `GameScene` 存在**上帝类反模式**，需要拆分为多个职责明确的组件。

---

## Part 2: Problems Identified

### 2.1 God Class Pattern (严重)

`GameScene` 承担了以下职责：

```
GameScene 职责清单:
├── 1. 游戏入口/场景管理 (enter/exit)
├── 2. 游戏循环控制 (update/render)
├── 3. 输入事件处理 (handle_events)
├── 4. 碰撞检测逻辑 (_check_collisions)
├── 5. 敌人生成控制 (_update_enemy_spawning)
├── 6. Boss战逻辑 (_update_boss)
├── 7. 奖励系统触发 (_check_milestones)
├── 8. 母舰系统集成 (_init_mother_ship_system)
├── 9. 状态属性代理 (20+ 属性)
├── 10. 存档恢复逻辑 (restore_from_save)
└── 11. HUD渲染协调 (_render_hud)
```

**违反原则**: SRP (单一职责原则)

### 2.2 Property Overload (中等)

```python
# 当前: 23个属性访问器 (Lines 357-529)
@property
def enemies(self) -> list: ...
@property
def score(self) -> int: ...
@property
def cycle_count(self) -> int: ...
@property
def kills(self) -> int: ...
@property
def milestone_index(self) -> int: ...
@property
def boss(self): ...
# ... 等等 17+ 个
```

**问题**: 这些属性只是委托给内部对象，暴露了过多内部实现细节。

### 2.3 Deep Nesting (中等)

**示例 1**: `_update_boss()` 方法 (Lines 181-214)

```python
def _update_boss(self) -> None:
    boss = self.spawn_controller.boss
    if not boss:                    # Level 1
        return
    player_pos = (...)
    boss.update(...)                # Level 1
    
    if not boss.is_entering() and boss.active:  # Level 2
        if boss.rect.colliderect(player_hitbox):  # Level 3
            if not self.game_controller.state.player_invincible:  # Level 4 ⚠️
                # 实际业务逻辑
```

**嵌套层级**: 4层 (超过标准3层限制)

**示例 2**: `_check_player_bullets_vs_enemies()` 方法 (Lines 247-266)

```python
for bullet in self.player.get_bullets():    # Level 1
    bullet.update()
    for enemy in enemies:                   # Level 2
        if bullet.active and enemy.active:  # Level 3
            if bullet_rect.colliderect(...): # Level 4 ⚠️
                if self.reward_system.explosive_level > 0:  # Level 5 ⚠️
```

**嵌套层级**: 5层 (严重超标)

### 2.4 Magic Numbers (轻微)

| Line | Code | Issue |
|------|------|-------|
| 63 | `self.player.rect.y = -80` | 硬编码初始Y位置 |
| 64 | `screen_height - 100` | 硬编码玩家最终Y位置 |
| 69 | `self.player.rect.y = -80` | 重复硬编码 |
| 145 | `damage = 30` | Boss碰撞伤害 |
| 150 | `damage = 20` | 敌人碰撞伤害 |
| 155 | `eb.data.damage` | 硬编码检查 |
| 157 | `self.player.remove_bullet(bullet)` | 错误处理时机 |
| 200 | `self.player.rect.y = 200` | 母舰状态玩家Y位置 |
| 201 | `self.player.rect.x = ... % 800` | 硬编码屏幕宽度 |

### 2.5 Private Member Access (中等)

**反模式**: 直接访问私有成员

```python
# Line 146: 访问 Player 私有成员
player_hitbox = self.player.get_hitbox()

# Line 214: 访问 RewardSystem 私有成员
self.reward_system.apply_lifesteal(self.player, boss.data.score)

# Line 522: 访问内部子系统私有状态
self.reward_system.unlocked_buffs = save_data.unlocked_buffs

# Line 526-531: 访问 RewardSystem 私有属性
self.reward_system.piercing_level = buff_levels.get('piercing_level', 0)
```

**问题**: 破坏封装性，暴露内部实现细节

---

## Part 3: Design Problems Summary

### 3.1 Responsibility Distribution Map

```
                    GameScene (God Class)
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
    ┌───┴───┐         ┌────┴────┐        ┌────┴────┐
    │输入处理│         │游戏循环控制│        │碰撞检测 │
    └───────┘         └─────────┘        └─────────┘
                                                │
                                    ┌───────────┼───────────┐
                                    │           │           │
                              ┌─────┴───┐  ┌────┴────┐  ┌───┴────┐
                              │玩家子弹 │  │敌人子弹 │  │Boss碰撞│
                              │ vs 敌人 │  │ vs 玩家 │  │        │
                              └─────────┘  └─────────┘  └────────┘
```

### 3.2 Dependency Graph

```
GameScene
    ├── GameController ⚠️ 直接依赖
    ├── GameRenderer ⚠️ 直接依赖
    ├── HealthSystem ⚠️ 直接依赖
    ├── RewardSystem ⚠️ 直接依赖
    ├── HUDRenderer ⚠️ 直接依赖
    ├── NotificationManager ⚠️ 直接依赖
    ├── SpawnController ⚠️ 直接依赖
    ├── RewardSelector ⚠️ 直接依赖
    ├── GameIntegrator ⚠️ 直接依赖
    ├── Player (Entity) ⚠️ 直接依赖
    ├── Enemy (Entity) ⚠️ 直接依赖
    ├── Boss (Entity) ⚠️ 直接依赖
    ├── Bullet (Entity) ⚠️ 直接依赖
    └── pygame ⚠️ 直接依赖
```

**依赖数量**: 14+ 个直接依赖 (过多)

### 3.3 Code Quality Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| 类方法数量 | 25+ | < 15 | ❌ |
| 类行数 | 530 | < 300 | ❌ |
| 最高嵌套层级 | 5 | ≤ 3 | ❌ |
| 属性访问器数量 | 23 | < 10 | ❌ |
| 魔法数字数量 | 10+ | 0 | ❌ |
| 直接依赖类数量 | 14 | < 8 | ⚠️ |

---

## Part 4: Recommendations

### 4.1 High Priority (立即处理)

1. **拆分碰撞检测系统**
   - 创建 `CollisionSystem` 类
   - 提取 `_check_collisions` 相关方法
   - 统一碰撞检测逻辑

2. **创建 GameLoopController**
   - 封装游戏主循环逻辑
   - 管理 update/render 流程
   - 协调各子系统更新

3. **减少属性委托**
   - 移除不必要的属性访问器
   - 使用组合替代委托
   - 提供更高层次的接口

### 4.2 Medium Priority (计划处理)

4. **提取常量定义**
   - 创建 `GameConstants` 类
   - 移除所有魔法数字
   - 集中管理可配置值

5. **重构嵌套方法**
   - 使用卫语句提前返回
   - 提取嵌套逻辑为独立方法
   - 使用策略模式处理复杂分支

### 4.3 Low Priority (长期改进)

6. **建立接口抽象层**
   - 为关键系统定义接口
   - 降低模块间耦合
   - 提高测试可替换性

### 4.4 Proposed Architecture

```
GameScene (场景管理 - 精简)
    │
    ├── GameLoopController (游戏循环)
    │       │
    │       ├── update()
    │       └── render()
    │
    ├── CollisionSystem (碰撞检测)
    │       │
    │       ├── check_player_bullets_vs_enemies()
    │       ├── check_enemy_bullets_vs_player()
    │       └── check_boss_collisions()
    │
    ├── GameStateProvider (状态提供)
    │       │
    │       └── 提供只读的游戏状态
    │
    └── 委托给外部系统:
            ├── GameController (游戏逻辑)
            ├── RewardSystem (奖励系统)
            ├── SpawnController (生成系统)
            └── GameIntegrator (母舰系统)
```

---

## Part 5: Constants Extraction

### Problem
Multiple magic numbers scattered throughout the code.

### Solution
Create a centralized constants class.

### File: `airwar/game/constants.py`

```python
"""游戏常量定义

集中管理所有游戏相关的常量值，避免魔法数字散落在代码各处。
遵循架构标准:
- 单一职责: 仅定义游戏常量
- 可扩展性: 使用dataclass支持继承扩展
- 可维护性: 集中管理，易于修改
"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class PlayerConstants:
    """玩家相关常量"""
    INITIAL_X_OFFSET: int = 25
    INITIAL_Y: int = -80
    FINAL_Y: int = -100
    SCREEN_BOTTOM_OFFSET: int = 100
    INVINCIBILITY_DURATION: int = 90
    MOTHERSHIP_Y_POSITION: int = 200
    DEFAULT_SCREEN_WIDTH: int = 800


@dataclass(frozen=True)
class DamageConstants:
    """伤害相关常量"""
    BOSS_COLLISION_DAMAGE: int = 30
    ENEMY_COLLISION_DAMAGE: int = 20
    DEFAULT_REGEN_RATE: int = 2
    REGEN_THRESHOLD: int = 60


@dataclass(frozen=True)
class AnimationConstants:
    """动画相关常量"""
    ENTRANCE_DURATION: int = 60
    RIPPLE_INITIAL_RADIUS: int = 15
    RIPPLE_INITIAL_ALPHA: int = 350
    NOTIFICATION_DECAY_RATE: int = 1


@dataclass(frozen=True)
class GameBalanceConstants:
    """游戏平衡相关常量"""
    MAX_CYCLES: int = 10
    BASE_THRESHOLDS: Tuple[int, ...] = (1000, 2500, 5000, 10000, 20000)
    CYCLE_MULTIPLIER: float = 1.5
    DIFFICULTY_MULTIPLIERS: Tuple[float, float, float] = (1.0, 1.5, 2.0)


@dataclass
class GameConstants:
    """游戏全局常量聚合类
    
    使用组合模式聚合各类常量，
    提供统一的访问入口。
    """
    PLAYER: PlayerConstants = field(default_factory=PlayerConstants)
    DAMAGE: DamageConstants = field(default_factory=DamageConstants)
    ANIMATION: AnimationConstants = field(default_factory=AnimationConstants)
    BALANCE: GameBalanceConstants = field(default_factory=GameBalanceConstants)
    
    @classmethod
    def get_difficulty_multiplier(cls, difficulty: str) -> float:
        """获取难度对应的分数倍率"""
        multipliers = {
            'easy': cls.BALANCE.DIFFICULTY_MULTIPLIERS[0],
            'medium': cls.BALANCE.DIFFICULTY_MULTIPLIERS[1],
            'hard': cls.BALANCE.DIFFICULTY_MULTIPLIERS[2],
        }
        return multipliers.get(difficulty, 1.0)
    
    @classmethod
    def get_next_threshold(cls, milestone_index: int, difficulty: str) -> float:
        """计算下一个里程碑阈值"""
        base_idx = milestone_index % len(cls.BALANCE.BASE_THRESHOLDS)
        cycle_bonus = milestone_index // len(cls.BALANCE.BASE_THRESHOLDS)
        base = cls.BALANCE.BASE_THRESHOLDS[base_idx]
        multiplier = cls.BALANCE.CYCLE_MULTIPLIER ** cycle_bonus
        difficulty_mult = cls.get_difficulty_multiplier(difficulty)
        return base * multiplier * difficulty_mult


# 全局常量实例
GAME_CONSTANTS = GameConstants()
```

### Usage in game_scene.py

```python
# Add to imports
from airwar.game.constants import GAME_CONSTANTS, PlayerConstants

# Replace Line 63-64
self.player.rect.y = PlayerConstants.INITIAL_Y
self.player.rect.x = screen_width // 2 - PlayerConstants.INITIAL_X_OFFSET

# Replace in _update_entrance (Line 69)
start_y = PlayerConstants.INITIAL_Y
target_y = screen_height - PlayerConstants.SCREEN_BOTTOM_OFFSET

# Replace in _update_boss collision (Line 145)
damage = self.reward_system.calculate_damage_taken(
    GAME_CONSTANTS.DAMAGE.BOSS_COLLISION_DAMAGE
)

# Replace in _update_entities collision (Line 150)
damage = self.reward_system.calculate_damage_taken(
    GAME_CONSTANTS.DAMAGE.ENEMY_COLLISION_DAMAGE
)

# Replace in restore_from_save (Line 200-201)
self.player.rect.y = PlayerConstants.MOTHERSHIP_Y_POSITION
self.player.rect.x = save_data.score // 2 % PlayerConstants.DEFAULT_SCREEN_WIDTH
```

---

## Part 6: Collision System Extraction

### Problem
Collision detection logic mixed in GameScene with deep nesting (5 levels).

### Solution
Extract into dedicated `CollisionSystem` class.

### File: `airwar/game/systems/collision_system.py`

```python
"""碰撞检测系统

统一管理游戏中的所有碰撞检测逻辑。
遵循架构标准:
- 单一职责: 仅负责碰撞检测
- 低耦合: 通过回调与外部系统通信
- 可测试: 纯函数逻辑，易于单元测试
"""

from typing import List, Callable, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from airwar.entities.player import Player
    from airwar.entities.enemy import Enemy
    from airwar.entities.boss import Boss
    from airwar.entities.bullet import Bullet, EnemyBullet
    from airwar.game.systems.reward_system import RewardSystem


@dataclass
class CollisionEvent:
    """碰撞事件数据"""
    type: str  # 'player_hit', 'enemy_killed', 'boss_hit'
    source: any
    target: any
    damage: int = 0
    score: int = 0


class CollisionSystem:
    """碰撞检测系统
    
    职责:
    - 检测玩家子弹与敌人的碰撞
    - 检测敌人子弹与玩家的碰撞  
    - 检测Boss相关碰撞
    - 通过回调通知碰撞结果
    """
    
    def __init__(self):
        self._events: List[CollisionEvent] = []
    
    @property
    def events(self) -> List[CollisionEvent]:
        """获取碰撞事件列表 (只读)"""
        return self._events.copy()
    
    def clear_events(self) -> None:
        """清除事件列表"""
        self._events.clear()
    
    def check_all_collisions(
        self,
        player: 'Player',
        enemies: List['Enemy'],
        boss: Optional['Boss'],
        enemy_bullets: List['EnemyBullet'],
        reward_system: 'RewardSystem',
        player_invincible: bool,
        score_multiplier: int,
        on_enemy_killed: Callable[[int], None],
        on_boss_killed: Callable[[int], None],
        on_boss_hit: Callable[[int], None],
        on_player_hit: Callable[[int, 'Player'], None],
        on_lifesteal: Callable[['Player', int], None],
    ) -> None:
        """执行所有碰撞检测
        
        统一的碰撞检测入口，协调各类碰撞检测逻辑。
        """
        self._events.clear()
        
        self._check_player_bullets_vs_enemies(
            player, enemies, reward_system, score_multiplier,
            on_enemy_killed, on_lifesteal
        )
        
        self._check_enemy_bullets_vs_player(
            player, enemy_bullets, reward_system, player_invincible,
            on_player_hit
        )
        
        if boss:
            self._check_boss_collisions(
                player, boss, reward_system, player_invincible,
                on_boss_killed, on_boss_hit, on_player_hit, on_lifesteal
            )
    
    def _check_player_bullets_vs_enemies(
        self,
        player: 'Player',
        enemies: List['Enemy'],
        reward_system: 'RewardSystem',
        score_multiplier: int,
        on_enemy_killed: Callable,
        on_lifesteal: Callable,
    ) -> None:
        """检测玩家子弹与敌人的碰撞"""
        for bullet in player.get_bullets():
            bullet.update()
            if not bullet.active:
                continue
            
            for enemy in enemies:
                if not (bullet.active and enemy.active):
                    continue
                
                if not bullet.get_rect().colliderect(enemy.get_hitbox()):
                    continue
                
                self._process_enemy_hit(
                    bullet, enemy, reward_system, score_multiplier,
                    on_enemy_killed, on_lifesteal
                )
    
    def _process_enemy_hit(
        self,
        bullet: 'Bullet',
        enemy: 'Enemy',
        reward_system: 'RewardSystem',
        score_multiplier: int,
        on_enemy_killed: Callable,
        on_lifesteal: Callable,
    ) -> None:
        """处理子弹命中敌人"""
        if reward_system.explosive_level > 0:
            damage = bullet.data.damage
            reward_system.do_explosive_damage(
                [], enemy.rect.centerx, enemy.rect.centery, damage
            )
        else:
            enemy.take_damage(bullet.data.damage)
        
        if reward_system.piercing_level <= 0:
            bullet.active = False
        
        if enemy.active:
            return
        
        score_gained = enemy.data.score * score_multiplier
        self._events.append(CollisionEvent(
            type='enemy_killed',
            source=bullet,
            target=enemy,
            score=score_gained
        ))
        on_enemy_killed(score_gained)
        on_lifesteal(enemy.data.score)
    
    def _check_enemy_bullets_vs_player(
        self,
        player: 'Player',
        enemy_bullets: List['EnemyBullet'],
        reward_system: 'RewardSystem',
        player_invincible: bool,
        on_player_hit: Callable,
    ) -> None:
        """检测敌人子弹与玩家的碰撞"""
        if player_invincible:
            for bullet in enemy_bullets:
                bullet.update()
            return
        
        player_hitbox = player.get_hitbox()
        
        for bullet in enemy_bullets:
            bullet.update()
            if not (bullet.active and bullet.rect.colliderect(player_hitbox)):
                continue
            
            damage = reward_system.calculate_damage_taken(bullet.data.damage)
            player.take_damage(damage)
            
            for eb in enemy_bullets[:]:
                eb.active = False
            enemy_bullets.clear()
            
            self._events.append(CollisionEvent(
                type='player_hit',
                source=bullet,
                target=player,
                damage=damage
            ))
            on_player_hit(damage, player)
            break
    
    def _check_boss_collisions(
        self,
        player: 'Player',
        boss: 'Boss',
        reward_system: 'RewardSystem',
        player_invincible: bool,
        on_boss_killed: Callable,
        on_boss_hit: Callable,
        on_player_hit: Callable,
        on_lifesteal: Callable,
    ) -> None:
        """检测Boss相关碰撞"""
        if boss.is_entering() or not boss.active:
            return
        
        player_pos = (player.rect.centerx, player.rect.centery)
        boss.update([], player_pos=player_pos)
        player_hitbox = player.get_hitbox()
        
        if boss.rect.colliderect(player_hitbox) and not player_invincible:
            damage = reward_system.calculate_damage_taken(30)
            player.take_damage(damage)
            
            for eb in player._bullets[:] if hasattr(player, '_bullets') else []:
                eb.active = False
            
            self._events.append(CollisionEvent(
                type='player_hit',
                source=boss,
                target=player,
                damage=damage
            ))
            on_player_hit(damage, player)
        
        for bullet in player.get_bullets():
            if not (bullet.active and bullet.get_rect().colliderect(boss.get_rect())):
                continue
            
            score_reward = boss.take_damage(bullet.data.damage)
            if score_reward > 0:
                self._events.append(CollisionEvent(
                    type='boss_hit',
                    source=bullet,
                    target=boss,
                    score=score_reward
                ))
                on_boss_hit(score_reward)
            
            if reward_system.piercing_level <= 0:
                bullet.active = False
            
            if not boss.active:
                self._events.append(CollisionEvent(
                    type='boss_killed',
                    source=player,
                    target=boss,
                    score=boss.data.score
                ))
                on_boss_killed(boss.data.score)
                on_lifesteal(player, boss.data.score)
```

### Update `game_scene.py`

```python
# Add import
from airwar.game.systems.collision_system import CollisionSystem

class GameScene(Scene):
    def __init__(self):
        # ... existing ...
        self.collision_system: CollisionSystem = None
    
    def enter(self, **kwargs) -> None:
        # ... existing ...
        self.collision_system = CollisionSystem()
    
    def _check_collisions(self) -> None:
        """碰撞检测 - 使用CollisionSystem"""
        self.collision_system.check_all_collisions(
            player=self.player,
            enemies=self.spawn_controller.enemies,
            boss=self.spawn_controller.boss,
            enemy_bullets=self.spawn_controller.enemy_bullets,
            reward_system=self.reward_system,
            player_invincible=self.game_controller.state.player_invincible,
            score_multiplier=self.game_controller.state.score_multiplier,
            on_enemy_killed=lambda s: self.game_controller.on_enemy_killed(s),
            on_boss_killed=lambda s: self.game_controller.on_boss_killed(s),
            on_boss_hit=lambda s: self._on_boss_hit_score(s),
            on_player_hit=lambda d, p: self.game_controller.on_player_hit(d, p),
            on_lifesteal=lambda p, s: self.reward_system.apply_lifesteal(p, s),
        )
    
    def _on_boss_hit_score(self, score: int) -> None:
        """Boss被击中加分"""
        self.game_controller.state.score += score
        self.game_controller.show_notification(f"+{score} BOSS SCORE!")
```

---

## Part 7: Reduce Property Overload

### Problem
23+ property accessors that just delegate to internal objects.

### Solution
Remove unnecessary properties and provide higher-level interfaces.

```python
# Before: 23+ property accessors
@property
def enemies(self) -> list:
    return self.spawn_controller.enemies if self.spawn_controller else []

@property
def score(self) -> int:
    return self.game_controller.state.score if self.game_controller else 0

# ... 等等

# After: 精简为必要的状态查询方法
class GameScene(Scene):
    """游戏场景
    
    职责:
    - 管理游戏主循环
    - 协调各游戏系统
    - 提供场景生命周期管理
    
    不直接暴露内部状态，通过接口方法提供访问。
    """
    
    # 移除所有属性委托，仅保留必要的方法
    # 使用组合替代属性委托
    
    def get_game_state(self) -> Optional['GameState']:
        """获取游戏状态 (只读视图)"""
        if self.game_controller:
            return self.game_controller.state
        return None
    
    def get_score(self) -> int:
        """获取当前分数"""
        if self.game_controller:
            return self.game_controller.state.score
        return 0
    
    def is_game_over(self) -> bool:
        """判断游戏是否结束"""
        return not self.player.active if self.player else True
    
    def pause_game(self) -> None:
        """暂停游戏"""
        if self.game_controller and not self.reward_selector.visible:
            self.game_controller.state.paused = True
    
    def resume_game(self) -> None:
        """继续游戏"""
        if self.game_controller:
            self.game_controller.state.paused = False
```

---

## Part 8: Fix Deep Nesting

### Problem
`_update_boss` method has 4 levels of nesting.

### Solution
Use early returns and extract helper methods.

```python
# Before (4 levels of nesting)
def _update_boss(self) -> None:
    boss = self.spawn_controller.boss
    if not boss:
        return
    player_pos = (self.player.rect.centerx, self.player.rect.centery)
    boss.update(self.spawn_controller.enemies, player_pos=player_pos)
    player_hitbox = self.player.get_hitbox()

    if not boss.is_entering() and boss.active:  # Level 2
        if boss.rect.colliderect(player_hitbox):  # Level 3
            if not self.game_controller.state.player_invincible:  # Level 4
                damage = self.reward_system.calculate_damage_taken(30)
                self.player.take_damage(damage)
                self._clear_enemy_bullets()
                self.game_controller.on_player_hit(damage, self.player)

    for bullet in self.player.get_bullets():
        if bullet.active and boss and boss.active and not boss.is_entering():  # Level 3
            if bullet.get_rect().colliderect(boss.get_rect()):  # Level 4
                # ... 业务逻辑

# After (Max 2 levels, using early returns)
def _update_boss(self) -> None:
    boss = self.spawn_controller.boss
    if not boss:
        return
    
    self._update_boss_movement(boss)
    self._check_boss_player_collision(boss)
    self._process_boss_damage(boss)
    self._handle_boss_escape(boss)

def _update_boss_movement(self, boss: 'Boss') -> None:
    """更新Boss移动"""
    player_pos = (self.player.rect.centerx, self.player.rect.centery)
    boss.update(self.spawn_controller.enemies, player_pos=player_pos)

def _check_boss_player_collision(self, boss: 'Boss') -> None:
    """检查Boss与玩家碰撞"""
    if boss.is_entering() or not boss.active:
        return
    
    if not boss.rect.colliderect(self.player.get_hitbox()):
        return
    
    if self.game_controller.state.player_invincible:
        return
    
    damage = self.reward_system.calculate_damage_taken(30)
    self.player.take_damage(damage)
    self._clear_enemy_bullets()
    self.game_controller.on_player_hit(damage, self.player)

def _process_boss_damage(self, boss: 'Boss') -> None:
    """处理对Boss造成的伤害"""
    if boss.is_entering() or not boss.active:
        return
    
    for bullet in self.player.get_bullets():
        if not self._is_valid_bullet_for_boss(bullet, boss):
            continue
        
        score_reward = boss.take_damage(bullet.data.damage)
        if score_reward > 0:
            self._on_boss_hit(score_reward)

def _is_valid_bullet_for_boss(self, bullet: 'Bullet', boss: 'Boss') -> bool:
    """检查子弹是否有效攻击Boss"""
    return (
        bullet.active and 
        boss.active and 
        not boss.is_entering() and
        bullet.get_rect().colliderect(boss.get_rect())
    )

def _on_boss_hit(self, score_reward: int) -> None:
    """Boss被击中处理"""
    self.game_controller.state.score += score_reward
    self.game_controller.show_notification(f"+{score_reward} BOSS SCORE!")
    
    if not self.spawn_controller.boss.active:
        self.game_controller.on_boss_killed(self.spawn_controller.boss.data.score)
        self.game_controller.cycle_count += 1
        self.reward_system.apply_lifesteal(self.player, self.spawn_controller.boss.data.score)

def _handle_boss_escape(self, boss: 'Boss') -> None:
    """处理Boss逃跑"""
    if boss and not boss.active and boss.is_escaped():
        self.game_controller.show_notification("BOSS ESCAPED! (+0)")
```

---

## Part 9: Migration Checklist

### Phase 1: Constants Extraction
- [ ] Create `airwar/game/constants.py`
- [ ] Define all dataclass constants
- [ ] Update imports in `game_scene.py`
- [ ] Replace all magic numbers

### Phase 2: Collision System
- [ ] Create `airwar/game/systems/collision_system.py`
- [ ] Implement `CollisionResult` dataclass
- [ ] Implement all collision check methods
- [ ] Update `GameScene.__init__` to create collision_system
- [ ] Update `GameScene._check_collisions` to delegate

### Phase 3: Deep Nesting Fix
- [ ] Refactor `_update_boss` into 6 helper methods
- [ ] Refactor `_check_player_bullets_vs_enemies` 
- [ ] Add early returns for all guard conditions

### Phase 4: Property Cleanup
- [ ] Identify essential properties only
- [ ] Remove unnecessary property delegations
- [ ] Replace with higher-level interface methods

### Phase 5: Testing
- [ ] Write unit tests for `CollisionSystem`
- [ ] Write unit tests for constants
- [ ] Run existing test suite
- [ ] Manual gameplay testing

---

## Part 10: Risk Assessment

| Refactoring | Risk Level | Mitigation |
|-------------|------------|------------|
| Constants Extraction | Low | Direct replacement, no logic change |
| Collision System | Medium | Keep old method as wrapper during transition |
| Deep Nesting Fix | Low | Equivalent logic, just restructured |
| Property Cleanup | Medium | Ensure backward compatibility for callers |

**Recommendation**: Perform refactoring in order, testing after each phase.

---

## Part 11: Verification Checklist

After each phase, verify:

- [ ] All tests pass: `python3 -m pytest airwar/tests/ -v`
- [ ] No new linting errors: Check with project linter
- [ ] Manual gameplay test
- [ ] Save/Load functionality still works
- [ ] Boss fight mechanics unchanged
- [ ] Score calculation correct
- [ ] Difficulty scaling works

---

## Part 12: Rollback Plan

If issues occur:

1. **Phase 1 (Constants)**: Simple revert, replace constants with inline values
2. **Phase 2 (CollisionSystem)**: Remove new class, restore old methods
3. **Phase 3**: Restore deleted methods from git
4. **Phase 4**: Restore properties from git

Always commit before starting each phase.

---

## Part 13: Next Steps

1. [ ] Review all documents
2. [ ] Create backup branch: `git checkout -b backup/game-scene-pre-refactor`
3. [ ] Start Phase 1: Constants Extraction
4. [ ] Test after each phase
5. [ ] Commit working code after each phase
6. [ ] Create PR when complete

---

**Review Conclusion**: `GameScene` 需要重大重构以满足架构标准。建议采用渐进式重构策略，逐步拆分职责，同时保持功能完整。
