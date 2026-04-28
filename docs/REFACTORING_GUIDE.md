# Airwar 代码重构指南

**日期：** 2026/04/25
**目的：** 统一代码结构和风格，消除技术债务

---

## 1. 项目结构

### 1.1 目录规范

| 类型 | 规范 | 示例 |
|------|------|------|
| Python 包 | `snake_case/` | `airwar/entities/` |
| 测试目录 | `airwar/tests/` | `airwar/tests/test_entities.py` |
| Rust 扩展 | `snake_case/` | `airwar_core/`（项目根目录下） |
| 入口文件 | 项目根目录 | `main.py` |

### 1.2 遗留目录清理（已完成）

```
遗留: airwar/airwar/airwar/data/  (多余的嵌套层次)
迁移: airwar/airwar/airwar/data/users.json → airwar/data/
删除: airwar/airwar/airwar/ 空目录树
状态: ✅ 已完成（commit b0b155e）
```

---

## 2. 命名规范

### 2.1 文件名

| 类型 | 规范 | 示例 |
|------|------|------|
| Python 模块 | `snake_case.py` | `enemy_bullet_spawner.py` |
| 测试文件 | `test_<module>.py` | `test_entities.py` |
| 包目录 | `snake_case/` | `game/managers/` |

### 2.2 类名

| 类型 | 规范 | 示例 |
|------|------|------|
| 普通类 | `PascalCase` | `class Player:` |
| 数据类 | `PascalCase` | `@dataclass class EnemyData:` |
| Mixin | `PascalCase` + `Mixin` | `class MouseSelectableMixin:` |
| Enum | `PascalCase` | `class GameplayState(Enum):` |

### 2.3 函数和方法

| 类型 | 规范 | 示例 |
|------|------|------|
| 公开方法 | `snake_case` | `def fire(self):` |
| 私有方法 | `_snake_case` | `def _update_movement(self):` |
| 特殊方法 | `__snake_case__` | `def __init__(self):` |

### 2.4 变量名

| 类型 | 规范 | 示例 |
|------|------|------|
| 实例变量 | `snake_case` | `self.health = 100` |
| 私有实例变量 | `_snake_case` | `self._fire_cooldown = 0` |
| 类常量 | `UPPER_SNAKE_CASE` | `MAX_HEALTH = 100` |
| 模块级常量 | `UPPER_SNAKE_CASE` | `FPS = 60` |

---

## 3. 导入规范

### 3.1 导入风格优先级

| 优先级 | 场景 | 风格 | 示例 |
|--------|------|------|------|
| 1 | 同包同层 | 相对 | `from .base import Entity` |
| 2 | 同包不同层 | 相对 | `from ..config import settings` |
| 3 | 不同包（包括 airwar 子包） | 绝对 | `from airwar.config import SCREEN_WIDTH` |
| 4 | 标准库/第三方 | 绝对 | `import pygame` |

### 3.2 局部导入（方法内）

**原则**：模块顶部导入优先，方法内导入仅作为补充手段。

**允许的场景**：

```python
# 1. 打破循环依赖（本项目 manager 模块最常见）
def _lazy_load_controller(self):
    from airwar.game.managers.game_controller import GameController
    ...

# 2. 可选依赖，延迟导入（避免硬依赖）
def render(self, surface):
    from airwar.utils.sprites import get_enemy_sprite
    sprite = get_enemy_sprite(...)

# 3. 大型模块按需加载
def play_sound(self, path):
    import pygame.mixer
    pygame.mixer.Sound(path).play()
```

**避免**：在无上述正当理由时使用方法内导入——这通常是模块职责不清的信号。

### 3.3 循环依赖处理

当必须使用惰性加载时，添加解释性注释：

```python
# NOTE: Lazy import to avoid circular dependency between game and entities modules.
# game.game imports from entities which may indirectly import from game.
def __getattr__(name):
    ...
```

---

## 4. 代码组织

### 4.1 类内方法顺序（标准顺序）

```python
class MyClass:
    # 1. 特殊方法
    def __init__(self): ...
    def __repr__(self): ...

    # 2. 属性（@property）
    @property
    def health(self): ...

    # 3. 公开生命周期方法
    def enter(self): ...
    def exit(self): ...
    def update(self): ...
    def render(self): ...

    # 4. 公开行为方法（命令/查询）
    def fire(self): ...
    def take_damage(self): ...

    # 5. 私有生命周期方法
    def _init_movement(self): ...
    def _setup_weapons(self): ...

    # 6. 私有行为方法
    def _update_movement(self): ...
    def _render_hitbox(self): ...

    # 7. 辅助方法
    def _calculate_damage(self): ...
```

### 4.2 模块结构标准

