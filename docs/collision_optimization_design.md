# CollisionController 性能优化设计文档

> **文档版本：** v2.0
> **更新日期：** 2026-04-21
> **审查状态：** 已通过代码审查

---

## 1. 当前实现分析

### 1.1 碰撞检测流程

```
GameLoopManager._update_core()
    └── CollisionController.check_all_collisions()
            ├── check_player_bullets_vs_enemies()     # O(子弹×敌人)
            ├── check_player_bullets_vs_boss()        # O(子弹×1)
            ├── check_enemy_bullets_vs_player()        # O(敌人子弹)
            └── check_player_vs_enemies()              # O(敌人)
```

### 1.2 当前性能瓶颈

**核心问题：O(n×m) 嵌套循环**

```python
# collision_controller.py:126-147
for bullet in player_bullets:           # n ≈ 50-100 玩家子弹
    for enemy in enemies:               # m ≈ 30-50 敌人
        if bullet.get_rect().colliderect(enemy.get_rect()):
            # ...
```

| 场景 | 玩家子弹 | 敌人 | 每帧检测次数 |
|------|---------|------|-------------|
| 正常 | 50 | 30 | 1,500 |
| 激烈 | 100 | 50 | 5,000 |
| Boss战 | 100 | 50 + 200敌人子弹 | 15,000+ |

### 1.3 游戏特点（适合优化的特性）

| 特性 | 说明 |
|------|------|
| 子弹单向移动 | 玩家子弹向上，敌人子弹向下，无需反向检测 |
| 敌人生成区域 | 敌人从屏幕上方生成，玩家在底部 |
| Boss固定位置 | Boss只在屏幕上半部分移动 |
| 实体数量可预估 | 正常场景 <100 个实体 |

### 1.4 现有代码架构（重要）

#### 1.4.1 Enemy 双重矩形系统

**⚠️ 设计注意点：** `Enemy` 类使用**两个独立的矩形**进行碰撞检测：

```python
# enemy.py:20-51
class Enemy(Entity):
    def __init__(self, x, y, data):
        # 碰撞框 - 用于碰撞检测
        collision_size = int(base_size * ENEMY_COLLISION_SCALE)
        self._collision_rect = pygame.Rect(...)

        # 渲染框 - 用于显示
        super().__init__(x, y, render_size, render_size)

    def get_hitbox(self) -> pygame.Rect:
        return self._collision_rect  # 使用碰撞框！
```

**关键点：**
- `get_hitbox()` 返回 `_collision_rect`（碰撞框）
- `get_rect()` 返回 `rect`（渲染框）
- 碰撞检测必须使用 `get_hitbox()` 而非 `get_rect()`

#### 1.4.2 Bullet 命中历史缓存（已存在）

**⚠️ 方案 D 修改：** `Bullet` 类**已有**命中历史功能，只需启用！

```python
# bullet.py:15, 38-42
class Bullet(Entity):
    def __init__(self, ...):
        self._hit_enemies: List[int] = []  # 已存在！

    def has_hit_enemy(self, enemy_id: int) -> bool:
        return enemy_id in self._hit_enemies

    def add_hit_enemy(self, enemy_id: int) -> None:
        self._hit_enemies.append(enemy_id)
```

#### 1.4.3 Shotgun 子弹水平速度分量

**⚠️ 方案 B 注意：** `Shotgun` 模式子弹有水平速度分量：

```python
# bullet.py:17-23
if data.angle_offset != 0:
    self.velocity = Vector2(
        data.speed * math.sin(angle_rad),   # vx != 0
        -data.speed * math.cos(angle_rad)   # vy != 0
    )
```

---

## 2. 优化方案

### 方案 A：空间分区网格（推荐）

#### 原理

将屏幕划分为固定大小的网格单元格，每个实体只与同格和相邻格的实体进行碰撞检测。

