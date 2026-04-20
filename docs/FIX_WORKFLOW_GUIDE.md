# AIRWAR项目修复工作指导文档

## 文档信息

- **文档版本**: 1.0
- **创建日期**: 2025-01-XX
- **最后更新**: 2025-01-XX
- **文档状态**: 有效
- **适用范围**: AIRWAR游戏项目所有代码修复工作

---

## 第一章：引言与目的

### 1.1 文档目的

本文档旨在为AIRWAR游戏项目建立一套标准化、规范化、可追溯的代码修复工作流程。所有开发人员在进行代码修复工作时，必须严格遵循本文档规定的流程、步骤和技术规范，确保修复工作的质量、效率和可维护性。

### 1.2 适用范围

本文档适用于以下场景：

- **缺陷修复**: 发现并修复游戏中的bug或错误行为
- **功能增强**: 在现有功能基础上进行优化和改进
- **性能优化**: 改善游戏性能，提升用户体验
- **代码重构**: 优化代码结构，提高可维护性
- **安全修复**: 修复安全漏洞或潜在风险

### 1.3 核心原则

修复工作应遵循以下核心原则：

1. **最小改动原则**: 只修复必要的部分，避免引入新的问题
2. **可逆性原则**: 所有改动必须可回滚，确保问题时可快速恢复
3. **测试优先原则**: 先编写测试用例，再进行代码修复
4. **文档同步原则**: 代码改动必须同步更新相关文档
5. **渐进式验证原则**: 分阶段验证，每步完成后立即测试

---

## 第二章：修复工作流程总览

### 2.1 工作流程阶段

修复工作分为以下五个主要阶段：

```
阶段1: 问题分析 ←──────────────┐
    ↓                            │
阶段2: 方案设计 ←──────────┐     │
    ↓                      │     │
阶段3: 代码实现 ←──────┐   │     │
    ↓                  │   │     │
阶段4: 测试验证 ←──┐   │   │     │
    ↓              │   │   │     │
阶段5: 文档提交 ──┴───┴───┴─────┘
```

### 2.2 详细流程图

```
开始修复
    ↓
┌─────────────────────────────┐
│ 阶段1: 问题分析              │
│ • 复现问题                   │
│ • 定位相关代码               │
│ • 分析问题根因               │
│ • 评估影响范围               │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────┐
│ 阶段2: 方案设计              │
│ • 设计修复方案               │
│ • 编写技术文档               │
│ • 制定测试计划               │
│ • 风险评估                   │
│ • 评审与批准                 │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────┐
│ 阶段3: 代码实现              │
│ • 创建备份                   │
│ • 实施修复                   │
│ • 遵循编码规范               │
│ • 同步更新文档               │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────┐
│ 阶段4: 测试验证              │
│ • 单元测试                   │
│ • 集成测试                   │
│ • 回归测试                   │
│ • 性能测试                   │
│ • 用户场景测试               │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────┐
│ 阶段5: 文档提交              │
│ • 提交代码                   │
│ • 更新相关文档               │
│ • 记录变更日志               │
│ • 通知相关人员               │
└─────────────┬───────────────┘
              ↓
           修复完成
```

---

## 第三章：阶段一 - 问题分析

### 3.1 问题复现

#### 3.1.1 复现步骤

1. **环境准备**: 确保测试环境与生产环境一致
2. **操作步骤**: 按照用户报告的步骤执行操作
3. **结果记录**: 记录实际发生的错误或异常行为
4. **频率确认**: 确认问题是否可稳定复现

#### 3.1.2 复现记录模板

```markdown
## 问题复现记录

**问题编号**: [自动生成或指定]
**复现日期**: YYYY-MM-DD
**复现人员**: [姓名]
**复现环境**: [操作系统、Python版本等]

### 操作步骤
1. [步骤1]
2. [步骤2]
3. [步骤3]

### 预期行为
[描述期望的正确行为]

### 实际行为
[描述实际发生的错误行为]

### 复现频率
- [ ] 100%复现
- [ ] 经常复现（>50%）
- [ ] 偶尔复现（<50%）
- [ ] 无法复现

### 附加信息
[截图、日志等]
```

### 3.2 代码定位

#### 3.2.1 定位方法

1. **关键词搜索**: 使用Grep工具搜索相关关键词
2. **文件追踪**: 从入口点逐步追踪代码执行流程
3. **日志分析**: 通过日志确定问题发生的位置
4. **断点调试**: 使用IDE调试器定位问题代码

#### 3.2.2 定位记录

```markdown
### 相关代码文件
- `airwar/scenes/pause_scene.py` (行号:L50-60)
- `airwar/game/scene_director.py` (行号:L157-173)
- `airwar/game/mother_ship/game_integrator.py` (行号:L92-98)

### 问题代码片段
```python
# L88-89 in pause_scene.py
elif self.selected_index == 2:
    self.result = PauseAction.QUIT
```

### 调用链路
```
用户按ESC键
    ↓
GameScene.pause()
    ↓
SceneDirector._show_pause_menu()
    ↓
PauseScene.handle_events()
    ↓
PauseScene._select_option()
    ↓
返回 PauseAction.QUIT
```
```

### 3.3 根因分析

#### 3.3.1 分析维度

1. **代码层面**: 语法错误、逻辑错误、边界条件处理
2. **架构层面**: 模块耦合、设计缺陷、接口不匹配
3. **数据层面**: 数据格式错误、类型不匹配、数据不一致
4. **环境层面**: 配置错误、依赖问题、版本兼容性

