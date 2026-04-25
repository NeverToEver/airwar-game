# Air War GPU 加速文档

## 项目概述

目标：将 Air War 游戏从 pygame CPU 软件渲染迁移到 ModernGL GPU 渲染，以利用 NVIDIA RTX 4060 等显卡的算力。

**当前状态：混合渲染模式集成完成，GPU 模式在游戏启动时选择，游戏开始后锁定。**

---

## 一、已完成工作

### Phase 1: GPU 基础设施 ✅

| 文件 | 说明 |
|------|------|
| `airwar/game/gpu/context.py` | ModernGL 上下文管理，支持 EGL fallback |
| `airwar/game/gpu/shader_manager.py` | 着色器加载/编译，内置精灵着色器源码 |
| `airwar/game/gpu/texture_manager.py` | 纹理上传 GPU 管理，Surface → Texture |
| `airwar/game/gpu/buffer_manager.py` | VBO/VAO 管理，精灵顶点数据工具函数 |
| `airwar/game/gpu/sprite_batch.py` | 实例化批量精灵渲染 |
| `airwar/game/gpu/sprite_renderer.py` | 精灵渲染器（推荐使用），支持多纹理批量渲染 |
| `airwar/game/gpu/background_renderer.py` | GPU 背景渲染（渐变 + 视差叶影 + 光线） |
| `airwar/game/gpu/composer.py` | GPUComposer - 渲染层编排器 |

**验证结果：**
- OpenGL 4.5 上下文创建成功
- 着色器编译正常
- Surface → GPU Texture 上传正常
- 精灵批量渲染正常
- 测试脚本：`airwar/game/gpu/test_gpu_renderer.py`

### Phase 2-3: 渲染框架验证 ✅

已通过 `test_gpu_renderer.py` 验证完整渲染管线可用。

### Phase 3.5: 混合渲染器 ✅

**新增文件：**
| 文件 | 说明 |
|------|------|
| `airwar/game/rendering/hybrid_renderer.py` | HybridRenderer - pygame/GPU 双后端混合渲染器 |

**功能：**
- 支持 pygame (CPU) 和 GPU (ModernGL) 双后端
- 默认使用 pygame（稳定），GPU 可选启用
- GPU 失败时自动 fallback 到 pygame
- 逐步迁移策略：先集成再优化

**GPUComposer 新增功能：**
```python
class GPUComposer:
    def add_sprite(texture_name, x, y, w, h, rotation=0, alpha=1, layer='entities')
    def add_pre_render_callback(callback)  # 渲染前回调
    def add_post_render_callback(callback) # 渲染后回调
    def set_layer_visible(layer_name, visible)  # 控制层可见性
    def get_surface() -> pygame.Surface  # 将 FBO 内容读取为 pygame Surface
```

**HybridRenderer 接口：**
```python
class HybridRenderer:
    def enable_gpu() -> bool   # 启用 GPU 后端
    def disable_gpu()          # 禁用 GPU，切换 pygame
    def is_gpu_enabled -> bool # 查询 GPU 状态
    def render_game(surface, state, player, enemies, boss)  # 渲染主画面
    def render_hud(...)        # 渲染 HUD
    @property screen_size      # 屏幕尺寸
```

### Phase 4: GPU 渲染显示修复 ✅

**问题：** ModernGL standalone context 渲染到独立帧缓冲，不显示在 pygame 窗口上。

**解决方案：** 使用 FBO + get_surface() 桥接模式
- GPUComposer 渲染到 FBO
- get_surface() 读取 FBO 像素数据转换为 pygame Surface
- blit 到主 surface

### Phase 6: GPU 模式选择 UI ✅

**新增文件：**
| 文件 | 说明 |
|------|------|
| `airwar/scenes/menu_scene.py` | 两阶段菜单：难度选择 + 渲染模式选择 |
| `game/rendering/hybrid_renderer.py` | 新增 `test_gpu()` 方法 |

**功能：**
- 主菜单第一阶段：选择难度（EASY / MEDIUM / HARD / TUTORIAL）
- 主菜单第二阶段：选择渲染模式（pygame CPU / GPU ModernGL）
- ESC 可返回上一阶段
- GPU 模式选择后锁定，游戏开始后不可切换

---

## 二、技术架构

### 2.1 当前架构

#### 混合渲染模式

```
GPU 渲染（游戏主画面）          pygame 渲染（UI/HUD）
       │                              │
       ▼                              │
┌─────────────────┐                   │
│  GPUComposer    │                   │
│  (FBO + 着色器) │                   │
└────────┬────────┘                   │
         │ get_surface()              │
         ▼                            │
┌─────────────────┐                   │
│  pygame Surface │◄──────────────────┤
└────────┬────────┘                   │
         │ blit                       │
         ▼                            │
┌─────────────────┐                   │
│   显示窗口      │                   │
└─────────────────┘                   │
```