```
┌─────────┬─────────┬─────────┐
│  敌人   │ 敌人    │         │
│    ●    │   ●     │         │
├─────────┼─────────┼─────────┤
│ 玩家子弹│         │ 敌人    │
│    ↑    │         │   ●     │
│    ↑    │ 玩家子弹│         │
│    ↑    │    ↑    │         │
├─────────┼─────────┼─────────┤
│         │  玩家   │         │
│         │   ▲     │         │
└─────────┴─────────┴─────────┘
```

#### 实现设计

```python
class SpatialGrid:
    def __init__(self, cell_size: int = None):
        # 关联配置：使用 ENEMY_HITBOX_SIZE 作为网格大小基准
        from airwar.config import ENEMY_HITBOX_SIZE
        self.cell_size = cell_size or ENEMY_HITBOX_SIZE
        self._grid: Dict[Tuple[int, int], List[Entity]] = {}

    def clear(self):
        """每帧开始时清空"""
        self._grid.clear()

    def insert(self, entity: Entity) -> None:
        """将实体插入到对应的网格

        ⚠️ 注意：Enemy 类使用 _collision_rect 作为碰撞框
        """
        # 优先使用 get_hitbox()，兼容所有实体类型
        hitbox = getattr(entity, 'get_hitbox', lambda: entity.rect)()

        min_x = int(hitbox.x / self.cell_size)
        max_x = int((hitbox.x + hitbox.width) / self.cell_size)
        min_y = int(hitbox.y / self.cell_size)
        max_y = int((hitbox.y + hitbox.height) / self.cell_size)

        for gx in range(min_x, max_x + 1):
            for gy in range(min_y, max_y + 1):
                key = (gx, gy)
                if key not in self._grid:
                    self._grid[key] = []
                self._grid[key].append(entity)

    def get_nearby(self, entity: Entity) -> List[Entity]:
        """获取附近潜在的碰撞体"""
        hitbox = getattr(entity, 'get_hitbox', lambda: entity.rect)()

        min_x = int(hitbox.x / self.cell_size) - 1
        max_x = int((hitbox.x + hitbox.width) / self.cell_size) + 1
        min_y = int(hitbox.y / self.cell_size) - 1
        max_y = int((hitbox.y + hitbox.height) / self.cell_size) + 1

        nearby = []
        for gx in range(max(0, min_x), max_x + 1):
            for gy in range(max(0, min_y), max_y + 1):
                nearby.extend(self._grid.get((gx, gy), []))
        return nearby
```

#### 复杂度分析

| 场景 | 原复杂度 | 优化后复杂度 | 提升 |
|------|---------|-------------|------|
| 正常 | O(1500) | O(200-400) | 4-8x |
| 激烈 | O(5000) | O(500-800) | 6-10x |
| Boss战 | O(15000) | O(800-1500) | 10-20x |
| **最坏情况** | O(n×m) | O(n×k) 其中 k≤9 | 取决于聚集度 |

> ⚠️ **最坏情况注意：** 当敌人/子弹高度聚集时，网格效率会退化到 O(n×m)。建议同时配合方案 B 使用。

#### 优点
- 实现简单，易于理解和维护
- 对游戏逻辑无侵入性
- 性能提升显著且稳定
- 可配置网格大小适应不同场景

#### 缺点
- 需要每帧重建网格（额外内存分配）
- 密集聚集场景效果有限

#### 注意事项
- **网格大小：** 使用 `ENEMY_HITBOX_SIZE` 配置，接近敌人尺寸
- **碰撞框优先：** 必须使用 `get_hitbox()` 获取正确的碰撞矩形
- **跨格实体：** 自动插入所有经过的格子

---

### 方案 B：方向预过滤（修正版）

#### 原理

利用游戏几何特性（玩家在底部、敌人在顶部），过滤掉**几何上不可能碰撞**的实体对。

