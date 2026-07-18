# Air War（空战）项目指南

> 本文件面向 AI 编码助手。它总结了项目结构、构建流程、代码约定和常见注意事项。阅读前默认你对本项目一无所知。

## 1. 项目概览

Air War（空战）是一款 2D 太空射击游戏，采用 **Python + Pygame** 构建，并通过可选的 **Rust + PyO3** 扩展加速性能热点。项目处于个人业余开发阶段，核心目标是稳定、可玩的主流程。

主要特性：

- 场景驱动（Scene-based）生命周期：Welcome、Tutorial、Game、Pause、Death、Settings、ExitConfirm。
- 玩家与 Boss 使用分层状态机（HSM）。
- 集中式优先级锁系统 `LockManager` 管理无敌、控制锁与暂停状态。
- 可选 Rust 扩展负责碰撞检测、向量运算、批量移动、粒子与子弹更新；未安装时自动回退到纯 Python。
- 本地 JSON 用户数据库 + 可选 FastAPI + SQLite 远程排行榜服务。
- 支持简体中文（`zh_CN`）与英文（`en_US`）国际化。

项目入口：

- `main.py` → `airwar.__main__:main()` → `airwar.game.Game.run()`
- 命令行入口：`airwar`（由 `pyproject.toml` 的 `[project.scripts]` 注册）

## 2. 技术栈与配置

| 层级 | 技术 |
|------|------|
| 运行时 | Python 3.11+、Pygame 2.6+、Pillow 12.2+、NumPy 1.26+ |
| 可选原生扩展 | Rust 2021 edition + PyO3 0.22，通过 `maturin` 构建 |
| 远程排行榜服务 | FastAPI 0.115+、uvicorn 0.34+ |
| 打包 | PyInstaller 6+（单文件 `AirWar.spec`） |
| 代码检查 | ruff 0.8+、mypy（非强制，仅参考） |
| 测试 | pytest 8+ |

关键配置文件：

- `pyproject.toml`：Python 包元数据、依赖、ruff 配置、mypy 配置、脚本入口。
- `requirements.txt`：运行时依赖。
- `requirements-dev.txt`：开发依赖（包含 maturin、PyInstaller、ruff、pytest）。
- `airwar_core/Cargo.toml`：Rust crate 配置（`cdylib`）。
- `airwar_core/pyproject.toml`：maturin 构建配置。
- `AirWar.spec`：PyInstaller 打包脚本，被 `build_*.sh` / `build_windows.bat` 共用。

## 3. 目录结构

```text
airwar/                 # 主 Python 包
  __main__.py           # CLI 入口
  game/                 # 游戏引擎、场景导演、管理器、系统
    frame_context.py    # 固定时间步进（FrameContext / FixedStepAccumulator）
    scene_director.py   # 高层场景流程编排
    scaled_viewport.py  # 逻辑分辨率到显示分辨率的映射
    managers/           # 碰撞、生成、子弹、Boss、输入、锁仲裁等
    systems/            # 生命、奖励、难度、通知、天赋、存档等
    rendering/          # 游戏渲染、HUD、背景
    spawners/           # 敌人子弹等生成器
    scene_director_components/  # SceneSwitcher / SceneStatePersistence
  scenes/               # 场景实现
    scene.py            # Scene 抽象基类与 SceneManager
    welcome_scene.py
    tutorial_scene.py
    game_scene.py
    game_scene_updater.py
    game_scene_renderer.py
    game_scene_factory.py
    game_scene_protocols.py / game_scene_protocol_adapter.py
    pause_scene.py / death_scene.py / settings_scene.py / exit_confirm_scene.py
  entities/             # 玩家、敌人、Boss、子弹、运动策略等
    base.py
    player.py
    enemy/
    enemy/boss/
    bullet.py
    movement_strategies.py
  ui/                   # UI 组件、面板、特效
  input/                # 输入处理（PygameInputHandler）
  config/               # 常量、设计 token、难度配置、教程配置
  leaderboard/          # 排行榜客户端、服务层、FastAPI 服务器
  utils/                # 数据库、字体、精灵、平台路径等辅助工具
  i18n/                 # 轻量级 JSON 国际化
  locales/              # 翻译文件（zh_CN.json / en_US.json）
  assets/               # 字体、音频、精灵图
  data/generated_assets/# 运行时生成的缓存素材

airwar_core/            # Rust 原生扩展
  src/
    lib.rs              # PyO3 模块导出
    vector2.rs          # 向量运算
    collision.rs        # 批量碰撞检测
    movement.rs         # 批量移动与寻敌
    particles.rs        # 粒子生成与渲染
    sprites.rs          # 发光精灵图生成
    starfield.rs        # 星空背景
    bullets.rs          # 子弹批量更新
  Cargo.toml
  pyproject.toml

tests/                  # pytest 测试（架构组件）
docs/audits/            # 类型接口审计报告等
scripts/                # 工具脚本
```

