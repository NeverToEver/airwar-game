# 新手教程系统实现计划

> **计划版本**: 1.0
> **创建日期**: 2026-04-21
> **依据**: [设计文档](../docs/superpowers/specs/2026-04-21-tutorial-system-design.md)

---

## 阶段一：创建 TutorialScene 场景类

### 任务 1.1: 创建基础框架
**文件**: `airwar/scenes/tutorial_scene.py`

**实现内容**:
1. 创建 `TutorialScene` 类，继承 `Scene` 基类
2. 实现基础属性：
   - `running`: 运行状态标志
   - `back_requested`: 返回请求标志
   - `animation_time`: 动画时间计数器
   - `particles`: 粒子效果列表
   - `stars`: 星空背景列表
   - `selected_button`: 按钮选中状态

3. 实现基础方法：
   - `__init__()`: 初始化所有属性
   - `enter(**kwargs)`: 初始化场景状态
   - `exit()`: 清理场景资源
   - `handle_events(event)`: 处理输入事件
   - `update(*args, **kwargs)`: 更新动画
   - `render(surface)`: 渲染界面

4. 实现状态查询方法：
   - `is_back_requested()` → bool
   - `is_ready()` → bool

**验收标准**:
- [ ] 类成功继承 Scene 基类
- [ ] 所有基础方法正确实现
- [ ] 能够被 SceneManager 加载

### 任务 1.2: 实现星空和粒子背景
**文件**: `airwar/scenes/tutorial_scene.py`

**实现内容**:
1. 初始化方法 `_init_particles()`:
   - 创建 40-60 个粒子
   - 每个粒子包含：x, y, size, speed, alpha, pulse_speed, pulse_offset
   - 粒子颜色使用 `particle: (100, 180, 255)`

2. 初始化方法 `_init_stars()`:
   - 创建 100-120 个星星
   - 每个星星包含：x, y, size, brightness, twinkle_speed, twinkle_offset
   - 亮度范围 50-150

3. 更新方法 `_update_particles()`:
   - 粒子向上飘动
   - 循环利用到达顶部的粒子
   - 脉冲动画效果

4. 更新方法 `_update_stars()`:
   - 星星缓慢下落
   - 闪烁效果

5. 渲染方法:
   - `_draw_background()`: 绘制渐变背景
   - `_draw_stars()`: 绘制星空
   - `_draw_particles()`: 绘制粒子效果

**验收标准**:
- [ ] 星空背景正常显示并闪烁
- [ ] 粒子效果流畅无卡顿
- [ ] 与 MenuScene 视觉效果一致

### 任务 1.3: 实现教程内容绘制
**文件**: `airwar/scenes/tutorial_scene.py`

**实现内容**:
1. 面板绘制 `_draw_panel()`:
   - 面板尺寸：700x650（基准值，使用 ResponsiveHelper 适配）
   - 面板背景：`(15, 20, 40)`
   - 边框：`(50, 80, 140)`，宽度2px，圆角15px
   - 发光效果：多层光晕叠加

2. 标题绘制 `_draw_title()`:
   - 主标题："AIR WAR"（大号字体，带发光效果）
   - 副标题："新手教程指南"（中号字体）
   - 脉动动画效果

3. 内容区块绘制 `_draw_content_sections()`:
   - 三个区块：基础控制、母舰系统、其他功能
   - 每个区块包含：
     - 标题（带 emoji 图标）
     - 内容框（圆角矩形背景）
     - 按键映射列表

4. 区块绘制 `_draw_section(surface, title, items, y_pos)`:
   - 标题样式：白色 + 左侧小圆点装饰
   - 内容框：半透明背景
   - 动态计算 Y 坐标

5. 按键映射绘制 `_draw_key_mapping(key, desc, x, y)`:
   - 按键显示：方角矩形包裹
   - 功能描述：普通文本
   - 对齐排列

**验收标准**:
- [ ] 面板正确显示在屏幕中央
- [ ] 三个区块清晰排列
- [ ] 所有按键说明正确显示
- [ ] 响应式适配不同分辨率

### 任务 1.4: 实现按钮和交互
**文件**: `airwar/scenes/tutorial_scene.py`

**实现内容**:
1. 按钮绘制 `_draw_button()`:
   - 按钮文本："返回主菜单"
   - 按钮尺寸：240x60（基准值）
   - 按钮位置：面板底部居中
   - 悬停效果：鼠标接近时变亮
   - 选中效果：边框发光