#### 3.3.2 根因分析模板

```markdown
### 问题描述
[简要描述问题]

### 根本原因
[深入分析问题的根本原因]

### 影响分析
**影响范围**:
- [影响的功能点1]
- [影响的功能点2]

**影响程度**:
- [ ] 严重（导致游戏无法运行）
- [ ] 较高（严重影响用户体验）
- [ ] 中等（影响部分功能）
- [ ] 较低（影响较小）

### 相关模块
- `airwar/scenes/` - 场景管理
- `airwar/game/` - 游戏逻辑
```

---

## 第四章：阶段二 - 方案设计

### 4.1 修复方案设计

#### 4.1.1 方案要求

1. **完整性**: 修复方案必须覆盖所有问题场景
2. **最小化**: 只修改必要的代码，避免过度改动
3. **可测试**: 修复方案必须可以通过测试验证
4. **兼容性**: 考虑向后兼容性，避免破坏现有功能

#### 4.1.2 方案设计模板

```markdown
## 修复方案

### 方案概述
[简要描述修复方案的核心思路]

### 详细设计

#### 改动1: [改动名称]
**文件**: `airwar/scenes/scene.py`
**位置**: L7-10
**改动类型**: [新增/修改/删除]

**改动前**:
```python
class PauseAction(Enum):
    RESUME = "resume"
    MAIN_MENU = "main_menu"
    QUIT = "quit"
```

**改动后**:
```python
class PauseAction(Enum):
    RESUME = "resume"
    MAIN_MENU = "main_menu"
    SAVE_AND_QUIT = "save_and_quit"      # 新增
    QUIT_WITHOUT_SAVING = "quit_without_saving"  # 新增
    QUIT = "quit"  # 保留但标记为deprecated
```

**改动原因**: [解释为什么需要这个改动]

#### 改动2: [改动名称]
[同上格式]

### 备选方案
**方案B**: [描述备选方案]
**优劣对比**: [对比分析]
**选择理由**: [为什么选择当前方案]
```

### 4.2 测试计划

#### 4.2.1 测试用例设计

```markdown
## 测试计划

### 测试用例

#### 用例1: 验证暂停菜单显示正确选项
- **用例ID**: TC001
- **前置条件**: 游戏运行中
- **操作步骤**: 按ESC键打开暂停菜单
- **预期结果**: 显示4个选项：RESUME, MAIN MENU, SAVE AND QUIT, QUIT WITHOUT SAVING
- **优先级**: 高

#### 用例2: 验证保存并退出功能
- **用例ID**: TC002
- **前置条件**: 游戏运行中，已进入过母舰
- **操作步骤**: 
  1. 按ESC键打开暂停菜单
  2. 选择"SAVE AND QUIT"
  3. 重新启动游戏
- **预期结果**: 
  - 第一次退出时保存了游戏进度
  - 重新进入后恢复到退出前的状态
- **优先级**: 高

#### 用例3: 验证不保存并退出功能
- **用例ID**: TC003
- **前置条件**: 游戏运行中，有存档存在
- **操作步骤**:
  1. 进入母舰，确保有存档
  2. 退出母舰，开始游戏
  3. 按ESC键打开暂停菜单
  4. 选择"QUIT WITHOUT SAVING"
  5. 重新启动游戏
- **预期结果**: 
  - 退出时清除了存档
  - 重新进入后从头开始，无之前进度
- **优先级**: 高

#### 用例4: 验证窗口关闭行为
- **用例ID**: TC004
- **前置条件**: 游戏运行中
- **操作步骤**: 点击窗口关闭按钮（X）
- **预期结果**: 自动保存当前进度并退出
- **优先级**: 中

### 测试环境要求
- 操作系统: Windows/MacOS
- Python版本: 3.8+
- Pygame版本: 2.0+
- 显示器分辨率: 1920x1080

### 测试数据准备
- 测试用户账户: test_user_001
- 测试存档文件: user_docking_save.json
```

### 4.3 风险评估

```markdown
## 风险评估

### 风险识别

| 风险ID | 风险描述 | 发生概率 | 影响程度 | 风险等级 | 应对措施 |
|--------|----------|----------|----------|----------|----------|
| R1 | 修改枚举类型导致其他模块不兼容 | 中 | 高 | 高 | 在修改前检查所有枚举使用点 |
| R2 | 存档格式变化导致旧存档无法加载 | 低 | 高 | 中 | 保留旧存档格式兼容逻辑 |
| R3 | 新增选项影响现有UI布局 | 中 | 低 | 低 | 测试不同分辨率下的显示效果 |

### 风险应对策略

**R1应对策略**:
- 在修改枚举前，使用SearchCodebase工具全面搜索所有使用点
- 确保PauseAction枚举的所有使用点都已更新
- 保留向后兼容的处理逻辑

**R2应对策略**:
- GameSaveData类添加版本字段
- 加载存档时检查版本，支持旧版本数据迁移
- 在发布说明中明确存档兼容性说明

**R3应对策略**:
- 在pause_scene.py的render方法中动态计算选项间距
- 测试多种分辨率（1920x1080, 1366x768, 1280x720）
- 确认所有选项在最小分辨率下仍可正常显示
```

---

## 第五章：阶段三 - 代码实现

### 5.1 实现前准备

#### 5.1.1 代码备份

在开始代码修改前，必须创建代码备份：

