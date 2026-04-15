# Air War 游戏优化待办清单

**日期**: 2026-04-15
**状态**: 待处理
**优先级**: 高

---

## 1. 概述

本文档记录了 Air War 游戏当前待优化的功能点和技术债务，基于架构规范（architecture-enforcer）进行问题分析和优化建议。

---

## 2. 待优化功能清单

### 2.1 Boss 全向攻击功能 ❌ 未实现

**问题描述**：
- Boss 目前只会朝一个方向进行攻击
- 缺少上下左右全向攻击的实现
- 射击模式可能是硬编码的单一方向

**预期行为**：
- Boss 应该能够向多个方向发射子弹
- 可能需要实现不同的攻击模式（如：扇形射击、集中射击、随机射击）
- 攻击频率和方向应该与 Boss 血量相关

**涉及文件**：
- `airwar/entities/enemy.py` - Boss 实体类
- `airwar/entities/bullet.py` - 子弹实体
- `airwar/game/spawners/` - Boss 子弹生成器

**架构规范检查点**：
- [ ] Boss 的攻击逻辑是否遵循单一职责原则？
- [ ] 子弹生成是否通过接口抽象？
- [ ] 攻击模式是否可以配置和扩展？

**待办任务**：
- [ ] 检查 Boss 的当前攻击实现
- [ ] 设计攻击模式接口（Strategy Pattern）
- [ ] 实现至少 3 种不同的攻击模式
- [ ] 根据 Boss 血量动态调整攻击模式
- [ ] 编写测试用例验证攻击模式切换

---

### 2.2 碰撞箱闪烁提示功能 ⚠️ 可能有问题

**问题描述**：
- 碰撞箱闪烁提示可能还未完全生效
- 需要验证 `_render_hitbox_indicator()` 是否被正确调用
- 需要检查闪烁效果的可见性

**当前实现**（根据最近修复）：
```python
def render(self, surface: pygame.Surface) -> None:
    # 绘制玩家飞船
    draw_player_ship(surface, self.rect.x, self.rect.y, ...)
    
    # 渲染碰撞箱提示
    self._render_hitbox_indicator(surface)
    
    # 渲染子弹
    for bullet in self._bullets:
        bullet.render(surface)
```

**预期行为**：
- 碰撞箱应该显示为实心菱形
- 菱形大小应该与碰撞箱一致（12×16 像素）
- 颜色应该为白色高亮，带透明度
- 应该通过 alpha 值实现明暗闪烁（频率约 0.15）

**涉及文件**：
- `airwar/entities/player.py` - Player 实体类
- `airwar/entities/base.py` - 基础实体类

**架构规范检查点**：
- [ ] `_render_hitbox_indicator()` 方法是否超过 40 行？
- [ ] 闪烁效果的计算是否有硬编码的魔法数字？
- [ ] 是否遵循了单一职责原则？

**待办任务**：
- [ ] 运行游戏验证碰撞箱提示是否可见
- [ ] 检查闪烁效果是否流畅
- [ ] 验证菱形大小和颜色是否正确
- [ ] 检查是否有性能问题（每帧创建 Surface）
- [ ] 考虑将 Surface 缓存以提高性能

---

## 3. 代码质量审查清单

### 3.1 健壮性检查

#### 3.1.1 异常处理 ❌ 未检查

**问题领域**：
- [ ] `airwar/entities/player.py` - Player 类
- [ ] `airwar/entities/enemy.py` - Enemy 类
- [ ] `airwar/entities/bullet.py` - Bullet 类
- [ ] `airwar/scenes/game_scene.py` - 游戏场景

**检查项**：
- [ ] 是否所有公开方法都有输入验证？
- [ ] 是否处理了 None 值和边界情况？
- [ ] 是否有 try-except 块处理可能的异常？
- [ ] 错误消息是否清晰且有意义？

**示例问题**：
```python
# ❌ 没有验证
def take_damage(self, damage: int) -> None:
    self.health -= damage

# ✅ 有验证
def take_damage(self, damage: int) -> None:
    if damage < 0:
        raise ValueError("Damage cannot be negative")
    self.health = max(0, self.health - damage)
```

---

#### 3.1.2 类型安全 ❌ 未检查

**问题领域**：
- [ ] 所有实体类的属性类型
- [ ] 接口定义的参数和返回值
- [ ] 配置文件的类型

**检查项**：
- [ ] 是否使用了类型注解（Type Hints）？
- [ ] 是否有一致的类型使用？
- [ ] 是否有类型转换需要注意？

---

#### 3.1.3 资源管理 ⚠️ 部分处理

**问题领域**：
- [ ] pygame.Surface 的创建和释放
- [ ] 文件资源的加载
- [ ] 内存中的实体列表管理

