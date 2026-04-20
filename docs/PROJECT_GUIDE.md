# Air War 项目指南

> **文档版本**: 2.0
> **日期**: 2026-04-17
> **最后更新**: 2026-04-20
> **维护者**: AI Assistant (Trae IDE)
> **项目仓库**: gitee.com:xxxplxxx/airwar-game.git

---

## 一、项目概述

### 1.1 项目信息

| 项目 | 内容 |
|------|------|
| **项目名称** | Air War (飞机大战) |
| **项目类型** | Python + Pygame 垂直卷轴空战游戏 |
| **代码总行数** | ~9000+ 行 |
| **测试用例** | 274 tests passed |
| **架构成熟度** | 良好 (持续优化中) |
| **综合评分** | 85/100 |

### 1.2 技术栈

| 组件 | 技术选型 | 版本要求 |
|------|----------|----------|
| **语言** | Python | 3.8+ |
| **游戏引擎** | Pygame | 2.6.1+ |
| **图像处理** | Pillow | 12.2.0+ |
| **测试框架** | pytest | - |
| **版本控制** | Git | - |

### 1.3 项目结构

```
airwar/
├── config/              # 配置模块
├── data/                # 数据存储
├── entities/           # 游戏实体
├── game/               # 核心游戏逻辑
│   ├── buffs/          # 天赋系统
│   ├── controllers/    # 控制器
│   ├── mother_ship/    # 母舰系统
│   ├── rendering/      # 渲染系统
│   └── systems/        # 游戏系统
├── input/              # 输入处理
├── scenes/             # 场景管理
├── ui/                 # UI组件
├── utils/              # 工具函数
├── window/             # 窗口管理
└── tests/              # 测试用例
```

### 1.4 核心特性

- 🎮 街机风格射击游戏
- 🛸 母舰系统（进度保存、增益强化）
- ⚔️ 多种难度模式（简单、普通、困难）
- 🧬 Roguelike增益系统
- 🎨 赛博朋克视觉风格
- 🎯 Boss战机制

---

## 二、系统架构

### 2.1 核心模块

```
airwar/
├── scenes/                      # 场景管理
│   ├── game_scene.py           # 游戏主场景
│   ├── menu_scene.py           # 菜单场景
│   ├── login_scene.py          # 登录场景
│   └── pause_scene.py          # 暂停场景
├── entities/                    # 游戏实体
│   ├── player.py               # 玩家战机
│   ├── enemy.py                # 敌机 & Boss
│   └── bullet.py               # 子弹
├── game/                        # 核心逻辑
│   ├── mother_ship/            # 母舰系统
│   ├── controllers/            # 控制器
│   ├── systems/                # 游戏系统
│   └── rendering/              # 渲染系统
├── config/                      # 配置
│   └── settings.py             # 游戏配置
├── ui/                          # UI组件
└── utils/                       # 工具函数
```

### 2.2 架构原则

- **单一职责 (SRP)**: 每个类/模块有明确职责
- **低耦合**: 通过事件总线解耦
- **接口导向**: 依赖抽象接口而非实现
- **可测试性**: 核心逻辑有完整测试覆盖

---

## 三、游戏功能规格

### 3.1 难度系统

| 难度 | 基础伤害 | 敌机速度 | 回血速度 |
|------|----------|----------|----------|
| Easy | 100 | 慢 | 3HP/0.75s (3秒后) |
| Medium | 50 | 中 | 2HP/1s (4秒后) |
| Hard | 34 | 快 | 1HP/1.5s (5秒后) |

### 3.2 天赋系统 (Buffs)

#### 生命类
| 天赋 | 效果 |
|------|------|
| Extra Life | 最大生命+50，当前+30 |
| Regeneration | 回血速度提升至2HP/秒 |
| Lifesteal | 击杀后回复生命 |

#### 攻击类
| 天赋 | 效果 |
|------|------|
| Power Shot | 子弹伤害+25% (基于基础值) |
| Rapid Fire | 射击间隔-20% (基于基础值) |
| Piercing | 子弹穿透敌人 |
| Spread Shot | 同时发射3颗子弹 |
| Explosive | 范围伤害 |