## 4. 构建与运行

### 4.1 推荐：一键启动脚本

脚本会自动检测 Python、创建/复用 `.venv`、同步依赖、按需编译 Rust 扩展并启动游戏。

| 平台 | 命令 |
|------|------|
| Linux / macOS | `chmod +x run.sh && ./run.sh` |
| Windows | 双击 `run.bat` |

常用选项：

```bash
./run.sh --prepare-only       # 仅准备运行环境
./run.sh --skip-rust          # 使用纯 Python 回退路径启动
./run.sh --rebuild-rust       # 强制重新编译 Rust 扩展
./run.sh -- --debug           # 将参数转发给游戏（DEBUG 级别日志；日志文件始终写入，见 7.9）
```

如需同时启动本地排行榜服务器：

```bash
# Linux / macOS
chmod +x run_with_server.sh && ./run_with_server.sh
# Windows
run_with_server.bat
```

可用 `./run_with_server.sh --port 8001 --debug` 指定服务端口与调试模式。

### 4.2 手动构建 Rust 扩展

```bash
cd airwar_core
python3 -m maturin develop --release
cd ..
```

若 `airwar_core` 不可用，游戏会自动使用 `airwar/core_bindings.py` 中的纯 Python 回退实现。

### 4.3 打包独立可执行文件

```bash
# Linux
bash build_linux.sh
# macOS
bash build_macos.sh
# Windows
build_windows.bat
```

输出目录：`dist/AirWar/`。打包需要 Python 3.11+、Rust 工具链与对应平台编译器。

### 4.4 清理构建产物

```bash
./clean.sh        # 删除 build、dist、target、缓存等，保留源码与存档
./uninstall.sh    # 额外删除 .venv（Linux / macOS）
```

## 5. 测试

运行全部测试：

```bash
python3 -m pytest tests/ -v
```

当前测试覆盖核心架构组件：帧时间上下文、锁仲裁、场景生命周期、存档持久化、缩放视口坐标转换、游戏场景事件总线。不覆盖渲染与具体玩法逻辑。

最近验证结果（2026-07-17）：`200 passed`，`ruff check .` 全绿，`compileall -q airwar main.py` 通过。

## 6. 代码风格与检查

- 使用 **ruff** 进行代码检查，配置在 `pyproject.toml`。
- 目标 Python 版本：`py312`。
- 行宽：`120`。
- 仅启用基础正确性规则：`E`、`W`、`F`（pycodestyle 错误/警告、pyflakes）。不启用风格偏好规则（B、I、SIM、C4、UP、RUF 等）。
- 部分 `__init__.py` 和 `core_bindings.py` 允许未使用导入（`F401`）。

提交前请运行：

```bash
python3 -m ruff check .
python3 -m compileall -q airwar main.py
```

## 7. 架构要点

### 7.1 场景生命周期

所有场景继承 `airwar.scenes.scene.Scene`，必须实现：

- `enter(**kwargs)`
- `exit()`
- `handle_events(event)`
- `update(*args, **kwargs)`
- `render(surface)`

`SceneManager` 负责注册与切换场景，切换时会调用当前场景的 `exit()` 与新场景的 `enter()`。

### 7.2 游戏主循环

`Game` 创建窗口、注册场景，然后调用 `SceneDirector.run()`。`SceneDirector` 使用内部组件 `SceneSwitcher` 和 `SceneStatePersistence` 管理流程：

```text
WelcomeScene → TutorialScene → GameScene
                    ├─ PauseScene
                    ├─ DeathScene
                    ├─ SettingsScene
                    └─ ExitConfirmScene
```

### 7.3 锁系统

`airwar.game.systems.lock_manager.LockManager` 按优先级统一仲裁无敌、控制锁与暂停：

```text
HOMECOMING > MOTHERSHIP > BOSS_ENRAGE > PHASE_DASH > PLAYER_HIT > GIVE_UP > GAME_PAUSE > TRANSIENT
```

相关类：