**检查项**：
- [ ] 是否正确清理了不再使用的 Surface？
- [ ] 实体列表是否有及时的清理机制？
- [ ] 是否有可能的内存泄漏？

---

### 3.2 冗余度检查

#### 3.2.1 重复代码 ❌ 未检查

**架构规范要求**：
> 重复代码（3+ occurrences）必须提取到工具函数或基类中

**可能存在的重复**：
- [ ] 碰撞检测逻辑
- [ ] 实体更新逻辑
- [ ] 子弹移动和边界检查
- [ ] 伤害计算逻辑

**检查工具**：
```bash
# 使用 IDE 或工具检查重复代码
- PyCharm: Code > Locate Duplicates
- VS Code: Search "duplicate code" extensions
- 手动审查：查找相似的代码块
```

---

#### 3.2.2 魔法数字 ❌ 未检查

**架构规范要求**：
> 所有常量必须命名，避免魔法数字

**已识别的魔法数字**：
- [ ] `fire_cooldown = 8` - 应该使用配置常量
- [ ] 伤害值 `20`, `30` 等 - 应该使用配置
- [ ] 速度值 - 应该使用配置
- [ ] 屏幕尺寸 - 部分已配置
- [ ] 碰撞箱大小 `12×16` - 应该使用配置

**待办任务**：
- [ ] 审查所有硬编码的数字
- [ ] 提取到 `airwar/config/` 中的常量
- [ ] 使用有意义的命名

---

#### 3.2.3 深层嵌套 ❌ 未检查

**架构规范要求**：
> 最多 3 层嵌套，使用早返回和卫语句

**检查项**：
- [ ] 是否存在 4 层以上的 if 语句嵌套？
- [ ] 是否使用了早返回模式？
- [ ] 是否有可以简化的复杂条件？

**反模式示例**：
```python
# ❌ 深层嵌套（4层）
def update(self):
    if self.active:
        if self.health > 0:
            if self.can_attack:
                if self.cooldown <= 0:
                    self.attack()

# ✅ 早返回（2层）
def update(self):
    if not self.active or self.health <= 0:
        return
    if not self.can_attack or self.cooldown > 0:
        return
    self.attack()
```

---

#### 3.2.4 过长函数 ❌ 未检查

**架构规范要求**：
> 函数不应超过约 40 行，超过必须拆分

**检查项**：
- [ ] `airwar/scenes/game_scene.py` - `_update_game()` 是否过长？
- [ ] `airwar/entities/player.py` - `render()` 是否过长？
- [ ] 实体更新方法是否过长？
- [ ] 碰撞检测方法是否过长？

**待办任务**：
- [ ] 统计每个函数的行数
- [ ] 识别超过 40 行的函数
- [ ] 提取辅助方法
- [ ] 重构复杂逻辑

---

### 3.3 架构合规性检查

#### 3.3.1 单一职责原则 ❌ 未系统检查

**检查项**：
- [ ] 每个类是否只有一个明确的职责？
- [ ] 方法是否遵循单一职责？
- [ ] 是否有 God Class（做所有事情的类）？

**高风险类**：
- [ ] `Player` 类 - 可能混合了移动、射击、状态管理
- [ ] `GameScene` 类 - 可能混合了多个系统的协调
- [ ] `GameController` 类 - 需要审查其职责范围

---

#### 3.3.2 接口一致性 ❌ 已部分检查

**检查项**：
- [ ] `InputHandler` 接口的所有实现是否一致？
- [ ] 实体基类的所有子类是否遵循相同接口？
- [ ] 是否有接口定义但未实现的方法？

**当前接口**：
```python
# InputHandler
- get_movement_direction() -> Vector2
- is_pause_pressed() -> bool

# Entity (基类)
- update()
- render(surface)
- get_hitbox() -> Rect
```

---

#### 3.3.3 耦合度 ❌ 未系统检查

**架构规范要求**：
> 模块间通过接口通信，不直接访问内部状态

**检查项**：
- [ ] 是否有模块直接访问其他模块的私有属性？
- [ ] 是否所有依赖都通过构造函数注入？
- [ ] 是否有循环依赖？

**高耦合警告**：
- [ ] `game_scene.py` 是否过度依赖 `player` 的内部实现？
- [ ] 子弹创建是否应该通过接口抽象？

---

## 4. 性能优化建议

### 4.1 渲染性能 ⚠️ 需要关注

**问题点**：
- [ ] `_render_hitbox_indicator()` 每帧创建新 Surface
- [ ] 子弹渲染可能创建多个 Surface
- [ ] 可能存在重复的绘制操作