#### 性能考量

- GPU 模式：适合大量精灵（玩家、敌人、Boss）的批量渲染
- pygame 模式：适合复杂的 HUD/UI 渲染（圆角、渐变、文字）
- 混合模式：游戏主画面用 GPU，HUD/UI 用 pygame

### 2.2 GPU 渲染架构

```
GameRenderer (pygame)          GPUComposer (ModernGL)
      │                              │
      ▼                              ▼
┌─────────────┐              ┌─────────────────┐
│ Background  │              │ GPUBackground   │
│   blit()   │      →       │  (着色器渲染)    │
├─────────────┤              ├─────────────────┤
│ Entities   │              │ GPUSpriteRenderer│
│   blit()   │      →       │  (批量纹理渲染)  │
├─────────────┤              ├─────────────────┤
│ Effects    │              │ GPUParticleSystem│
│   blit()   │      →       │  (可选)          │
├─────────────┤              ├─────────────────┤
│ HUD/UI     │              │ 预渲染 + GPU    │
│   blit()   │      →       │ 纹理渲染        │
└─────────────┘              └─────────────────┘
```

### 2.3 GPU 模式渲染内容

| 组件 | 渲染方式 | 说明 |
|------|----------|------|
| 背景（渐变 + 叶影 + 光线） | GPU 着色器 | 视差效果 |
| 玩家飞船 | GPU 批量精灵 | 实例化渲染 |
| 敌机 | GPU 批量精灵 | 实例化渲染 |
| Boss | GPU 批量精灵 | 实例化渲染 |
| 子弹 | pygame | 需要频繁更新 |
| HUD/分数 | pygame | 复杂文字渲染 |
| 爆炸效果 | pygame | 粒子数量少 |
| 奖励选择界面 | pygame | 复杂 UI |
| 暂停按钮 | pygame | 简单 UI |

### 2.4 核心类设计

**GPUSpriteRenderer** (已实现)
```python
class GPUSpriteRenderer:
    def upload_surface(name: str, surface: pygame.Surface) -> None
    def add_sprite(texture_name, x, y, w, h, rotation=0, alpha=1) -> None
    def render(screen_width, screen_height) -> None
    def clear() -> None
```

**SpriteCache** (已实现)
```python
class SpriteCache:
    def cache_surface(name: str, surface: pygame.Surface) -> None
    def set_renderer(renderer: GPUSpriteRenderer) -> None
    def upload_all() -> None
```

---

## 三、GPU 模式切换说明

### 3.1 操作流程

### 启动时选择（推荐流程）

```
1. 启动游戏 → 进入主菜单
2. 选择难度（EASY / MEDIUM / HARD / TUTORIAL）
3. 按 Enter 确认 → 进入渲染模式选择
4. 选择渲染模式：
   - pygame (CPU) - 稳定兼容
   - GPU (ModernGL) - 高性能（需要显卡支持）
5. 按 Enter 开始游戏，GPU 模式锁定
```

### 3.2 操作控制

| 按键 | 功能 |
|------|------|
| W / ↑ | 上移选择 |
| S / ↓ | 下移选择 |
| Enter / 空格 | 确认选择 |
| ESC | 返回上一步 |

### 3.3 设计原因

**为什么游戏开始后不允许切换 GPU 模式？**

1. **防止不可预料的问题**：运行时切换渲染模式可能导致状态不一致
2. **简化状态管理**：渲染模式在游戏生命周期内保持一致
3. **避免复杂错误处理**：不需要处理"切换过程中"的边界情况

### 3.4 GPU 检测机制

- 选择 GPU 模式后，系统会测试 GPU 是否可用
- 如果 GPU 初始化失败，显示错误提示：
  ```
  GPU 初始化失败！
  您的系统不支持 ModernGL GPU 渲染
  建议使用 pygame (CPU) 模式运行游戏
  按 ENTER 选择 pygame 模式
  ```
- 自动回退到 pygame 模式

---

## 四、初始化与资源管理

### 4.1 初始化流程

```python
# SceneDirector._run_menu_flow()
# 用户在菜单中选择 GPU 模式
self._selected_gpu_mode = ms.get_use_gpu()  # True = GPU, False = pygame

# SceneDirector._run_game_flow()
self._scene_manager.switch("game",
                          difficulty=self._selected_difficulty,
                          username=username,
                          use_gpu=self._selected_gpu_mode)  # 传递给 GameScene

# GameScene.enter()
use_gpu = kwargs.get('use_gpu', False)
self._init_gpu_renderer(screen_width, screen_height, use_gpu)
```

