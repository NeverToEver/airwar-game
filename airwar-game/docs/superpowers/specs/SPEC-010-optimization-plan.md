# Air War 项目优化执行计划

**日期**: 2026-04-16
**版本**: 1.0
**状态**: 待执行
**优先级**: P0 (最高)

---

## 一、问题评估总结

### 1.1 性能瓶颈 (Critical)

| 优先级 | 问题 | 影响文件 | 严重程度 |
|--------|------|----------|----------|
| P0 | 全屏渐变每帧重绘 | background_renderer.py:115 | 极高 |
| P0 | Surface 在渲染循环中创建 | 15+ 文件 | 高 |
| P1 | O(n²) 碰撞检测 | game_scene.py, collision_controller.py | 高 |
| P1 | 重复计算未缓存 | 5+ 文件 | 中 |

### 1.2 架构缺陷 (High)

| 优先级 | 问题 | 影响文件 | 严重程度 |
|--------|------|----------|----------|
| P0 | God Class: GameScene (500+行) | game_scene.py | 严重 |
| P0 | God Class: SceneDirector (250+行) | scene_director.py | 严重 |
| P1 | 重复代码: 渐变背景绘制 | 3个scene文件 | 高 |
| P1 | 魔法数字散落 | 14+ 处 | 中 |
| P2 | 函数过长 (>40行) | 10个函数 | 中 |

### 1.3 安全问题 (Medium)

| 优先级 | 问题 | 影响文件 | 严重程度 |
|--------|------|----------|----------|
| P1 | JSON反序列化无验证 | persistence_manager.py | 中 |
| P1 | 用户输入验证不足 | login_scene.py | 中 |
| P2 | 游戏存档可篡改 | game_scene.py | 中 |
| P2 | 弱密码哈希 | database.py | 低 |

---

## 二、优化目标

### 2.1 性能目标

| 指标 | 当前值 | 目标值 | 改善 |
|------|--------|--------|------|
| 背景渐变渲染 | 每帧重绘 | 缓存Surface | -70% CPU |
| Surface创建次数 | 100+/帧 | <20/帧 | -80% |
| 碰撞检测 | O(n*m) | 空间分区 | -50% |

### 2.2 架构目标

| 指标 | 当前值 | 目标值 | 改善 |
|------|--------|--------|------|
| GameScene行数 | 500+ | <200 | -60% |
| 重复代码块 | 6 | 0 | -100% |
| 魔法数字 | 14+ | 0 | -100% |

### 2.3 安全目标

| 指标 | 当前值 | 目标值 | 改善 |
|------|--------|--------|------|
| 输入验证覆盖 | 30% | 100% | +70% |
| 存档数据验证 | 无 | 严格验证 | +100% |

---

## 三、优化方案

### 方案 A: 背景渐变缓存优化 (P0)

**问题**: `background_renderer.py` 第115-122行每帧重绘全屏渐变

**修复代码**:
```python
# 修改 background_renderer.py

class BackgroundRenderer:
    def __init__(self, screen_width: int, screen_height: int):
        # ... 现有代码 ...
        self._gradient_cache: Optional[pygame.Surface] = None
        self._cache_valid: bool = False

    def _ensure_gradient_cached(self) -> None:
        if self._gradient_cache is None or not self._cache_valid:
            self._gradient_cache = pygame.Surface(
                (self.screen_width, self.screen_height)
            )
            for y in range(self.screen_height):
                ratio = y / self.screen_height
                r = int(5 + ratio * 10)
                g = int(5 + ratio * 8)
                b = int(20 + ratio * 30)
                pygame.draw.line(
                    self._gradient_cache, (r, g, b), (0, y), (self.screen_width, y)
                )
            self._cache_valid = True

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_gradient_cached()
        surface.blit(self._gradient_cache, (0, 0))
        # ... 其余代码 ...
```

**预期效果**: 渐变渲染从 ~2ms/帧 降至 ~0.1ms/帧

**风险评估**: 低 - 仅改变渲染缓存策略，不影响功能

---

### 方案 B: UI渐变背景缓存 (P1)

**问题**: 3个scene文件重复渐变绘制代码

**修复**: 创建 `airwar/ui/visual_helpers.py`

```python
# airwar/ui/visual_helpers.py

import pygame
from typing import Optional

class GradientCache:
    _cache: dict = {}

    @classmethod
    def get_gradient(cls, width: int, height: int, color1: tuple, color2: tuple) -> pygame.Surface:
        key = (width, height, color1, color2)
        if key not in cls._cache:
            surface = pygame.Surface((width, height))
            for y in range(height):
                ratio = y / height
                r = int(color1[0] + (color2[0] - color1[0]) * ratio)
                g = int(color1[1] + (color2[1] - color1[1]) * ratio)
                b = int(color1[2] + (color2[2] - color1[2]) * ratio)
                pygame.draw.line(surface, (r, g, b), (0, y), (width, y))
            cls._cache[key] = surface
        return cls._cache[key]
```

**风险评估**: 低 - 新增工具类，不修改现有逻辑

---

### 方案 C: 输入验证增强 (P1)

**问题**: `GameSaveData.from_dict()` 无数据验证