```bash
# 使用Git创建备份分支
git checkout -b fix/[issue-id]-backup

# 或者直接复制文件备份
cp airwar/scenes/scene.py airwar/scenes/scene.py.backup
cp airwar/scenes/pause_scene.py airwar/scenes/pause_scene.py.backup
cp airwar/game/scene_director.py airwar/game/scene_director.py.backup
```

#### 5.1.2 环境检查

```markdown
### 环境检查清单
- [ ] 代码仓库状态正常（无未提交的改动）
- [ ] 当前分支是正确的开发分支
- [ ] Python环境配置正确
- [ ] 所有依赖已安装
- [ ] 测试框架可用
```

### 5.2 代码修改规范

#### 5.2.1 通用规范

1. **代码风格**: 遵循PEP 8规范，使用4空格缩进
2. **命名规范**: 
   - 类名使用PascalCase: `PauseScene`, `SceneDirector`
   - 方法名使用snake_case: `create_save_data`, `handle_events`
   - 常量使用UPPER_SNAKE_CASE: `MAX_ENEMY_COUNT`, `DEFAULT_DIFFICULTY`
3. **注释规范**: 
   - 类和方法必须有文档字符串
   - 复杂逻辑需要行内注释
   - 更新代码时同步更新注释
4. **函数长度**: 单个函数不超过50行（特殊情况除外）
5. **文件长度**: 单个文件不超过500行

#### 5.2.2 本项目特定规范

**AIRWAR项目编码规范**:

```python
# ✅ 正确的示例
class PauseScene(Scene):
    def __init__(self):
        self.running = True
        self.result: PauseAction = None
        self.options = ['RESUME', 'MAIN MENU', 'SAVE AND QUIT', 'QUIT WITHOUT SAVING']
        self.selected_index = 0

    def _select_option(self) -> None:
        """处理选项选择"""
        self.running = False
        if self.selected_index == 0:
            self.result = PauseAction.RESUME
        elif self.selected_index == 1:
            self.result = PauseAction.MAIN_MENU
        elif self.selected_index == 2:
            self.result = PauseAction.SAVE_AND_QUIT
        elif self.selected_index == 3:
            self.result = PauseAction.QUIT_WITHOUT_SAVING
```

```python
# ❌ 错误的示例
class PauseScene(Scene):
    def __init__(self):
        self.running=True
        self.result=None
        self.options=['RESUME','MAIN MENU','SAVE AND QUIT','QUIT WITHOUT SAVING']
        self.selected_index=0
```

#### 5.2.3 Git提交规范

提交信息必须遵循以下格式：

```
<类型>(<范围>): <简短描述>

[可选的详细说明]

[可选的关联issue]
```

**类型**:
- `feat`: 新功能
- `fix`: 缺陷修复
- `docs`: 文档更新
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 杂项

**示例**:

```bash
# 提交修复
git commit -m "fix(pause_menu): add save and quit functionality

- Added SAVE_AND_QUIT and QUIT_WITHOUT_SAVING options to pause menu
- Updated SceneDirector to handle new quit actions
- Modified PauseAction enum to include new action types

Closes #123"
```

### 5.3 具体实现步骤

#### 步骤1: 修改枚举类型

**文件**: `airwar/scenes/scene.py`

```python
# 修改前 (L7-10)
class PauseAction(Enum):
    RESUME = "resume"
    MAIN_MENU = "main_menu"
    QUIT = "quit"

# 修改后
class PauseAction(Enum):
    RESUME = "resume"
    MAIN_MENU = "main_menu"
    SAVE_AND_QUIT = "save_and_quit"      # 新增
    QUIT_WITHOUT_SAVING = "quit_without_saving"  # 新增
    QUIT = "quit"  # 保留，向后兼容
```

#### 步骤2: 修改暂停菜单选项

**文件**: `airwar/scenes/pause_scene.py`

```python
# 修改前 (L10)
self.options = ['RESUME', 'MAIN MENU', 'QUIT']

# 修改后
self.options = ['RESUME', 'MAIN MENU', 'SAVE AND QUIT', 'QUIT WITHOUT SAVING']
```

#### 步骤3: 修改选项选择逻辑

**文件**: `airwar/scenes/pause_scene.py`

```python
# 修改前 (L81-88)
def _select_option(self) -> None:
    self.running = False
    if self.selected_index == 0:
        self.result = PauseAction.RESUME
    elif self.selected_index == 1:
        self.result = PauseAction.MAIN_MENU
    elif self.selected_index == 2:
        self.result = PauseAction.QUIT

# 修改后
def _select_option(self) -> None:
    self.running = False
    if self.selected_index == 0:
        self.result = PauseAction.RESUME
    elif self.selected_index == 1:
        self.result = PauseAction.MAIN_MENU
    elif self.selected_index == 2:
        self.result = PauseAction.SAVE_AND_QUIT
    elif self.selected_index == 3:
        self.result = PauseAction.QUIT_WITHOUT_SAVING
```

#### 步骤4: 调整UI布局

**文件**: `airwar/scenes/pause_scene.py`

```python
# 修改前 (L224-225)
option_spacing = 85
start_y = height // 2 + 30

# 修改后
option_spacing = 70
start_y = height // 2 + 20
```

#### 步骤5: 扩展SceneDirector处理逻辑

**文件**: `airwar/game/scene_director.py`

