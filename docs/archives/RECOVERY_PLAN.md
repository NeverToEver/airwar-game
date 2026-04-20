# AIRWAR项目分阶段恢复计划

**计划制定日期**: 2026-04-20  
**基于**: 紧急代码审核报告  
**预计完成时间**: 12-17小时

---

## 执行摘要

### 问题总结
经过紧急代码审核，发现AIRWAR项目存在4个严重问题和4个主要问题，主要集中在：
1. **碰撞检测逻辑重复且不一致** - 伤害可能被计算多次或缺失
2. **子弹更新时机错误** - 导致碰撞检测不稳定
3. **回调函数签名不匹配** - 无敌状态失效
4. **GameOver界面触发异常** - 游戏结束流程断裂

### 修复策略
采用**渐进式修复**策略，分3个阶段执行：
1. **阶段1（紧急修复）**: 修复核心缺陷，2-3小时
2. **阶段2（优化重构）**: 提高代码质量，4-6小时
3. **阶段3（完善测试）**: 确保长期稳定，6-8小时

### 风险评估
- **修复风险**: 中等（通过完整测试缓解）
- **回归风险**: 低（增量修复，每步验证）
- **性能风险**: 低（有性能测试监控）

---

## 阶段1: 紧急修复（高优先级）

### 1.1 统一碰撞检测逻辑

**问题**: 碰撞检测逻辑分散在3个地方，导致伤害计算不一致

**修复步骤**:

#### 步骤1.1.1: 识别所有碰撞检测点
```bash
# 查看相关代码
grep -n "on_player_hit" airwar/game/controllers/collision_controller.py
grep -n "on_player_hit" airwar/scenes/game_scene.py
```

#### 步骤1.1.2: 统一CollisionController接口
```python
# 文件: collision_controller.py
# 修改: check_all_collisions()方法

def check_all_collisions(
    self,
    player: 'Player',
    enemies: List['Enemy'],
    boss: Optional['Boss'],
    enemy_bullets: List['EnemyBullet'],
    reward_system: any,
    player_invincible: bool,
    score_multiplier: int,
    on_enemy_killed: Callable[[int], None],
    on_boss_killed: Callable[[int], None],
    on_boss_hit: Callable[[int], None],
    on_player_hit: Callable[[int, 'Player'], None],  # 统一签名
    on_lifesteal: Callable,
) -> None:
    # 新增: 敌人碰撞检测
    for enemy in enemies:
        if enemy.active and player.get_hitbox().colliderect(enemy.get_hitbox()):
            if not player_invincible:
                if not reward_system.try_dodge():
                    damage = reward_system.calculate_damage_taken(20)  # 硬编码 -> 常量
                    on_player_hit(damage, player)
                    self._clear_enemy_bullets()
```

#### 步骤1.1.3: 删除GameScene中的重复逻辑
```python
# 文件: game_scene.py
# 删除以下方法和调用:
# - _check_boss_player_collision() (第280-293行)
# - _update_entities()中的碰撞检测 (第334-342行)

# 修改 _update_boss()
def _update_boss(self) -> None:
    boss = self.spawn_controller.boss
    if not boss:
        return
    
    self._update_boss_movement(boss)
    # 删除: _check_boss_player_collision(boss)
    # 新增: Boss子弹生成已由CollisionController处理
```

#### 步骤1.1.4: 更新GameScene调用
```python
# 文件: game_scene.py
# 修改 _check_collisions()

def _check_collisions(self) -> None:
    if not self.collision_controller:
        self.collision_controller = CollisionController()
    
    self.collision_controller.check_all_collisions(
        player=self.player,
        enemies=self.spawn_controller.enemies,
        boss=self.spawn_controller.boss,
        enemy_bullets=self.spawn_controller.enemy_bullets,
        reward_system=self.reward_system,
        player_invincible=self.game_controller.state.player_invincible,
        score_multiplier=self.game_controller.state.score_multiplier,
        on_enemy_killed=lambda score: self.game_controller.on_enemy_killed(score),
        on_boss_killed=lambda score: self.game_controller.on_boss_killed(score),
        on_boss_hit=lambda score: self._on_boss_hit(score),
        on_player_hit=lambda damage, player: self.game_controller.on_player_hit(damage, player),
        on_lifesteal=lambda player, score: self.reward_system.apply_lifesteal(player, score),
    )
```

