# Air War 项目需求与技术规范总览

> **文档版本**: 3.1
> **日期**: 2026-04-16
> **维护者**: AI Assistant (Claude)
> **项目仓库**: gitee.com:xxxplxxx/airwar-game.git

---

## 一、项目背景与当前状态

### 1.1 项目概述

**Air War** 是一款基于 Python + Pygame 开发的垂直卷轴空战游戏，采用经典街机风格设计，支持多难度模式、天赋升级系统、Boss 战斗和母舰停靠存档机制。

### 1.2 技术栈

| 组件 | 技术选型 | 版本要求 |
|------|----------|----------|
| **语言** | Python | 3.11+ |
| **游戏引擎** | Pygame | 2.6.1+ |
| **图形** | Pygame Surface | - |
| **音频** | Pygame Mixer | - |
| **测试框架** | pytest | - |
| **版本控制** | Git | - |

### 1.3 项目结构

```
airwar/
├── config/              # 配置模块
│   ├── game_config.py   # 游戏配置
│   └── settings.py      # 设置常量
├── data/                # 数据存储
│   ├── users.json       # 用户数据
│   └── user_docking_save.json  # 存档数据
├── entities/           # 游戏实体
│   ├── player.py        # 玩家战机
│   ├── enemy.py        # 敌机 & Boss
│   ├── bullet.py       # 子弹
│   └── interfaces.py  # 实体接口
├── game/               # 核心游戏逻辑
│   ├── buffs/          # 天赋系统
│   ├── controllers/   # 控制器
│   ├── mother_ship/    # 母舰系统 (新增)
│   ├── rendering/     # 渲染系统
│   ├── systems/        # 游戏系统
│   └── scene_director.py
├── input/              # 输入处理
├── scenes/             # 场景管理
│   ├── game_scene.py   # 游戏主场景
│   ├── login_scene.py  # 登录场景
│   ├── menu_scene.py   # 菜单场景
│   └── pause_scene.py  # 暂停场景
├── ui/                 # UI组件
├── utils/              # 工具函数
├── window/             # 窗口管理
└── tests/              # 测试用例 (155个)
```

### 1.4 当前状态

| 指标 | 数值 |
|------|------|
| **代码总行数** | ~5000+ 行 |
| **测试覆盖** | 155 tests passed |
| **模块数量** | 15+ 个子系统 |
| **架构成熟度** | 中等 (进行中重构) |

---

## 二、已识别问题清单

### 2.1 架构缺陷 (🔴 高优先级)

| 编号 | 问题 | 影响文件 | 严重程度 | 状态 |
|------|------|----------|----------|------|
| ARC-001 | GameScene 上帝类 | game_scene.py | 严重 | 待修复 |
| ARC-002 | SceneDirector 职责过多 | scene_director.py | 严重 | 待修复 |
| ARC-003 | RewardSystem if-elif 链 | reward_system.py | 中等 | 待重构 |
| ARC-004 | Enemy/Boss 循环依赖 | enemy.py | 严重 | 部分修复 |

### 2.2 性能瓶颈 (🟠 中高优先级)

| 编号 | 问题 | 影响文件 | 严重程度 | 状态 |
|------|------|----------|----------|------|
| PERF-001 | 全屏渐变每帧重绘 | background_renderer.py | 极高 | ✅ **已修复** |
| PERF-002 | Surface 在渲染循环中创建 | 15+ 文件 | 高 | 待优化 |
| PERF-003 | O(n²) 碰撞检测 | game_scene.py | 高 | 待优化 |
| PERF-004 | 粒子系统 Surface 重复创建 | background_renderer.py | 高 | ✅ **已修复** |

### 2.3 状态同步缺陷 (🔴 高优先级)

| 编号 | 问题 | 影响文件 | 严重程度 | 状态 |
|------|------|----------|----------|------|
| STATE-001 | 母舰存档状态残留导致错误加载 | scene_director.py, game_scene.py | 高 | **已记录，待修复** |
| STATE-002 | JSON反序列化无验证 | mother_ship_state.py | 中 | **已记录，待修复** |

### 2.4 安全问题 (🟡 中优先级)

| 编号 | 问题 | 影响文件 | 严重程度 | 状态 |
|------|------|----------|----------|------|
| SEC-002 | 用户输入验证不足 | login_scene.py | 中 | 待增强 |
| SEC-003 | 弱密码哈希 (SHA256) | database.py | 低 | 可接受 |
| SEC-004 | 游戏存档可篡改 | game_scene.py | 中 | 设计局限 |

> **注意**：SEC-001 (JSON反序列化无验证) 已合并到 STATE-002

### 2.5 代码质量问题 (🟡 中优先级)

| 编号 | 问题 | 影响文件 | 数量 | 状态 |
|------|------|----------|------|------|
| QUAL-001 | 函数过长 (>40行) | 多文件 | 10个 | 待拆分 |
| QUAL-002 | 深度嵌套 (4+层) | 多文件 | 6处 | 待优化 |
| QUAL-003 | 魔法数字 | 多文件 | 14+处 | 待提取 |
| QUAL-004 | 重复代码块 | 3个scene | 6处 | 待提取 |