```python
# 修改 _handle_pause_toggle 方法 (L157-173)
# 添加新的动作处理分支
if action == PauseAction.RESUME:
    game_scene.resume()
    return "resume"
elif action == PauseAction.MAIN_MENU:
    return "main_menu"
elif action == PauseAction.SAVE_AND_QUIT:  # 新增
    return "save_and_quit"
elif action == PauseAction.QUIT_WITHOUT_SAVING:  # 新增
    return "quit_without_saving"
elif action == PauseAction.QUIT:  # 保留兼容
    return "save_and_quit"
```

#### 步骤6: 修改游戏流程处理

**文件**: `airwar/game/scene_director.py`

```python
# 修改 _run_game_flow 方法 (L114-122)
if isinstance(current_scene, GameScene):
    result = self._handle_pause_toggle(events, current_scene)
    if result == "main_menu":
        self._clear_saved_game()
        return "main_menu"
    elif result == "save_and_quit":  # 新增
        self._save_and_quit(current_scene)
        return "quit"
    elif result == "quit_without_saving":  # 新增
        self._quit_without_saving()
        return "quit"
    elif result == "quit":  # 保留兼容
        self._save_game_on_quit(current_scene)
        return "quit"
    escape_handled = result is True
```

#### 步骤7: 添加新的处理方法

**文件**: `airwar/game/scene_director.py`

```python
# 在类末尾添加新方法

def _save_and_quit(self, game_scene: GameScene) -> None:
    """保存游戏并退出
    
    将当前游戏状态保存到文件，然后退出游戏。
    保存内容包括分数、击杀数、buff效果、玩家生命值等所有进度数据。
    
    Args:
        game_scene: 当前游戏场景实例
    """
    if not game_scene or not game_scene._mother_ship_integrator:
        return
    
    save_data = game_scene._mother_ship_integrator.create_save_data()
    if save_data:
        persistence_manager = PersistenceManager()
        persistence_manager.save_game(save_data)

def _quit_without_saving(self) -> None:
    """清除存档并退出，不保存当前进度
    
    删除已存在的存档文件，确保下次进入游戏时从头开始。
    用于玩家明确选择不保存当前进度的场景。
    """
    self._clear_saved_game()
```

### 5.4 实现检查清单

```markdown
### 代码实现检查清单
- [ ] 所有新增的枚举值已添加
- [ ] 所有新增的选项已添加
- [ ] 所有动作处理逻辑已更新
- [ ] UI布局已适当调整
- [ ] 新的处理方法已添加
- [ ] 所有代码遵循编码规范
- [ ] 所有文档字符串已更新
- [ ] 编译/解释检查通过
```

---

## 第六章：阶段四 - 测试验证

### 6.1 测试原则

1. **全面性**: 测试用例必须覆盖所有功能点
2. **独立性**: 每个测试用例独立运行，不依赖其他测试
3. **可重复性**: 测试结果稳定，可重复执行
4. **自动化**: 优先编写自动化测试用例

### 6.2 测试类型

#### 6.2.1 单元测试

针对单个函数或方法的测试：

```python
# tests/test_pause_scene.py
import pytest
from airwar.scenes.pause_scene import PauseScene
from airwar.scenes.scene import PauseAction

class TestPauseScene:
    def test_initial_options_count(self):
        """测试暂停菜单初始化时是否有4个选项"""
        scene = PauseScene()
        scene.enter()
        assert len(scene.options) == 4
        assert scene.options == ['RESUME', 'MAIN MENU', 'SAVE AND QUIT', 'QUIT WITHOUT SAVING']
    
    def test_select_save_and_quit(self):
        """测试选择SAVE AND QUIT选项"""
        scene = PauseScene()
        scene.enter()
        scene.selected_index = 2  # 选择SAVE AND QUIT
        scene._select_option()
        assert scene.result == PauseAction.SAVE_AND_QUIT
    
    def test_select_quit_without_saving(self):
        """测试选择QUIT WITHOUT SAVING选项"""
        scene = PauseScene()
        scene.enter()
        scene.selected_index = 3  # 选择QUIT WITHOUT SAVING
        scene._select_option()
        assert scene.result == PauseAction.QUIT_WITHOUT_SAVING
```

#### 6.2.2 集成测试

测试多个模块协同工作的测试：

```python
# tests/test_scene_director.py
import pytest
from unittest.mock import Mock, MagicMock
from airwar.game.scene_director import SceneDirector
from airwar.scenes.scene import PauseAction

class TestSceneDirector:
    def test_save_and_quit_creates_save_data(self):
        """测试保存并退出功能"""
        # 准备测试环境
        scene_director = SceneDirector(...)
        game_scene = Mock()
        game_scene._mother_ship_integrator = Mock()
        game_scene._mother_ship_integrator.create_save_data = Mock(return_value=Mock())
        
        # 执行保存并退出
        scene_director._save_and_quit(game_scene)
        
        # 验证保存逻辑被调用
        game_scene._mother_ship_integrator.create_save_data.assert_called_once()
    
    def test_quit_without_saving_clears_save(self):
        """测试不保存并退出功能"""
        scene_director = SceneDirector(...)
        scene_director._clear_saved_game = Mock()
        
        scene_director._quit_without_saving()
        
        scene_director._clear_saved_game.assert_called_once()
```

#### 6.2.3 回归测试

确保修复不破坏现有功能的测试：

```python
# tests/test_regression.py
class TestRegression:
    def test_resume_functionality_unchanged(self):
        """测试RESUME功能未被破坏"""
        scene = PauseScene()
        scene.enter()
        scene.selected_index = 0
        scene._select_option()
        assert scene.result == PauseAction.RESUME
    
    def test_main_menu_functionality_unchanged(self):
        """测试MAIN MENU功能未被破坏"""
        scene = PauseScene()
        scene.enter()
        scene.selected_index = 1
        scene._select_option()
        assert scene.result == PauseAction.MAIN_MENU
```