**验收标准**:
- ✅ 碰撞检测只通过CollisionController
- ✅ 伤害计算正确（无敌状态生效）
- ✅ 单元测试通过

**预计时间**: 45分钟

---

### 1.2 修复子弹更新时机

**问题**: `bullet.update()`在碰撞检测前调用，导致碰撞结果不稳定

**修复步骤**:

#### 步骤1.2.1: 修改子弹更新顺序
```python
# 文件: game_scene.py
# 修改 _update_game()

def _update_game(self) -> None:
    has_regen = 'Regeneration' in self.reward_system.unlocked_buffs
    self.game_controller.update(self.player, has_regen)

    self.player.update()
    self.player.auto_fire()
    
    # 新增: 先更新所有子弹
    self._update_all_bullets()  # 玩家子弹 + 敌人子弹
    
    self._update_enemy_spawning()
    self._update_entities()  # 移除子弹更新
    self._check_collisions()  # 碰撞检测在子弹更新后
    self._check_milestones()

    self.spawn_controller.cleanup()
    self._cleanup_bullets()

def _update_all_bullets(self) -> None:
    """更新所有子弹（玩家子弹 + 敌人子弹）"""
    for bullet in self.player.get_bullets():
        bullet.update()
    for bullet in self.spawn_controller.enemy_bullets:
        bullet.update()
```

#### 步骤1.2.2: 修改CollisionController
```python
# 文件: collision_controller.py
# 修改 check_player_bullets_vs_enemies()

def check_player_bullets_vs_enemies(
    self,
    player_bullets: List['Bullet'],
    enemies: List['Enemy'],
    score_multiplier: int,
    explosive_level: int
) -> Tuple[int, int]:
    score_gained = 0
    enemies_killed = 0

    for bullet in player_bullets:
        # 删除: bullet.update()  # 不再在这里更新
        for enemy in enemies:
            if bullet.active and enemy.active:
                if bullet.get_rect().colliderect(enemy.get_rect()):
                    damage = bullet.data.damage
                    enemy.take_damage(damage)

                    if explosive_level > 0:
                        self._handle_explosive_damage(bullet, enemies, explosive_level)

                    if not enemy.active:
                        enemies_killed += 1
                        score_gained += enemy.data.score * score_multiplier

                    if bullet.data.owner == "player":
                        bullet.active = False
                    break

    return score_gained, enemies_killed
```

**验收标准**:
- ✅ 子弹不会穿透薄型敌人
- ✅ 穿透buff正确工作
- ✅ 碰撞检测结果稳定

**预计时间**: 30分钟

---

### 1.3 修复GameOver触发逻辑

**问题**: `player.active`立即变为False，导致游戏结束流程断裂

**修复步骤**:

#### 步骤1.3.1: 添加游戏状态管理
```python
# 文件: game_controller.py
# 添加新的状态枚举

from enum import Enum

class GameplayState(Enum):
    PLAYING = "playing"
    DYING = "dying"
    GAME_OVER = "game_over"

# 修改 GameState
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
    kill_count: int = 0
    boss_kill_count: int = 0
    # 新增
    gameplay_state: GameplayState = GameplayState.PLAYING
    death_timer: int = 0
    death_duration: int = 90  # 1.5秒死亡动画
```

#### 步骤1.3.2: 修改Player.take_damage()
```python
# 文件: player.py
# 修改 take_damage()

def take_damage(self, damage: int) -> None:
    if self.is_shielded:
        return
    self.health -= damage
    if self.health <= 0:
        self.health = 0  # 保持为0，不立即设置为inactive
        # 新增: 通知游戏控制器处理死亡
        if hasattr(self, '_on_death_callback'):
            self._on_death_callback()
```

#### 步骤1.3.3: 修改GameController处理死亡
```python
# 文件: game_controller.py
# 修改 on_player_hit()

def on_player_hit(self, damage: int, player) -> None:
    player.take_damage(damage)
    
    center_x = player.rect.centerx
    center_y = player.rect.centery
    self.state.ripple_effects.append({
        'x': center_x,
        'y': center_y,
        'radius': 15,
        'alpha': 350,
        'pulse': 0
    })
    
    # 检查是否死亡
    if player.health <= 0:
        self.state.gameplay_state = GameplayState.DYING
        self.state.death_timer = self.state.death_duration
    else:
        self.state.player_invincible = True
        self.state.invincibility_timer = 90

def update(self, player, has_regen: bool = False) -> None:
    self.health_system.update(player, has_regen)
    self.notification_manager.update()
    self.update_ripples()

    if self.state.notification_timer > 0:
        self.state.notification_timer -= 1

    # 新增: 处理死亡状态
    if self.state.gameplay_state == GameplayState.DYING:
        self.state.death_timer -= 1
        if self.state.death_timer <= 0:
            self.state.gameplay_state = GameplayState.GAME_OVER
            self.state.running = False
            player.active = False

    self._update_invincibility()
```