### 4.2 GPU 资源释放

```python
# GameScene.exit()
if self._gpu_renderer:
    self._gpu_renderer.release()  # 释放 FBO、纹理、着色器等
    self._gpu_renderer = None
```

### 4.3 HybridRenderer

```python
class HybridRenderer:
    def __init__(self, screen_width, screen_height, use_gpu=False):
        # use_gpu=True 时立即初始化 GPU 资源
        # use_gpu=False 时延迟初始化（首次 enable_gpu 时）
```

### 4.4 FBO 桥接

ModernGL standalone context 无法直接渲染到窗口，使用 FBO 中转：

```
GPUComposer.render()
      │
      ▼
┌─────────────┐
│ FBO         │  ← GPU 渲染目标
│ (帧缓冲)    │
└──────┬──────┘
       │ get_surface() 读取像素
       ▼
┌─────────────┐
│ pygame.Surface │  ← 转换回 pygame 格式
└──────┬──────┘
       │ blit
       ▼
┌─────────────┐
│ 主 Surface  │
└─────────────┘
```

---

## 五、集成指南

### 5.1 初始化 GPU 渲染器

```python
from airwar.game.gpu import GPUContext, GPUSpriteRenderer, SpriteCache

# 初始化上下文
gpu_ctx = GPUContext()
gpu_ctx.initialize(screen_width, screen_height)

# 创建渲染器
sprite_renderer = GPUSpriteRenderer(gpu_ctx.context)
sprite_cache = SpriteCache(gpu_ctx)
sprite_cache.set_renderer(sprite_renderer)
```

### 5.2 上传精灵纹理

```python
from airwar.utils.sprites import get_player_sprite, get_enemy_sprite

# 预渲染并上传
player_surf = get_player_sprite(50, 60)
enemy_surf = get_enemy_sprite(50, 50, 1.0)

sprite_cache.cache_surface('player', player_surf)
sprite_cache.cache_surface('enemy', enemy_surf)
sprite_cache.upload_all()
```

### 5.3 渲染循环

```python
# 清屏
gpu_ctx.clear(r=0.1, g=0.1, b=0.2, a=1.0)

# 添加精灵
sprite_renderer.add_sprite('player', 400, 300, 50, 60)
sprite_renderer.add_sprite('enemy', 500, 350, 50, 50)

# 渲染
sprite_renderer.render(screen_width, screen_height)
```

### 5.4 清理

```python
sprite_renderer.release()
gpu_ctx.release()
```

---

## 六、剩余工作

### Phase 5: HUD/UI GPU 预渲染（可选优化）

**工作量：中**

建议方案：
```
保留 pygame 绘制逻辑 → 预渲染到 Surface → 上传 GPU 纹理 → GPU 渲染
```

适用于相对静态的 UI 组件：
- 静态面板背景
- 按钮图标
- 装饰性元素

动态内容（分数、生命值）继续使用 pygame 渲染。

### Phase 5: 特效系统 GPU 化

**工作量：中**

| 特效 | 文件位置 | 状态 |
|------|----------|------|
| 爆炸粒子 | `airwar/game/explosion_animation/` | ⚠️ 保留 pygame（足够快） |
| 死亡动画 | `airwar/game/death_animation/` | ⚠️ 保留 pygame（足够快） |
| 涟漪效果 | `airwar/game/rendering/hud_renderer.py` | ⚠️ 保留 pygame（足够快） |
| GPU 粒子系统 | `airwar/game/gpu/particle_system.py` | ✅ 已创建框架 |

**GPU 粒子系统接口：**
```python
class GPUParticleSystem:
    def add_particle(x, y, vx, vy, life, size, r=1.0, g=0.5, b=0.0)
    def add_explosion(x, y, count=30)  # 便捷方法
    def update(dt=1.0)                 # CPU 更新粒子位置
    def render(screen_width, screen_height)
    def clear()
    @property count                    # 当前粒子数
```

---

## 七、文件清单

### GPU 模块
```
airwar/game/gpu/
├── __init__.py              # 导出所有公共类
├── context.py               # GPUContext 类 - ModernGL 上下文管理
├── shader_manager.py        # ShaderManager 类 + 内置着色器源码
├── texture_manager.py        # TextureManager 类 - Surface → GPU Texture
├── buffer_manager.py         # BufferManager 类 + 顶点数据工具函数
├── sprite_batch.py          # SpriteBatch / SimpleSpriteBatch - 实例化批量渲染
├── sprite_renderer.py        # GPUSpriteRenderer (推荐) / SpriteCache
├── background_renderer.py     # GPUBackgroundRenderer - 视差背景
├── composer.py              # GPUComposer - 渲染层编排器
├── particle_system.py       # GPUParticleSystem - GPU 粒子系统
└── test_gpu_renderer.py      # 测试脚本
```