### 6.3 测试执行流程

#### 6.3.1 本地测试

```bash
# 1. 运行单元测试
pytest tests/test_pause_scene.py -v

# 2. 运行集成测试
pytest tests/test_scene_director.py -v

# 3. 运行回归测试
pytest tests/test_regression.py -v

# 4. 运行所有测试
pytest tests/ -v

# 5. 生成测试覆盖率报告
pytest tests/ --cov=airwar --cov-report=html
```

#### 6.3.2 手动测试流程

```markdown
### 手动测试清单

#### 功能测试
- [ ] 测试1: 打开暂停菜单，验证显示4个选项
- [ ] 测试2: 使用W/UP键选择上一个选项
- [ ] 测试3: 使用S/DOWN键选择下一个选项
- [ ] 测试4: 按ESC键继续游戏
- [ ] 测试5: 选择SAVE AND QUIT并验证存档创建
- [ ] 测试6: 选择QUIT WITHOUT SAVING并验证存档删除
- [ ] 测试7: 选择MAIN MENU返回主菜单
- [ ] 测试8: 点击窗口关闭按钮并验证自动保存

#### 边界测试
- [ ] 测试9: 快速连续选择不同选项
- [ ] 测试10: 在最低分辨率下测试UI布局
- [ ] 测试11: 测试存档文件不存在时的行为
- [ ] 测试12: 测试存档文件损坏时的行为

#### 场景测试
- [ ] 测试13: 完整场景：进入母舰→退出母舰→选择保存并退出
- [ ] 测试14: 完整场景：正常游戏→选择不保存并退出
- [ ] 测试15: 完整场景：游戏中途关闭窗口
```

### 6.4 测试结果记录

```markdown
## 测试结果记录

### 测试执行信息
- **测试日期**: YYYY-MM-DD
- **测试人员**: [姓名]
- **测试环境**: [环境配置]
- **测试版本**: [版本号]

### 测试结果汇总
| 测试类型 | 用例数 | 通过数 | 失败数 | 阻塞数 |
|---------|--------|--------|--------|--------|
| 单元测试 | 10     | 10     | 0      | 0      |
| 集成测试 | 5      | 5      | 0      | 0      |
| 回归测试 | 3      | 3      | 0      | 0      |
| 手动测试 | 15     | 15     | 0      | 0      |

### 失败用例详情
[如果有任何失败用例，详细记录]

### 测试结论
[通过/不通过，附上结论说明]
```

---

## 第七章：阶段五 - 文档提交

### 7.1 代码提交

#### 7.1.1 提交前检查

```markdown
### 提交前检查清单
- [ ] 所有代码修改已完成
- [ ] 所有测试用例通过
- [ ] 代码符合编码规范
- [ ] 文档已同步更新
- [ ] 变更日志已记录
- [ ] 无临时调试代码
- [ ] 无敏感信息泄露
```

#### 7.1.2 Git操作流程

```bash
# 1. 查看变更状态
git status

# 2. 查看具体变更
git diff airwar/scenes/scene.py
git diff airwar/scenes/pause_scene.py
git diff airwar/game/scene_director.py

# 3. 添加变更文件
git add airwar/scenes/scene.py
git add airwar/scenes/pause_scene.py
git add airwar/game/scene_director.py
git add docs/FIX_WORKFLOW_GUIDE.md  # 如果更新了文档

# 4. 提交变更
git commit -m "fix(pause_menu): implement save and quit functionality

- Added SAVE_AND_QUIT and QUIT_WITHOUT_SAVING options to pause menu
- Extended PauseAction enum with new action types
- Updated SceneDirector to handle new quit actions
- Added _save_and_quit() and _quit_without_saving() methods
- Adjusted UI layout to accommodate 4 options

Closes #123"

# 5. 推送到远程仓库
git push origin fix/pause-menu-quit-options
```

### 7.2 文档更新

#### 7.2.1 需要更新的文档

1. **项目指南**: `docs/PROJECT_GUIDE.md`
   - 如果新增了功能，添加到功能说明部分

2. **变更日志**: `docs/CHANGELOG.md`
   - 记录本次修复的详细内容

3. **API文档**: 如果有的话
   - 更新相关的API说明

4. **用户手册**: 如果有的话
   - 更新用户操作说明

#### 7.2.2 文档更新示例

```markdown
# docs/CHANGELOG.md

## [Unreleased]

### Added
- 暂停菜单新增"保存并退出"选项（SAVE AND QUIT）
- 暂停菜单新增"不保存并退出"选项（QUIT WITHOUT SAVING）

### Changed
- 暂停菜单选项数量从3个增加到4个
- 窗口关闭按钮行为改为自动保存当前进度

### Fixed
- [相关缺陷修复]

## [Previous Version]
[历史版本记录]
```

### 7.3 变更通知

#### 7.3.1 通知内容