#### 步骤1.3.4: 修改GameScene.is_game_over()
```python
# 文件: game_scene.py
# 修改 is_game_over()

def is_game_over(self) -> bool:
    if not self.player:
        return True
    return self.game_controller.state.gameplay_state == GameplayState.GAME_OVER
```

**验收标准**:
- ✅ 游戏结束后正确显示GameOver界面
- ✅ 有死亡动画/延迟
- ✅ 分数和击杀数正确显示
- ✅ 按钮可点击

**预计时间**: 45分钟

---

### 1.4 验证紧急修复

**运行测试**:
```bash
# 运行所有测试
pytest airwar/tests/ -v --tb=short

# 运行碰撞相关测试
pytest airwar/tests/test_collision*.py -v

# 检查是否所有测试通过
```

**手动测试**:
1. 启动游戏
2. 受到一次伤害，检查无敌状态生效
3. 生命值归零，检查有死亡动画
4. 检查GameOver界面显示正确
5. 测试按钮可点击

**预计时间**: 30分钟

---

## 阶段2: 优化重构

### 2.1 清理未使用代码

**任务**: 删除以下方法和相关测试

```python
# CollisionController中未使用的方法:
- check_player_vs_enemies()  # 已被check_all_collisions替代
- _check_player_bullets_vs_enemies()  # 已被check_all_collisions替代
- _check_enemy_bullets_vs_player()  # 已被check_all_collisions替代

# GameScene中未使用的方法:
- _check_player_bullets_vs_enemies()
- _check_enemy_bullets_vs_player()
```

**预计时间**: 30分钟

---

### 2.2 统一配置管理

**任务**: 提取硬编码数值

```python
# 文件: airwar/game/constants.py
# 添加以下常量

class DamageConstants:
    ENEMY_COLLISION_DAMAGE = 20
    BOSS_COLLISION_DAMAGE = 30
    BOSS_BULLET_DAMAGE_BASE = 50
    
class InvincibilityConstants:
    INVINCIBILITY_DURATION = 90  # 帧数
    DEATH_DURATION = 90  # 帧数
    
class CollisionConstants:
    PLAYER_HITBOX_WIDTH = 12
    PLAYER_HITBOX_HEIGHT = 16
```

**预计时间**: 30分钟

---

### 2.3 改进错误处理

**任务**: 添加异常捕获和日志

```python
# 文件: game_scene.py
# 添加错误处理

def _update_game(self) -> None:
    try:
        has_regen = 'Regeneration' in self.reward_system.unlocked_buffs
        self.game_controller.update(self.player, has_regen)
        
        self.player.update()
        self.player.auto_fire()
        
        self._update_enemy_spawning()
        self._update_bullets()
        self._update_entities()
        self._check_collisions()
        self._check_milestones()
        
        self.spawn_controller.cleanup()
        self._cleanup_bullets()
        
        if not self.player.active:
            self.game_controller.state.running = False
            
    except Exception as e:
        import logging
        logging.error(f"Game update error: {e}", exc_info=True)
        self.game_controller.state.running = False
```

**预计时间**: 30分钟

---

## 阶段3: 完善测试

### 3.1 添加集成测试

```python
# 文件: airwar/tests/test_integration_collision.py

def test_full_collision_sequence():
    """测试完整的碰撞检测序列"""
    # 1. 创建游戏环境
    # 2. 生成敌人和子弹
    # 3. 执行多次碰撞检测
    # 4. 验证伤害累计正确
    
def test_invincibility_timing():
    """测试无敌状态时序"""
    # 1. 玩家受到伤害
    # 2. 检查无敌状态激活
    # 3. 再次受到伤害（应该无效）
    # 4. 无敌状态结束后再次受伤
    
def test_game_over_sequence():
    """测试游戏结束序列"""
    # 1. 玩家生命值归零
    # 2. 检查死亡动画播放
    # 3. 检查GameOver界面显示
    # 4. 检查按钮响应
```