**优化建议**：
```python
# ❌ 每帧创建新 Surface
def _render_hitbox_indicator(self, surface):
    glow_surf = pygame.Surface((hb.width + 20, ...), pygame.SRCALPHA)
    pygame.draw.polygon(glow_surf, ...)
    surface.blit(glow_surf, ...)

# ✅ 缓存 Surface
def __init__(self, ...):
    self._hitbox_surf_cache = None

def _render_hitbox_indicator(self, surface):
    if self._hitbox_surf_cache is None:
        self._hitbox_surf_cache = pygame.Surface(...)
    # 使用缓存的 Surface
```

---

### 4.2 更新性能 ❌ 未检查

**检查项**：
- [ ] 实体列表更新是否有冗余遍历？
- [ ] 碰撞检测是否有优化空间（空间分区）？
- [ ] 是否每帧都进行不必要的计算？

---

## 5. 测试覆盖度 ❌ 未检查

### 5.1 单元测试 ⚠️ 部分完成

**当前状态**：
- 约 150 个测试用例通过
- 但测试可能未覆盖所有边界情况

**待办任务**：
- [ ] 添加边界情况测试（负数、零、超大值）
- [ ] 添加异常情况测试（None 值、无效输入）
- [ ] 添加性能基准测试
- [ ] 添加集成测试覆盖关键流程

---

### 5.2 测试质量 ❌ 未检查

**检查项**：
- [ ] 测试是否真正验证了功能？
- [ ] 测试是否依赖实现细节？
- [ ] 测试命名是否清晰描述意图？
- [ ] 是否有测试的测试（测试测试）？

---

## 6. 文档缺失清单

### 6.1 代码文档 ❌ 未完成

**缺失文档**：
- [ ] 所有公开方法的文档字符串
- [ ] 类和模块的 docstring
- [ ] 复杂算法的注释说明

**示例**：
```python
def fire(self) -> Optional[Bullet]:
    """
    Fire a bullet from the player.
    
    Returns:
        Bullet: The created bullet, or None if on cooldown
        
    Raises:
        No exceptions
        
    Note:
        This method sets the cooldown timer to prevent
        rapid fire. The cooldown duration is defined in config.
    """
    pass
```

---

### 6.2 架构文档 ⚠️ 部分完成

**已有文档**：
- [x] `2026-04-14-airwar-refactoring-design.md` - 架构重构设计
- [x] `2026-04-15-boss-redesign-design.md` - Boss 重绘设计

**缺失文档**：
- [ ] 游戏循环和数据流图
- [ ] 实体关系图（ER Diagram）
- [ ] 碰撞检测系统设计
- [ ] 奖励系统设计
- [ ] Boss 攻击模式设计

---

## 7. 优先级排序

### 高优先级（P0）🔴

1. **[ ] Boss 全向攻击功能** - 核心游戏功能缺失
2. **[ ] 碰撞箱闪烁提示验证** - 需要确认是否正常工作
3. **[ ] 魔法数字提取** - 影响代码可维护性

### 中优先级（P1）🟡

4. **[ ] 健壮性检查** - 添加输入验证和异常处理
5. **[ ] 过长函数重构** - 提高代码可读性
6. **[ ] 重复代码提取** - 降低维护成本

### 低优先级（P2）🟢

7. **[ ] 性能优化** - 缓存 Surface
8. **[ ] 测试覆盖度提升** - 添加边界情况测试
9. **[ ] 代码文档完善** - 添加 docstring

---

## 8. 下一步行动

### 立即行动（今天）
1. [ ] 验证碰撞箱闪烁提示是否正常工作
2. [ ] 检查 Boss 当前的攻击实现
3. [ ] 识别所有魔法数字

### 本周行动
1. [ ] 实现 Boss 全向攻击功能
2. [ ] 提取所有魔法数字到配置
3. [ ] 添加健壮性检查

### 持续改进
1. [ ] 每日代码审查
2. [ ] 每周测试覆盖率检查
3. [ ] 每月架构合规性审计

---

## 9. 附录

### A. 相关文件路径

```
airwar/
├── entities/
│   ├── player.py          # Player 实体
│   ├── enemy.py          # Enemy 和 Boss 实体
│   ├── bullet.py          # Bullet 实体
│   └── base.py           # 基类
├── scenes/
│   └── game_scene.py     # 游戏场景
├── config/
│   └── settings.py        # 配置文件
├── input/
│   └── input_handler.py   # 输入处理
└── utils/
    └── sprites.py         # 精灵绘制
```

### B. 架构规范参考

详见：`d:\Trae\pygames_dev\.trae\skills\architecture-enforcer`

**关键原则**：
- 单一职责（SRP）
- 接口导向设计
- 高内聚低耦合
- 代码清晰简洁
- 避免 Shotgun Surgery

### C. 联系方式

如有问题或建议，请联系开发团队。

---

**文档版本**：1.0
**最后更新**：2026-04-15
**维护者**：AI Assistant (Claude)
**批准状态**：待批准