```markdown
## 修复完成通知

**问题编号**: #123
**问题标题**: 暂停菜单缺少保存退出选项
**修复日期**: YYYY-MM-DD
**修复人员**: [姓名]

### 修复内容
- 新增"保存并退出"选项，保存所有游戏进度后退出
- 新增"不保存并退出"选项，清除存档后退出
- 窗口关闭按钮现在会自动保存当前进度

### 影响范围
- 影响文件: 3个
  - `airwar/scenes/scene.py`
  - `airwar/scenes/pause_scene.py`
  - `airwar/game/scene_director.py`
- 影响功能: 暂停菜单、游戏退出流程

### 测试情况
- 单元测试: 通过（10/10）
- 集成测试: 通过（5/5）
- 手动测试: 通过（15/15）
- 回归测试: 通过（3/3）

### 注意事项
- 旧存档格式仍然兼容
- 向后兼容性已保留（PauseAction.QUIT仍然有效）

### 相关文档
- [文档链接]
```

### 7.4 提交后验证

```markdown
### 提交后验证清单
- [ ] 代码已成功推送到远程仓库
- [ ] CI/CD流水线全部通过
- [ ] 代码审查已通过（如有）
- [ ] 相关文档已更新
- [ ] 通知已发送
- [ ] 备份分支已清理（如有）
```

---

## 第八章：技术规范

### 8.1 文件组织规范

```
airwar/
├── scenes/                    # 场景相关
│   ├── __init__.py
│   ├── scene.py              # 场景基类和枚举定义
│   ├── pause_scene.py        # 暂停菜单场景
│   ├── game_scene.py         # 游戏主场景
│   └── menu_scene.py         # 主菜单场景
│
├── game/                      # 游戏逻辑
│   ├── scene_director.py     # 场景导演（流程控制）
│   ├── mother_ship/          # 母舰系统
│   │   ├── game_integrator.py
│   │   ├── state_machine.py
│   │   ├── persistence_manager.py
│   │   └── mother_ship_state.py
│   └── controllers/          # 控制器
│
├── ui/                       # UI组件
│
├── entities/                 # 游戏实体
│
├── utils/                    # 工具类
│   └── database.py          # 数据库工具
│
└── config.py                # 配置文件
```

### 8.2 代码结构规范

#### 8.2.1 类结构

```python
class ClassName:
    """类的简要描述
    
    类的详细说明，包括功能、用法等。
    
    Attributes:
        attr1: 属性1的描述
        attr2: 属性2的描述
    """
    
    def __init__(self, param1: Type1, param2: Type2) -> None:
        """初始化方法
        
        Args:
            param1: 参数1的描述
            param2: 参数2的描述
        """
        self.attr1 = param1
        self.attr2 = param2
    
    def public_method(self, arg1: Type) -> ReturnType:
        """公共方法
        
        方法的详细说明。
        
        Args:
            arg1: 参数描述
        
        Returns:
            返回值描述
        
        Raises:
            ExceptionType: 异常条件
        """
        pass
    
    def _private_method(self, arg1: Type) -> None:
        """私有方法
        
        私有方法的说明。
        """
        pass
```

#### 8.2.2 枚举结构

```python
from enum import Enum

class ActionEnum(Enum):
    """动作枚举类
    
    枚举类的详细说明。
    """
    ACTION_ONE = "action_one"
    ACTION_TWO = "action_two"
    ACTION_THREE = "action_three"
```

### 8.3 命名规范速查表

| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `PauseScene`, `SceneDirector` |
| 方法名 | snake_case | `handle_events`, `create_save_data` |
| 实例变量 | snake_case | `self.selected_index`, `self.options` |
| 类变量 | snake_case | - |
| 常量 | UPPER_SNAKE_CASE | `MAX_OPTIONS`, `DEFAULT_TIMEOUT` |
| 私有属性 | _前缀 | `self._running`, `self._event_bus` |
| 私有方法 | _前缀 | `def _select_option(self)` |
| 文件名 | snake_case | `pause_scene.py`, `scene_director.py` |
| 包名 | lowercase | `airwar`, `scenes` |

### 8.4 注释规范

#### 8.4.1 文档字符串规范

```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """函数的简要描述（一句完整的话，以句号结尾）
    
    函数的详细描述，说明函数的功能、用途、算法等。
    如果函数有特殊的使用方式或注意事项，也应在此说明。
    
    Args:
        param1: 参数1的描述，包括类型和含义
        param2: 参数2的描述，包括类型和含义
    
    Returns:
        返回值的描述，包括类型和含义
    
    Raises:
        ValueError: 当参数不符合要求时
        TypeError: 当参数类型错误时
    
    Examples:
        >>> result = function_name("test", 123)
        >>> print(result)
        "test_123"
    """
    pass
```

#### 8.4.2 行内注释规范

```python
# ✅ 好的注释
def calculate_score(self):
    # 分数 = 基础分数 × (1 + 连击加成) + 奖励分数
    score = self.base_score * (1 + self.combo_bonus) + self.bonus_score
    
    # 确保分数不为负数
    return max(0, score)

# ❌ 不好的注释
def calculate_score(self):
    score = self.base_score * (1 + self.combo_bonus) + self.bonus_score  # 计算分数
    return max(0, score)  # 返回分数
```

---

## 第九章：注意事项

### 9.1 常见错误及避免方法

#### 9.1.1 代码层面

| 错误类型 | 常见错误 | 避免方法 |
|---------|---------|----------|
| 逻辑错误 | 条件判断错误 | 使用测试用例覆盖所有分支 |
| 边界条件 | 未处理空值或异常值 | 进行边界测试 |
| 状态管理 | 状态不一致 | 使用状态机模式 |
| 资源泄漏 | 未释放资源 | 使用上下文管理器 |
| 线程安全 | 并发访问冲突 | 使用线程锁 |