#### 防御类
| 天赋 | 效果 |
|------|------|
| Shield | 抵挡下一次攻击 |
| Armor | 受到伤害-15% |
| Evasion | 20%闪避几率 |
| Barrier | 获得50点临时HP |

#### 工具类
| 天赋 | 效果 |
|------|------|
| Speed Boost | 移动速度+15% |
| Magnet | 拾取范围增加 |
| Slow Field | 敌人速度-20% |

### 3.3 Boss 系统

**Boss 属性**:
- 生命值: 500 ~ 2000 (根据循环递增)
- 存活时间: 30秒
- 逃跑时间: 根据伤害动态计算

**攻击模式**:
1. 扇形弹幕
2. 追踪弹
3. 全方位弹幕

**Boss 生成惩罚机制**:
- 击杀Boss: 正常间隔重置（30秒）
- Boss逃跑: 惩罚间隔（45秒，1.5x惩罚系数）

---

## 四、母舰系统规格

### 4.1 触发机制

**触发方式**: 长按 H 键 3 秒

**状态转换**:
```
IDLE → PRESSING → DOCKING → DOCKED
  ↑                              │
  └── UNDOCKING ←───────────────┘
```

### 4.2 数据持久化

**存档数据结构** (GameSaveData):
| 字段 | 类型 | 说明 |
|------|------|------|
| score | int | 当前分数 |
| cycle_count | int | 循环计数 |
| kill_count | int | 击杀数 |
| unlocked_buffs | List[str] | 已解锁天赋 |
| buff_levels | Dict[str, int] | 天赋等级 |
| player_health | int | 玩家生命值 |
| difficulty | str | 难度设置 |
| is_in_mothership | bool | 是否在母舰中 |
| username | str | 用户名 |

**存储路径**: `airwar/data/user_docking_save.json`

### 4.3 事件列表

| 事件名 | 说明 |
|--------|------|
| H_PRESSED | H键按下 |
| H_RELEASED | H键释放 |
| PROGRESS_COMPLETE | 进度达到100% |
| STATE_CHANGED | 状态切换 |
| START_DOCKING_ANIMATION | 开始进入动画 |
| DOCKING_ANIMATION_COMPLETE | 进入动画完成 |
| START_UNDOCKING_ANIMATION | 开始离开动画 |
| UNDOCKING_ANIMATION_COMPLETE | 离开动画完成 |
| SAVE_GAME_REQUEST | 请求保存游戏 |

---

## 五、里程碑记录

### 里程碑 1: 基础架构重构 (2026-04-14)

**目标**: 建立模块化、可测试的代码架构

**完成内容**:
- ✅ 实现输入层抽象 (InputHandler 接口)
- ✅ 拆分 GameScene 上帝类
- ✅ 解耦 Enemy/Boss 循环依赖
- ✅ 重构 RewardSystem (策略模式)
- ✅ 提取魔法数字到 settings.py

**关键指标**:
| 指标 | 改善 |
|------|------|
| GameScene 行数 | 524行 → ~150行 (-71%) |
| 子系统数量 | 0 → 10+ |
| 耦合度 | 高 → 低 |

---

### 里程碑 2: 母舰停靠系统 (2026-04-15~16)

**目标**: 实现母舰召唤、停靠、存档功能

**完成内容**:
- ✅ H键长按(3秒)触发母舰召唤
- ✅ 平滑进入/离开动画
- ✅ 游戏状态持久化
- ✅ 状态机完整实现

---

### 里程碑 3: 性能优化 (2026-04-16)

**目标**: 优化运行时资源消耗

**完成内容**:
- ✅ 背景渐变缓存 (20x性能提升)
- ✅ Particle Surface 缓存 (5x性能提升)
- ✅ Hitbox 缓存 (50x性能提升)
- ✅ SurfaceCache 统一缓存系统

**性能数据**:
| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 背景渐变渲染 | ~2ms/帧 | ~0.1ms/帧 | **20x** |
| Particle 渲染 | ~0.5ms/帧 | ~0.1ms/帧 | **5x** |
| Hitbox 获取 | ~0.05ms/次 | ~0.001ms/次 | **50x** |
| Surface 每帧创建 | 50+ 次 | 20 次 | **60%↓** |

---

### 里程碑 4: Bug 修复与质量提升 (2026-04-16)

**目标**: 修复已知问题，提升代码质量