- `LockLayer`：优先级枚举。
- `LockRequest`：请求参数（无敌、控制锁、暂停、静默无敌、无敌时长、过期时间）。
- `LockToken`：`acquire*` 返回的能力令牌，建议用令牌释放锁；直接传 `LockLayer` 释放仍可工作，但会记录 warning。
- `acquire` / `acquire_or_update` / `acquire_strict` / `release` / `clear`。

语义要点：

- 无敌状态取最高优先级且设置了 `invincible=True` 的层。
- 控制锁与暂停按优先级仲裁：一旦高优先级层置位，低优先级层不再覆盖；高优先级层释放后低优先级层生效。
- `expires_at` 到期的非永久锁会在 `_recompute()` / `refresh()` 时自动清理。
- `TRANSIENT` 层用于临时状态，多个 `apply_transient_state` 调用会合并布尔值，而不是相互覆盖。

### 7.4 帧时间

`FrameContext` 与 `FixedStepAccumulator` 将 wall-clock 时间转换为固定 60 Hz 的 `simulation_steps`，避免浮点误差和掉帧后的过度模拟。上限为 15 步/帧。

### 7.5 缩放视口

`ScaledViewport` 将 1920×1080 的逻辑渲染面映射到任意显示分辨率。配合 pygame `SCALED` 标志，窗口缩放由 SDL2 GPU 渲染器处理，程序中通常为 1:1 blit。

### 7.6 Rust 扩展回退

`airwar/core_bindings.py` 在 `airwar_core` 不可用时提供纯 Python 实现。新增 Rust 函数必须同时：

1. 在 `airwar_core/src/lib.rs` 中导出。
2. 在 `airwar/core_bindings.py` 的 `_RUST_NAMES` 与 fallback 中实现。
3. 提供 `airwar_core.pyi` 类型存根（`mypy_path` 已指向 `airwar_core`）。

### 7.7 持久化

- 用户账户与本地排行榜：`airwar.utils.database.UserDB`，基于 JSON 文件，路径为平台用户数据目录下的 `users.json`（会从旧版 `airwar/data/users.json` 迁移）。
- 游戏存档：`airwar.game.mother_ship.PersistenceManager`，每个用户一个 JSON 存档文件，支持版本迁移。
- 用户设置：保存在 `UserDB` 的 `settings` 字段中。

### 7.8 排行榜

`airwar.leaderboard.service.LeaderboardService` 协调本地 `UserDB` 与远程服务器。模式由环境变量控制：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `AIRWAR_LEADERBOARD_URL` | `http://localhost:8000` | 远程服务器地址；非法 URL 回退到默认值 |
| `AIRWAR_LEADERBOARD_MODE` | `auto` | `auto` / `remote` / `local` |
| `AIRWAR_LEADERBOARD_TIMEOUT` | `3.0` | HTTP 超时（秒）；超出 `0 < t <= 30` 回退到默认值 |
| `AIRWAR_LEADERBOARD_DB_PATH` | 平台数据目录 | 服务端 SQLite 路径 |
| `AIRWAR_LEADERBOARD_CORS_ORIGINS` | `http://localhost,http://127.0.0.1` | 服务端 CORS 来源，逗号分隔；`*` 或空字符串为开发模式 |

手动启动服务器：

```bash
pip install -e ".[server]"
python -m airwar.leaderboard.server --port 8000 --db-path ./leaderboard.db
```

### 7.9 日志与崩溃转储

集中配置在 `airwar/_log.py`，产物目录为 `get_cache_dir()`（`$AIRWAR_CACHE_DIR` 优先，否则 POSIX 下 `~/.cache/airwar`，Windows 下 `%LOCALAPPDATA%\airwar`）：

- `airwar.log`：常驻滚动文件日志（1 MB × 2），handler 挂在 **root** logger 上，所有模块 logger（含 `airwar.*` 与类名 logger）都会落盘；`--debug` 仅提升 `airwar` logger 与控制台到 DEBUG。
- `faulthandler.log`：`faulthandler` 输出，SDL 层原生崩溃（segfault 等不经过 `sys.excepthook` 的崩溃）在此留下 Python 栈。
- `crash-*.json`：`sys.excepthook` 捕获的未处理异常转储（异常、traceback、平台信息、上下文）。实时游戏状态（场景名、帧计数、用户等）通过 `register_crash_context_provider()` 注入，目前由 `SceneDirector._crash_context` 提供；transient 崩溃排查先看 `airwar.log` 里的 `Frame error in ...` 记录。

