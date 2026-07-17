# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> 完整版 AI 助手指南见 `AGENTS.md`（中文）。本文件是 Claude Code 的精简版，聚焦架构骨架与高频命令。

## 项目一句话

`main.py` → `airwar/__main__:main()` → `airwar.game.Game.run()`。Scene-based 2D 太空射击（Python + Pygame，可选 Rust + PyO3 加速）。

## 必备命令

```bash
./run.sh                              # 一键启动(自动建 venv、装依赖、按需编 Rust)
./run.sh --skip-rust                  # 跳过 Rust 扩展,走纯 Python fallback
./run.sh --rebuild-rust               # 强制重编 Rust 扩展

cd airwar_core && python3 -m maturin develop --release   # 手动编 Rust 扩展
cd ..

python3 -m pytest                     # 跑全部测试(当前 215 个用例, ~2s)
python3 -m pytest -m smoke            # 只跑 smoke 标记的
python3 -m pytest tests/test_lock_manager.py -v         # 跑单个文件
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -m pytest   # 无头(CI)

python3 -m ruff check .               # lint(仅 E/W/F,见 pyproject.toml)
python3 -m compileall -q airwar main.py   # 字节码编译自检

bash build_macos.sh                   # PyInstaller 打包(其他平台同名 build_*)
./clean.sh                            # 清理 build/dist/target/缓存, 保留源码与存档
```

测试**只覆盖架构组件**(锁仲裁、帧时间、场景生命周期、存档、视口、事件总线),**不覆盖玩法逻辑**。改实体/子弹/Boss/天赋后必须手动跑游戏验证。

## 架构骨架(必须跨多文件理解)

### 场景生命周期

`airwar/scenes/scene.py::Scene` 是所有场景的基类,要求 `enter / exit / handle_events / update / render`。`SceneManager` 负责注册与切换。

`GameScene` 已经被拆成五件套而非单个文件:
- `game_scene.py`(734 行,Fascade) → `game_scene_factory.py` 装配
- `game_scene_updater.py` — 固定步进更新
- `game_scene_renderer.py` — 渲染主分支
- `game_scene_event_dispatcher.py` — 事件总线扇出
- `game_scene_protocols.py` / `game_scene_protocol_adapter.py` — `GameSceneProtocol` 抽象
- `update_pipeline.py` — Stage 流水(UpdatePipeline 已上生产)

完整流程:`SceneDirector.run()` → `SceneSwitcher` + `SceneStatePersistence` 组件:

```
WelcomeScene → TutorialScene → GameScene
                               ├─ PauseScene
                               ├─ DeathScene
                               ├─ SettingsScene
                               └─ ExitConfirmScene
```

### 锁系统(必读)

`airwar/game/systems/lock_manager.py::LockManager` 是无敌/控制锁/暂停的**单一仲裁者**,**不要在别处再写一遍状态机**。

优先级(高→低):

```
HOMECOMING > MOTHERSHIP > BOSS_ENRAGE > PHASE_DASH > PLAYER_HIT > GIVE_UP > GAME_PAUSE > TRANSIENT
```

API 关键点:
- `acquire / acquire_or_update / acquire_strict / release / clear`
- 返回 `LockToken`,**优先用 token 释放**(直接传 `LockLayer` 释放会打 warning)
- 高优先级一旦置位,低优先级即使重新 `acquire` 也不会生效;只有高优先级释放后才回落到低优先级
- `TRANSIENT` 层用 OR-merge,多次 `apply_transient_state` 不会相互覆盖
- `expires_at` 在 `_recompute() / refresh()` 时自动清理

新增锁层前**必须**确认优先级顺序并更新 `tests/test_lock_manager.py`。

### 帧时间

`airwar/game/frame_context.py::FrameContext` + `FixedStepAccumulator` 把 wall-clock 转成固定 60 Hz `simulation_steps`,**上限 15 步/帧**。所有 gameplay update 都用 `simulation_steps`,不要直接拿 `dt`。

### 视口

`ScaledViewport` 把 1920×1080 逻辑面映射到任意物理分辨率。逻辑坐标唯一可信源,渲染时 1:1 blit 给 pygame `SCALED` 标志处理缩放。

### Rust 扩展回退契约

新增任何性能热路径函数,必须**三件同步**:

1. `airwar_core/src/lib.rs` 添加 `#[pyfunction]` 并在 `lib.rs` 注册
2. `airwar/core_bindings.py` 的 `_RUST_NAMES` 和 fallback 实现都加上
3. `airwar_core/airwar_core.pyi` 加类型存根(`mypy_path` 已指向 `airwar_core`)