```python
def check_player_bullets_vs_enemies(self, bullets, enemies, ...):
    for bullet in bullets:
        if not bullet.active:
            continue

        # ⚠️ 修正：不再依赖 velocity.y 判断
        # 改为基于几何位置的快速排除

        for enemy in enemies:
            if not enemy.active:
                continue

            # ⚠️ 关键优化：玩家子弹在屏幕下方，敌人在上方
            # 只有当子弹 y 坐标 >= 敌人 y 坐标时才可能碰撞
            if bullet.rect.y > enemy.rect.y + enemy.rect.height:
                continue  # 子弹还在敌人下方，跳过

            # ⚠️ 同样地，只有敌人 y 坐标 <= 子弹 y 坐标时才可能碰撞
            if enemy.rect.y > bullet.rect.y + bullet.rect.height:
                continue  # 敌人还在子弹下方，跳过

            # 精确碰撞检测
            if bullet.get_rect().colliderect(enemy.get_hitbox()):
                # 处理碰撞
                ...
```

#### 适用范围

| 子弹类型 | 是否适用 | 说明 |
|---------|---------|------|
| 普通子弹 | ✅ 适用 | 垂直向上移动 |
| Shotgun | ✅ 适用 | 角度偏移但仍从底部向上 |
| Laser | ⚠️ 部分适用 | 仍需检测，但可配合空间分区 |

#### 优点
- 无需额外数据结构
- 实现简单，改动较小
- 对性能有明显提升

#### 缺点
- 不适用于双向移动场景（如有）
- 需要配合空间分区应对聚集场景

---

### 方案 C：批量矩形检测

#### 原理

将多个小矩形（子弹）合并为一个大矩形进行粗检测，只有命中时才逐个验证。

```
┌─────────────────────┐
│ ● ● ● ● ● ● ● ●   │  大矩形粗检测
│ ● ● ● ● ● ● ● ●   │
│ ● ● ● ● ● ● ● ●   │
└─────────────────────┘
        ↓
    命中！
        ↓
┌─────────────────────┐
│ ●   ●   ●   ●     │  逐个精确检测
│   ●   ●   ●   ●   │
│ ●   ●   ●   ●     │
└─────────────────────┘
```

#### 实现设计

```python
def batch_collision_check(bullets: List[Bullet], enemies: List[Enemy]):
    # 1. 计算所有子弹的外包围盒
    if not bullets:
        return

    # ⚠️ 优化：直接使用 entity.rect 避免 get_rect() 创建新对象
    active_bullets = [b for b in bullets if b.active]
    if not active_bullets:
        return

    min_x = min(b.rect.x for b in active_bullets)
    min_y = min(b.rect.y for b in active_bullets)
    max_x = max(b.rect.right for b in active_bullets)
    max_y = max(b.rect.bottom for b in active_bullets)

    # 2. 与敌人外包围盒快速检测
    for enemy in enemies:
        if not enemy.active:
            continue

        enemy_hitbox = enemy.get_hitbox()

        # 快速排除
        if max_y < enemy_hitbox.top or min_x > enemy_hitbox.right:
            continue
        if min_y > enemy_hitbox.bottom or max_x < enemy_hitbox.left:
            continue

        # 3. 命中后逐个精确检测
        for bullet in active_bullets:
            if bullet.get_rect().colliderect(enemy_hitbox):
                # 处理碰撞
                ...
```

#### 优点
- 大幅减少精确碰撞检测次数
- 对密集子弹场景效果极佳

#### 缺点
- 实现复杂度较高
- 需要额外内存跟踪子弹分组

---

### 方案 D：启用现有命中历史缓存（修正版）

#### 原理

`Bullet` 类**已有**命中历史功能，只需在碰撞检测中启用即可。

#### 现有代码确认

```python
# bullet.py:38-42 - 已存在！
def has_hit_enemy(self, enemy_id: int) -> bool:
    return enemy_id in self._hit_enemies

def add_hit_enemy(self, enemy_id: int) -> None:
    self._hit_enemies.append(enemy_id)
```

#### 启用方法

在 `check_player_bullets_vs_enemies()` 中启用：