#### 9.1.2 实现层面

| 错误类型 | 常见错误 | 避免方法 |
|---------|---------|----------|
| 遗漏处理 | 新增枚举未处理 | 枚举类型使用完整switch/if |
| 兼容性问题 | 破坏向后兼容 | 保留旧接口，标记deprecated |
| 性能问题 | 循环中创建对象 | 复用对象或延迟创建 |
| 安全性问题 | 敏感信息泄露 | 不在代码中硬编码密钥 |

### 9.2 风险控制

#### 9.2.1 备份策略

1. **代码备份**: 修改前使用Git创建备份分支
2. **数据库备份**: 修改前备份用户数据
3. **配置备份**: 修改前备份配置文件
4. **存档备份**: 测试前备份游戏存档

#### 9.2.2 回滚策略

```bash
# 如果需要回滚代码
git revert <commit-hash>  # 创建一个新的提交来撤销更改

# 如果需要完全回退到某个版本
git reset --hard <commit-hash>

# 如果需要从备份文件恢复
cp airwar/scenes/scene.py.backup airwar/scenes/scene.py
```

#### 9.2.3 灰度发布

对于重大修改，采用灰度发布策略：

1. **内部测试**: 仅内部人员可用的测试版本
2. **小范围发布**: 5-10%的用户使用新版本
3. **全量发布**: 确认无问题后全量发布
4. **快速回滚**: 监控问题，支持快速回滚

### 9.3 调试技巧

#### 9.3.1 日志调试

```python
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 在关键位置添加日志
logger.debug(f"Selected index: {self.selected_index}")
logger.info(f"Pause action selected: {self.result}")
logger.warning(f"Game scene not found, skipping save")
logger.error(f"Failed to save game: {e}")
```

#### 9.3.2 断点调试

```python
# 使用pdb进行交互式调试
import pdb

def _select_option(self):
    pdb.set_trace()  # 在此处设置断点
    self.running = False
    # ... 其余代码
```

#### 9.3.3 打印调试

```python
# 临时调试打印
print(f"[DEBUG] Selected index: {self.selected_index}")
print(f"[DEBUG] Options: {self.options}")
print(f"[DEBUG] Result: {self.result}")
```

**注意**: 调试完成后，务必删除所有临时调试代码！

### 9.4 性能优化

#### 9.4.1 避免的性能问题

```python
# ❌ 错误：在循环中创建对象
for i in range(100):
    particle = Particle()  # 每次循环都创建新对象
    particles.append(particle)

# ✅ 正确：复用对象或使用生成器
particles = [Particle() for _ in range(100)]  # 列表推导式
```

#### 9.4.2 缓存优化

```python
# 对于频繁访问的属性，使用缓存
class GameScene:
    @property
    def expensive_computation(self):
        if not hasattr(self, '_cached_value'):
            self._cached_value = self._do_expensive_computation()
        return self._cached_value
```

---

## 第十章：验收标准

### 10.1 功能验收

#### 10.1.1 必需功能

```markdown
### 功能验收清单

#### 核心功能
- [ ] 暂停菜单显示4个选项（RESUME, MAIN MENU, SAVE AND QUIT, QUIT WITHOUT SAVING）
- [ ] 键盘导航正常工作（W/S或UP/DOWN选择）
- [ ] ENTER/SPACE键确认选择
- [ ] ESC键继续游戏
- [ ] SAVE AND QUIT保存所有进度并退出
- [ ] QUIT WITHOUT SAVING清除存档并退出
- [ ] 窗口关闭自动保存当前进度

#### 交互功能
- [ ] 选项高亮显示正确
- [ ] 鼠标选择不响应（仅键盘操作）
- [ ] 快速连续操作无异常
- [ ] 循环导航正常工作（底部到顶部）

#### 边界情况
- [ ] 存档文件不存在时正常退出
- [ ] 存档文件损坏时正确处理
- [ ] 内存不足时正确处理
- [ ] 游戏场景无效时静默退出
```

### 10.2 代码验收

#### 10.2.1 代码质量标准

```markdown
### 代码验收清单

#### 代码规范
- [ ] 遵循PEP 8编码规范
- [ ] 类名、方法名、变量名命名规范
- [ ] 包含必要的文档字符串
- [ ] 无硬编码的魔法数字
- [ ] 无临时调试代码

#### 代码结构
- [ ] 类结构清晰，职责单一
- [ ] 方法长度不超过50行
- [ ] 文件长度不超过500行
- [ ] 无重复代码（DRY原则）

#### 代码安全
- [ ] 无敏感信息硬编码
- [ ] 输入参数进行验证
- [ ] 异常处理完善
- [ ] 无SQL注入风险
```

### 10.3 测试验收

#### 10.3.1 测试覆盖率标准

```markdown
### 测试覆盖率要求

| 模块 | 最低覆盖率 | 目标覆盖率 |
|------|-----------|-----------|
| scene.py | 90% | 100% |
| pause_scene.py | 85% | 95% |
| scene_director.py | 80% | 90% |
| 全局 | 75% | 85% |

### 测试用例要求
- 单元测试: 所有公共方法必须有测试用例
- 集成测试: 关键流程必须覆盖
- 回归测试: 所有已有功能必须通过
```

### 10.4 文档验收

