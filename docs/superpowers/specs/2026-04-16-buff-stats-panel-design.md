# 2026-04-16 技术更新文档 - 侧边统计栏功能

## 更新日期: 2026-04-16

---

## 1. 功能概述

### 1.1 功能名称
侧边Buff统计栏 (Buff Stats Panel)

### 1.2 功能描述
在游戏进行过程中，于屏幕右侧显示实时生效的Buff信息统计栏。该功能以非侵入式设计提供实时战斗数据展示，不干扰玩家操作和游戏视野。

### 1.3 需求来源
用户反馈需要更清晰地了解当前生效的所有Buff及其数值效果，特别是在多Buff叠加时难以直观了解总体效果。

---

## 2. 设计方案

### 2.1 视觉设计原则

#### 2.1.1 非侵入式设计
- **位置**: 屏幕右侧边缘，距右边界15像素
- **垂直位置**: 居中显示，超出屏幕顶部时自动调整至距顶50像素
- **透明度**: 背景alpha值25-30，确保不完全遮挡游戏画面
- **边框**: 1像素宽，低透明度边框以界定区域

#### 2.1.2 尺寸规格
| 参数 | 值 |
|------|-----|
| 面板宽度 | 160像素 |
| 内边距 | 10像素 |
| 单项高度 | 28像素 |
| 项间距 | 4像素 |
| 汇总区高度 | 50像素 |
| 圆角半径 | 8像素 |

#### 2.1.3 配色方案
- **背景色**: `(15, 15, 30, 25)` - 深蓝黑色，极低透明度
- **边框色**: `(60, 60, 90, 80)` - 蓝灰色
- **标题色**: `(180, 180, 210)` - 浅蓝灰色
- **汇总区背景**: `(20, 20, 40, 30)` - 略深于主背景

### 2.2 功能设计

#### 2.2.1 数据显示内容
1. **Buff名称**: 使用4字母缩写显示
   - 例如: "PWR"(Power Shot), "RPD"(Rapid Fire), "PIR"(Piercing)

2. **Buff等级**: 适用于可叠加Buff
   - 显示格式: `x{N}` (例如: x2, x3)

3. **具体数值**: 根据Buff类型显示实际数值
   - 伤害加成: `+25%`
   - 护甲减免: `-15%`
   - 闪避率: `+20%`
   - 射速加成: `+20%`

4. **模式状态**: 用于特殊模式Buff
   - 显示: "ON" 或 "-"

#### 2.2.2 汇总区设计
底部汇总区显示所有Buff效果的总和：
- **DMG**: 总伤害加成
- **RATE**: 总射速加成
- **ARM**: 总护甲减免
- **EVD**: 总闪避率
- **PIR**: 穿透等级
- **EXP**: 爆炸等级
- **SPD**: 散布等级

#### 2.2.3 数据显示规则
| Buff名称 | 显示格式 | 示例 |
|----------|----------|------|
| Power Shot | `+{N}%` | +25% |
| Rapid Fire | `+{N}%` | +20% |
| Piercing | `Lv.{N}` | Lv.2 |
| Spread Shot | `Lv.{N}` | Lv.1 |
| Explosive | `Lv.{N}` | Lv.3 |
| Shotgun | ON/- | ON |
| Laser | ON/- | ON |
| Armor | `-{N}%` | -30% |
| Evasion | `+{N}%` | +40% |
| Barrier | `+50` | +50 |
| Extra Life | `+50 HP` | +50 HP |
| Regeneration | `+2/s` | +2/s |
| Lifesteal | `+10%` | +10% |
| Speed Boost | `+15%` | +15% |
| Magnet | `+30%` | +30% |
| Slow Field | `{N}%` | 20% |
| Shield | Ready/- | Ready |

---

## 3. 实现方案

### 3.1 新增文件
- `airwar/ui/buff_stats_panel.py` - 侧边统计栏组件

### 3.2 新增类

#### 3.2.1 BuffStatsAggregator
**职责**: Buff数据收集与聚合

**主要方法**:
- `get_buff_stats(reward_system, player)` - 获取所有Buff条目
- `get_summary_stats(reward_system, player)` - 获取汇总统计数据
- `_get_buff_color(name, reward_system)` - 获取Buff对应颜色
- `_get_buff_category(name)` - 获取Buff类别
- `_get_short_name(name)` - 获取Buff缩写名
- `_get_buff_level(name, reward_system)` - 获取Buff等级

#### 3.2.2 BuffStatsPanel
**职责**: 侧边统计栏UI渲染

**主要方法**:
- `render(surface, reward_system, player, screen_width, screen_height)` - 渲染统计栏
- `_calculate_panel_height(buff_count)` - 计算面板高度
- `_create_panel_surface(width, height)` - 创建面板Surface
- `_render_header(surface)` - 渲染标题区
- `_render_buff_items(surface, entries)` - 渲染Buff列表
- `_render_summary(surface, summary)` - 渲染汇总区

### 3.3 修改文件

#### 3.3.1 hud_renderer.py
- 新增导入: `BuffStatsPanel`
- 构造函数中初始化: `self._buff_stats_panel = BuffStatsPanel()`
- 新增方法: `render_buff_stats_panel(surface, reward_system, player)`

