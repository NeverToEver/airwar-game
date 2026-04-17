# Air War 技术规格文档

> **文档版本**: 1.0
> **日期**: 2026-04-17
> **维护者**: AI Assistant (Trae IDE)

---

## 一、系统架构

### 1.1 核心模块

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
│   ├── controllers/             # 控制器
│   ├── systems/                # 游戏系统
│   └── rendering/              # 渲染系统
├── config/                      # 配置
│   └── settings.py             # 游戏配置
├── ui/                          # UI组件
└── utils/                       # 工具函数
```

### 1.2 架构原则

- **单一职责 (SRP)**: 每个类/模块有明确职责
- **低耦合**: 通过事件总线解耦
- **接口导向**: 依赖抽象接口而非实现
- **可测试性**: 核心逻辑有完整测试覆盖

---

## 二、游戏功能规格

### 2.1 难度系统

| 难度 | 基础伤害 | 敌机速度 | 回血速度 |
|------|----------|----------|----------|
| Easy | 100 | 慢 | 3HP/0.75s (3秒后) |
| Medium | 50 | 中 | 2HP/1s (4秒后) |
| Hard | 34 | 快 | 1HP/1.5s (5秒后) |

### 2.2 天赋系统 (Buffs)

#### 生命类
| 天赋 | 效果 |
|------|------|
| Extra Life | 最大生命+50，当前+30 |
| Regeneration | 回血速度提升至2HP/秒 |
| Lifesteal | 击杀后回复生命 |

#### 攻击类
| 天赋 | 效果 |
|------|------|
| Power Shot | 子弹伤害+25% |
| Rapid Fire | 射击间隔-20% |
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

### 2.3 Boss 系统

**Boss 属性**:
- 生命值: 500 ~ 2000 (根据循环递增)
- 存活时间: 30秒
- 逃跑时间: 根据伤害动态计算

**攻击模式**:
1. 扇形弹幕
2. 追踪弹
3. 全方位弹幕

---

## 三、母舰系统规格

### 3.1 触发机制

**触发方式**: 长按 H 键 3 秒

**状态转换**:
```
IDLE → PRESSING → DOCKING → DOCKED
  ↑                              │
  └── UNDOCKING ←───────────────┘
```

### 3.2 数据持久化

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

### 3.3 事件列表

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

## 四、碰撞检测规格

### 4.1 碰撞盒配置

| 实体 | 碰撞盒尺寸 | 说明 |
|------|------------|------|
| Player | 12x16 | 实际精灵 20x24 |
| Enemy | 50x50 | 含 padding 66x66 |
| Bullet | 动态 | 根据子弹类型 |

### 4.2 碰撞检测算法

**玩家子弹 vs 敌机**:
1. 使用扩展碰撞盒检测
2. 命中后触发涟漪特效
3. 计算范围伤害（如有）

---

## 五、渲染优化规格

### 5.1 SurfaceCache 缓存策略

**缓存类型**:
- 垂直渐变缓存
- 矩形填充/边框缓存
- 粒子光晕缓存
- 精灵绘制缓存
- 文本预渲染缓存

**缓存治理**:
- 按尺寸和量化透明度作为键
- 设置最大条目数限制
- 防止缓存无限增长

### 5.2 性能目标

| 指标 | 目标值 |
|------|--------|
| 游戏 FPS | 稳定 60 FPS |
| 背景渐变渲染 | <0.5ms/帧 |
| Surface 每帧创建 | <20 次 |
| 内存占用 | <100MB |

---

## 六、数据验证规格

### 6.1 存档数据验证

**输入验证规则**:
- 数值字段: 类型转换 + 最小值限制
- difficulty: 仅允许 {easy, medium, hard}
- shot_mode: 仅允许 {normal, spread, laser}
- is_in_mothership: 安全布尔解析
- 字符串: 长度限制 (如 username ≤ 50)

**默认值策略**:
- 无效数据自动回退到可用默认值
- 保持向后兼容

### 6.2 配置常量

```python
# 尺寸常量
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PLAYER_HITBOX_WIDTH = 12
PLAYER_HITBOX_HEIGHT = 16
ENEMY_HITBOX_SIZE = 50
ENEMY_HITBOX_PADDING = 8

# 时间常量
BOSS_SURVIVAL_TIME = 30  # 秒
HOLD_TO_DOCK_DURATION = 3  # 秒
DOCKING_ANIMATION_FRAMES = 90
UNDOCKING_ANIMATION_FRAMES = 60

# 难度设置
DIFFICULTY_SETTINGS = {
    'easy': {'base_damage': 100, 'enemy_speed': 2},
    'medium': {'base_damage': 50, 'enemy_speed': 3},
    'hard': {'base_damage': 34, 'enemy_speed': 4},
}
```

---

## 七、测试规格

### 7.1 测试覆盖目标

| 模块 | 覆盖率目标 |
|------|-----------|
| mother_ship | ≥80% |
| entities | ≥70% |
| reward_system | ≥75% |
| 全局 | ≥85% |

### 7.2 测试执行

```bash
# 语法检查
python -m compileall airwar

# 全量测试
SDL_VIDEODRIVER=dummy pytest -q

# 覆盖率报告
pytest airwar/tests/ --cov=airwar --cov-report=html
```

---

## 八、代码规范

### 8.1 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `GameScene`, `MotherShipStateMachine` |
| 函数/变量 | snake_case | `get_hitbox()`, `bullet_damage` |
| 常量 | UPPER_SNAKE_CASE | `SCREEN_WIDTH`, `FPS` |
| 私有成员 | _前缀 | `_mother_ship_integrator` |

### 8.2 函数规范

| 规范 | 目标 |
|------|------|
| 函数长度 | ≤40 行 |
| 嵌套层级 | ≤3 层 |
| 参数数量 | ≤5 个 |

### 8.3 文档规范

- 每个公共类/函数必须有 docstring
- 公共接口必须有类型注解
- 复杂逻辑需要注释说明

---

## 九、已知问题与限制

### 9.1 已知问题

| 问题 | 影响 | 状态 |
|------|------|------|
| SceneDirector 职责过多 | 可维护性 | 计划中重构 |
| 部分函数过长 | 可读性 | 持续优化 |

### 9.2 设计局限

- 游戏存档可被篡改（设计决策）
- 使用 SHA256 密码哈希（非生产级安全）

---

## 十、参考文档

| 文档 | 说明 |
|------|------|
| `PROJECT-MILESTONES.md` | 项目里程碑记录 |
| `TEST_CHECKLIST.md` | 功能测试清单 |
| `README.md` | 项目主文档 |

---

**文档结束**

*本文档定义了 Air War 项目的技术规格，是开发工作的主要参考文档。*
