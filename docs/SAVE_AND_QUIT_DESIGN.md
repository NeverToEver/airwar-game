# 保存并退出功能 - 技术设计方案

## 文档信息

- **文档版本**: 1.0
- **创建日期**: 2025-01-XX
- **文档状态**: 有效
- **问题编号**: FEATURE-001
- **需求来源**: 用户请求增加三种退出机制

---

## 第一章：架构设计总览

### 1.1 模块划分和职责边界

根据架构师技能和FIX_WORKFLOW_GUIDE.md的规范，本次变更涉及以下模块：

```
airwar/
├── scenes/
│   ├── scene.py              # [修改] 枚举类型定义
│   └── pause_scene.py        # [修改] 暂停菜单UI和交互
│
└── game/
    └── scene_director.py     # [修改] 游戏流程控制和退出处理
```

**职责边界**：

| 模块 | 职责 | 修改范围 |
|------|------|----------|
| `scene.py` | 定义PauseAction枚举类型 | 添加2个新枚举值 |
| `pause_scene.py` | 管理暂停菜单UI和用户交互 | 扩展选项列表、调整UI布局 |
| `scene_director.py` | 控制游戏流程，处理退出逻辑 | 添加新动作处理分支和专用方法 |

### 1.2 数据流和依赖关系

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
返回 PauseAction (RESUME/MAIN_MENU/SAVE_AND_QUIT/QUIT_WITHOUT_SAVING)
    ↓
SceneDirector._handle_pause_toggle()
    ↓
根据动作类型执行不同处理
    ├─ RESUME: 继续游戏
    ├─ MAIN_MENU: 返回主菜单
    ├─ SAVE_AND_QUIT: 调用_save_and_quit() → 保存并退出
    └─ QUIT_WITHOUT_SAVING: 调用_quit_without_saving() → 不保存退出
```

### 1.3 关键接口和契约

#### 1.3.1 PauseAction枚举

```python
class PauseAction(Enum):
    RESUME = "resume"                      # 继续游戏
    MAIN_MENU = "main_menu"                # 返回主菜单
    SAVE_AND_QUIT = "save_and_quit"        # 保存并退出 [新增]
    QUIT_WITHOUT_SAVING = "quit_without_saving"  # 不保存退出 [新增]
    QUIT = "quit"                          # 保留，向后兼容
```

**契约**：
- 所有PauseAction枚举值必须被SceneDirector处理
- 不得出现未处理的枚举值（使用完整if/elif分支）

#### 1.3.2 PauseScene接口

```python
class PauseScene(Scene):
    options: List[str]  # 包含4个选项的列表
    selected_index: int  # 当前选中索引 (0-3)
    result: PauseAction  # 用户选择的动作

    def _select_option(self) -> None:
        """根据selected_index设置result"""
```

#### 1.3.3 SceneDirector接口

```python
class SceneDirector:
    def _save_and_quit(self, game_scene: GameScene) -> None:
        """保存游戏并退出

        保存当前游戏状态到文件，然后退出游戏。
        适用于SAVE_AND_QUIT动作。

        Args:
            game_scene: 当前游戏场景实例

        Returns:
            None
        """

    def _quit_without_saving(self) -> None:
        """清除存档并退出

        删除已存在的存档文件，确保下次进入游戏时从头开始。
        适用于QUIT_WITHOUT_SAVING动作。

        Returns:
            None
        """
```

---

## 第二章：详细设计

### 2.1 改动1：扩展PauseAction枚举

**文件**: `airwar/scenes/scene.py`

**位置**: L7-10

**改动类型**: 修改

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
    SAVE_AND_QUIT = "save_and_quit"
    QUIT_WITHOUT_SAVING = "quit_without_saving"
    QUIT = "quit"
```

**改动原因**:
- 原枚举只有3个动作，无法满足新增的保存退出和不保存退出功能
- 添加新枚举值支持新增功能，同时保留QUIT枚举确保向后兼容