2. 底部提示绘制 `_draw_hints()`:
   - 提示文字："↑↓ 选择    ENTER 确认"
   - 提示位置：屏幕底部 50px
   - 交替闪烁效果

3. 事件处理增强 `handle_events()`:
   - ESC 键：返回主菜单
   - ENTER 键：返回主菜单
   - 空格键：返回主菜单
   - 鼠标悬停检测

**验收标准**:
- [ ] 按钮正常显示并可点击
- [ ] 悬停效果正常
- [ ] ESC/ENTER/空格键都能返回
- [ ] 底部提示正常显示

---

## 阶段二：注册新场景

### 任务 2.1: 更新场景注册
**文件**: `airwar/scenes/__init__.py`

**实现内容**:
1. 导入 TutorialScene:
   ```python
   from .tutorial_scene import TutorialScene
   ```

2. 更新 `_init_scenes()` 函数:
   ```python
   scene_manager.register("tutorial", TutorialScene())
   ```

**验收标准**:
- [ ] TutorialScene 成功导入
- [ ] 场景成功注册到 SceneManager

### 任务 2.2: 检查 Scene 基类
**文件**: `airwar/scenes/scene.py`

**实现内容**:
1. 确认基类包含所有必要接口
2. 如需要，添加抽象方法定义

**验收标准**:
- [ ] TutorialScene 能正常继承 Scene
- [ ] 所有必需方法已实现

---

## 阶段三：修改 MenuScene

### 任务 3.1: 添加教程选项
**文件**: `airwar/scenes/menu_scene.py`

**实现内容**:
1. 修改菜单选项列表:
   ```python
   self.menu_options = ['easy', 'medium', 'hard', 'tutorial']
   ```

2. 添加选项名称映射:
   ```python
   self.option_names = {
       'easy': 'EASY',
       'medium': 'MEDIUM',
       'hard': 'HARD',
       'tutorial': 'TUTORIAL'  # 新增
   }
   ```

3. 更新 `__init__()` 中的基础值:
   - 面板高度需要增加（从280增加到340）
   - 选项数量从3变为4

4. 修改 `_draw_option_item()`:
   - 支持4个选项的布局
   - 确保第4个选项正确显示

5. 修改 `_draw_bottom_hints()`:
   - 更新提示文字逻辑

**验收标准**:
- [ ] 菜单显示4个选项
- [ ] 教程选项可见并可选
- [ ] 键盘导航正常（↑↓选择）
- [ ] 视觉效果一致

### 任务 3.2: 添加选项查询方法
**文件**: `airwar/scenes/menu_scene.py`

**实现内容**:
1. 添加 `get_selected_option()` 方法:
   ```python
   def get_selected_option(self) -> str:
       return self.menu_options[self.selected_index]
   ```

2. 修改 `get_difficulty()` 逻辑:
   ```python
   def get_difficulty(self) -> str:
       selected = self.get_selected_option()
       if selected == 'tutorial':
           return None  # 或返回特殊值
       return selected
   ```

**验收标准**:
- [ ] 能正确获取当前选中的选项
- [ ] 返回值与选项列表一致

---

## 阶段四：集成到 SceneDirector

### 任务 4.1: 修改菜单流程
**文件**: `airwar/game/scene_director.py`

**实现内容**:
1. 修改 `_run_menu_flow()` 方法:
   ```python
   if ms.is_selection_confirmed():
       selected_option = ms.get_selected_option()
       if selected_option == 'tutorial':
           # 进入教程流程
           self._run_tutorial_flow()
           continue  # 继续显示菜单
       else:
           self._selected_difficulty = selected_option
           break
   ```

2. 确保 `should_go_back()` 和 `is_selection_confirmed()` 互不冲突

**验收标准**:
- [ ] 选择教程选项能触发教程流程
- [ ] 教程结束后正确返回菜单
- [ ] 选择难度能正常进入游戏

### 任务 4.2: 实现教程流程方法
**文件**: `airwar/game/scene_director.py`

**实现内容**:
1. 新增 `_run_tutorial_flow()` 方法:
   ```python
   def _run_tutorial_flow(self) -> None:
       """运行教程流程"""
       self._scene_manager.switch("tutorial")
       tutorial_scene = self._scene_manager.get_current_scene()
       
       while tutorial_scene.is_running():
           events = self._poll_events()
           if not self._check_quit(events):
               return
           self._handle_resize_if_needed(events)
           self._handle_scene_events(events)
           tutorial_scene.update()
           tutorial_scene.render(self._window.get_surface())
           self._window.flip()
           self._window.tick(60)
   ```

