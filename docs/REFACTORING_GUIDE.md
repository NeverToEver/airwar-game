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

### 1.2 遗留目录清理

```
遗留: airwar/airwar/airwar/data/  (多余的嵌套层次)
迁移: airwar/airwar/airwar/data/users.json → airwar/data/
删除: airwar/airwar/airwar/ 空目录树
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

**禁止**：使用方法内导入来避免循环依赖

**允许**：可选依赖的延迟导入
```python
def render(self, surface):
    # 可选依赖，延迟导入
    from airwar.utils.sprites import get_enemy_sprite
    sprite = get_enemy_sprite(...)
```

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

# Standard library imports (alphabetical)
import abc
import enum
from typing import List, Optional

# Third-party imports (alphabetical)
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
| 语言 | 英文 |
| 内容 | 说明「为什么」，而非「是什么」 |
| 分组注释 | 允许（如 `# === Movement ===`） |
| 废弃注释 | 使用 `# TODO: ...` 或 `# FIXME: ...` |

**错误示例：**
```python
# Set health to zero
self.health = 0
```

**正确示例：**
```python
# Death triggered when health reaches zero
self.health = 0
```

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

### 7.1 遗留嵌套目录

```bash
# 移动
mv airwar/airwar/airwar/data/users.json airwar/data/

# 删除空目录
rm -rf airwar/airwar/airwar/
```

### 7.2 方法内局部导入（禁止模式）

```python
# 错误：在方法内导入（避免循环依赖）
def update(self):
    from airwar.config import get_screen_width
    ...

# 正确：移至模块顶部
from ..config import get_screen_width

def update(self):
    ...
```

### 7.3 Docstring 缺失

所有以下文件需要补全英文 docstring：
- `entities/base.py`
- `entities/player.py`
- `entities/enemy.py`
- `entities/bullet.py`
- `game/constants.py`
- `utils/mouse_interaction.py`
- `scenes/game_scene.py`
- `scenes/menu_scene.py`
- `scenes/scene.py`

---

## 8. 验证命令

```bash
# 1. 语法检查所有 Python 文件
python3 -m py_compile airwar/airwar/**/*.py

# 2. 验证导入链
python3 -c "from airwar.game import Game; from airwar.entities import Player, Enemy"

# 3. 运行所有测试
cd airwar && python3 -m pytest -x -v

# 4. 检查方法内局部导入（应为 0）
grep -rn "^\s\+from airwar\." airwar/airwar/ --include="*.py" \
  | grep -v "core_bindings" \
  | grep -v "from airwar.core_bindings"
```

---

*文档版本：1.0*
*更新日期：2026/04/25*