扩展不可用时 `core_bindings.py` 自动回退到纯 Python,**不要假设 Rust 一定在场**(CI / 用户跳过 `--skip-rust` / macOS cargo test 链接失败等场景)。

### 持久化三块

| 内容 | 位置 |
|------|------|
| 用户账号 + 设置 + 本地排行 | `airwar/utils/database.py::UserDB`,JSON 文件,平台用户数据目录下 `users.json`(会从旧 `airwar/data/users.json` 迁移) |
| 游戏存档 | `airwar/game/mother_ship.PersistenceManager`(`game_save_service.py`,`save_restore_manager.py`),每用户独立 JSON,带版本迁移 |
| 远程排行榜 | `airwar/leaderboard/service.py`,模式由 `AIRWAR_LEADERBOARD_*` 环境变量控制,见 `.env.example` |

写文件用 temp file + `os.replace()` 保证原子。

### 日志与崩溃

集中配置在 `airwar/_log.py`,落 `$AIRWAR_CACHE_DIR`(默认 POSIX `~/.cache/airwar`,Windows `%LOCALAPPDATA%\airwar`):

- `airwar.log` — 1 MB × 2 滚动,挂在 **root logger**,所有 `airwar.*` 都落盘;`--debug` 仅抬 `airwar` logger + 控制台到 DEBUG
- `faulthandler.log` — SDL 原生崩溃(segfault 等不经过 `sys.excepthook`)的 Python 栈
- `crash-*.json` — `sys.excepthook` 转储,带 scene/frame/user 上下文(经 `register_crash_context_provider()` 注入,由 `SceneDirector._crash_context` 提供)

对局主循环(`SceneSwitcher.run_game_flow`)有逐帧异常隔离:单帧 error 记录 traceback 后跳过,**连续 5 帧**才退回主菜单(不杀进程)。transient bug 先查 `airwar.log` 的 `Frame error in ...`。

### i18n

默认 `zh_CN`,运行时 `airwar.i18n.set_locale(locale)` 切换。翻译在 `airwar/locales/{locale}.json`,`t(key, **kwargs)` 访问。缺 key 记录 warning 回退到 key 本身(**不要**在业务代码里硬编码中文字符串)。

### 输入

默认键位在 `airwar/input/input_handler.py::InputHandler.DEFAULT_BINDINGS`:

| 按键 | 行为 |
|------|------|
| 方向键 / WASD | 移动 |
| 左 Ctrl | 微调姿态 |
| 左 Shift | 加速推进;按-松 = 相位冲刺(需天赋) |
| 鼠标 | 瞄准(带自动辅瞄) |
| ESC | 暂停 |
| B 长按 2.4 s | 返航基地 |
| H 长按 3 s | 对接母舰并保存 |
| K 长按 3 s | 放弃当前出击 |
| L | 展开/收起 HUD |

## 关键约定

- **颜色 / UI 常量**走 `airwar/config/design_tokens.py::Colors / Typography / Spacing`,**禁止**业务代码里硬编码颜色元组。
- **mypy 非强制**,仍有数百历史错误(`docs/audits/type_interface_audit_report.md`)。新代码尽量加类型注解,但不要去修历史错误。
- **Python 3.12 风格**,ruff 仅启用 `E / W / F`(`pyproject.toml`),行宽 120。
- **最小改动**:个人业余项目,为单用例引入抽象 / 加配置开关 / 加防御代码 = 不需要。匹配既有风格,哪怕你自己会写不同。
- **预提交自检**:`ruff check .` + `compileall -q airwar main.py` + `pytest tests/`(三个都要绿)。

## 历史上下文(避免重复踩坑)

来自项目 memory 的高频反馈:

1. **`@given(Hypothesis)` 必须 `unique_by` 收敛到生产契约**,不要只靠 seed 运气过 CI。历史上 collision-symmetry 反例藏了 6 周(2026-06-10 才扫到)。
2. **`__pycache__` / `cargo` 缓存可能让"CI 绿 = 没测过"成为假象**。重构 f32 断言必须用 exact-f32 inputs + tolerance + property,否则缓存的 old binary 会蒙混过关。
3. **macOS arm64 上 `cargo test` 链接 `__Py_NoneStruct` 必败**,是 PyO3 已知限制,**非代码 bug**。真测试在 Python 侧 `tests/test_*_bindings.py`。
4. **改 Rust 必须三件同步**(见上 §Rust 扩展回退契约)。