2. 确保事件处理正确传递给 TutorialScene

**验收标准**:
- [ ] 教程场景正常启动
- [ ] 事件处理正常工作
- [ ] 窗口resize处理正常

---

## 阶段五：测试和优化

### 任务 5.1: 功能测试
**测试内容**:
1. **场景切换测试**:
   - [ ] 登录 → 主菜单：正常
   - [ ] 主菜单 → 教程：正常
   - [ ] 教程 → 主菜单：正常
   - [ ] 主菜单 → 游戏：正常

2. **菜单交互测试**:
   - [ ] 键盘上下导航：正常
   - [ ] 选中教程选项：正常高亮
   - [ ] 按Enter进入教程：正常

3. **教程页面测试**:
   - [ ] 显示所有按键说明：正确
   - [ ] 动画效果流畅：是
   - [ ] 返回按钮可点击：是

4. **键盘操作测试**:
   - [ ] ESC返回：正常
   - [ ] Enter返回：正常
   - [ ] 空格返回：正常

**运行命令**:
```bash
cd /Users/xiepeilin/TRAE1/AIRWAR
python main.py
```

### 任务 5.2: 视觉测试
**测试内容**:
1. **布局测试**:
   - [ ] 不同分辨率下显示正确
   - [ ] 面板居中显示
   - [ ] 内容无溢出

2. **视觉效果测试**:
   - [ ] 星空闪烁：正常
   - [ ] 粒子飘动：流畅
   - [ ] 标题发光：正常
   - [ ] 按钮悬停：有效

3. **色彩测试**:
   - [ ] 与游戏整体风格一致
   - [ ] 色彩对比度适中
   - [ ] 可读性良好

### 任务 5.3: 边界情况测试
**测试内容**:
1. **快速操作**:
   - [ ] 快速切换选项：正常
   - [ ] 快速进入/退出教程：正常

2. **重复操作**:
   - [ ] 多次进入教程：正常
   - [ ] 反复返回菜单：正常

3. **异常情况**:
   - [ ] 窗口最小化后恢复：正常
   - [ ] 窗口拖动：正常

---

## 实施顺序

### 顺序一：基础实现（高优先级）
1. ✅ 创建 TutorialScene 基础框架
2. ✅ 注册场景
3. ✅ 修改 MenuScene（仅添加选项，不改逻辑）
4. ✅ 集成到 SceneDirector

### 顺序二：完善功能（中优先级）
5. 实现星空和粒子背景
6. 实现教程内容绘制
7. 实现按钮和交互

### 顺序三：测试优化（低优先级）
8. 功能测试
9. 视觉调整
10. 性能优化

---

## 风险控制

### 风险1: 布局适配问题
**预防措施**:
- 使用 ResponsiveHelper 进行尺寸计算
- 在多种分辨率下测试（800x600, 1280x720, 1920x1080）

### 风险2: 菜单逻辑干扰
**预防措施**:
- 最小化修改 MenuScene
- 充分测试所有原有功能
- 确保4个选项都能正常工作

### 风险3: 场景切换状态问题
**预防措施**:
- enter() 方法正确重置所有状态
- 确保 back_requested 标志正确设置和清除

---

## 成功标准

### 功能成功标准
- ✅ 用户能通过主菜单进入教程
- ✅ 教程页面正确显示所有按键说明
- ✅ 用户能通过多种方式返回主菜单
- ✅ 教程不影响正常游戏流程

### 视觉成功标准
- ✅ 教程页面与游戏整体风格一致
- ✅ 所有文字和元素清晰可见
- ✅ 动画效果流畅无卡顿
- ✅ 响应式适配各种窗口尺寸

### 技术成功标准
- ✅ 代码无语法错误
- ✅ 无运行时异常
- ✅ 符合现有代码规范
- ✅ 单元测试通过（如果适用）

---

## 后续工作（可选）

### 教程扩展
1. 添加具体游戏演示动画
2. 添加可交互的教程练习关卡
3. 支持多语言教程内容

### 数据统计
1. 记录用户查看教程的次数
2. 分析教程完成率
3. 优化教程内容展示

---

**计划结束**

*执行顺序：按上述顺序依次实现，每个任务完成后进行简单测试，确保无问题后继续下一个任务。*