**架构原则遵循**:
- ✅ 单一职责原则（每个枚举值代表一个独立动作）
- ✅ 接口导向设计（枚举作为场景间通信的契约）
- ✅ 向后兼容性（保留QUIT枚举不删除）

### 2.2 改动2：扩展暂停菜单选项列表

**文件**: `airwar/scenes/pause_scene.py`

**位置**: L10

**改动类型**: 修改

**改动前**:
```python
self.options = ['RESUME', 'MAIN MENU', 'QUIT']
```

**改动后**:
```python
self.options = ['RESUME', 'MAIN MENU', 'SAVE AND QUIT', 'QUIT WITHOUT SAVING']
```

**改动原因**:
- 用户界面需要显示4个选项供玩家选择
- 新的选项名称清晰表达功能：SAVE AND QUIT（保存并退出）、QUIT WITHOUT SAVING（不保存退出）

### 2.3 改动3：修改选项选择逻辑

**文件**: `airwar/scenes/pause_scene.py`

**位置**: L81-88

**改动类型**: 修改

**改动前**:
```python
def _select_option(self) -> None:
    self.running = False
    if self.selected_index == 0:
        self.result = PauseAction.RESUME
    elif self.selected_index == 1:
        self.result = PauseAction.MAIN_MENU
    elif self.selected_index == 2:
        self.result = PauseAction.QUIT
```

**改动后**:
```python
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

**改动原因**:
- 扩展选项选择逻辑以处理新增的2个选项
- 移除对QUIT枚举的依赖（保留但不直接使用）

**架构原则遵循**:
- ✅ 单一职责原则（_select_option只负责设置结果）
- ✅ 完整性（覆盖所有可能的selected_index值）

### 2.4 改动4：调整UI布局参数

**文件**: `airwar/scenes/pause_scene.py`

**位置**: L224-225

**改动类型**: 修改

**改动前**:
```python
option_spacing = 85
start_y = height // 2 + 30
```

**改动后**:
```python
option_spacing = 70
start_y = height // 2 + 20
```

**改动原因**:
- 从3个选项扩展到4个选项，需要调整间距以适应更多选项
- 减小option_spacing（85→70）和start_y（+30→+20）使4个选项更好地显示在屏幕上
- 保持选项在屏幕中央区域，避免超出边界

**布局计算**：
- 4个选项占用高度：70 × 3 = 210像素
- 总高度：start_y + 210 = height // 2 + 20 + 210 ≈ height // 2 + 230
- 选项区域：height // 2 - 50 到 height // 2 + 230
- 在标准分辨率（1080p）下：270 到 770，适合显示

### 2.5 改动5：扩展SceneDirector动作处理

**文件**: `airwar/game/scene_director.py`

**位置**: L157-173

**改动类型**: 修改

**改动前**:
```python
def _handle_pause_toggle(self, events: List[pygame.event.Event], game_scene: GameScene) -> str:
    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if game_scene.is_paused():
                game_scene.resume()
                return "resume"
            else:
                game_scene.pause()
                action = self._show_pause_menu(game_scene)
                if action == PauseAction.RESUME:
                    game_scene.resume()
                    return "resume"
                elif action == PauseAction.MAIN_MENU:
                    return "main_menu"
                elif action == PauseAction.QUIT:
                    return "quit"
    return "none"
```

**改动后**:
```python
def _handle_pause_toggle(self, events: List[pygame.event.Event], game_scene: GameScene) -> str:
    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if game_scene.is_paused():
                game_scene.resume()
                return "resume"
            else:
                game_scene.pause()
                action = self._show_pause_menu(game_scene)
                if action == PauseAction.RESUME:
                    game_scene.resume()
                    return "resume"
                elif action == PauseAction.MAIN_MENU:
                    return "main_menu"
                elif action == PauseAction.SAVE_AND_QUIT:
                    return "save_and_quit"
                elif action == PauseAction.QUIT_WITHOUT_SAVING:
                    return "quit_without_saving"
                elif action == PauseAction.QUIT:
                    return "save_and_quit"
    return "none"