```python
"""
Module docstring in English. Describes purpose and usage.
"""

# Standard library imports
import abc
import enum
from typing import List, Optional

# Third-party imports
import pygame

# Local imports - relative preferred
from .base import Entity, Vector2
from ..config import settings

# Constants (UPPER_SNAKE_CASE)
MAX_BUFFER_SIZE = 1024

# Classes (PascalCase)
class MyClass:
    """Class docstring in English."""
    ...
```

---

## 5. 文档规范

### 5.1 Docstrings（必需）

| 元素 | 要求 |
|------|------|
| 所有公开类 | 必须有 docstring |
| 所有公开方法 | 必须有 docstring |
| 语言 | 英文 |
| 格式 | Google 风格 |

**Google 风格示例：**
```python
class Player(Entity):
    """Player entity representing the user's spaceship.

    The Player class handles movement, weapon firing, health and shield
    systems. It responds to input from the InputHandler and delegates
    bullet rendering to UIManager.

    Attributes:
        health: Current health points (0 to max_health).
        max_health: Maximum health points.
        speed: Movement speed in pixels per frame.
    """

    def fire(self) -> List['Bullet']:
        """Fire a bullet from the player's current weapon.

        Creates bullets based on the current shot mode and applies
        fire rate cooldown. Bullets are delegated to UIManager for
        rendering.

        Returns:
            List of Bullet entities created.
        """
        ...
```

### 5.2 注释

| 要求 | 说明 |
|------|------|
| 语言 | 推荐英文（团队可自行决定） |
| 内容 | 说明「为什么」，而非「是什么」 |
| 分组注释 | 允许（如 `# === Movement ===`） |
| 标记注释 | 常用 `# TODO:`、`# FIXME:`、`# DEPRECATED:` 等 |

---

## 6. 导入顺序模板

每个 Python 文件顶部应有清晰的导入分组：

```python
"""
Module name and brief description.
"""

# === Standard library ===
import abc
import enum
from typing import List, Optional, Dict

# === Third-party ===
import pygame

# === Local: same package ===
from .base import Entity, Vector2
from .bullet import Bullet, BulletData

# === Local: different package in airwar ===
from ..config import get_screen_width, get_screen_height
from ..game.constants import GAME_CONSTANTS

# === Constants ===
MAX_SIZE = 100
DEFAULT_SPEED = 5.0
```

---

## 7. 已识别的问题与修复

### 7.1 方法内局部导入（识别与处理）

当前代码库中存在约 22 处方法内局部导入（`boss_manager.py`、`milestone_manager.py`、`collision_controller.py` 等），绝大部分用于打破 manager 模块之间的循环依赖。

**已识别的情况：**

```python
# 合法：打破循环依赖（boss_manager → game_controller）
def _setup_boss_spawn(self):
    from airwar.game.managers.game_controller import GameController
    ...

# 合法：惰性加载避免类型导入时的循环
def _on_collision(self):
    from airwar.entities.player import Player
    ...

# 需优化：可以移到模块顶部
def update(self):
    from airwar.config import get_screen_width  # config 不会导致循环依赖
    ...
```

**处理策略：**
1. 如果导入不涉及循环依赖 → 移到模块顶部
2. 如果导入用于打破循环依赖 → 保留，加 `# NOTE: Lazy import to avoid circular dependency` 注释
3. 如果多个方法导入同一个模块 → 考虑重构模块边界，从根本上消除循环

### 7.2 Docstring 缺失

**已完成**（已添加模块级 docstring）：
- `entities/base.py`
- `entities/player.py`
- `entities/bullet.py`
- `game/constants.py`

**仍需补全**（缺少模块级 docstring 和/或公开 API docstring）：
- `entities/enemy.py` — 缺少模块级 docstring；`Enemy` 和 `Boss` 类及其公开方法需补全
- `utils/mouse_interaction.py` — 缺少模块级 docstring；Mixin 类需补全
- `scenes/game_scene.py` — 缺少模块级 docstring；`GameScene` 关键方法需补全
- `scenes/menu_scene.py` — 缺少模块级 docstring
- `scenes/scene.py` — 缺少模块级 docstring；`Scene`、`SceneManager` 类已部分补全

---

## 8. 验证命令

```bash
# 1. 语法检查所有 Python 文件
find airwar -name "*.py" -exec python3 -m py_compile {} +

# 2. 验证导入链
python3 -c "from airwar.game import Game; from airwar.entities import Player, Enemy"

# 3. 运行所有测试
python3 -m pytest -x -v

# 4. 检查方法内局部导入（排查是否有不需要的惰性导入）
grep -rn "^\s\+from airwar\." airwar/ --include="*.py" \
  | grep -v "core_bindings" \
  | grep -v "from airwar.core_bindings" \
  | grep -v "__init__\.py" \
  | grep -v "/tests/"
```

---

*文档版本：1.1*
*更新日期：2026/04/26*