```python
def check_player_bullets_vs_enemies(self, player_bullets, enemies, ...):
    for bullet in player_bullets:
        if not bullet.active:
            continue

        for enemy in enemies:
            if not enemy.active:
                continue

            # ⚠️ 启用命中历史缓存
            if bullet.has_hit_enemy(enemy.entity_id):
                continue  # 已经击打过这个敌人，跳过

            if bullet.get_rect().colliderect(enemy.get_hitbox()):
                damage = bullet.data.damage
                enemy.take_damage(damage)

                # ⚠️ 记录命中历史
                bullet.add_hit_enemy(enemy.entity_id)

                if not enemy.active:
                    ...
                bullet.active = False
                break
```

#### 优点
- 避免重复检测同一敌人
- 无需修改 Bullet 类
- 与其他方案完全兼容

#### 缺点
- 需要在每帧开始时清空 `_hit_enemies` 列表

#### 注意事项

```python
# 在 Bullet.update() 中添加清理
def update(self, *args, **kwargs) -> None:
    # ... 现有代码 ...

    # ⚠️ 屏幕外子弹清空命中历史
    if self.rect.y < -self.rect.height:
        self.active = False
        self._hit_enemies.clear()  # 新增
```

---

## 3. 爆炸伤害优化（新增）

### 当前问题

```python
# collision_controller.py:164-172
def _handle_explosive_damage(self, bullet, enemies, explosive_level):
    # ⚠️ 每次爆炸都遍历所有敌人，效率低
    for enemy in enemies:
        if enemy.active:
            # 计算距离...
```

### 优化方案

```python
def _handle_explosive_damage(self, bullet, enemies, explosive_level, killed_enemies: set = None):
    """爆炸伤害处理

    Args:
        bullet: 爆炸源子弹
        enemies: 所有敌人列表
        explosive_level: 爆炸天赋等级
        killed_enemies: 本帧已击杀的敌人集合（用于避免重复爆炸）
    """
    if explosive_level <= 0:
        return

    from airwar.config import EXPLOSION_RADIUS
    from airwar.game.constants import GAME_CONSTANTS

    bullet_x = bullet.rect.centerx
    bullet_y = bullet.rect.centery
    explosion_radius_sq = (EXPLOSION_RADIUS * explosive_level) ** 2
    explosion_damage = GAME_CONSTANTS.DAMAGE.EXPLOSIVE_DAMAGE * explosive_level

    killed_enemies = killed_enemies or set()

    for enemy in enemies:
        if not enemy.active:
            continue

        # ⚠️ 跳过本帧已被击杀的敌人
        if enemy.entity_id in killed_enemies:
            continue

        dx = bullet_x - enemy.rect.centerx
        dy = bullet_y - enemy.rect.centery
        distance_sq = dx * dx + dy * dy

        if distance_sq <= explosion_radius_sq:
            was_active = enemy.active
            enemy.take_damage(explosion_damage)

            # ⚠️ 记录本帧击杀的敌人
            if was_active and not enemy.active:
                killed_enemies.add(enemy.entity_id)
```

---

## 4. 推荐方案组合

### 轻量组合（改动最小）

| 方案 | 效果 | 改动量 | 优先级 |
|------|------|--------|--------|
| 启用命中历史缓存 | +15-25% | 极小 | 1 |
| 方向预过滤（修正版） | +20-40% | 小 | 2 |

### 性能组合（效果最佳）

| 方案 | 效果 | 改动量 | 优先级 |
|------|------|--------|--------|
| 启用命中历史缓存 | +15-25% | 极小 | 1 |
| 方向预过滤（修正版） | +20-40% | 小 | 2 |
| 空间分区网格 | +400-1000% | 中等 | 3 |
| 爆炸伤害优化 | +10-20% | 小 | 4 |

---

## 5. 实现优先级建议