```

**改动原因**:
- 扩展动作处理分支以支持新增的SAVE_AND_QUIT和QUIT_WITHOUT_SAVING动作
- 保留QUIT动作的处理（向后兼容），映射为save_and_quit行为

**架构原则遵循**:
- ✅ 完整性（所有枚举值都被处理）
- ✅ 向后兼容性（旧QUIT动作仍然有效）

### 2.6 改动6：扩展游戏流程处理

**文件**: `airwar/game/scene_director.py`

**位置**: L114-122

**改动类型**: 修改

**改动前**:
```python
if isinstance(current_scene, GameScene):
    result = self._handle_pause_toggle(events, current_scene)
    if result == "main_menu":
        self._clear_saved_game()
        return "main_menu"
    if result == "quit":
        self._save_game_on_quit(current_scene)
        return "quit"
    escape_handled = result is True
```

**改动后**:
```python
if isinstance(current_scene, GameScene):
    result = self._handle_pause_toggle(events, current_scene)
    if result == "main_menu":
        self._clear_saved_game()
        return "main_menu"
    elif result == "save_and_quit":
        self._save_and_quit(current_scene)
        return "quit"
    elif result == "quit_without_saving":
        self._quit_without_saving()
        return "quit"
    elif result == "quit":
        self._save_and_quit(current_scene)
        return "quit"
    escape_handled = result is True
```

**改动原因**:
- 扩展游戏流程处理以支持新的save_and_quit和quit_without_saving结果
- 调用新的专用方法处理不同的退出逻辑

### 2.7 改动7：添加新的处理方法

**文件**: `airwar/game/scene_director.py`

**位置**: L250后（类末尾）

**改动类型**: 新增

**新增代码**:
```python
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
        if not game_scene._mother_ship_integrator.is_docked():
            save_data.is_in_mothership = False
        persistence_manager = PersistenceManager()
        persistence_manager.save_game(save_data)

def _quit_without_saving(self) -> None:
    """清除存档并退出，不保存当前进度

    删除已存在的存档文件，确保下次进入游戏时从头开始。
    用于玩家明确选择不保存当前进度的场景。
    """
    self._clear_saved_game()
