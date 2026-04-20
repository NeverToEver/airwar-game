# AIRWAR 项目变更日志

> **文档版本**: 3.2
> **最后更新**: 2026-04-20
> **维护者**: AI Assistant (Trae IDE)

---

## 版本历史概览

| 版本 | 日期 | 类型 | 主要变更 |
|------|------|------|----------|
| [3.2](#v32-2026-04-20) | 2026-04-20 | 优化 | Phase 2&3优化、测试增强 |
| [3.1](#v31-2026-04-20) | 2026-04-20 | 增强 | Buff系统重构 |
| [3.0](#v30-2025-01-xx) | 2025-01-XX | 合并 | 文档整合 |
| [2.0](#v20-2026-04-20) | 2026-04-20 | 审核 | 添加问题追踪和评估报告 |
| [1.0](#v10-2026-04-19) | 2026-04-19 | 初始 | 初始项目文档 |

---

## v3.2 (2026-04-20)

**类型**: 优化版本
**状态**: 最新版本

### 新增功能

#### 1. 错误处理增强

**文件**: `airwar/scenes/game_scene.py`

- 在 `_update_game()` 方法中添加了完整的 try-except 错误处理
- 在 `_check_collisions()` 方法中添加了异常捕获和日志记录
- 确保游戏异常不会导致程序崩溃，而是优雅地停止游戏

**影响**: 提高了游戏的健壮性和可调试性

#### 2. 配置常量统一管理

**文件**: `airwar/game/constants.py`

- 新增 `EXPLOSIVE_DAMAGE` 常量定义 (值: 30)
- 统一管理所有伤害相关常量
- 便于后期游戏平衡调整

**常量列表**:
```python
class DamageConstants:
    BOSS_COLLISION_DAMAGE: int = 30
    ENEMY_COLLISION_DAMAGE: int = 20
    EXPLOSIVE_DAMAGE: int = 30
    DEFAULT_REGEN_RATE: int = 2
    REGEN_THRESHOLD: int = 60
```

#### 3. 配置导出完善

**文件**: `airwar/config/settings.py`

- 新增 `EXPLOSION_RADIUS = 50` 常量
- 用于爆炸Buff的范围伤害计算

**文件**: `airwar/config/__init__.py`

- 将 `EXPLOSION_RADIUS` 添加到 `__all__` 导出列表
- 保持配置导出的一致性

### 代码优化

#### 1. 代码清理

**文件**: `airwar/scenes/game_scene.py`

- 删除了重复的 `_on_boss_hit` 方法
- 保留了功能更完整的版本（包含 `_clear_enemy_bullets()` 调用）
- 减少了代码重复，提高了可维护性

#### 2. 常量使用

**文件**: `airwar/game/controllers/collision_controller.py`

- 将硬编码的爆炸伤害值替换为常量 `GAME_CONSTANTS.DAMAGE.EXPLOSIVE_DAMAGE`
- 遵循统一配置管理原则

**优化前**:
```python
explosion_damage = 30 * explosive_level
```

**优化后**:
```python
from airwar.game.constants import GAME_CONSTANTS
explosion_damage = GAME_CONSTANTS.DAMAGE.EXPLOSIVE_DAMAGE * explosive_level
```

### 测试增强

#### 1. 新增集成测试

**文件**: `airwar/tests/test_collision_integration.py`

新增以下集成测试用例：
- `test_player_bullets_vs_enemies_collision` - 玩家子弹与敌人碰撞
- `test_enemy_bullets_vs_player_collision` - 敌人子弹与玩家碰撞
- `test_player_vs_enemies_collision` - 玩家与敌人直接碰撞
- `test_boss_vs_player_collision` - Boss与玩家碰撞
- `test_explosive_damage` - 爆炸伤害测试
- `test_full_collision_sequence` - 完整碰撞序列测试

#### 2. 新增性能测试

**文件**: `airwar/tests/test_performance.py`

新增以下性能测试用例：
- `test_collision_detection_performance_small_scale` - 小规模碰撞检测性能 (10x10)
- `test_collision_detection_performance_medium_scale` - 中等规模碰撞检测性能 (50x50)
- `test_collision_detection_performance_large_scale` - 大规模碰撞检测性能 (100x100)
- `test_bullet_update_performance` - 子弹更新性能
- `test_explosive_damage_performance` - 爆炸伤害性能

**性能基准**:
| 测试类型 | 性能目标 | 数据规模 |
|----------|----------|----------|
| 小规模碰撞检测 | < 1.0ms | 10x10 |
| 中等规模碰撞检测 | < 10.0ms | 50x50 |
| 大规模碰撞检测 | < 16.0ms | 100x100 |
| 子弹更新 | < 5.0ms | 100子弹 |
| 爆炸伤害 | < 2.0ms | 50敌人 |

### 测试统计

**当前测试状态**:
- 总测试数: 314
- 通过测试: 307
- 跳过测试: 7
- 失败测试: 0

### 代码审查发现

**审查文件**: `docs/archives/phase2-code-review-2026-04-20.md`

| 问题 | 状态 | 优先级 |
|------|------|--------|
| 重复的 `_on_boss_hit` 方法 | ✅ 已修复 | 高 |
| error handling imports inside try blocks | ⏳ 待修复 | 低 |

### 架构改进

#### 1. 错误处理架构

```python
try:
    has_regen = 'Regeneration' in self.reward_system.unlocked_buffs
    self.game_controller.update(self.player, has_regen)
    # ... 更多逻辑
except Exception as e:
    import logging
    logging.error(f"Game update error: {e}", exc_info=True)
    self.game_controller.state.running = False
```

**优势**:
- 异常不会导致游戏崩溃
- 错误信息被记录到日志
- 游戏状态被安全地设置为非运行状态

#### 2. 配置管理架构

```
airwar/game/constants.py
├── PlayerConstants (玩家相关)
├── DamageConstants (伤害相关)
├── AnimationConstants (动画相关)
└── GameBalanceConstants (游戏平衡相关)
```

### 向后兼容性

**破坏性变更**: 无

**注意事项**:
1. **常量使用**: 代码现在使用 `GAME_CONSTANTS.DAMAGE.EXPLOSIVE_DAMAGE` 替代硬编码值
2. **错误处理**: 游戏异常现在会被捕获并记录，但不会导致崩溃
3. **配置导出**: `EXPLOSION_RADIUS` 现在可从 `airwar.config` 导入

### 迁移指南

#### 对于使用爆炸伤害的代码

```python
# 旧代码
explosion_damage = 30 * explosive_level

# 新代码
from airwar.game.constants import GAME_CONSTANTS
explosion_damage = GAME_CONSTANTS.DAMAGE.EXPLOSIVE_DAMAGE * explosive_level
```

#### 对于使用爆炸半径的代码

```python
# 旧代码
# 需要自己定义 EXPLOSION_RADIUS

# 新代码
from airwar.config import EXPLOSION_RADIUS
# EXPLOSION_RADIUS = 50
```

---

## v3.1 (2026-04-20)

**类型**: 增强版本

### Buff系统重构

#### 完成内容

- ✅ PowerShot累积伤害bug修复
- ✅ RapidFire双重缩减修复
- ✅ UI状态显示增强
- ✅ Buff无状态化重构

#### 新架构

```
RewardSystem (唯一状态源)
    ↓
Buff (无状态, 定义计算公式)
    ↓
Player (只读属性)
    ↓
UI (展示状态)
```

#### 关键修复

##### 问题1: PowerShotBuff累积性伤害bug (已修复)

**问题描述**: 每次应用PowerShot奖励时，直接将当前 `player.bullet_damage` 乘以1.25，造成指数级增长。

**解决方案**: 引入 `calculate_value(base_value, level)` 方法，每次升级基于基础值计算：

```python
def calculate_value(self, base_value: int, current_level: int) -> int:
    return int(base_value * (1.25 ** current_level))
```

##### 问题2: RapidFireBuff双重缩减机制 (已修复)

**问题描述**: 冷却缩减被Buff层和RewardSystem层双重计算。

**解决方案**: 移除Buff层的冷却缩减，只由RewardSystem统一计算。

#### 验收结果

| 验收项 | 状态 |
|--------|------|
| Power Shot 每次升级伤害增加固定25%（基于基础值） | ✅ 已验证 |
| Rapid Fire 每次升级冷却减少固定20% | ✅ 已验证 |
| UI正确显示已拥有奖励的等级 | ✅ 已实现 |
| 所有现有测试通过 | ✅ 274/274通过 |
| 新增测试覆盖重构逻辑 | ✅ 已完成 |

#### 关键文件清单

| 文件 | 操作 | 描述 |
|------|------|------|
| `buffs/base_buff.py` | ✅ 已修改 | 添加calculate_value等接口 |
| `buffs/buffs.py` | ✅ 已重构 | 所有17个Buff类实现新接口 |
| `systems/reward_system.py` | ✅ 已重构 | 统一状态管理和计算 |
| `ui/reward_selector.py` | ✅ 已修改 | 增强状态显示 |
| `tests/test_buffs.py` | ✅ 已更新 | 新增接口测试 |

---

## v3.0 (2025-01-XX)

**类型**: 合并版本

### 文档整合

- ✅ 合并所有文档，统一格式
- ✅ 添加Buff系统重构详解
- ✅ 更新版本历史

---

## v2.0 (2026-04-20)

**类型**: 审核版本

### 添加内容

- ✅ 问题追踪
- ✅ 评估报告
- ✅ 修复进度

---

## v1.0 (2026-04-19)

**类型**: 初始版本

### 初始项目文档

- ✅ 项目概述
- ✅ 技术栈
- ✅ 架构设计
- ✅ 核心功能
- ✅ 测试清单

---

## 里程碑记录

### 里程碑 6: 保存并退出功能 (2025-01-XX)

**目标**: 实现三种退出机制

**完成内容**:
- ✅ 保存并退出 (SAVE AND QUIT)
- ✅ 不保存并退出 (QUIT WITHOUT SAVING)
- ✅ 保留现有直接退出功能
- ✅ 完整的架构评审

### 里程碑 5: Buff系统重构 (2026-04-20)

**目标**: 修复Buff累积计算bug，统一奖励系统

**完成内容**:
- ✅ PowerShot累积伤害bug修复
- ✅ RapidFire双重缩减修复
- ✅ UI状态显示增强
- ✅ Buff无状态化重构

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

### 里程碑 2: 母舰停靠系统 (2026-04-15~16)

**目标**: 实现母舰召唤、停靠、存档功能

**完成内容**:
- ✅ H键长按(3秒)触发母舰召唤
- ✅ 平滑进入/离开动画
- ✅ 游戏状态持久化
- ✅ 状态机完整实现

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

## 历史问题追踪

### 问题统计总览

| 严重程度 | 数量 | 已修复 | 待评估 |
|---------|------|--------|--------|
| P0 - 紧急 | 1 | 1 | 0 |
| P1 - 重要 | 1 | 1 | 0 |
| P2 - 优化 | 2 | 1 | 1 |
| **总计** | **4** | **3** | **1** |

### 已识别问题列表

| Issue ID | 问题标题 | 优先级 | 状态 | 影响模块 |
|----------|---------|--------|------|---------|
| #001 | Boss自然逃跑后快速生成 | P0 | ✅ 已修复 | Boss生成系统 |
| #002 | Boss逃跑惩罚机制缺失 | P1 | ✅ 已修复 | 游戏平衡 |
| #003 | Boss状态管理分散 | P2 | ✅ 已修复 | 代码架构 |
| #004 | cycle_count在逃跑时未更新 | P2 | ⚠️ 待评估 | 游戏进度 |

### Issue #001: Boss自然逃跑后快速生成问题

**问题现象**:
- 理论生成间隔：30 秒（1800 帧 @ 60 FPS）
- 实际生成间隔：约 13 秒（800 帧）
- 间隔缩短比例：57%

**根本原因**: 计时器状态不同步

**修复方案**:
```python
def reset_boss_timer(self, penalty: bool = False) -> None:
    self.boss_spawn_timer = 0
    if penalty:
        self.boss_spawn_interval = int(self._base_boss_spawn_interval * self._escape_penalty_multiplier)
```

**修复效果**:
| 指标 | 修复前 | 修复后 |
|------|-------|-------|
| Boss 生成间隔（逃跑后） | ~13 秒 | 45 秒 |
| 惩罚延迟 | 无 | 1.5x 基础间隔 |
| Boss 清理位置 | 3 处分散 | 1 处集中 |

### Issue #004: cycle_count在逃跑时未更新

**状态**: ⚠️ 待评估

**问题描述**: 当Boss被击杀时，`game_controller.cycle_count += 1`会增加游戏进度。当Boss逃跑时，这个计数器不会增加。

**建议方案**:
- **方案A**: 逃跑时也增加cycle_count（平衡性可能受影响）
- **方案B**: 保持现状（当前实现）- 逃跑不增加进度是合理的惩罚机制

---

## 相关文档

- [AIRWAR_PROJECT_DOCUMENTATION.md](AIRWAR_PROJECT_DOCUMENTATION.md) - 项目完整文档
- [docs/archives/](docs/archives/) - 历史文档归档

---

**最后更新**: 2026-04-20
**维护者**: AI Assistant (Trae IDE)
**版本**: 3.2