对局主循环（`SceneSwitcher.run_game_flow`）与其他场景循环一样有逐帧异常隔离：单帧异常记录 traceback 后跳过，连续 5 帧出错退回主菜单而不是杀掉整个进程。

## 8. 国际化

默认语言为 `zh_CN`（保留历史中文 UI 字符串）。运行时通过 `airwar.i18n.set_locale(locale)` 切换。翻译文件位于 `airwar/locales/{locale}.json`，使用 `t(key, **kwargs)` 访问，缺失 key 会记录警告并回退到 key 本身。

## 9. 输入映射

默认键位定义在 `airwar.input.input_handler.InputHandler.DEFAULT_BINDINGS`：

| 按键 | 功能 |
|------|------|
| 方向键 / WASD | 移动 |
| 左 Ctrl | 微调姿态（precision） |
| 左 Shift | 加速推进；按下松开触发相位冲刺（需天赋） |
| 鼠标 | 瞄准（带自动辅瞄） |
| ESC | 暂停 |
| B 长按 2.4 秒 | 返航基地 |
| H 长按 3 秒 | 对接母舰并保存 |
| K 长按 3 秒 | 放弃当前出击 |
| L | 展开/收起 HUD |

## 10. 安全注意事项

- 用户密码使用 `hashlib.pbkdf2_hmac("sha256", ...)` 与随机 salt 存储，迭代次数 `_HASH_ITERATIONS = 100_000`。
- 数据库写操作使用临时文件 + `os.replace()` 保证原子性。
- `.env` 与凭证文件已被 `.gitignore` 排除。
- 远程排行榜服务使用 HTTP（本地/局域网场景），不要直接暴露到公网。
- 不要提交游戏存档、`.venv`、构建产物或 `airwar/data/generated_assets`。

## 11. AI 助手常见注意事项

1. **不要臆测运行时代码**：项目测试覆盖的是架构组件，玩法逻辑没有自动化测试。改动实体、Boss、子弹、天赋等玩法代码后，应手动运行游戏验证。
2. **Rust 与 Python 必须同步**：修改性能热路径时，同时更新 Rust 实现、`core_bindings.py` fallback 和 `.pyi` 存根。
3. **不要破坏锁优先级**：新增锁层前确认优先级顺序，并更新 `tests/test_lock_manager.py`。
4. **保持最小改动**：本项目是个人业余项目，优先简单直接，避免为单一用例引入抽象。
5. **颜色/UI 常量**：统一在 `airwar/config/design_tokens.py` 的 `Colors` / `Typography` / `Spacing` 中注册，不要在业务代码中硬编码颜色元组。
6. **类型检查仅供参考**：`mypy` 当前仍有数百个历史错误（见 `docs/audits/type_interface_audit_report.md`）。新增代码尽量加类型注解，但不要求一次性修复全部历史问题。
7. **运行前检查**：提交前执行 `ruff check .`、`compileall -q airwar main.py` 和 `pytest tests/`。

## 12. 高优先级执行任务（2026-07-17 标记）

以下任务由项目所有者于 2026-07-17 标记为**高优先级**，按编号顺序执行。完成某一项后，在该行「状态」列标注完成日期与提交哈希。