**修复**:
```python
# mother_ship_state.py

@classmethod
def from_dict(cls, data: Dict) -> 'GameSaveData':
    # 验证必需字段
    required_fields = ['score', 'kill_count', 'player_health']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # 类型验证和默认值
    def safe_int(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def safe_bool(value, default=False):
        return bool(value) if isinstance(value, bool) else default

    def safe_str(value, default=""):
        return str(value) if value else default

    def safe_list(value, default=None):
        return list(value) if isinstance(value, list) else (default or [])

    def safe_dict(value, default=None):
        return dict(value) if isinstance(value, dict) else (default or {})

    return cls(
        score=safe_int(data.get('score'), 0),
        cycle_count=safe_int(data.get('cycle_count'), 0),
        kill_count=safe_int(data.get('kill_count'), 0),
        unlocked_buffs=safe_list(data.get('unlocked_buffs'), []),
        buff_levels=safe_dict(data.get('buff_levels'), {}),
        player_health=safe_int(data.get('player_health'), 100),
        player_max_health=safe_int(data.get('player_max_health'), 100),
        difficulty=safe_str(data.get('difficulty'), 'medium'),
        timestamp=safe_float(data.get('timestamp'), 0.0),
        is_in_mothership=safe_bool(data.get('is_in_mothership'), False),
        username=safe_str(data.get('username'), ''),
    )
```

**风险评估**: 中 - 修改数据加载逻辑，可能影响旧存档兼容性
**缓解**: 提供向后兼容默认值

---

### 方案 D: Hitbox缓存 (P1)

**问题**: `Player.get_hitbox()` 每帧重复计算

**修复**:
```python
# player.py

class Player(Entity):
    def __init__(self, x: float, y: float, input_handler):
        # ... 现有代码 ...
        self._cached_hitbox: Optional[pygame.Rect] = None
        self._last_rect_state: tuple = None

    def update(self, dt: float) -> None:
        # ... 现有代码 ...

        # 更新后刷新 hitbox 缓存
        self._refresh_hitbox_cache()

    def _refresh_hitbox_cache(self) -> None:
        current_state = (self.rect.x, self.rect.y)
        if current_state != self._last_rect_state:
            hb_x = self.rect.x + (self.rect.width - self.hitbox_width) // 2
            hb_y = self.rect.y + (self.rect.height - self.hitbox_height) // 2
            self._cached_hitbox = pygame.Rect(hb_x, hb_y, self.hitbox_width, self.hitbox_height)
            self._last_rect_state = current_state

    def get_hitbox(self) -> pygame.Rect:
        if self._cached_hitbox is None:
            self._refresh_hitbox_cache()
        return self._cached_hitbox
```

**风险评估**: 低 - 仅添加缓存，不改变功能

---

### 方案 E: 提取UI渲染助手 (P1)

**问题**: 3个scene文件重复粒子和星星绘制代码

**修复**: 创建 `airwar/ui/particle_system.py`

```python
# airwar/ui/particle_system.py

import pygame
import random
from typing import List, Tuple, Optional

class Particle:
    def __init__(self, x: float, y: float, vx: float, vy: float, color: Tuple[int, int, int], life: int):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        alpha = int(255 * (self.life / self.max_life))
        glow = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.color, alpha), (3, 3), 3)
        surface.blit(glow, (int(self.x) - 3, int(self.y) - 3))

class ParticleSystem:
    def __init__(self):
        self.particles: List[Particle] = []

    def spawn(self, x: float, y: float, count: int, color: Tuple[int, int, int]) -> None:
        for _ in range(count):
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(0.5, 2.0)
            life = random.randint(30, 60)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                color, life
            ))

    def update(self) -> None:
        self.particles = [p for p in self.particles if p.update()]

    def draw(self, surface: pygame.Surface) -> None:
        for particle in self.particles:
            particle.draw(surface)
```

**风险评估**: 低 - 新增系统，不修改现有代码

---

## 四、执行计划

### 阶段1: 性能优化 (Day 1)

| 任务 | 负责人 | 工时 | 风险 |
|------|--------|------|------|
| A1: 背景渐变缓存 | AI | 1h | 低 |
| A2: Hitbox缓存 | AI | 1h | 低 |
| A3: 粒子系统提取 | AI | 2h | 低 |

### 阶段2: 安全加固 (Day 2)

| 任务 | 负责人 | 工时 | 风险 |
|------|--------|------|------|
| C1: 输入验证增强 | AI | 2h | 中 |
| C2: 存档数据验证 | AI | 1h | 中 |

### 阶段3: 架构优化 (Day 3)

| 任务 | 负责人 | 工时 | 风险 |
|------|--------|------|------|
| E1: UI渲染助手提取 | AI | 3h | 低 |
| E2: GameScene拆分准备 | AI | 4h | 高 |

---

## 五、风险评估矩阵

| 风险 | 概率 | 影响 | 等级 | 缓解措施 |
|------|------|------|------|----------|
| 缓存失效 | 低 | 中 | 🟡 | 添加缓存验证逻辑 |
| 存档兼容 | 中 | 高 | 🟠 | 提供默认值，向后兼容 |
| 性能回退 | 低 | 高 | 🟡 | 性能测试验证 |
| 功能回归 | 低 | 高 | 🟡 | 完整测试覆盖 |

---

## 六、验收标准

### 6.1 性能验收

```bash
# 渐变渲染性能测试
pytest airwar/tests/test_performance.py -v
# 目标: 渐变渲染 < 0.5ms/帧
```

### 6.2 功能验收

```bash
# 完整测试
pytest airwar/tests/ -q
# 目标: 155+ 测试全部通过
```

### 6.3 代码质量验收

| 检查项 | 目标 |
|--------|------|
| 函数最大行数 | ≤40行 |
| 重复代码块 | 0 |
| 魔法数字 | 0 |

---

## 七、监控指标

| 指标 | 优化前 | 优化后 | 监控方式 |
|------|--------|--------|----------|
| FPS | 60 | 60 | 游戏内显示 |
| 渐变渲染 | 2ms/帧 | 0.1ms/帧 | 性能分析 |
| Surface创建 | 100+/帧 | <20/帧 | 代码统计 |
| 测试通过率 | 100% | 100% | pytest |

---

**批准状态**: 待批准
**下一步**: 按阶段执行优化任务