---

## 三、新工程文件需求

### 3.1 待开发文件清单

| 序号 | 文件路径 | 功能定位 | 优先级 | 依赖关系 |
|------|----------|----------|--------|----------|
| 1 | `airwar/utils/visual_helpers.py` | UI渲染辅助函数 | P0 | 被多模块依赖 |
| 2 | `airwar/ui/particle_system.py` | 粒子系统封装 | P1 | 依赖sprites |
| 3 | `airwar/config/constants.py` | 游戏常量集中管理 | P1 | 全局引用 |
| 4 | `airwar/game/buff_renderer.py` | Buff渲染器抽象 | P2 | 依赖buffs |
| 5 | `airwar/tests/test_performance.py` | 性能基准测试 | P2 | 依赖主模块 |

### 3.2 新文件规格要求

#### 3.2.1 `airwar/utils/visual_helpers.py`

```python
# 功能定位: 提取3个scene文件中的重复渲染代码
# 包含内容:
#   - GradientCache: 渐变背景缓存类
#   - ParticleSystem: 粒子系统管理
#   - GlowTextRenderer: 发光文字渲染器
# 技术要求:
#   - 使用 pygame.Surface 缓存
#   - 支持屏幕尺寸自适应
#   - 线程安全 (如需要)
```

#### 3.2.2 `airwar/config/constants.py`

```python
# 功能定位: 集中管理游戏中的魔法数字
# 包含内容:
#   - 伤害常量: BULLET_DAMAGE, BOSS_DAMAGE
#   - 尺寸常量: PLAYER_WIDTH, PLAYER_HEIGHT
#   - 时间常量: ENTRANCE_DURATION, BOSS_ESCAPE_TIME
#   - 颜色常量: 所有硬编码颜色值
# 技术要求:
#   - 使用 UPPER_SNAKE_CASE 命名
#   - 提供类型注解
#   - 文档字符串说明
```

### 3.3 技术栈要求

| 要求类型 | 具体要求 |
|----------|----------|
| **代码规范** | PEP 8, snake_case 变量/函数, PascalCase 类 |
| **类型注解** | 所有公共接口必须有类型注解 |
| **文档** | 每个模块/类/函数需要 docstring |
| **测试** | 新代码必须有对应测试用例 |
| **性能** | 避免每帧创建 Surface, 使用缓存 |

---

## 四、新特性详细规格

### 4.1 母舰停靠系统 (已实现)

**功能描述**: 玩家长按 H 键 3 秒触发母舰召唤，进入母舰后自动存档

**用户场景**:
1. 战斗中按 H 键，显示进度条
2. 3 秒后母舰出现，战机进入
3. 自动保存游戏状态
4. 长按 H 键离开母舰

**技术实现要点**:
```python
# 状态机设计
IDLE → PRESSING → DOCKING → DOCKED
  ↑                              │
  └────────── UNDOCKING ←────────┘

# 核心类
- InputDetector: H键检测
- StateMachine: 状态管理
- EventBus: 模块通信
- PersistenceManager: 存档管理
```

### 4.2 Buff 统计面板 (已设计)

**功能描述**: 屏幕右侧显示实时生效的 Buff 统计

**用户场景**:
1. 选择 Buff 后，面板显示激活的 Buff
2. 实时更新数值变化
3. 面板样式与游戏风格一致

**技术实现要点**:
```python
# 显示格式
Power Shot: +{N}%
Rapid Fire: +{N}%
Armor: -{N}%
Evasion: +{N}%

# 视觉设计
- 面板宽度: 160px
- 半透明背景
- 圆角边框
```

### 4.3 性能优化特性 (待实现)

**功能描述**: 减少每帧渲染开销，提升 FPS 稳定性

**技术实现要点**:
```python
# 1. Surface 缓存
class GradientCache:
    _cache: dict = {}
    @classmethod
    def get(cls, width, height) -> pygame.Surface:
        # 缓存键: (width, height)
        # 过期策略: 屏幕尺寸变化时刷新

# 2. Hitbox 缓存
class Player:
    _cached_hitbox: Optional[pygame.Rect] = None
    def get_hitbox(self) -> pygame.Rect:
        if self._cached_hitbox is None:
            # 计算并缓存
        return self._cached_hitbox
```

---

## 五、工程维护任务

### 5.1 紧急修复 (P0)

| 任务ID | 任务描述 | 预期工时 | 验收标准 |
|---------|----------|----------|----------|
| TASK-P0-001 | 修复 background_renderer.py 语法错误 | 1h | `python -m py_compile` 通过 |
| TASK-P0-002 | 验证语法修复后游戏正常运行 | 0.5h | 手动测试通过 |

### 5.2 架构重构 (P1)

| 任务ID | 任务描述 | 预期工时 | 验收标准 |
|---------|----------|----------|----------|
| TASK-P1-001 | 提取 UI 渲染辅助函数 | 2h | 新模块测试覆盖100% |
| TASK-P1-002 | 提取游戏常量到 constants.py | 1h | 无魔法数字残留 |
| TASK-P1-003 | 实现 Hitbox 缓存优化 | 1h | 性能提升50% |
| TASK-P1-004 | 实现渐变背景缓存 | 1h | 每帧减少 Surface 创建 |