```
┌─────────────────────────────────────────────────────────┐
│  第一优先级：启用命中历史缓存                             │
│  - 现有代码已支持，只需启用                             │
│  - 几乎不影响现有逻辑                                   │
├─────────────────────────────────────────────────────────┤
│  第二优先级：方向预过滤（修正版）                        │
│  - 修正依赖 velocity.y 的假设                          │
│  - 改为基于几何位置判断                                 │
├─────────────────────────────────────────────────────────┤
│  第三优先级：空间分区网格                               │
│  - 性能提升最显著                                       │
│  - 需要新建 SpatialGrid 类                             │
│  - 注意使用 get_hitbox() 而非 get_rect()               │
├─────────────────────────────────────────────────────────┤
│  第四优先级：爆炸伤害优化                               │
│  - 避免重复爆炸击杀同一敌人                             │
│  - 配合命中历史缓存使用                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 6. 测试验证

### 性能基准测试

| 指标 | 测量方法 |
|------|---------|
| FPS | `pygame.time.Clock.get_fps()` |
| 每帧碰撞检测次数 | 在检测循环中添加计数器 |
| 碰撞检测耗时 | `time.perf_counter()` 包裹检测函数 |

### 永久性性能监控（建议添加）

```python
class CollisionController:
    _total_checks: int = 0
    _total_collisions: int = 0

    def check_all_collisions(self, ...):
        CollisionController._total_checks += self._count_checks()
        CollisionController._total_collisions += self._count_collisions()
```

### 边界情况测试

- [ ] 屏幕无敌人时
- [ ] 屏幕满是敌人时
- [ ] Boss 战多弹幕场景
- [ ] 玩家靠近屏幕边缘
- [ ] Spread Shot 扩散弹道
- [ ] **Shotgun + Rapid Fire 同时激活** ← 新增
- [ ] **Laser 子弹的碰撞行为** ← 新增
- [ ] **Piercing 穿透多个敌人** ← 新增
- [ ] **Explosive 天赋触发时同一敌人不重复受伤** ← 新增

---

## 7. 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| 引入 bug | 中 | 完整保留原方法，新增优化方法并行运行做对比 |
| 内存增加 | 低 | 空间分区使用对象池复用 |
| 代码复杂度 | 中 | 添加详细注释和单元测试 |
| 双重矩形系统遗漏 | 高 | 必须使用 `get_hitbox()` 而非 `get_rect()` |
| 命中历史未清理 | 高 | 确保子弹离开屏幕时清空 `_hit_enemies` |

---

## 8. 配置关联

### 必须关联的配置

```python
# 空间分区网格大小应与敌人碰撞框关联
from airwar.config import ENEMY_HITBOX_SIZE, ENEMY_HITBOX_PADDING

class SpatialGrid:
    def __init__(self, cell_size: int = None):
        base_size = ENEMY_HITBOX_SIZE + ENEMY_HITBOX_PADDING * 2
        self.cell_size = cell_size or base_size
```

### 配置检查清单

- [ ] `ENEMY_HITBOX_SIZE` - 敌人碰撞框大小
- [ ] `ENEMY_COLLISION_SCALE` - 碰撞框缩放比例
- [ ] `EXPLOSION_RADIUS` - 爆炸范围
- [ ] `SCREEN_WIDTH` / `SCREEN_HEIGHT` - 屏幕尺寸

---

## 9. 决策确认

请确认以下选项：

1. **是否进行优化？** (是 / 否)
2. **选择哪个方案组合？**
   - 轻量组合（改动最小）
   - 性能组合（效果最佳）
3. **是否有其他约束？**
   - 必须保持向后兼容
   - 不修改现有数据结构
   - 其他：__________

---

## 附录 A：修改日志

| 版本 | 日期 | 修改内容 |
|------|------|---------|
| v2.0 | 2026-04-21 | 代码审查后修订：修正方案 D（启用现有缓存）、补充双重矩形说明、修正方案 B 逻辑、添加配置关联、优化爆炸伤害 |
| v1.0 | 2026-04-21 | 初始版本 |