**修复的 Bug**:
| Bug | 严重程度 | 状态 |
|-----|----------|------|
| Boss逃跑时间异常 | 高 | ✅ 已修复 |
| Boss倒计时时间流速异常 | 中高 | ✅ 已修复 |
| DMG显示异常 (+400%) | 中 | ✅ 已修复 |
| RATE显示闪动 | 中高 | ✅ 已修复 |
| 母舰内子弹冻结 | 高 | ✅ 已修复 |
| H键检测失效 | 高 | ✅ 已修复 |
| 母舰无法重复进入 | 高 | ✅ 已修复 |
| 敌机碰撞体过小 | 中 | ✅ 已修复 |

---

### 里程碑 5: Buff系统重构 (2026-04-20)

**目标**: 修复Buff累积计算bug，统一奖励系统

**完成内容**:
- ✅ PowerShot累积伤害bug修复
- ✅ RapidFire双重缩减修复
- ✅ UI状态显示增强
- ✅ Buff无状态化重构

**新架构**:
```
RewardSystem (唯一状态源)
    ↓
Buff (无状态, 定义计算公式)
    ↓
Player (只读属性)
    ↓
UI (展示状态)
```

---

## 六、测试清单

### 6.1 测试执行命令

```bash
# 全量测试 (无头模式)
SDL_VIDEODRIVER=dummy pytest -q

# 特定模块测试
pytest airwar/tests/test_mother_ship_logic.py -v
pytest airwar/tests/test_buffs.py -v

# 代码编译检查
python -m compileall airwar
```

### 6.2 核心功能测试

#### 登录与菜单
| 测试项 | 预期结果 | 状态 |
|--------|----------|------|
| 注册新账号 | 成功创建并保存 | ☐ |
| 登录已有账号 | 成功登录，显示用户名 | ☐ |
| 难度选择切换 | Easy/Medium/Hard 正确显示 | ☐ |

#### Boss 系统
| 测试项 | 预期结果 | 状态 |
|--------|----------|------|
| 30秒后出现 | 正常出现 | ☐ |
| 逃跑惩罚延迟 | 45秒间隔 | ☐ |
| 击杀奖励 | 获得 5000+ 分数 | ☐ |

#### 母舰系统
| 测试项 | 预期结果 | 状态 |
|--------|----------|------|
| H键长按进入 | 动画播放 | ☐ |
| 存档保存 | 数据正确保存 | ☐ |
| 可重新进入母舰 | 功能正常 | ☐ |

#### Buff系统
| 天赋 | 测试项 | 状态 |
|------|--------|------|
| Power Shot | DMG显示稳定百分比 | ☐ |
| Rapid Fire | RATE显示稳定百分比 | ☐ |
| Armor | 伤害减免 -15% | ☐ |

### 6.3 测试结果

| 测试套件 | 测试数 | 通过数 | 状态 |
|----------|--------|--------|------|
| 全量测试 | 274 | 274 | ✅ |

---

## 七、代码规范

### 7.1 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `GameScene`, `MotherShipStateMachine` |
| 函数/变量 | snake_case | `get_hitbox()`, `bullet_damage` |
| 常量 | UPPER_SNAKE_CASE | `SCREEN_WIDTH`, `FPS` |
| 私有成员 | _前缀 | `_mother_ship_integrator` |

### 7.2 函数规范

| 规范 | 目标 |
|------|------|
| 函数长度 | ≤40 行 |
| 嵌套层级 | ≤3 层 |
| 参数数量 | ≤5 个 |

### 7.3 文档规范

- 每个公共类/函数必须有 docstring
- 公共接口必须有类型注解
- 复杂逻辑需要注释说明

---

## 八、快速启动

```bash
# 安装依赖
pip install pygame pytest pillow

# 运行测试
pytest airwar/tests/ -q

# 运行游戏
python main.py
```

---

## 九、相关文档

| 文档 | 说明 |
|------|------|
| `PROJECT_ISSUES.md` | 项目问题追踪与修复 |
| `PROJECT_EVALUATION_REPORT.md` | 项目综合评估报告 |
| `airwar/game/buffs/refactor_docs/` | Buff系统重构文档 |

---

**文档版本**: 2.0
**最后更新**: 2026-04-20
