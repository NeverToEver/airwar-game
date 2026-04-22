# AIRWAR 架构重构工作计划

**创建日期：** 2026-04-22  
**项目：** AIRWAR 飞机大战游戏  
**目标：** 整理散落的目录结构，消除重复代码，统一代码组织

---

## 📋 目录

1. [问题概述](#问题概述)
2. [重构原则](#重构原则)
3. [第一阶段：配置目录统一](#第一阶段配置目录统一)
4. [第二阶段：UI 组件整合](#第二阶段ui-组件整合)
5. [第三阶段：删除重复 BackgroundRenderer](#第三阶段删除重复-backgroundrenderer)
6. [第四阶段：Controller/Manager 命名统一](#第四阶段controllermanager-命名统一)
7. [第五阶段：渲染层职责整理](#第五阶段渲染层职责整理)
8. [验证清单](#验证清单)
9. [回滚方案](#回滚方案)

---

## 问题概述

### 当前架构问题

| 问题 | 严重程度 | 影响 |
|------|----------|------|
| `config/` 和 `configs/` 并存 | 🔴 严重 | 配置分散，导入混乱 |
| UI 组件分散在 3 个位置 | 🔴 严重 | 难以维护，功能重复风险 |
| `BackgroundRenderer` 重复实现 | 🔴 严重 | 代码冗余，维护成本增加 |
| Controller vs Manager 职责不清 | 🟡 中等 | 代码组织混乱 |
| 渲染层职责重叠 | 🟡 中等 | 三处渲染逻辑，职责不清 |

### 当前目录结构

```
airwar/
├── config/          ← 配置文件
│   ├── settings.py
│   ├── game_config.py
│   └── difficulty_config.py
├── configs/         ← 教程配置（应合并到 config/）
│   └── tutorial/
│       └── tutorial_config.py
├── ui/              ← 游戏 UI 组件
│   ├── game_over_screen.py
│   ├── reward_selector.py
│   └── buff_stats_panel.py
├── scenes/ui/       ← 场景 UI 组件（应合并到 ui/）
│   ├── background.py
│   ├── particles.py
│   └── effects.py
├── game/
│   ├── rendering/   ← 渲染层
│   │   ├── game_renderer.py
│   │   └── background_renderer.py  ← ⚠️ 与 scenes/ui/background.py 重复
│   ├── systems/     ← 游戏系统
│   │   ├── hud_renderer.py
│   │   └── integrated_hud.py
│   ├── controllers/ ← Controller 命名（应统一为 Manager）
│   │   ├── game_controller.py
│   │   ├── spawn_controller.py
│   │   └── collision_controller.py
│   └── managers/    ← Manager
│       ├── bullet_manager.py
│       ├── boss_manager.py
│       └── ...
```

---

## 重构原则

### 外科手术式修改原则

1. **每次只修改一个阶段**，不要一次性修改太多
2. **每步完成后验证**，确保不影响现有功能
3. **保持功能不变**，只改变文件位置和导入路径
4. **保留历史记录**，使用 Git 提交记录每个阶段

### 命名规范

- 使用 **Manager** 统一替代 Controller
- UI 组件统一放在 `ui/` 目录
- 配置文件统一放在 `config/` 目录
- 渲染相关统一放在 `rendering/` 目录

---

## 第一阶段：配置目录统一

### 目标

将 `configs/tutorial/` 合并到 `config/`，统一配置管理。

### 目标结构

```
config/
├── __init__.py
├── settings.py
├── game_config.py
├── difficulty_config.py
└── tutorial/           ← 从 configs/tutorial/ 移动
    ├── __init__.py
    └── tutorial_config.py
```

### 操作步骤

#### 步骤 1.1：创建目标目录

```bash
mkdir -p airwar/config/tutorial
```

#### 步骤 1.2：移动教程配置文件

```bash
mv airwar/configs/tutorial/tutorial_config.py airwar/config/tutorial/
mv airwar/configs/tutorial/__init__.py airwar/config/tutorial/
```

#### 步骤 1.3：更新导入路径

编辑以下文件的导入语句：

**airwar/config/__init__.py**
```python
# 修改前
from airwar.configs.tutorial import TUTORIAL_COLORS, TUTORIAL_FONTS, TUTORIAL_STEPS

# 修改后
from airwar.config.tutorial import TUTORIAL_COLORS, TUTORIAL_FONTS, TUTORIAL_STEPS
```

**airwar/config/tutorial/__init__.py**
```python
# 确保包含正确的导出
from .tutorial_config import TUTORIAL_COLORS, TUTORIAL_FONTS, TUTORIAL_STEPS

__all__ = ['TUTORIAL_COLORS', 'TUTORIAL_FONTS', 'TUTORIAL_STEPS']
```

#### 步骤 1.4：搜索其他引用

```bash
grep -r "airwar.configs.tutorial" airwar/
```

将所有 `airwar.configs.tutorial` 替换为 `airwar.config.tutorial`

#### 步骤 1.5：删除空目录

```bash
rm -rf airwar/configs/
```

#### 步骤 1.6：验证

```bash
# 运行测试
python -m pytest airwar/tests/test_config.py -v

# 检查导入
python -c "from airwar.config import TUTORIAL_COLORS, TUTORIAL_FONTS, TUTORIAL_STEPS; print('OK')"
```

### 提交信息

```
refactor(config): 统一配置目录结构

- 将 configs/tutorial/ 合并到 config/tutorial/
- 更新所有相关导入路径
- 删除空的 configs/ 目录
```

---

## 第二阶段：UI 组件整合

### 目标

将分散在 3 个位置的 UI 组件统一到 `ui/` 目录。

### 目标结构

```
ui/
├── __init__.py
├── game_over/
│   ├── __init__.py
│   └── game_over_screen.py    ← 从 ui/ 移动
├── reward/
│   ├── __init__.py
│   └── reward_selector.py     ← 从 ui/ 移动
├── buff/
│   ├── __init__.py
│   └── buff_stats_panel.py     ← 从 ui/ 移动
├── effects/
│   ├── __init__.py
│   ├── background.py           ← 从 scenes/ui/ 移动
│   ├── particles.py            ← 从 scenes/ui/ 移动
│   └── effects.py              ← 从 scenes/ui/ 移动
├── give_up/
│   ├── __init__.py
│   └── give_up_ui.py           ← 从 game/give_up/ 移动
└── panels/                     ← 新增：游戏内面板
    ├── __init__.py
    └── difficulty_coefficient_panel.py  ← 从 systems/ 移动
```

### 操作步骤

#### 步骤 2.1：创建子目录

```bash
mkdir -p airwar/ui/game_over
mkdir -p airwar/ui/reward
mkdir -p airwar/ui/buff
mkdir -p airwar/ui/effects
mkdir -p airwar/ui/give_up
mkdir -p airwar/ui/panels
```

#### 步骤 2.2：移动文件

```bash
# 游戏结束屏幕
mv airwar/ui/game_over_screen.py airwar/ui/game_over/
mv airwar/ui/reward_selector.py airwar/ui/reward/
mv airwar/ui/buff_stats_panel.py airwar/ui/buff/

# 场景特效
mv airwar/scenes/ui/background.py airwar/ui/effects/
mv airwar/scenes/ui/particles.py airwar/ui/effects/
mv airwar/scenes/ui/effects.py airwar/ui/effects/

# 投降 UI
mv airwar/game/give_up/give_up_ui.py airwar/ui/give_up/

# 难度系数面板
mv airwar/game/systems/difficulty_coefficient_panel.py airwar/ui/panels/
```

#### 步骤 2.3：创建子模块 __init__.py

**airwar/ui/game_over/__init__.py**
```python
from .game_over_screen import GameOverScreen, ScreenAction

__all__ = ['GameOverScreen', 'ScreenAction']
```

**airwar/ui/reward/__init__.py**
```python
from .reward_selector import RewardSelector

__all__ = ['RewardSelector']
```

**airwar/ui/buff/__init__.py**
```python
from .buff_stats_panel import BuffStatsPanel

__all__ = ['BuffStatsPanel']
```

**airwar/ui/effects/__init__.py**
```python
from .background import BackgroundRenderer
from .particles import ParticleSystem
from .effects import EffectsRenderer

__all__ = ['BackgroundRenderer', 'ParticleSystem', 'EffectsRenderer']
```

**airwar/ui/give_up/__init__.py**
```python
from .give_up_ui import GiveUpUI

__all__ = ['GiveUpUI']
```

**airwar/ui/panels/__init__.py**
```python
from .difficulty_coefficient_panel import DifficultyCoefficientPanel

__all__ = ['DifficultyCoefficientPanel']
```

#### 步骤 2.4：更新导入路径

需要更新的文件列表：

| 原导入 | 新导入 |
|--------|--------|
| `from airwar.ui import GameOverScreen` | `from airwar.ui.game_over import GameOverScreen` |
| `from airwar.ui import RewardSelector` | `from airwar.ui.reward import RewardSelector` |
| `from airwar.ui.buff_stats_panel import ...` | `from airwar.ui.buff import ...` |
| `from airwar.scenes.ui import BackgroundRenderer` | `from airwar.ui.effects import BackgroundRenderer` |
| `from airwar.game.give_up.give_up_ui import ...` | `from airwar.ui.give_up import ...` |

#### 步骤 2.5：删除空目录

```bash
rm -rf airwar/scenes/ui/
rm -rf airwar/game/give_up/
```

#### 步骤 2.6：验证

```bash
# 搜索旧路径引用
grep -r "airwar.scenes.ui" airwar/
grep -r "airwar.game.give_up" airwar/

# 运行相关测试
python -m pytest airwar/tests/test_give_up.py -v
python -m pytest airwar/tests/test_death_scene.py -v
```

### 提交信息

```
refactor(ui): 统一 UI 组件到 ui/ 目录

- 创建 ui/game_over/, ui/reward/, ui/buff/, ui/effects/, ui/give_up/, ui/panels/
- 将分散的 UI 组件整合到对应子目录
- 更新所有导入路径
- 删除空的 scenes/ui/ 和 game/give_up/ 目录
```

---

## 第三阶段：区分 BackgroundRenderer 功能

### ⚠️ 重要修正

**原计划错误：直接删除 `game/rendering/background_renderer.py`**

经过代码审查，两个 `BackgroundRenderer` 实现有**显著不同的功能**：

| 特性 | `game/rendering/background_renderer.py` | `ui/effects/background.py` |
|------|----------------------------------------|---------------------------|
| 星星数量 | 80 颗（固定） | 使用配置值（STAR_COUNT） |
| 星云效果 | ✅ Nebula 类 | ❌ 无 |
| 发光效果 | ✅ 星星 glow | ❌ 无 |
| 粒子系统 | ✅ 有 | ❌ 无 |
| 使用 design_tokens | ❌ 无 | ✅ 有 |
| **适用场景** | 游戏主场景（需要丰富效果） | 菜单/暂停等场景（轻量） |

**结论**：两个实现服务于不同场景，不应删除。正确做法是**重命名以区分语义**。

### 目标

重命名两个 BackgroundRenderer 以明确各自职责：

| 原名称 | 新名称 | 职责 |
|--------|--------|------|
| `game/rendering/background_renderer.py` | `game_rendering_background.py` | 游戏主场景背景（丰富效果） |
| `ui/effects/background.py` | `menu_background.py` | 菜单/UI 场景背景（轻量） |

### 操作步骤

#### 步骤 3.1：重命名游戏场景背景渲染器

```bash
# 重命名文件
mv airwar/game/rendering/background_renderer.py airwar/game/rendering/game_rendering_background.py

# 更新类名
# 在文件中将 class BackgroundRenderer 改为 class GameSceneBackground
```

#### 步骤 3.2：重命名菜单背景渲染器

```bash
# 重命名文件
mv airwar/ui/effects/background.py airwar/ui/effects/menu_background.py

# 更新类名
# 在文件中将 class BackgroundRenderer 改为 class MenuBackground
```

#### 步骤 3.3：更新 game_rendering_background.py 的导入

编辑 `airwar/game/rendering/game_rendering_background.py`：

```python
# 文件顶部添加说明
"""
游戏主场景背景渲染器

提供丰富的星空效果，包含：
- 星云（Nebula）效果
- 星星发光效果
- 粒子系统
- 闪烁动画

用于游戏主场景，提供沉浸式游戏体验。
"""
```

#### 步骤 3.4：更新 game_renderer.py 的导入

编辑 `airwar/game/rendering/game_renderer.py`：

```python
# 修改前
from airwar.game.rendering.background_renderer import BackgroundRenderer

# 修改后
from airwar.game.rendering.game_rendering_background import GameSceneBackground
```

并更新类中的引用：
```python
# 修改前
self.background_renderer: BackgroundRenderer = None

# 修改后
self.background_renderer: GameSceneBackground = None
```

#### 步骤 3.5：更新 ui/effects/menu_background.py 的导出

编辑 `airwar/ui/effects/__init__.py`：

```python
# 修改前
from .background import BackgroundRenderer

# 修改后
from .menu_background import MenuBackground
```

并更新所有使用 `from airwar.ui.effects import BackgroundRenderer` 的文件：

```python
# 修改前
from airwar.ui.effects import BackgroundRenderer

# 修改后
from airwar.ui.effects import MenuBackground
```

#### 步骤 3.6：验证

```bash
# 检查是否还有未更新的引用
grep -r "background_renderer import BackgroundRenderer" airwar/game/rendering/
grep -r "ui.effects import BackgroundRenderer" airwar/scenes/

# 运行游戏相关测试
python3 -m pytest airwar/tests/test_rendering.py -v 2>/dev/null || echo "无专门渲染测试"
python3 -m pytest airwar/tests/ -k "scene" -v 2>&1 | head -50
```

### 提交信息

```
refactor(background): 重命名 BackgroundRenderer 以区分功能

- game/rendering/background_renderer.py → GameSceneBackground
- ui/effects/background.py → MenuBackground
- 两个实现服务不同场景，不应删除
```

---

## 第四阶段：Controller/Manager 命名统一

### 目标

将 `game/controllers/` 合并到 `game/managers/`，统一使用 Manager 命名。

### 目标结构

```
game/
├── managers/       ← 扩展此目录
│   ├── __init__.py
│   ├── bullet_manager.py
│   ├── boss_manager.py
│   ├── game_controller.py    ← 从 controllers/ 移动并重命名
│   ├── spawn_controller.py    ← 从 controllers/ 移动并重命名
│   ├── collision_controller.py ← 从 controllers/ 移动并重命名
│   └── ...
```

### 操作步骤

#### 步骤 4.1：移动文件

```bash
mv airwar/game/controllers/game_controller.py airwar/game/managers/game_manager.py
mv airwar/game/controllers/spawn_controller.py airwar/game/managers/spawn_manager.py
mv airwar/game/controllers/collision_controller.py airwar/game/managers/collision_manager.py
```

#### 步骤 4.2：重命名类（可选）

如果类名使用 Controller 后缀，建议重命名为 Manager：

```python
# game/managers/game_manager.py
# 修改前
class GameController:
# 修改后
class GameManager:
```

#### 步骤 4.3：更新导入路径

需要更新的文件：

| 原导入 | 新导入 |
|--------|--------|
| `from airwar.game.controllers import GameController` | `from airwar.game.managers import GameManager` |
| `from airwar.game.controllers import SpawnController` | `from airwar.game.managers import SpawnManager` |
| `from airwar.game.controllers import CollisionController` | `from airwar.game.managers import CollisionManager` |

#### 步骤 4.4：更新 managers/__init__.py

```python
# 添加新的导出
from .game_manager import GameManager
from .spawn_manager import SpawnManager
from .collision_manager import CollisionManager
```

#### 步骤 4.5：删除空目录

```bash
rm -rf airwar/game/controllers/
```

#### 步骤 4.6：验证

```bash
# 检查旧路径引用
grep -r "airwar.game.controllers" airwar/

# 运行测试
python -m pytest airwar/tests/test_collision_events.py -v
python -m pytest airwar/tests/test_collision_and_edge_cases.py -v
```

### 提交信息

```
refactor(managers): 统一 Manager 命名，删除 controllers/ 目录

- 将 controllers/ 下的文件移动到 managers/
- 重命名 Controller 类为 Manager
- 更新所有导入路径
```

---

## 第五阶段：渲染层职责整理

### 目标

整合渲染相关代码，明确职责边界。

### 目标结构

```
game/
├── rendering/
│   ├── __init__.py
│   ├── game_renderer.py       ← 主渲染器
│   ├── hud_renderer.py        ← 从 systems/ 移动
│   ├── integrated_hud.py      ← 从 systems/ 移动
│   └── difficulty_indicator.py
```

### 操作步骤

#### 步骤 5.1：移动文件

```bash
mv airwar/game/systems/hud_renderer.py airwar/game/rendering/
mv airwar/game/systems/integrated_hud.py airwar/game/rendering/
```

#### 步骤 5.2：更新渲染模块 __init__.py

**airwar/game/rendering/__init__.py**
```python
from .game_renderer import GameRenderer, GameEntities
from .hud_renderer import HUDRenderer, HUDLayout
from .integrated_hud import IntegratedHUD
from .difficulty_indicator import DifficultyIndicator

__all__ = [
    'GameRenderer', 'GameEntities',
    'HUDRenderer', 'HUDLayout',
    'IntegratedHUD',
    'DifficultyIndicator',
]
```

#### 步骤 5.3：更新导入路径

需要更新的文件：

| 原导入 | 新导入 |
|--------|--------|
| `from airwar.game.systems.hud_renderer import HUDRenderer` | `from airwar.game.rendering import HUDRenderer` |
| `from airwar.game.systems.integrated_hud import IntegratedHUD` | `from airwar.game.rendering import IntegratedHUD` |

#### 步骤 5.4：验证

```bash
# 检查旧路径引用
grep -r "game.systems.hud_renderer" airwar/
grep -r "game.systems.integrated_hud" airwar/

# 运行测试
python -m pytest airwar/tests/ -k "hud or render" -v
```

### 提交信息

```
refactor(rendering): 将渲染相关代码整合到 rendering/ 模块

- 将 hud_renderer.py 和 integrated_hud.py 从 systems/ 移动到 rendering/
- 统一渲染层职责
- 更新相关导入路径
```

---

## 验证清单

每个阶段完成后，执行以下验证：

### 基础验证

- [ ] `python -c "import airwar; print('Import OK')"`
- [ ] `python -m pytest airwar/tests/ -v --tb=short 2>&1 | tail -50`
- [ ] `python main.py --help 2>&1 || echo "无帮助信息（正常）"`

### 导入验证

对于每个阶段：

```bash
# 检查旧路径是否完全移除
grep -r "旧的模块路径" airwar/ || echo "✓ 无残留引用"

# 检查新路径是否可导入
python -c "from 新的模块路径 import *; print('✓ 导入成功')"
```

### 功能验证

- [ ] 启动游戏主界面
- [ ] 进入游戏场景
- [ ] 测试暂停功能
- [ ] 测试退出确认
- [ ] 测试死亡场景

---

## 回滚方案

### 如果出现问题

#### 方法 1：使用 Git 回滚

```bash
# 查看重构提交历史
git log --oneline -10

# 回滚到重构前
git revert <commit-hash>

# 或重置到重构前
git reset --hard <重构前的commit-hash>
```

#### 方法 2：手动恢复

每个阶段移动/修改文件时，使用以下模式记录：

```bash
# 记录操作
echo "移动: airwar/configs/tutorial/ -> airwar/config/tutorial/" >> rollback_log.txt

# 恢复操作
git mv airwar/config/tutorial/ airwar/configs/tutorial/
```

### 重构前的备份

```bash
# 创建备份分支
git branch backup-before-refactor

# 或创建标签
git tag refactor-start
```

---

## 重构完成后的目标结构

```
airwar/
├── __init__.py
├── config/                    ← 统一配置目录
│   ├── __init__.py
│   ├── settings.py
│   ├── game_config.py
│   ├── difficulty_config.py
│   ├── design_tokens.py
│   └── tutorial/
│       ├── __init__.py
│       └── tutorial_config.py
├── entities/                 ← 游戏实体
│   ├── __init__.py
│   ├── base.py
│   ├── player.py
│   ├── enemy.py
│   ├── bullet.py
│   └── interfaces.py
├── game/                     ← 游戏核心
│   ├── __init__.py
│   ├── constants.py
│   ├── game.py
│   ├── scene_director.py
│   ├── managers/             ← 统一的管理器
│   │   ├── __init__.py
│   │   ├── game_manager.py
│   │   ├── spawn_manager.py
│   │   ├── collision_manager.py
│   │   ├── bullet_manager.py
│   │   ├── boss_manager.py
│   │   ├── milestone_manager.py
│   │   ├── input_coordinator.py
│   │   ├── ui_manager.py
│   │   └── game_loop_manager.py
│   ├── rendering/            ← 统一渲染
│   │   ├── __init__.py
│   │   ├── game_renderer.py
│   │   ├── hud_renderer.py
│   │   ├── integrated_hud.py
│   │   └── difficulty_indicator.py
│   ├── systems/              ← 游戏系统
│   │   ├── __init__.py
│   │   ├── difficulty/
│   │   │   ├── __init__.py
│   │   │   ├── manager.py
│   │   │   └── strategies.py
│   │   ├── health_system.py
│   │   ├── reward_system.py
│   │   ├── movement_pattern_generator.py
│   │   └── notification_manager.py
│   ├── buffs/
│   ├── mother_ship/
│   ├── explosion_animation/
│   ├── death_animation/
│   └── spawners/
├── ui/                       ← 统一 UI 组件
│   ├── __init__.py
│   ├── game_over/
│   ├── reward/
│   ├── buff/
│   ├── effects/
│   ├── give_up/
│   └── panels/
├── scenes/                   ← 场景管理
│   ├── __init__.py
│   ├── scene.py
│   ├── game_scene.py
│   ├── menu_scene.py
│   ├── pause_scene.py
│   ├── death_scene.py
│   ├── login_scene.py
│   ├── exit_confirm_scene.py
│   └── tutorial_scene.py
├── input/                    ← 输入处理
├── utils/                    ← 工具函数
├── window/                   ← 窗口管理
├── components/               ← 可复用组件
│   └── tutorial/
└── tests/                    ← 测试
```

---

## 总结

按顺序执行以上 5 个阶段，可以将项目从散乱的架构整理为清晰统一的结构。

**预计影响：**
- 消除 1 个重复目录（configs/）
- 整合 3 个 UI 目录为 1 个
- 删除 1 个重复文件（BackgroundRenderer）
- 统一 1 组命名（Controller -> Manager）
- 整合 1 组分散代码（渲染层）

**建议执行顺序：** 阶段 1 → 阶段 2 → 阶段 3 → 阶段 4 → 阶段 5

每个阶段完成后记得运行测试验证，确保不影响现有功能。