```

**改动原因**:
- 封装保存并退出的逻辑到独立方法，符合单一职责原则
- 封装不保存退出的逻辑到独立方法，清晰分离关注点
- 提供清晰的文档字符串说明方法行为

**架构原则遵循**:
- ✅ 单一职责原则（每个方法只做一件事）
- ✅ 高内聚（相关逻辑集中在同一方法）
- ✅ 低耦合（方法通过参数接收依赖，而非直接访问）
- ✅ 可维护性（清晰的文档字符串）
- ✅ 可扩展性（预留扩展点）

---

## 第三章：备选方案

### 方案A（推荐）：扩展现有枚举和方法

**描述**：在现有PauseAction枚举中添加新值，扩展PauseScene和SceneDirector的处理逻辑。

**优点**：
- 最小化代码改动，符合增量式开发原则
- 保持现有架构稳定
- 向后兼容（保留QUIT枚举）

**缺点**：
- 需要修改多个文件
- 需要调整UI布局参数

**选择理由**：
- 用户明确要求保留现有直接退出功能
- 增量式修改风险最低
- 符合FIX_WORKFLOW_GUIDE.md的最小改动原则

### 方案B：创建新的QuitAction子枚举

**描述**：创建QuitAction枚举专门处理退出相关动作，保留PauseAction不变。

**优点**：
- 不修改现有PauseAction枚举
- 退出逻辑独立封装

**缺点**：
- 增加新的枚举类型，增加代码复杂度
- 需要修改更多文件处理新的枚举
- 用户需求明确需要在暂停菜单中显示新选项，不适合拆分

**选择理由**：
- 增加不必要的复杂度
- 不符合KISS原则（Keep It Simple, Stupid）

### 方案C：重构为策略模式

**描述**：使用策略模式重构退出逻辑，将每种退出行为封装为独立策略类。

**优点**：
- 高度解耦，符合开闭原则
- 易于扩展新的退出行为

**缺点**：
- 过度设计，当前需求只需3种退出行为
- 增加大量新类和接口
- 开发周期长，不符合快速迭代需求

**选择理由**：
- 当前需求简单，不需要策略模式的灵活性
- 增加不必要的架构复杂度
- YAGNI原则（You Aren't Gonna Need It）

---

## 第四章：风险评估

### 4.1 风险识别

| 风险ID | 风险描述 | 发生概率 | 影响程度 | 风险等级 | 应对措施 |
|--------|----------|----------|----------|----------|----------|
| R1 | 修改枚举类型导致其他模块不兼容 | 中 | 高 | 高 | 在修改前检查所有枚举使用点，使用SearchCodebase工具搜索 |
| R2 | 存档格式变化导致旧存档无法加载 | 低 | 高 | 中 | 保留现有GameSaveData格式不变 |
| R3 | 新增选项影响现有UI布局 | 中 | 低 | 低 | 测试不同分辨率下的显示效果 |
| R4 | 窗口关闭事件处理与新逻辑冲突 | 低 | 中 | 低 | 保持现有_check_quit逻辑不变 |

### 4.2 风险应对策略

**R1应对策略**:
- 在修改枚举前，使用SearchCodebase工具全面搜索所有PauseAction使用点
- 确保PauseAction枚举的所有使用点都已更新
- 保留向后兼容的处理逻辑（QUIT枚举仍被处理）

**R2应对策略**:
- GameSaveData类保持不变
- 不修改PersistenceManager的save_game和load_game方法
- 仅在调用方选择不同的保存时机

**R3应对策略**:
- 在pause_scene.py的render方法中动态计算选项间距
- 测试多种分辨率（1920x1080, 1366x768, 1280x720）
- 确认所有选项在最小分辨率下仍可正常显示

**R4应对策略**:
- 保持_check_quit方法逻辑不变
- _check_quit只处理窗口关闭事件，不处理具体的保存逻辑
- 具体的保存逻辑由_save_game_on_quit方法处理（已在_check_quit中调用）

---

## 第五章：测试计划

### 5.1 测试用例

#### 5.1.1 单元测试

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|--------|----------|----------|----------|--------|
| TC001 | 验证暂停菜单显示正确选项 | 游戏运行中 | 按ESC键打开暂停菜单 | 显示4个选项：RESUME, MAIN MENU, SAVE AND QUIT, QUIT WITHOUT SAVING | 高 |
| TC002 | 验证SAVE_AND_QUIT枚举值 | 正常 | - | PauseAction.SAVE_AND_QUIT存在且值为"save_and_quit" | 高 |
| TC003 | 验证QUIT_WITHOUT_SAVING枚举值 | 正常 | - | PauseAction.QUIT_WITHOUT_SAVING存在且值为"quit_without_saving" | 高 |
| TC004 | 验证选择SAVE_AND_QUIT选项 | 暂停菜单打开 | 选择第3个选项并确认 | scene.result == PauseAction.SAVE_AND_QUIT | 高 |
| TC005 | 验证选择QUIT_WITHOUT_SAVING选项 | 暂停菜单打开 | 选择第4个选项并确认 | scene.result == PauseAction.QUIT_WITHOUT_SAVING | 高 |

#### 5.1.2 集成测试

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|--------|----------|----------|----------|--------|
| IT001 | 验证保存并退出功能 | 游戏运行中，有母舰状态 | 选择SAVE AND QUIT | 调用_save_and_quit方法，保存游戏数据 | 高 |
| IT002 | 验证不保存并退出功能 | 游戏运行中，有存档存在 | 选择QUIT WITHOUT SAVING | 调用_clear_saved_game方法，删除存档 | 高 |
| IT003 | 验证向后兼容性 | 正常 | 选择QUIT选项 | 行为与选择SAVE AND QUIT相同 | 中 |

#### 5.1.3 回归测试

| 用例ID | 测试项 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|--------|----------|----------|----------|--------|
| RT001 | 验证RESUME功能未破坏 | 暂停菜单打开 | 选择RESUME并确认 | 游戏继续运行 | 高 |
| RT002 | 验证MAIN MENU功能未破坏 | 暂停菜单打开 | 选择MAIN MENU并确认 | 返回主菜单 | 高 |
| RT003 | 验证窗口关闭自动保存 | 游戏运行中 | 点击窗口关闭按钮 | 保存游戏并退出 | 高 |

### 5.2 测试环境要求

- **操作系统**: Windows 10/11, macOS 10.14+
- **Python版本**: 3.8+
- **Pygame版本**: 2.0+
- **显示器分辨率**: 1920x1080（主测试）、1366x768、1280x720（兼容性测试）

### 5.3 测试数据准备

- 测试用户账户: test_user_001, test_user_002
- 测试存档文件: user_docking_save.json
- 测试场景：母舰状态、战斗状态、存档存在/不存在

---

## 第六章：实现检查清单

根据FIX_WORKFLOW_GUIDE.md第五章的要求：

```markdown
### 代码实现检查清单
- [ ] 所有新增的枚举值已添加（SAVE_AND_QUIT, QUIT_WITHOUT_SAVING）
- [ ] 所有新增的选项已添加（SAVE AND QUIT, QUIT WITHOUT SAVING）
- [ ] 所有动作处理逻辑已更新（_handle_pause_toggle, _run_game_flow）
- [ ] UI布局已适当调整（option_spacing=70, start_y=height//2+20）
- [ ] 新的处理方法已添加（_save_and_quit, _quit_without_saving）
- [ ] 所有代码遵循编码规范（PEP 8, 项目规范）
- [ ] 所有文档字符串已更新
- [ ] 编译/解释检查通过
```

---

## 第七章：验收标准

根据FIX_WORKFLOW_GUIDE.md第十章的要求：

### 7.1 功能验收

```markdown
### 功能验收清单