### 游戏集成
```
airwar/scenes/
├── menu_scene.py             # 两阶段菜单：难度 + 渲染模式选择
└── game_scene.py            # 已集成 HybridRenderer，GPU 模式锁定
airwar/game/
├── rendering/
│   └── hybrid_renderer.py    # HybridRenderer - pygame/GPU 双后端渲染器
└── scene_director.py         # 传递 GPU 模式选择到 GameScene
```

---

## 八、已知约束

1. **WSL2 环境**：需要 EGL 支持，已验证可用
2. **macOS**：OpenGL 4.1 受限，Apple 已弃用 OpenGL
3. **Windows/Linux**：完整支持 OpenGL 4.6+
4. **numpy 依赖**：已添加到 requirements.txt

---

## 九、使用说明

### 9.1 运行游戏

```bash
cd /home/ubt/airwar
sudo -u ubt python3 main.py
```

### 9.2 启用 GPU 渲染模式

GPU 模式在游戏启动时选择（菜单中选择），游戏开始后锁定：

1. 启动游戏后，在主菜单选择难度
2. 确认后会进入渲染模式选择界面
3. 选择 `pygame (CPU)` 或 `GPU (ModernGL)`
4. 按 Enter 开始游戏，GPU 模式锁定

**注意：** 游戏开始后不允许切换渲染模式，以防出现不可预料的问题。

### 9.3 运行测试

```bash
python3 airwar/game/gpu/test_gpu_renderer.py
```

---

## 十、故障排除

### GPU 初始化失败

如果 GPU 模式初始化失败，会自动 fallback 到 pygame 模式：
```python
# HybridRenderer._init_gpu_backend()
try:
    self._gpu_composer = GPUComposer(screen_size)
    return True
except Exception as e:
    print(f"GPU backend init failed: {e}")
    self._gpu_composer = None
    return False
```

### WSL2 环境

WSL2 需要 EGL 支持，ModernGL 会自动尝试 EGL fallback。

### 测试清单
- [x] 游戏启动正常
- [x] 背景渲染正确
- [x] 玩家/敌人/Boss 渲染正确
- [x] 子弹渲染正确
- [x] HUD 渲染正确
- [ ] 暂停/奖励选择等 UI 正常
- [ ] 存档/加载正常
- [x] GPU 模式选择正常（菜单测试通过）
- [x] 游戏开始后 GPU 模式不可切换（已锁定）
- [x] GPU 渲染管线测试通过

---

## 十一、参考资源

- ModernGL 文档：https://moderngl.readthedocs.io/
- ModernGL 示例：https://github.com/cprogrammer1994/moderngl-examples
- GLSL 教程：https://learnopengl.com/

---

## 更新日志

| 日期 | 更新内容 |
|------|----------|
| 2026-04-25 | 完成 Phase 1-3，GPU 渲染管线验证通过 |
| 2026-04-25 | 新增 GPUComposer 渲染编排器 |
| 2026-04-25 | 新增 HybridRenderer 双后端混合渲染器 |
| 2026-04-25 | 新增 GPUParticleSystem 粒子系统框架 |
| 2026-04-25 | Phase 5 特效系统评估完成，pygame 方案保留 |
| 2026-04-25 | GameScene 集成 HybridRenderer，支持 GPU 模式切换 |
| 2026-04-25 | 修复 GPU 渲染显示问题：添加 FBO + get_surface() 桥接 |
| 2026-04-25 | 修复 background_renderer 着色器 uniform 和实例化渲染问题 |
| 2026-04-25 | 验证混合渲染模式架构：GPU 渲染主画面 + pygame 渲染 HUD/UI |
| 2026-04-25 | GPU 模式改为启动时选择，游戏开始后锁定，防止运行时切换导致的问题 |
| 2026-04-25 | MenuScene 改为两阶段选择：难度 → 渲染模式 |
| 2026-04-25 | SceneDirector 新增 GPU 模式传递，GameScene GPU 模式锁定 |
| 2026-04-25 | 新增 GPU 模式检测：GPU 初始化失败时显示错误提示并推荐 pygame 模式 |
| 2026-04-25 | 修复 background_renderer 中未定义变量 hw/hh 导致 GPU 模式下背景渲染异常 |