### 5.3 安全加固 (P2)

| 任务ID | 任务描述 | 预期工时 | 验收标准 |
|---------|----------|----------|----------|
| TASK-P2-001 | GameSaveData 输入验证 | 1h | 无效数据不崩溃 |
| TASK-P2-002 | 登录输入格式验证 | 1h | 特殊字符过滤 |

### 5.4 代码质量 (P3)

| 任务ID | 任务描述 | 预期工时 | 验收标准 |
|---------|----------|----------|----------|
| TASK-P3-001 | 拆分过长函数 | 3h | 无函数超过40行 |
| TASK-P3-002 | 消除重复代码 | 2h | 重复代码块<3处 |
| TASK-P3-003 | 添加性能基准测试 | 2h | 测试文件存在 |

### 5.5 文档更新

| 任务ID | 任务描述 | 预期工时 | 验收标准 |
|---------|----------|----------|----------|
| TASK-DOC-001 | 更新 SPEC-000 综合文档 | 1h | 包含最新架构 |
| TASK-DOC-002 | 编写新模块 API 文档 | 2h | docstring 完整 |
| TASK-DOC-003 | 更新 README.md | 0.5h | 包含运行说明 |

---

## 六、预期交付成果与质量标准

### 6.1 代码交付标准

| 检查项 | 目标 | 验证方式 |
|--------|------|----------|
| 测试通过率 | 100% | `pytest airwar/tests/ -q` |
| 语法检查 | 0 errors | `python -m py_compile` |
| 类型检查 | 0 warnings | `mypy airwar/` |
| 代码覆盖 | ≥80% | `pytest --cov` |

### 6.2 性能标准

| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| 游戏 FPS | 稳定 60 FPS | 游戏内显示 |
| 渐变渲染 | <0.5ms/帧 | 性能分析器 |
| Surface 创建 | <20/帧 | 代码统计 |
| 内存占用 | <100MB | 系统监控 |

### 6.3 架构标准

| 检查项 | 目标 | 工具 |
|--------|------|------|
| 函数长度 | ≤40 行 | radon |
| 圈复杂度 | ≤10 | radon |
| 继承深度 | ≤3 | pycallgraph |
| 模块耦合 | 低耦合 | import 检查 |

### 6.4 安全标准

| 检查项 | 目标 | 验证方式 |
|--------|------|----------|
| 输入验证 | 100% 覆盖 | 代码审查 |
| SQL 注入 | 0 风险 | 代码审查 |
| 敏感数据 | 不泄露 | 日志审查 |

---

## 七、工作指导

### 7.1 快速上手

1. **环境配置**:
```bash
cd d:\Trae\pygames_dev
python -m venv venv
.\venv\Scripts\activate
pip install pygame pytest
```

2. **运行测试**:
```bash
pytest airwar/tests/ -v
```

3. **运行游戏**:
```bash
python main.py
```

### 7.2 代码审查清单

| 检查项 | 说明 |
|--------|------|
| ✅ | 函数有 docstring |
| ✅ | 公共接口有类型注解 |
| ✅ | 无魔法数字 (使用常量) |
| ✅ | 函数 ≤40 行 |
| ✅ | 嵌套 ≤3 层 |
| ✅ | 有对应测试 |
| ✅ | 测试通过 |

### 7.3 Git 提交规范

```bash
# 格式
<type>: <subject>

# Type
feat:     新功能
fix:      Bug修复
refactor: 重构 (非功能修改)
docs:     文档更新
style:    代码格式
perf:     性能优化
test:     测试相关
chore:    构建/工具

# 示例
feat: 实现Hitbox缓存优化

详细说明:
- 添加 _cached_hitbox 属性
- 实现缓存失效机制
- 性能提升50%

Fixes: #PERF-004
Tests: test_player.py::test_hitbox_caching
```

### 7.4 问题反馈模板

```markdown
## 问题描述
[清晰描述问题]

## 复现步骤
1. [步骤1]
2. [步骤2]
3. [步骤3]

## 预期行为
[期望的结果]

## 实际行为
[实际的结果]

## 环境信息
- OS: Windows
- Python: 3.11
- Pygame: 2.6.1

## 相关代码
```python
# 代码片段
```
```

---

## 八、参考文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 综合技术文档 | `docs/superpowers/specs/SPEC-000-comprehensive-technical-report.md` | 项目完整技术规格 |
| 优化计划 | `docs/superpowers/specs/SPEC-010-optimization-plan.md` | 待执行优化任务 |
| 优化报告 | `docs/superpowers/specs/SPEC-011-optimization-report.md` | 已完成优化记录 |
| 母舰状态保存异常报告 | `docs/superpowers/specs/SPEC-012-mothership-save-state-bug-report.md` | 存档状态同步问题记录 |

---

**文档结束**

*本文档为 Air War 项目的需求与技术规范总览，旨在为开发者提供清晰的项目上下文和可操作的工作指导。*
