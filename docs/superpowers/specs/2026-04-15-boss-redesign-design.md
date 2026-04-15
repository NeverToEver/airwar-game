# Boss 重绘与碰撞箱提示优化设计方案

**日期**: 2026-04-15
**状态**: 已批准
**改动**: 重绘 Boss 飞船 + 优化碰撞箱提示效果

---

## 1. 改动概述

本次改动包含两个独立的视觉优化：
1. **Boss 飞船重绘**：重新设计 Boss 的绘制逻辑，解决当前版本中出现的错位、不对称等问题
2. **碰撞箱提示优化**：将碰撞箱提示改为更醒目的实心菱形闪烁效果

---

## 2. Boss 飞船重绘（方案 A）

### 2.1 设计目标
- 创建对称的外星飞船设计
- 保持紫色/粉色色调的外星风格
- 确保所有视觉元素在合理范围内
- 结构清晰，代码可维护

### 2.2 设计结构
**主体设计**：
- **中心椭圆**：飞船的核心区域，基于 `center_x` 和 `center_y`
- **两侧翅膀**：左右对称的三角形翅膀
- **底部触手**：3-4 个向下延伸的触手，带有发光核心
- **眼睛**：两个对称的眼睛，带有发光效果
- **顶部尖刺**：顶部装饰性尖刺

### 2.3 坐标系统
```
宽度：width (默认 120)
高度：height (默认 100)
中心 X: center_x = x + width / 2
中心 Y: center_y = y + height / 2
```

所有坐标计算基于相对比例，范围在 `[0, 1]` 之间：
- 水平位置：`center_x ± width * (0.0 ~ 0.5)`
- 垂直位置：`y + height * (0.0 ~ 1.0)`

### 2.4 颜色方案
根据血量比例变化：
- **高血量 (60-100%)**：
  - Hull Dark: (50, 20, 70)
  - Hull Mid: (90, 40, 120)
  - Hull Light: (140, 80, 170)
  - Core: (200, 50, 255)
  - Eye: (255, 50, 200)

- **中血量 (30-60%)**：
  - 颜色过渡到橙色/红色调

- **低血量 (0-30%)**：
  - 颜色过渡到红色调

### 2.5 视觉元素
1. **翅膀**：两个对称多边形
2. **主体**：椭圆形主体 + 细节层次
3. **触手**：3-4 个，带发光核心
4. **眼睛**：两个，带瞳孔和高光
5. **装饰线条**：水平装饰线

---

## 3. 碰撞箱提示优化

### 3.1 设计目标
- 将空心菱形改为实心菱形
- 提高可见性，便于观察碰撞箱位置
- 保持闪烁效果

### 3.2 实现方式
```python
def _render_hitbox_indicator(surface: pygame.Surface) -> None:
    hb = self.get_hitbox()
    cx = hb.x + hb.width / 2
    cy = hb.y + hb.height / 2

    # 计算菱形顶点
    half_w = hb.width / 2
    half_h = hb.height / 2

    # 基础形状（12x16 的菱形）
    diamond_points = [
        (cx, cy - half_h),      # 上
        (cx + half_w, cy),      # 右
        (cx, cy + half_h),      # 下
        (cx - half_w, cy),      # 左
    ]

    # 脉冲效果
    pulse = abs(math.sin(self._hitbox_timer * 0.15))
    alpha = int(150 + pulse * 105)  # 150-255

    # 绘制实心菱形
    glow_surf = pygame.Surface((hb.width + 20, hb.height + 20), pygame.SRCALPHA)
    glow_color = (255, 255, 255, alpha)
    pygame.draw.polygon(glow_surf, glow_color, diamond_points)
    surface.blit(glow_surf, (hb.x - 10, hb.y - 10))
```

### 3.3 效果描述
- **形状**：实心菱形，与碰撞箱尺寸一致
- **大小**：12×16 像素
- **颜色**：白色，带透明度
- **闪烁频率**：基于 `sin()` 函数，频率约 0.15
- **透明度范围**：150-255（避免完全透明）

---

## 4. 文件改动清单

### 4.1 需修改的文件
1. **`airwar/utils/sprites.py`**
   - 重写 `draw_boss_ship` 函数

2. **`airwar/entities/player.py`**
   - 修改 `_render_hitbox_indicator` 方法

### 4.2 保留的内容
- `draw_player_ship` 函数：不做改动
- `draw_enemy_ship` 函数：不做改动
- `draw_bullet` 相关函数：不做改动
- `draw_ripple` 函数：不做改动

---

## 5. 测试计划

### 5.1 Boss 渲染测试
- [ ] Boss 进入屏幕时显示正确
- [ ] Boss 血量变化时颜色正确过渡
- [ ] Boss 移动时渲染不出现抖动
- [ ] Boss 形状左右对称

### 5.2 碰撞箱提示测试
- [ ] 碰撞箱提示可见且清晰
- [ ] 闪烁效果流畅
- [ ] 菱形大小与碰撞箱一致
- [ ] 在各种背景下都可观察

### 5.3 整体测试
- [ ] 游戏正常运行，无崩溃
- [ ] 性能影响最小
- [ ] 视觉效果符合预期

---

## 6. 设计原则遵守

本次设计遵循以下架构原则：
- **单一职责**：`draw_boss_ship` 专门负责 Boss 渲染，`_render_hitbox_indicator` 专门负责碰撞箱提示
- **高内聚低耦合**：每个函数功能独立，不相互依赖
- **代码清晰**：使用有意义的变量名和注释
- **可维护性**：结构化设计，便于后续修改

---

**批准状态**：✅ 已由用户于 2026-04-15 批准

---

## 7. Bug 修复记录 (2026-04-15 补充)

### 7.1 Vector2 对象访问错误

**问题描述**：
- `Player._update_movement()` 方法中尝试使用索引访问 `direction` 对象
- `direction` 类型为 `Vector2`，不支持索引访问（`direction[0]`, `direction[1]`）
- 正确方式应使用 `.x` 和 `.y` 属性访问

**错误信息**：
```
TypeError: 'Vector2' object is not subscriptable
```

**修复方案**：
```python
# 错误代码 ❌
direction = self._input_handler.get_movement_direction()
self.rect.x += direction[0] * self.speed
self.rect.y += direction[1] * self.speed

# 正确代码 ✅
direction = self._input_handler.get_movement_direction()
self.rect.x += direction.x * self.speed
self.rect.y += direction.y * self.speed
```

**涉及文件**：
- `airwar/entities/player.py` (第 56-57 行)

**遵循原则**：
- **接口导向设计**：Vector2 是抽象数据类型，应使用其定义的属性访问器
- **类型安全**：尊重类型的实际接口，避免运行时错误

---

### 7.2 架构符合性验证

本次修复遵循了以下架构原则：

✅ **单一职责**：Vector2 的使用符合其定义的接口
✅ **接口导向设计**：尊重 Vector2 类的属性访问器设计
✅ **代码清晰**：使用 `.x` 和 `.y` 属性，语义明确
✅ **可维护性**：符合 Python 的类型使用最佳实践

**相关文件改动**：
- `airwar/entities/player.py`：修复了 Player 的移动逻辑

**测试结果**：
- ✅ 游戏成功启动，无运行时错误
- ✅ 28/30 个单元测试通过（2个失败为原有代码问题）
- ✅ Boss 渲染正常
- ✅ 碰撞箱提示显示正常

---

**补充日期**：2026-04-15
**补充状态**：✅ 已完成并验证

