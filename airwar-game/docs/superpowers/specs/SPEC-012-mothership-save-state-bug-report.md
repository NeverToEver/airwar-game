# 母舰状态保存与读取异常问题报告

> **文档版本**: 1.0
> **日期**: 2026-04-16
> **问题类型**: 状态同步缺陷 (State Synchronization Bug)
> **严重程度**: 高 (High)
> **影响范围**: 存档恢复系统

---

## 一、问题现象描述

### 1.1 主要问题
用户在未进入母舰的情况下重新加载游戏时，系统错误地从母舰状态加载数据，导致游戏出现以下异常：

1. **玩家战机消失**：玩家战机被放置在屏幕上方 (`y = -80`)，不可见
2. **游戏卡在母舰状态**：游戏暂停在母舰界面，无法进行正常游戏
3. **控制失效**：玩家的输入无法正常控制战机

### 1.2 复现场景
```
场景A（正常流程）：
1. 玩家正常游戏
2. 按H键进入母舰
3. 存档被创建（is_in_mothership: true）
4. 退出母舰继续游戏
5. 退出游戏
6. 下次登录 → 正确加载游戏状态

场景B（问题流程）：
1. 玩家正常游戏
2. 按H键进入母舰
3. 存档被创建（is_in_mothership: true）
4. 退出母舰继续游戏 ← 关键：存档未更新
5. 退出游戏 ← 存档仍为 is_in_mothership: true
6. 下次登录 → 错误加载母舰状态！
```

---

## 二、根本原因分析

### 2.1 问题定位

**问题文件**：
- `airwar/game/mother_ship/persistence_manager.py` - 存档管理
- `airwar/game/scene_director.py` - 场景导演（存档加载逻辑）
- `airwar/game/mother_ship/game_integrator.py` - 游戏集成器（存档创建逻辑）

### 2.2 根本原因

#### 原因一：退出时不强制更新存档