```markdown
### 文档验收清单

#### 代码文档
- [ ] 所有类有文档字符串
- [ ] 所有公共方法有文档字符串
- [ ] 复杂逻辑有行内注释

#### 项目文档
- [ ] CHANGELOG已更新
- [ ] 相关文档已同步更新
- [ ] 用户手册已更新（如适用）

#### 提交记录
- [ ] Git提交信息规范
- [ ] 提交前检查清单完成
- [ ] 代码审查通过（如有）
```

### 10.5 性能验收

```markdown
### 性能验收标准

#### 响应时间
- 暂停菜单打开: < 100ms
- 选项切换: < 50ms
- 保存操作: < 500ms
- 退出操作: < 1000ms

#### 资源占用
- 内存增量: < 10MB
- CPU占用: < 5%

#### 兼容性
- Windows 10/11: 完全支持
- macOS 10.14+: 完全支持
- Python 3.8+: 完全支持
```

### 10.6 最终验收流程

```markdown
## 最终验收流程

### 验收步骤
1. [ ] 功能测试全部通过
2. [ ] 代码审查通过
3. [ ] 测试覆盖率达标
4. [ ] 文档更新完成
5. [ ] 性能测试达标
6. [ ] 安全扫描通过
7. [ ] 兼容性测试通过
8. [ ] 用户验收测试通过

### 验收签字
- 开发人员: _____________ 日期: _______
- 测试人员: _____________ 日期: _______
- 项目经理: _____________ 日期: _______

### 验收结论
□ 通过
□ 有条件通过（附注）
□ 不通过（原因）
```

---

## 附录A：常用命令参考

### A.1 Git命令

```bash
# 创建修复分支
git checkout -b fix/[issue-id]-description

# 查看变更
git diff
git diff --stat

# 暂存和提交
git add .
git commit -m "fix: description"
git push origin fix/[issue-id]-description

# 查看提交历史
git log --oneline -10
git log --graph --oneline --all

# 回滚操作
git revert <commit-hash>
git reset --hard <commit-hash>

# 清理操作
git branch -d <branch-name>  # 删除本地分支
git push origin --delete <branch-name>  # 删除远程分支
```

### A.2 测试命令

```bash
# 运行测试
pytest tests/ -v
pytest tests/test_pause_scene.py -v
pytest -k "test_name" -v

# 运行带覆盖率的测试
pytest tests/ --cov=airwar --cov-report=html
pytest tests/ --cov=airwar --cov-report=term-missing

# 调试测试
pytest tests/ --pdb
pytest tests/ -x  # 遇到第一个失败就停止
pytest tests/ -v -s  # 显示所有输出
```

### A.3 代码检查命令

```bash
# Python语法检查
python -m py_compile airwar/scenes/scene.py

# 代码格式化
black airwar/scenes/scene.py
autopep8 --in-place airwar/scenes/scene.py

# 静态分析
pylint airwar/scenes/scene.py
flake8 airwar/scenes/scene.py
mypy airwar/scenes/scene.py
```

---

## 附录B：模板库

### B.1 问题报告模板

```markdown
## 问题报告

**问题编号**: 
**报告日期**: 
**报告人员**: 
**严重程度**: [严重/高/中/低]
**问题类型**: [功能缺陷/性能问题/界面问题/其他]

### 问题描述
[详细描述问题]

### 复现步骤
1. 
2. 
3. 

### 预期行为
[描述期望的正确行为]

### 实际行为
[描述实际发生的错误行为]

### 影响分析
[分析问题的影响范围和程度]

### 附加信息
- 截图
- 日志
- 环境信息
```

### B.2 修复报告模板

```markdown
## 修复报告

**问题编号**: 
**修复日期**: 
**修复人员**: 

### 修复摘要
[简要描述修复内容]

### 修复详情
[详细的修复说明]

### 变更文件
- `airwar/scenes/scene.py`
- `airwar/scenes/pause_scene.py`
- `airwar/game/scene_director.py`

### 测试情况
- 单元测试: [通过/失败]
- 集成测试: [通过/失败]
- 手动测试: [通过/失败]
- 回归测试: [通过/失败]

### 风险评估
[评估修复可能带来的风险]

### 验收情况
[记录验收结果]
```

### B.3 发布检查清单

```markdown
## 发布检查清单

### 预发布检查
- [ ] 所有测试通过
- [ ] 代码审查通过
- [ ] 文档更新完成
- [ ] 变更日志已更新
- [ ] 发布说明已编写

### 发布后检查
- [ ] 监控系统正常
- [ ] 用户反馈正常
- [ ] 性能指标正常
- [ ] 无异常报警

### 回滚准备
- [ ] 回滚方案已准备
- [ ] 回滚脚本已测试
- [ ] 备份已确认
```

---

## 附录C：联系与支持

### C.1 团队联系方式

- **项目经理**: [姓名] - [邮箱]
- **技术负责人**: [姓名] - [邮箱]
- **测试负责人**: [姓名] - [邮箱]

### C.2 问题反馈渠道

- **Bug反馈**: [邮箱/链接]
- **功能建议**: [邮箱/链接]
- **文档纠错**: [邮箱/链接]

### C.3 相关资源

- **项目文档**: `docs/`
- **代码仓库**: [Git仓库地址]
- **CI/CD状态**: [CI/CD平台链接]
- **监控面板**: [监控平台链接]

---

## 文档版本历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| 1.0 | YYYY-MM-DD | [姓名] | 初始版本创建 |

---

**文档结束**

*本文档为AIRWAR项目修复工作的标准化指导文档，所有修复工作必须严格遵循本文档的规定。如有任何疑问，请联系技术负责人。*