#### 3.3.2 game_renderer.py
- 新增方法: `render_buff_stats_panel(surface, reward_system, player)`

#### 3.3.3 game_scene.py
- 在 `_render_hud` 方法末尾调用 `render_buff_stats_panel`

---

## 4. 架构设计

### 4.1 模块职责划分
```
UI Layer
└── BuffStatsPanel (airwar/ui/buff_stats_panel.py)
    ├── BuffStatsAggregator (数据层)
    └── 渲染逻辑

Integration Layer
└── HUDRenderer (airwar/game/systems/hud_renderer.py)
    └── 调用BuffStatsPanel渲染

Scene Layer
└── GameScene (airwar/scenes/game_scene.py)
    └── 在渲染流程中调用统计栏渲染
```

### 4.2 数据流
1. GameScene持有RewardSystem和Player引用
2. GameScene.render调用GameRenderer.render_hud
3. GameRenderer.render_hud调用HUDRenderer.render_buff_stats_panel
4. HUDRenderer.render_buff_stats_panel调用BuffStatsPanel.render
5. BuffStatsPanel通过BuffStatsAggregator获取数据并渲染

---

## 5. 异常处理与边界检查

### 5.1 数据验证
- `reward_system`为None时不渲染
- `player`为None时不渲染
- `unlocked_buffs`为空列表时不渲染
- 所有Buff条目获取时使用try-except包裹，失败时跳过该条目

### 5.2 渲染保护
- 面板渲染使用顶层try-except，任何异常不传播
- Surface创建失败时安全返回
- 字体渲染失败时安全降级

### 5.3 边界处理
- 面板高度超出屏幕时，顶部对齐点调整为50像素
- 汇总区内容超出宽度时截断显示
- Buff条目数量无上限，但高度自适应

---

## 6. 性能考虑

### 6.1 优化措施
- 使用pygame.SRCALPHA创建透明Surface
- 面板尺寸根据内容动态计算
- 无需每帧重新计算面板高度

### 6.2 渲染成本
- 面板仅在有激活Buff时渲染
- 透明背景减少overdraw
- 字体使用系统默认字体，避免加载时间

### 6.3 预期性能影响
- 渲染额外开销: <1ms/帧
- 内存占用: <50KB (面板Surface)
- 无显著帧率影响

---

## 7. 测试计划

### 7.1 功能测试
| 测试场景 | 预期结果 |
|----------|----------|
| 无Buff激活 | 不显示统计栏 |
| 单个Buff激活 | 显示单个条目和对应数值 |
| 多个不同类Buff | 按类别显示所有条目 |
| 可叠加Buff (Lv.2+) | 显示等级标识 |
| 满屏Buff (10+) | 面板高度扩展，显示滚动效果(待实现) |

### 7.2 视觉测试
| 测试场景 | 预期结果 |
|----------|----------|
| 不同分辨率 (1400x800) | 面板正确位于右侧中央 |
| 小分辨率 (800x600) | 面板顶部不遮挡HUD |
| 透明度 | 背景不完全透明，边缘可见 |
| 颜色对比 | Buff名称与背景对比度足够 |

### 7.3 数据准确性测试
| 测试场景 | 预期结果 |
|----------|----------|
| Power Shot Lv.1 | 显示 +25% |
| Power Shot Lv.2 | 显示 +56% (1.25*1.25=1.5625) |
| Armor Lv.2 | 显示 -30% |
| 多个Buff同时激活 | 汇总区显示所有效果总和 |

---

## 8. 潜在风险点及应对措施

### 8.1 风险: 面板遮挡Boss血条
**风险等级**: 中
**描述**: 在Boss战时，面板可能与Boss血条产生视觉冲突
**应对措施**:
- Boss血条位于屏幕顶部中央
- 面板位于屏幕右侧边缘
- 面板具有低透明度，不完全遮挡

### 8.2 风险: 数据计算错误
**风险等级**: 中
**描述**: Buff数值计算可能因叠加规则不明确而出错
**应对措施**:
- 使用与RewardSystem相同的计算逻辑
- 所有Buff数值显示基于实际应用值
- 添加单元测试验证数值准确性

### 8.3 风险: 性能影响
**风险等级**: 低
**描述**: 频繁渲染可能导致帧率下降
**应对措施**:
- 仅在Buff列表变化时重新计算
- 使用低复杂度绘制操作
- 监控渲染时间确保 <1ms/帧

---

## 9. 未来改进方向

1. **可折叠设计**: 可通过快捷键折叠/展开统计栏
2. **详细tooltip**: 鼠标悬停显示完整Buff名称和效果描述
3. **动画过渡**: Buff激活/失效时添加淡入淡出动画
4. **声音反馈**: Buff激活时添加音效提示
5. **对比模式**: 显示装备前后的数值变化

---

## 10. 相关文档

- [项目重构设计](./2026-04-14-airwar-refactoring-design.md)
- [Boss重新设计](./2026-04-15-boss-redesign-design.md)
- [优化报告](./2026-04-16-optimization-report.md)