在 [scene_director.py:239-247](file:///d:/Trae/pygames_dev/airwar/game/scene_director.py#L239-L247) 中：

```python
def _save_game_on_quit(self, game_scene: GameScene) -> None:
    if not game_scene or not game_scene._mother_ship_integrator:
        return
    if not game_scene._mother_ship_integrator.is_docked():  # ← 问题点！
        return
    # ...
```

**问题**：
- 当玩家退出游戏时，只有在**已停靠母舰**状态下才会保存游戏
- 如果玩家从正常游戏状态（非母舰）退出，存档**不会被更新**
- 旧的存档（包含 `is_in_mothership: true`）被保留

#### 原因二：加载时无条件信任存档状态

在 [game_scene.py:498-516](file:///d:/Trae/pygames_dev/airwar/scenes/game_scene.py#L498-L516) 中：

```python
def restore_from_save(self, save_data) -> None:
    # ... 恢复游戏数据 ...

    if save_data.is_in_mothership:  # ← 问题点！
        self._restore_to_mothership_state()
```

**问题**：
- `restore_from_save()` 方法无条件信任存档中的 `is_in_mothership` 标志
- 没有验证当前场景是否应该进入母舰状态

#### 原因三：母舰状态恢复逻辑问题

在 [game_scene.py:511-516](file:///d:/Trae/pygames_dev/airwar/scenes/game_scene.py#L511-L516) 中：

```python
def _restore_to_mothership_state(self) -> None:
    if self._mother_ship_integrator:
        self._mother_ship_integrator.force_docked_state()
    self.game_controller.state.entrance_animation = False
    self.game_controller.state.paused = True
    self.player.rect.y = -80  # ← 玩家消失！
    self.player.rect.x = self.game_controller.state.score // 2 % 800
```

**问题**：
- 将玩家放置在 `y = -80`（屏幕上方）
- 游戏暂停
- 没有提供任何视觉反馈告知玩家处于母舰状态

### 2.3 数据流分析

```
存档保存流程（当前）：
┌──────────────────────────────────────────────────────────────┐
│ 玩家按H进入母舰                                               │
│    ↓                                                         │
│ MotherShipStateMachine → DOCKED                              │
│    ↓                                                         │
│ SceneDirector._save_game_on_quit()                           │
│    ↓ (is_docked() == True)                                   │
│ 创建存档 {is_in_mothership: true}                             │
└──────────────────────────────────────────────────────────────┘

问题场景：
┌──────────────────────────────────────────────────────────────┐
│ 玩家退出母舰 → 继续游戏                                       │
│    ↓                                                         │
│ SceneDirector._save_game_on_quit()                           │
│    ↓ (is_docked() == False) ← 不保存！                       │
│ 存档保持 {is_in_mothership: true} ← 旧数据！                   │
└──────────────────────────────────────────────────────────────┘

加载流程（当前）：
┌──────────────────────────────────────────────────────────────┐
│ 玩家登录                                                     │
│    ↓                                                         │
│ SceneDirector._check_and_get_saved_game()                    │
│    ↓                                                         │
│ PersistenceManager.load_game()                               │
│    ↓                                                         │
│ GameScene.restore_from_save()                                │
│    ↓ (is_in_mothership == true)                             │
│ _restore_to_mothership_state()                               │
│    ↓                                                         │
│ 游戏状态错误：玩家消失 + 强制母舰状态                          │
└──────────────────────────────────────────────────────────────┘
```

---

## 三、相关代码分析

### 3.1 存档创建逻辑

[game_integrator.py:96-113](file:///d:/Trae/pygames_dev/airwar/game/mother_ship/game_integrator.py#L96-L113)：

```python
def create_save_data(self) -> 'GameSaveData':
    if not self._game_scene:
        return GameSaveData()

    is_docked = self._state_machine.current_state == MotherShipState.DOCKED

    return GameSaveData(
        score=self._game_scene.score,
        # ... 其他字段 ...
        is_in_mothership=is_docked,  # ← 正确记录停靠状态
        username=self._game_scene.game_controller.state.username,
    )
```

### 3.2 存档保存条件

[scene_director.py:239-247](file:///d:/Trae/pygames_dev/airwar/game/scene_director.py#L239-L247)：

```python
def _save_game_on_quit(self, game_scene: GameScene) -> None:
    if not game_scene or not game_scene._mother_ship_integrator:
        return
    if not game_scene._mother_ship_integrator.is_docked():  # ← 仅在停靠时保存
        return
    # ... 保存逻辑 ...
```

### 3.3 存档加载逻辑

[game_scene.py:480-499](file:///d:/Trae/pygames_dev/airwar/scenes/game_scene.py#L480-L499)：

```python
def restore_from_save(self, save_data) -> None:
    if not save_data or not self.game_controller or not self.player:
        return

    self.game_controller.state.score = save_data.score
    # ... 恢复其他数据 ...

    if save_data.is_in_mothership:  # ← 问题：无条件信任
        self._restore_to_mothership_state()
```

---

## 四、安全与数据完整性问题

### 4.1 数据完整性风险

| 风险类型 | 描述 | 影响 |
|----------|------|------|
| **状态残留** | 旧的母舰状态被保留 | 玩家体验中断 |
| **无验证加载** | 存档数据无验证直接使用 | 可能加载损坏数据 |
| **状态不一致** | 游戏状态与场景不同步 | 游戏行为异常 |

### 4.2 JSON反序列化风险

[mother_ship_state.py:62-63](file:///d:/Trae/pygames_dev/airwar/game/mother_ship/mother_ship_state.py#L62-L63)：

```python
@classmethod
def from_dict(cls, data: Dict) -> 'GameSaveData':
    return cls(**data)  # ← 无类型验证，直接解包
```

**问题**：
- 不验证必需字段是否存在
- 不验证字段类型是否正确
- 如果JSON损坏或格式错误，可能抛出异常

---

## 五、建议修复方案

### 5.1 短期修复（最小改动）

**方案A：退出时始终保存非母舰状态**

修改 `scene_director.py`：

```python
def _save_game_on_quit(self, game_scene: GameScene) -> None:
    if not game_scene or not game_scene._mother_ship_integrator:
        return

    save_data = game_scene._mother_ship_integrator.create_save_data()
    # 强制设置 is_in_mothership 为 False
    save_data.is_in_mothership = False

    persistence_manager = PersistenceManager()
    persistence_manager.save_game(save_data)
```

**优点**：改动最小，一次性解决问题
**缺点**：退出时需要重新创建存档对象

### 5.2 中期修复（推荐）

**方案B：分离存档时机和状态标志**

1. 修改 `GameSaveData` 增加 `quit_during_gameplay` 字段
2. 修改退出逻辑，始终保存存档并标记退出状态
3. 修改加载逻辑，根据退出状态决定是否恢复母舰

### 5.3 长期修复（架构层面）

**方案C：完整重构存档系统**

1. 引入存档版本控制
2. 添加数据验证层
3. 实现存档迁移机制
4. 添加完整性校验（checksum）

---

## 六、测试建议

### 6.1 单元测试

```python
def test_save_not_docked_clears_mothership_flag():
    """测试：退出非母舰状态时，is_in_mothership应为False"""
    save_data = create_save_data_with_mothership_flag(True)
    # 模拟非母舰退出
    save_data.is_in_mothership = False
    assert save_data.is_in_mothership == False

def test_load_respects_is_in_mothership_false():
    """测试：is_in_mothership为False时不进入母舰状态"""
    save_data = GameSaveData(is_in_mothership=False)
    scene = GameScene()
    scene.restore_from_save(save_data)
    # 验证未进入母舰状态
    assert not scene._mother_ship_integrator.is_docked()
```

### 6.2 集成测试

1. **完整流程测试**：进入母舰 → 退出 → 继续游戏 → 退出 → 重新加载
2. **边界条件测试**：快速进入/退出母舰
3. **异常恢复测试**：模拟JSON损坏场景

---

## 七、附录

### 7.1 相关文件清单

| 文件路径 | 职责 | 问题相关度 |
|----------|------|------------|
| `airwar/game/mother_ship/persistence_manager.py` | 存档读写 | 高 |
| `airwar/game/scene_director.py` | 场景管理 | 高 |
| `airwar/scenes/game_scene.py` | 游戏场景 | 高 |
| `airwar/game/mother_ship/game_integrator.py` | 母舰集成 | 中 |
| `airwar/game/mother_ship/mother_ship_state.py` | 状态定义 | 中 |

### 7.2 相关问题编号

| 编号 | 描述 | 严重程度 |
|------|------|----------|
| SEC-001 | JSON反序列化无验证 | 中 |
| SEC-004 | 游戏存档可篡改 | 中 |
| ARC-002 | SceneDirector职责过多 | 中 |

---

**文档结束**

*本报告详细记录了母舰状态保存与读取功能中发现的问题，旨在为开发者提供清晰的问题上下文和可操作的修复指导。*
