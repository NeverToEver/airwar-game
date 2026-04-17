# 全量 Pytest 修复说明

> **文档版本**: 1.0  
> **编制日期**: 2026-04-17  
> **修复类型**: 测试稳定性修复  
> **影响范围**: `test_docking_debug.py`、全量 pytest 回归流程  

---

## 一、问题背景

在执行全量 `pytest` 时，根目录测试文件 `test_docking_debug.py` 暴露出两个问题：

1. 测试文件在模块导入阶段直接执行 `pygame.init()` 与 `pygame.display.set_mode()`，导致无图形显示环境下在收集阶段失败。
2. 测试直接实例化 `GameScene()` 后立即访问 `scene.game_controller.state`，但当前实现中运行态组件是在 `scene.enter()` 中初始化，因此会触发 `AttributeError`。

此外，该测试原本是偏“人工调试脚本”风格，带有大量 `print` 输出，并依赖真实时间流逝来推动 H 键长按读条，稳定性较差。

---

## 二、根因分析

### 2.1 模块级副作用过重

旧实现将以下代码放在模块级：

```python
pygame.init()
pygame.display.set_mode((800, 600))
```

这会导致 pytest 在“导入测试文件”阶段就依赖图形环境，不符合自动化测试的隔离原则。

### 2.2 未遵循场景生命周期约定

`GameScene` 当前遵循如下初始化约定：

1. `GameScene()` 仅完成对象构造
2. `enter()` 才负责创建 `game_controller`、`player`、`spawn_controller` 与母舰集成器

旧测试跳过 `enter()`，因此访问 `scene.game_controller.state` 时对象尚未初始化。

### 2.3 时间推进不可控

H 键读条依赖 `pygame.time.get_ticks()` 计算按压时长。旧测试只做循环调用，不显式控制时间，在高性能环境中可能远不足 3 秒，属于非确定性测试。

---

## 三、修复方案

### 3.1 将调试脚本改写为标准 pytest 用例

本次将 `test_docking_debug.py` 重构为单一、明确的回归测试：

- 测试名：`test_h_key_docking_flow_during_entrance`
- 目标：验证入场动画期间，按住 `H` 仍能推进母舰停靠状态到 `DOCKING` 或 `DOCKED`

### 3.2 消除模块级图形副作用

修复后不再在模块导入时初始化 `pygame` 显示，而是在测试函数内部进行：

```python
pygame.init()
pygame.display.set_mode((800, 600))
```

并在 `finally` 中显式释放：

```python
pygame.display.quit()
pygame.quit()
```

同时增加：

```python
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
```

保证测试在无头环境下可运行。

### 3.3 按正确生命周期初始化场景

修复后测试通过以下方式初始化：

```python
scene = GameScene()
scene.enter(difficulty='medium', username='TestPilot')
```

这样能确保：

- `game_controller`
- `player`
- `_mother_ship_integrator`

全部处于有效状态。

### 3.4 让时间推进可控

通过 `monkeypatch` 接管 `pygame.time.get_ticks()`，每次调用推进 100ms：

```python
def fake_get_ticks():
    value = tick_state['current']
    tick_state['current'] += 100
    return value
```

并通过自定义按键状态持续模拟按住 `H`：

```python
monkeypatch.setattr(pygame.key, 'get_pressed', lambda: _pressed_keys(pygame.K_h))
```

这样测试不再依赖真实机器速度，而是具备确定性。

---

## 四、修复收益

### 4.1 测试行为更符合自动化回归要求

- 去除了大量调试输出
- 去除了模块导入副作用
- 避免了图形环境耦合带来的收集失败

### 4.2 与当前代码设计保持一致

测试现已遵循 `GameScene.enter()` 的初始化约定，不再与场景生命周期设计冲突。

### 4.3 支持无头环境全量回归

修复后，在当前环境中可通过以下命令完成全量测试：

```bash
SDL_VIDEODRIVER=dummy pytest -q
```

---

## 五、验证结果

已执行验证：

```bash
pytest -q test_docking_debug.py
SDL_VIDEODRIVER=dummy pytest -q
```

验证结果：

- `test_docking_debug.py`：`1 passed`
- 全量 pytest：`161 passed`

---

## 六、涉及文件

- `test_docking_debug.py`
- `docs/superpowers/specs/2026-04-17-game-scene-mothership-update/技术说明.md`
- `docs/superpowers/specs/2026-04-17-game-scene-mothership-update/全量pytest修复说明.md`

---

## 七、后续建议

1. 将根目录这类“调试性质测试”逐步收敛进 `airwar/tests/`，统一按 pytest 规范管理。
2. 若后续需要真实窗口渲染验证，建议使用单独的 `integration` 或 `visual` 测试标记，与无头回归测试分层执行。
