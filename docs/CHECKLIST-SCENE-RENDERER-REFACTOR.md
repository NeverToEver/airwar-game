# Scene Renderer 重构检查清单

**设计文档**: [REFACTOR-DESIGN-SCENE-RENDERER.md](REFACTOR-DESIGN-SCENE-RENDERER.md)
**任务清单**: [TASKS-SCENE-RENDERER-REFACTOR.md](TASKS-SCENE-RENDERER-REFACTOR.md)

---

## Phase 1: 环境准备

- [ ] 阅读设计文档 `docs/REFACTOR-DESIGN-SCENE-RENDERER.md`
- [ ] 阅读任务清单 `docs/TASKS-SCENE-RENDERER-REFACTOR.md`
- [ ] 备份现有场景文件（可选）

---

## Phase 2: 创建 UI 组件

### 任务 1: 创建目录和 __init__.py

- [ ] 创建目录 `airwar/scenes/ui/`
- [ ] 创建文件 `airwar/scenes/ui/__init__.py`
- [ ] 验证: `from airwar.scenes.ui import BackgroundRenderer, ParticleSystem, EffectsRenderer`

### 任务 2: BackgroundRenderer

- [ ] 创建 `airwar/scenes/ui/background.py`
- [ ] 实现 `__init__` 方法
- [ ] 实现 `_init_stars` 方法（100 颗星星）
- [ ] 实现 `_get_cached_gradient` 方法（缓存机制）
- [ ] 实现 `update` 方法
- [ ] 实现 `render` 方法
- [ ] 验证: 渐变背景从缓存获取

### 任务 3: ParticleSystem

- [ ] 创建 `airwar/scenes/ui/particles.py`
- [ ] 定义类级别 `_texture_cache`
- [ ] 实现 `_init_cache` 方法（4 种尺寸 × 2 种颜色）
- [ ] 实现 `_init_particles` 方法
- [ ] 实现 `update` 方法
- [ ] 实现 `render` 方法（使用缓存纹理）
- [ ] 实现 `reset` 方法
- [ ] 验证: 纹理缓存创建成功

### 任务 4: EffectsRenderer

- [ ] 创建 `airwar/scenes/ui/effects.py`
- [ ] 实现 `render_glow_text` 方法
- [ ] 实现 `render_option_box` 方法
- [ ] 验证: 发光文字和选项框渲染正常

---

## Phase 3: 重构场景文件

### 任务 5: MenuScene

- [ ] 读取当前 `menu_scene.py`
- [ ] 添加导入语句
- [ ] 修改 `enter` 方法（初始化渲染器）
- [ ] 修改 `reset` 方法
- [ ] 修改 `update` 方法
- [ ] 修改 `render` 方法
- [ ] 删除 `_init_particles` 方法
- [ ] 删除 `_init_stars` 方法
- [ ] 删除 `_draw_gradient_background` 方法
- [ ] 删除 `_draw_stars` 方法
- [ ] 删除 `_draw_particles` 方法
- [ ] **功能测试**: 菜单场景正常显示

### 任务 6: DeathScene

- [ ] 读取当前 `death_scene.py`
- [ ] 添加导入语句
- [ ] 修改 `enter` 方法
- [ ] 修改 `update` 方法
- [ ] 修改 `render` 方法
- [ ] 删除重复的渲染方法
- [ ] **保留**: `_draw_ripples`, `_draw_decorative_lines`, `_draw_icon_decoration`
- [ ] **功能测试**: 死亡场景正常显示

### 任务 7: ExitConfirmScene

- [ ] 读取当前 `exit_confirm_scene.py`
- [ ] 添加导入语句
- [ ] 修改 `enter` 方法
- [ ] 修改 `update` 方法
- [ ] 修改 `render` 方法
- [ ] 删除重复的渲染方法
- [ ] **保留**: `_draw_decorative_lines`, `_draw_icon_decoration`, `_draw_success_indicator`
- [ ] **功能测试**: 退出确认场景正常显示

### 任务 8: PauseScene

- [ ] 读取当前 `pause_scene.py`
- [ ] 添加导入语句
- [ ] 修改 `enter` 方法
- [ ] 修改 `update` 方法
- [ ] 修改 `render` 方法
- [ ] 删除重复的渲染方法
- [ ] **保留**: `_draw_decorative_lines`, `_draw_icon_decoration`
- [ ] **功能测试**: 暂停场景正常显示

### 任务 9: LoginScene

- [ ] 读取当前 `login_scene.py`
- [ ] 添加导入语句
- [ ] 修改 `enter` 方法
- [ ] 修改 `update` 方法
- [ ] 修改 `render` 方法
- [ ] 删除重复的渲染方法
- [ ] **保留**: 所有 `_render_*` 方法
- [ ] **功能测试**: 登录场景正常显示

---

## Phase 4: 验证与测试

### 功能验证

- [ ] 运行游戏，菜单场景正常显示
- [ ] 运行游戏，登录场景正常显示
- [ ] 运行游戏，暂停场景正常显示
- [ ] 运行游戏，死亡场景正常显示
- [ ] 运行游戏，退出确认场景正常显示

### 单元测试

- [ ] 运行 `pytest airwar/tests/test_scenes.py -v`
- [ ] 运行 `pytest airwar/tests/test_menu_scene.py -v` (如果存在)
- [ ] 运行 `pytest airwar/tests/test_death_scene.py -v` (如果存在)
- [ ] 所有测试通过

### 代码质量

- [ ] 无导入错误
- [ ] 无 Pyflakes/Lint 警告
- [ ] 代码风格与项目一致

---

## Phase 5: 文档更新

- [ ] 更新 README 或相关文档（如果需要）
- [ ] 记录重构变更（CHANGELOG）

---

## 完成确认

**所有复选框已勾选？**

- [ ] **是的，所有任务已完成**

**签名**: _________________**日期**: _________________