| # | 任务 | 背景与现状 | 验收标准 | 关键模块 | 状态 |
|---|------|-----------|---------|---------|------|
| P0 | 提交已验证的未提交改动 | 战机素材重绘、主界面点击失灵修复、爆炸导弹渲染崩溃修复已在工作区验证（193 项测试通过 + 实机游玩通过 Boss #4），尚未提交 | 三个主题分别成 commit 合入 master | `utils/_sprites_ships.py`、`scenes/welcome_scene.py`、`utils/_sprites_bullets.py`、`tests/test_welcome_scene_clicks.py`、`tests/test_sprites_bullets.py`、`scripts/render_ship_sprites.py` | ✅ 2026-07-17（6017217 / 8ca1b97 / 8a42f5f） |
| P1 | Boss 狂暴抓取 × 母舰对接的位置冲突 | 玩家在母舰对接状态下触发 Boss 狂暴，Boss 实施抓取（aim-dash / enrage path）后，玩家舰船出现在意料之外的位置。疑似狂暴位移逻辑与对接位置锁（`GameScene.update` 第 13 步）相互打架 | 明确定义对接状态下的抓取行为（跳过抓取，或将玩家刚性绑定于母舰）；任意时序下玩家坐标合法；手动完整验证「对接中触发狂暴→抓取→脱离」全流程 | `entities/enemy/boss/`（`boss_movement.py` aim-dash / enrage 路径）、`scenes/game_scene.py`、`game/managers/game_loop_manager.py` | 未开始 |
| P2 | 狂暴期间母舰应被锁定并停火 | 设计意图（所有者原话）：Boss 狂暴同样锁定母舰位置，但玩家不会受到伤害；母舰此时停止开火，防止造成"仅开火但造不成伤害"的假象。现状：对接中触发狂暴时母舰仍可自由移动并开火（`LockLayer.MOTHERSHIP`=80 高于 `BOSS_ENRAGE`=60，狂暴锁不住母舰行为） | 狂暴激活期间：母舰位置锁定、武器停火、玩家保持无敌；狂暴结束后全部恢复正常；为 LockManager 交互新增回归测试 | `game/managers/lock_manager.py`、`game/managers/game_loop_manager.py::_sync_boss_enrage_lock`、`game/mother_ship/game_integrator.py` | 未开始 |
| P3 | Rust 扩展逻辑审计 → 本地重编 | 本地 wheel 过时：17 个绑定测试失败、启动报 `missing functions ... falling back`。**先**审计 Rust 源码与 `core_bindings.py` Python fallback 的逻辑一致性，确认正确后**再**重编本地扩展 | 审计结论记录在案（哪个函数、哪侧、是否一致）；重编安装后 17 个绑定测试全部通过 | `airwar_core/src/*.rs`、`airwar/core_bindings.py` | ✅ 2026-07-17：绑定测试套件即一致性审计（Rust 与 fallback 输出逐函数比对），wheel 0.1.0→0.2.0 重编安装后 210 项测试全绿，启动 fallback 警告消失 |
| P4 | 排行榜服务器集成检测 | FastAPI 远程排行榜（`run_with_server.py`）从未实测，仅单元测试覆盖 | 服务器启动、成绩提交、排行榜拉取全链路手动验证通过；发现的问题单独立项 | `airwar/leaderboard/`、`run_with_server.py` | 未开始 |
| P5 | 固定攻击音效资产 | `bullet_fire` 目前由 numpy + `pygame.sndarray` 按各平台 mixer 采样率**程序生成**，每个平台音色都不同；`airwar/assets/audio/` 目录为空 | 生成一份固定音频文件随仓库分发，全平台播放一致；文件缺失时保留程序生成回退；确认 PyInstaller 打包（`AirWar.spec`）包含该资产 | `airwar/audio/sound_manager.py`、`airwar/assets/audio/`、`AirWar.spec` | 未开始 |
| P6 | 次要功能回归检测 | 部分边缘功能缺乏近期实机验证 | 手动过一遍：相位冲刺、返航（homecoming）、投降（give-up）流程、设置项持久化、窗口缩放/全屏切换；发现问题单独立项 | 多模块 | 未开始 |
| P7 | 可变分辨率：固定长宽比 + 大/中/小三档 | 窗口默认 1920×1080 且可自由拖放（`Window._min_size`=1024×768 还是 4:3），VIDEORESIZE 任意改变宽高比，pygame `SCALED` 把 1920×1080 逻辑面直接拉伸到窗口，非 16:9 窗口下画面变形；设置界面无分辨率选项 | 提供大/中/小三档窗口尺寸且全部锁定 16:9（建议 2560×1440 / 1920×1080 / 1280×720），设置界面可切换并持久化到 `UserDB.settings`，启动时按上次档位恢复；任意档位与全屏切换下画面不变形、鼠标坐标映射正确 | `airwar/window/window.py`、`game/scaled_viewport.py`、`scenes/settings_scene.py`、`utils/database.py`（settings 字段） | 未开始 |

执行备注：

- P1 / P2 都涉及 `LockManager` 优先级交互，动手前重读第 7 节架构要点中的锁层表与 `tests/test_lock_manager.py`；两个 bug 建议同一轮实机验证。
- P3 重编命令：`cd airwar_core && maturin build --release && pip install --force-reinstall target/wheels/airwar_core-*.whl`（无需 venv）；或 `maturin develop --release`（需 venv）。
- P5 的一次性音频生成脚本放 `scripts/`，产出物（如 `bullet_fire.wav`）提交进 `airwar/assets/audio/`。
- P7 注意 `SCALED` 模式下 display surface 保持逻辑分辨率、鼠标事件用 OS 窗口坐标（见 `Window.get_size` 注释），档位切换后必须验证 `ScaledViewport` 的鼠标换算；`Window._min_size` 目前是 4:3（1024×768），随本任务一并改为 16:9。