**预计时间**: 2小时

---

### 3.2 添加性能测试

```python
# 文件: airwar/tests/test_performance.py

def test_collision_performance():
    """测试碰撞检测性能"""
    import time
    
    start = time.perf_counter()
    for _ in range(1000):
        collision_controller.check_all_collisions(...)
    elapsed = time.perf_counter() - start
    
    assert elapsed < 16.0, f"Collision check too slow: {elapsed}ms"
```

**预计时间**: 1小时

---

## 资源估算

### 时间估算

| 阶段 | 任务 | 预计时间 | 实际时间（待填） |
|------|------|---------|----------------|
| 阶段1 | 统一碰撞检测逻辑 | 45分钟 | ___ |
| 阶段1 | 修复子弹更新时机 | 30分钟 | ___ |
| 阶段1 | 修复GameOver逻辑 | 45分钟 | ___ |
| 阶段1 | 验证紧急修复 | 30分钟 | ___ |
| 阶段2 | 清理未使用代码 | 30分钟 | ___ |
| 阶段2 | 统一配置管理 | 30分钟 | ___ |
| 阶段2 | 改进错误处理 | 30分钟 | ___ |
| 阶段3 | 添加集成测试 | 2小时 | ___ |
| 阶段3 | 添加性能测试 | 1小时 | ___ |
| **总计** | | **12-17小时** | **___** |

### 人力资源

- **开发者**: 1人
- **测试人员**: 1人（可与开发者合并）
- **代码审查**: 1人（建议）

---

## 风险缓解

### 风险1: 修复引入新bug

**缓解措施**:
1. 增量修复，每步验证
2. 完整测试覆盖
3. 代码审查
4. 保留备份/分支

**应急计划**:
- 如果测试失败，立即回滚
- 使用`git revert`回退单个提交
- 在独立分支开发

### 风险2: 性能下降

**缓解措施**:
1. 性能测试
2. 监控FPS
3. 优化算法

**应急计划**:
- 分析性能瓶颈
- 优化或回退

### 风险3: 测试失败

**缓解措施**:
1. 理解测试失败原因
2. 修复代码而非测试
3. 如果测试有误，更新测试

---

## 成功标准

### 阶段1成功标准
- ✅ 所有碰撞检测通过CollisionController
- ✅ 伤害计算正确（无敌状态生效）
- ✅ GameOver界面正确显示
- ✅ 所有单元测试通过
- ✅ 手动测试通过

### 阶段2成功标准
- ✅ 无未使用的公共方法
- ✅ 所有硬编码数值提取为常量
- ✅ 错误处理完善
- ✅ 代码可读性提升

### 阶段3成功标准
- ✅ 集成测试覆盖核心功能
- ✅ 性能测试通过
- ✅ 测试覆盖率>90%
- ✅ 无回归问题

---

## 执行检查清单

### 阶段1检查清单
- [ ] 识别所有碰撞检测点
- [ ] 统一CollisionController接口
- [ ] 删除GameScene中的重复逻辑
- [ ] 修改子弹更新顺序
- [ ] 添加游戏状态管理
- [ ] 修改Player.take_damage()
- [ ] 修改GameController处理死亡
- [ ] 修改GameScene.is_game_over()
- [ ] 运行单元测试
- [ ] 执行手动测试
- [ ] 记录测试结果

### 阶段2检查清单
- [ ] 识别未使用代码
- [ ] 删除未使用方法
- [ ] 更新相关测试
- [ ] 提取硬编码常量
- [ ] 更新所有引用
- [ ] 添加错误处理
- [ ] 添加日志输出
- [ ] 代码审查

### 阶段3检查清单
- [ ] 编写集成测试
- [ ] 编写性能测试
- [ ] 运行所有测试
- [ ] 验证覆盖率
- [ ] 性能基准测试
- [ ] 文档更新

---

## 后续建议

### 短期（1-2周）
1. 完成所有修复
2. 建立代码审查流程
3. 完善CI/CD

### 中期（1个月）
1. 考虑架构重构
2. 优化性能
3. 增加功能测试

### 长期（3个月）
1. 技术债务清理
2. 文档完善
3. 社区建设

---

**计划状态**: 已制定，待执行  
**下次更新**: 修复开始前  
**更新记录**:
- 2026-04-20: 初始计划制定