#### 核心功能
- [ ] 暂停菜单显示4个选项（RESUME, MAIN MENU, SAVE AND QUIT, QUIT WITHOUT SAVING）
- [ ] 键盘导航正常工作（W/S或UP/DOWN选择）
- [ ] ENTER/SPACE键确认选择
- [ ] ESC键继续游戏
- [ ] SAVE AND QUIT保存所有进度并退出
- [ ] QUIT WITHOUT SAVING清除存档并退出
- [ ] 窗口关闭自动保存当前进度（保持原有行为）

#### 交互功能
- [ ] 选项高亮显示正确
- [ ] 鼠标选择不响应（仅键盘操作）
- [ ] 快速连续操作无异常
- [ ] 循环导航正常工作（底部到顶部）

#### 边界情况
- [ ] 存档文件不存在时正常退出
- [ ] 游戏场景无效时静默退出
```

### 7.2 代码验收

```markdown
### 代码验收清单

#### 代码规范
- [ ] 遵循PEP 8编码规范
- [ ] 类名、方法名、变量名命名规范
- [ ] 包含必要的文档字符串
- [ ] 无硬编码的魔法数字（option_spacing=70, start_y调整）
- [ ] 无临时调试代码

#### 代码结构
- [ ] 类结构清晰，职责单一
- [ ] 方法长度不超过50行
- [ ] 无重复代码（DRY原则）
```

---

## 附录：变更文件清单

| 序号 | 文件路径 | 改动类型 | 改动说明 |
|------|----------|----------|----------|
| 1 | `airwar/scenes/scene.py` | 修改 | 添加2个新枚举值 |
| 2 | `airwar/scenes/pause_scene.py` | 修改 | 扩展选项列表和UI布局 |
| 3 | `airwar/game/scene_director.py` | 修改 | 扩展动作处理，添加新方法 |

---

**文档结束**

*本文档为保存并退出功能的技术设计方案，所有实现工作必须严格遵循本文档的规定。*
