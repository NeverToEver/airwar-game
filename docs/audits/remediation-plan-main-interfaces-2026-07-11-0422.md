# Air War 主要函数接口健壮性全量修复计划

Date: 2026-07-11
Based on: `docs/audits/review-findings-main-interfaces-2026-07-11-0422.md`

---

## 1. 目标与范围

### 1.1 目标

基于 `review-findings-main-interfaces-2026-07-11-0422.md` 的 38 项发现，制定可逐项执行的全量修复计划，提升以下维度：

1. **数据安全**：防止存档/数据库损坏、并发写入冲突、数据丢失。
2. **运行稳定**：主循环、场景生命周期、核心管理器具备异常隔离与降级能力。
3. **接口一致**：Python 实体基类、Rust/Python 边界、输入抽象等接口行为统一。
4. **安全加固**：排行榜服务端、用户认证、国际化路径等减少攻击面。
5. **可维护性**：清理死代码、明确契约、补充测试。

### 1.2 范围

覆盖以下模块：

- `airwar/utils/database.py`
- `airwar/game/mother_ship/persistence_manager.py`
- `airwar/leaderboard/`（server/config/client/service/store/models）
- `airwar/game/scene_director.py`
- `airwar/game/scene_director_components/scene_switcher.py`
- `airwar/scenes/scene.py`
- `airwar/game/systems/lock_manager.py`
- `airwar/game/frame_context.py`
- `airwar/game/scaled_viewport.py`
- `airwar/input/input_handler.py`
- `airwar/entities/base.py`
- `airwar/entities/player.py` / `player_state.py`
- `airwar/entities/enemy/boss/boss.py`
- `airwar/game/managers/bullet_manager.py`
- `airwar/game/managers/game_loop_manager.py`
- `airwar/game/managers/boss_manager.py`
- `airwar/core_bindings.py`
- `airwar_core/src/`（sprites/particles/starfield/bullets/collision/movement）
- `airwar/i18n/__init__.py`
- 相关类型存根与测试

### 1.3 不涉及范围

- 不改动游戏核心玩法数值、美术资源、音效逻辑。
- 不重构整体架构，仅修复接口健壮性与边界行为。
- 不引入新的第三方依赖（除非明确标注为可选）。

---

## 2. 执行原则

1. **分批提交**：每个模块或每个优先级批次作为一次独立提交，便于回滚与评审。
2. **测试先行**：每个修复项必须伴随测试或至少不破坏现有 `62 passed`。
3. **Rust/Python 同步**：修改 Rust 扩展时，必须同步更新 `core_bindings.py` fallback 与 `.pyi` 存根。
4. **最小改动**：仅修改与修复直接相关的代码，不借机重构无关逻辑。
5. **文档同步**：修改 `AGENTS.md` 中若相关约定发生变化则同步更新。

---

## 3. 修复批次总览

| 批次 | 主题 | 优先级 | 预计文件数 | 依赖批次 |
|------|------|--------|-----------|----------|
| A | 持久化与用户数据安全 | Critical | 4 | 无 |
| B | 排行榜服务端安全 | Critical | 4 | 无 |
| C | 主循环与场景生命周期异常隔离 | Major | 4 | 无 |
| D | LockManager 接口与语义 | Major | 3 | 无 |
| E | 帧时间、视口、输入边界 | Major/Minor | 3 | 无 |
| F | 实体与战斗系统边界 | Major | 6 | 无 |
| G | Rust ↔ Python 边界一致 | Major | 8 | 无 |
| H | 杂项与测试补全 | Minor/Nit | 6 | A-G |

---

## 4. 详细修复方案

---

### 4.1 批次 A：持久化与用户数据安全

#### A1 — 用户数据库损坏自动备份与重置

- **问题编号**：Critical DATA-1
- **文件**：`airwar/utils/database.py`
- **当前行为**：`SimpleDB._load()` 在 `JSONDecodeError` 时直接抛出 `DatabaseError`，不会自动备份或重置。
- **目标**：与 `PersistenceManager` 保持一致，损坏时备份为 `.corrupted.{timestamp}.bak`，然后重置为空数据库。
- **修复步骤**：
  1. 在 `_load()` 中捕获 `JSONDecodeError`。
  2. 若文件存在且非空，备份为 `{db_path}.corrupted.{timestamp}.bak`。
  3. 删除原文件，并保存空 `{}`。
  4. 记录 `logger.error` 与 `logger.info`。
- **建议代码**：

```python
# airwar/utils/database.py
import time

class SimpleDB:
    def _load(self) -> dict[str, Any]:
        try:
            with open(self.db_path, encoding="utf-8") as f:
                result: dict[str, Any] = json.load(f)
                return result
        except json.JSONDecodeError as e:
            if os.path.exists(self.db_path) and os.path.getsize(self.db_path) > 0:
                backup_path = f"{self.db_path}.corrupted.{int(time.time())}.bak"
                try:
                    os.replace(self.db_path, backup_path)
                except OSError as move_err:
                    logger.error("Failed to backup corrupted database: %s", move_err)
                    try:
                        os.remove(self.db_path)
                    except OSError:
                        pass
            logger.error("Account database corrupted; resetting to empty: %s", self.db_path)
            self._save({})
            return {}
        except OSError as e:
            raise DatabaseError(f"Failed to load account database: {self.db_path}") from e
```

- **验证方法**：
  - 写入损坏 JSON 到临时文件，调用 `SimpleDB(tmp_path)._load()`，确认返回 `{}` 且备份文件存在。
  - 现有 `test_persistence.py` 仍通过。

#### A2 — 持久化并发写入：唯一临时文件名 + 文件锁

- **问题编号**：Critical DATA-2
- **文件**：`airwar/utils/database.py`、`airwar/game/mother_ship/persistence_manager.py`
- **当前行为**：使用固定 `.tmp` 文件名，多进程/实例同时保存会互相覆盖。
- **目标**：使用 `tempfile.NamedTemporaryFile` 生成唯一临时文件，并可选加文件锁保护读-改-写。
- **修复步骤**：
  1. 引入 `tempfile` 与 `fcntl`（POSIX）/ `msvcrt`（Windows）或依赖 `filelock`（若允许新增可选依赖）。
  2. 将 `_save()` 改为：
     - 创建 `NamedTemporaryFile(dir=db_dir, delete=False, suffix=".tmp")`。
     - 写入、flush、fsync。
     - `os.replace(tmp.name, db_path)`。
     - 清理失败时删除 tmp。
  3. 在 `SimpleDB` 加可选文件锁，保护 `load-modify-save`。
- **建议代码（不引入新依赖）**：

```python
# airwar/utils/database.py
import tempfile

def _save(self, data: dict[str, Any]) -> None:
    db_dir = os.path.dirname(self.db_path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=db_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, self.db_path)
    except (OSError, TypeError) as e:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            logger.warning("Failed to remove temporary account database file: %s", tmp_path, exc_info=True)
        raise DatabaseError(f"Failed to save account database: {self.db_path}") from e
```

- **文件锁（可选但推荐）**：
  - 若允许新增 `filelock` 到 `requirements.txt`：

```python
from filelock import FileLock

class SimpleDB:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path if db_path is not None else _DEFAULT_DB_PATH
        self._lock = FileLock(f"{self.db_path}.lock")
        ...

    def _atomic_load_modify_save(self, modifier: Callable[[dict], None]) -> None:
        with self._lock:
            data = self._load()
            modifier(data)
            self._save(data)
```

- **验证方法**：
  - 多进程并发写入测试，确认最终 JSON 合法且数据不丢失。
  - `PersistenceManager` 做同样改造后验证。

#### A3 — 缺失 salt 时拒绝验证而非回退到 user_id

- **问题编号**：Critical SEC-1
- **文件**：`airwar/utils/database.py`
- **当前行为**：`verify_user` 使用 `data[user_id].get("salt", user_id)`，salt 可预测。
- **目标**：缺失 salt 视为账户凭证损坏，拒绝验证并记录错误，可选触发密码重置流程。
- **修复步骤**：
  1. 在 `verify_user` 中检查 `salt` 是否存在且为字符串。
  2. 若缺失，记录 `logger.error`，返回 `False`。
  3. 登录面板可提示“账户凭证异常，请联系开发者或重置密码”。
- **建议代码**：

```python
def verify_user(self, user_id: str, password: str) -> bool:
    data = self._load()
    if user_id not in data:
        return False
    stored = data[user_id].get("password")
    if not stored:
        return False
    salt = data[user_id].get("salt")
    if not isinstance(salt, str) or not salt:
        logger.error("User %r is missing a valid salt; refusing verification", user_id)
        return False
    return secrets.compare_digest(stored, self._hash_password(password, salt))
```

- **验证方法**：
  - 构造无 salt 用户记录，调用 `verify_user` 应返回 `False`。
  - 正常 salt 用户仍能验证通过。

#### A4 — 明确拒绝 bool 类型分数

- **问题编号**：Minor PAT-13
- **文件**：`airwar/utils/database.py`
- **当前行为**：`bool` 是 `int` 子类，会被转换为 `0/1`。
- **目标**：明确拒绝 `bool`，与注释一致。
- **修复步骤**：
  1. 将条件 `isinstance(score, bool)` 放在 `try/except` 之前直接拒绝。
- **建议代码**：

```python
def submit_score(self, name: str, score: int) -> int:
    if isinstance(score, bool):
        return 0
    if not isinstance(score, int):
        try:
            score = int(score)
        except (TypeError, ValueError):
            return 0
    if score < 0:
        score = 0
    ...
```

---

### 4.2 批次 B：排行榜服务端安全

#### B1 — 收紧 CORS 配置

- **问题编号**：Critical SEC-2
- **文件**：`airwar/leaderboard/server.py`
- **当前行为**：`allow_origins=["*"]`、`allow_methods=["*"]`。
- **目标**：默认只允许本地/实际游戏客户端来源，保留环境变量覆盖能力。
- **修复步骤**：
  1. 在 `LeaderboardConfig` 增加 `cors_origins` 配置项，默认 `["http://localhost", "http://127.0.0.1"]`。
  2. 环境变量 `AIRWAR_LEADERBOARD_CORS_ORIGINS` 可覆盖，逗号分隔；空字符串或 `*` 视为开发模式。
  3. `server.py` 使用 `config.cors_origins`。
- **建议代码**：

```python
# airwar/leaderboard/config.py
_DEFAULT_CORS_ORIGINS = "http://localhost,http://127.0.0.1"

class LeaderboardConfig:
    def __init__(self) -> None:
        ...
        raw_origins = os.environ.get("AIRWAR_LEADERBOARD_CORS_ORIGINS", _DEFAULT_CORS_ORIGINS)
        self.cors_origins = [o.strip() for o in raw_origins.split(",") if o.strip()] or ["http://localhost"]
```

```python
# airwar/leaderboard/server.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

- **验证方法**：
  - 启动服务端，非允许来源的 preflight 请求应被拒绝。
  - 允许来源请求正常返回。

#### B2 — 限制 `/leaderboard?limit=` 范围

- **问题编号**：Critical SEC-3
- **文件**：`airwar/leaderboard/server.py`、`airwar/leaderboard/models.py`
- **当前行为**：`limit` 只校验为 `int`，无上限。
- **目标**：限制 `1 <= limit <= 100`。
- **修复步骤**：
  1. 在 Pydantic 模型中增加 `Field(..., ge=1, le=100)`。
  2. 或在端点函数中显式校验。
- **建议代码**：

```python
# airwar/leaderboard/models.py
from pydantic import Field

class LeaderboardQueryParams(BaseModel):
    limit: int = Field(10, ge=1, le=100)
```

```python
# airwar/leaderboard/server.py
from fastapi import Query
from airwar.leaderboard.models import LeaderboardQueryParams

@app.get("/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(limit: int = Query(10, ge=1, le=100)) -> LeaderboardResponse:
    entries = leaderboard_store.get_leaderboard(limit=limit)
    return LeaderboardResponse(entries=entries, total=leaderboard_store.count())
```

- **验证方法**：
  - 请求 `limit=101` 返回 `422 Unprocessable Entity`。
  - 请求 `limit=50` 正常返回。

#### B3 — 校验 timeout 与 URL

- **问题编号**：Major CFG-1、CFG-2
- **文件**：`airwar/leaderboard/config.py`
- **当前行为**：`timeout` 可为 `0` 或 `inf`；URL 可为空字符串。
- **目标**：限制 `0 < timeout <= 30`，URL 非空且包含 scheme/host。
- **修复步骤**：
  1. 使用 `urllib.parse.urlparse` 校验 URL。
  2. `timeout` 校验范围。
- **建议代码**：

```python
from urllib.parse import urlparse

_MAX_TIMEOUT = 30.0

class LeaderboardConfig:
    def __init__(self) -> None:
        url = os.environ.get("AIRWAR_LEADERBOARD_URL", _DEFAULT_URL).rstrip("/")
        if not url or urlparse(url).scheme not in ("http", "https") or not urlparse(url).hostname:
            logger.warning("Invalid AIRWAR_LEADERBOARD_URL %r, using default", url)
            url = _DEFAULT_URL
        self.url = url

        try:
            timeout = float(os.environ.get("AIRWAR_LEADERBOARD_TIMEOUT", _DEFAULT_TIMEOUT))
        except ValueError:
            logger.warning("Invalid AIRWAR_LEADERBOARD_TIMEOUT, using default %s", _DEFAULT_TIMEOUT)
            timeout = float(_DEFAULT_TIMEOUT)
        if not (0 < timeout <= _MAX_TIMEOUT):
            logger.warning("AIRWAR_LEADERBOARD_TIMEOUT out of range, clamping to %s", _DEFAULT_TIMEOUT)
            timeout = float(_DEFAULT_TIMEOUT)
        self.timeout = timeout
        ...
```

- **验证方法**：
  - 设置 `AIRWAR_LEADERBOARD_TIMEOUT=0` 或 `inf`，确认被重置为默认值。
  - 设置 `AIRWAR_LEADERBOARD_URL=""`，确认使用默认 URL。

#### B4 — 服务端 `player_name` 长度本地校验

- **问题编号**：Minor SEC-4
- **文件**：`airwar/utils/database.py`
- **目标**：本地 `submit_score` 对 `player_name` 限制 1–32 字符，与远程 Pydantic 模型一致。
- **修复步骤**：
  1. 在 `submit_score` 中加入长度检查。
- **建议代码**：

```python
_MAX_NAME_LEN = 32
player_name = name if isinstance(name, str) and name else "Guest"
player_name = player_name[:_MAX_NAME_LEN]
```

---

### 4.3 批次 C：主循环与场景生命周期异常隔离

#### C1 — 主循环帧级异常隔离

- **问题编号**：Major ERR-1
- **文件**：`airwar/game/scene_director_components/scene_switcher.py`
- **当前行为**：`_run_scene_loop` 中 `update()` / `render()` / `flip()` / `handle_events()` 任一异常直接退出。
- **目标**：单帧异常不退出，记录错误并跳过坏帧；连续多帧异常再退出或回退菜单。
- **修复步骤**：
  1. 在 `_run_scene_loop` 的帧循环中，将 `handle_events`、`update`、`render`、`flip` 分别包裹 `try/except`。
  2. 使用连续失败计数器，超过阈值（如 5 帧）才重新抛出异常。
  3. 异常时调用场景的 `on_frame_error()` 钩子（可选）。
- **建议代码**：

```python
def _run_scene_loop(self, scene, ...):
    consecutive_errors = 0
    max_consecutive_errors = 5
    while self._running and self._current_scene is scene:
        try:
            self._next_frame(scene)
            consecutive_errors = 0
        except Exception:
            consecutive_errors += 1
            logger.exception("Frame error in scene %r (consecutive=%d)", scene.__class__.__name__, consecutive_errors)
            if consecutive_errors >= max_consecutive_errors:
                raise
            # 给事件循环一个喘息机会，避免 busy loop
            pygame.time.wait(16)
```

- **验证方法**：
  - 注入一个会抛异常的 `update()` 方法，确认游戏不立即崩溃，而是跳过坏帧并记录日志。
  - 连续异常超过阈值后退出。

#### C2 — SceneManager.switch 异常回滚

- **问题编号**：Major ERR-2
- **文件**：`airwar/scenes/scene.py`
- **当前行为**：先设置 `_current_scene`，再调用 `enter()`，异常后状态不一致。
- **目标**：`enter()` 异常时回滚到原场景。
- **修复步骤**：
  1. 保存 `old_scene` 与 `old_name`。
  2. 在 `try/except` 中调用 `enter()`。
  3. 异常时恢复旧场景，并重新 `enter()` 旧场景（如果旧场景支持）。
- **建议代码**：

```python
def switch(self, name: str, **kwargs) -> None:
    if name not in self._scenes:
        raise KeyError(f"Scene '{name}' not registered")
    old_scene = self._current_scene
    old_name = self._current_scene_name
    new_scene = self._scenes[name]
    self._current_scene = new_scene
    self._current_scene_name = name
    try:
        if old_scene is not None:
            old_scene.exit()
        new_scene.enter(**kwargs)
    except Exception:
        self._current_scene = old_scene
        self._current_scene_name = old_name
        logger.exception("Failed to enter scene %r; rolling back to %r", name, old_name)
        if old_scene is not None:
            try:
                old_scene.enter()
            except Exception:
                logger.exception("Rollback enter failed for scene %r", old_name)
        raise
```

- **验证方法**：
  - 注册一个 `enter()` 会抛异常的场景，切换时确认原场景恢复。

#### C3 — 子场景 enter/exit 使用 try/finally

- **问题编号**：Major ERR-3
- **文件**：`airwar/game/scene_director_components/scene_switcher.py`
- **目标**：确保 `exit()` 总是被调用。
- **修复步骤**：
  1. 在 `_run_subscene_flow` 或类似函数中，使用 `try/finally` 包裹子场景循环。
- **建议代码**：

```python
def _run_subscene(self, subscene_name, *, overlay_on):
    subscene = self._scene_manager.get(subscene_name)
    subscene.enter(overlay_scene=overlay_on)
    try:
        while self._active_subscene == subscene_name:
            self._next_frame(subscene)
    finally:
        try:
            subscene.exit()
        except Exception:
            logger.exception("Subscene %r exit failed", subscene_name)
```

- **验证方法**：
  - 注入异常到子场景 `update()`，确认 `exit()` 仍被调用。

#### C4 — 替换 assert 为显式检查

- **问题编号**：Nit
- **文件**：`airwar/game/scene_director_components/scene_switcher.py:46`、`airwar/scenes/game_scene_updater.py:364-370`
- **修复步骤**：
  1. `assert welcome is not None` → `if welcome is None: raise RuntimeError(...)`。
  2. `assert bus is not None` → `if bus is None: raise RuntimeError(...)`。

---

### 4.4 批次 D：LockManager 接口与语义

#### D1 — release 增加 owner/cookie 校验

- **问题编号**：Major ERR-4
- **文件**：`airwar/game/systems/lock_manager.py`
- **当前行为**：任何调用者可释放任意层。
- **目标**：引入 `acquire` 返回的 token，只有持有者能释放；或至少记录调用栈警告。
- **修复步骤（轻量方案）**：
  1. `acquire` / `acquire_or_update` / `acquire_strict` 返回一个 `LockToken`（包含 layer）。
  2. `release` 可接受 `LockToken` 或 layer；若用 layer，记录 warning。
  3. 保持向后兼容：先支持 layer，同时推荐 token。
- **建议代码**：

```python
import dataclasses

@dataclasses.dataclass(frozen=True)
class LockToken:
    layer: LockLayer

class LockManager:
    def acquire(self, layer: LockLayer, request: LockRequest) -> LockToken:
        ...
        return LockToken(layer)

    def release(self, token: LockLayer | LockToken) -> None:
        layer = token.layer if isinstance(token, LockToken) else token
        if not isinstance(token, LockToken):
            logger.warning("Releasing lock by layer %r without token; prefer using token from acquire", layer)
        removed = self._locks.pop(layer, None)
        ...
```

- **验证方法**：
  - 用 token 释放成功；用 layer 释放时记录 warning。

#### D2 — 明确控制锁/暂停的优先级语义

- **问题编号**：Major ARCH-1
- **文件**：`airwar/game/systems/lock_manager.py`
- **当前行为**：控制锁和暂停是全局 OR。
- **目标**：要么改为按优先级仲裁，要么更新文档与 `AGENTS.md` 说明当前行为。
- **修复步骤（推荐按优先级仲裁）**：
  1. `_recompute` 中只取最高优先级层的 `lock_controls` 和 `is_paused`。
  2. 新增 `LockLayer` 的优先级语义注释。
- **建议代码**：

```python
def _recompute(self):
    invincible = False
    lock_controls = False
    paused = False
    silent = False
    timer = 0
    invincibility_applied = False
    for layer in sorted(self._locks.keys(), reverse=True):
        req = self._locks[layer]
        if req.invincible and not invincibility_applied:
            invincible = True
            silent = req.is_silent_invincible
            if req.expires_at > 0:
                timer = round(max(0, req.expires_at - time.monotonic()))
            else:
                timer = req.invincibility_duration
            invincibility_applied = True
        # 优先级仲裁：一旦某一层置位，低优先级层不再覆盖
        if req.lock_controls and not lock_controls:
            lock_controls = True
        if req.is_paused and not paused:
            paused = True
        if lock_controls and paused and invincibility_applied:
            break
    ...
```

- **验证方法**：
  - 测试高优先级层释放后，低优先级层的控制锁/暂停生效；高优先级层存在时低优先级层被压制。
  - 更新 `tests/test_lock_manager.py`。

#### D3 — 自动清理过期锁

- **问题编号**：Major RES-1
- **文件**：`airwar/game/systems/lock_manager.py`
- **当前行为**：`expires_at` 只用于计算 timer，锁对象永久留在 `_locks`。
- **目标**：`refresh()` 或 `_recompute()` 中清理已过期且非永久的锁。
- **修复步骤**：
  1. `_recompute` 遍历前移除 `expires_at > 0 and expires_at <= now` 的锁。
  2. 永久无敌使用 `invincibility_duration >= PERMANENT_INVINCIBILITY_FRAMES` 识别，不清理。
- **建议代码**：

```python
now = time.monotonic()
expired = [
    layer for layer, req in self._locks.items()
    if req.expires_at > 0 and req.expires_at <= now
    and req.invincibility_duration < self.PERMANENT_INVINCIBILITY_FRAMES
]
for layer in expired:
    logger.debug("Lock %s expired, removing", layer.name)
    self._locks.pop(layer, None)
```

- **验证方法**：
  - 创建一个带 `expires_at` 的锁，时间到后调用 `refresh()`，确认 `is_locked` 为 `False`。

#### D4 — acquire 不原地修改传入的 LockRequest

- **问题编号**：Minor（来自探索代理）
- **文件**：`airwar/game/systems/lock_manager.py`
- **目标**：避免修改调用者传入的 dataclass 实例。
- **修复步骤**：
  1. 在设置 `expires_at` 前先 `dataclasses.replace(request, expires_at=...)`。

```python
if request.expires_at <= 0 and request.invincibility_duration > 0:
    request = dataclasses.replace(request, expires_at=time.monotonic() + request.invincibility_duration)
```

#### D5 — 拆分 TRANSIENT 层语义

- **问题编号**：Minor（来自探索代理）
- **文件**：`airwar/game/systems/lock_manager.py`
- **目标**：避免 `apply_transient_state(paused=True)` 被 `apply_transient_state(invincible=True)` 覆盖。
- **修复步骤**：
  1. `apply_transient_state` 在更新前先读取现有 `TRANSIENT` 请求，合并布尔值后再 `acquire_or_update`。
- **建议代码**：

```python
def apply_transient_state(self, *, paused=None, invincible=None, invincibility_duration=None, silent_invincible=None):
    existing = self._locks.get(LockLayer.TRANSIENT)
    merged_kwargs = {}
    if existing:
        merged_kwargs = dataclasses.asdict(existing)
    if paused is not None:
        merged_kwargs["is_paused"] = paused
    if invincible is not None:
        merged_kwargs["invincible"] = invincible
    if invincibility_duration is not None:
        merged_kwargs["invincibility_duration"] = invincibility_duration
        merged_kwargs["invincible"] = True
    if silent_invincible is not None:
        merged_kwargs["is_silent_invincible"] = silent_invincible
    if any(merged_kwargs.get(k) for k in ("invincible", "lock_controls", "is_paused")) or merged_kwargs.get("invincibility_duration"):
        self.acquire_or_update(LockLayer.TRANSIENT, LockRequest(**merged_kwargs))
    else:
        self.release(LockLayer.TRANSIENT)
```

---

### 4.5 批次 E：帧时间、视口、输入边界

#### E1 — FrameContext 校验非法 dt

- **问题编号**：Major ERR-5
- **文件**：`airwar/game/frame_context.py`
- **当前行为**：负数 dt 静默取 0；NaN/Inf 未处理；极小 fixed_delta 可爆炸。
- **目标**：对非法输入抛出清晰异常或记录 warning。
- **修复步骤**：
  1. `FixedStepAccumulator.advance` 中校验 `delta_seconds` 为有限非负数。
  2. `__init__` 中限制 `fixed_delta_seconds` 不能过小（如 `>= 1.0 / 1200`）。
- **建议代码**：

```python
import math

_MIN_FIXED_DELTA = 1.0 / 1200.0
_MAX_FIXED_DELTA = 1.0 / 10.0

class FixedStepAccumulator:
    def __init__(self, fixed_delta_seconds: float = FrameContext.FIXED_DELTA_SECONDS) -> None:
        if not math.isfinite(fixed_delta_seconds):
            raise ValueError("fixed_delta_seconds must be finite")
        if not (_MIN_FIXED_DELTA <= fixed_delta_seconds <= _MAX_FIXED_DELTA):
            raise ValueError(f"fixed_delta_seconds must be in [{_MIN_FIXED_DELTA}, {_MAX_FIXED_DELTA}]")
        ...

    def advance(self, delta_seconds: float, *, simulate: bool) -> FrameContext:
        if not math.isfinite(delta_seconds) or delta_seconds < 0:
            raise ValueError(f"delta_seconds must be finite and non-negative, got {delta_seconds}")
        delta = min(delta_seconds, self.MAX_DELTA_SECONDS)
        ...
```

- **验证方法**：
  - 传入 `-0.1`、`float('nan')`、`float('inf')` 均抛出 `ValueError`。
  - 传入 `fixed_delta_seconds=1e-9` 抛出 `ValueError`。

#### E2 — ScaledViewport 参数保护与 logical_size 不可变

- **问题编号**：Minor PAT-7、PAT-8
- **文件**：`airwar/game/scaled_viewport.py`
- **当前行为**：`logical_size` 是公开可变属性；构造参数可非正。
- **目标**：校验构造参数；将 `logical_size` 改为 property 保护 surface 一致性。
- **修复步骤**：
  1. `__init__` 校验 `logical_w > 0 and logical_h > 0`。
  2. 将 `logical_size` 改为 property，`setter` 同步重建 `_logical_surface`。
  3. 外部 resize 统一走 `update()` 而非直接改属性。
- **建议代码**：

```python
class ScaledViewport:
    def __init__(self, logical_w: int = 1920, logical_h: int = 1080) -> None:
        if logical_w <= 0 or logical_h <= 0:
            raise ValueError(f"logical size must be positive, got ({logical_w}, {logical_h})")
        self._logical_size = (logical_w, logical_h)
        self._logical_surface = pygame.Surface((logical_w, logical_h))
        self._scale = 1.0
        self._display_size = (logical_w, logical_h)

    @property
    def logical_size(self) -> tuple[int, int]:
        return self._logical_size

    def update(self, display_w: int, display_h: int) -> None:
        if display_w <= 0 or display_h <= 0:
            self._scale = 0.0
            self._display_size = (max(1, display_w), max(1, display_h))
            return
        lw, lh = self._logical_size
        self._scale = min(display_w / lw, display_h / lh)
        self._display_size = (display_w, display_h)
```

- **验证方法**：
  - 构造 `ScaledViewport(0, 1080)` 抛出 `ValueError`。
  - 直接赋值 `viewport.logical_size = ...` 应不可行（若保留 setter 则同步重建 surface）。

#### E3 — InputHandler 协议与绑定校验

- **问题编号**：Minor PAT-3、PAT-4、PAT-5、PAT-6
- **文件**：`airwar/input/input_handler.py`
- **当前行为**：`tick()` 不在协议中；绑定值未校验；默认绑定是可变类属性；对向键冲突未文档。
- **目标**：完善协议、校验绑定、文档化按键冲突行为。
- **修复步骤**：
  1. 在 `InputHandler` 抽象基类中加入 `tick()` 抽象方法。
  2. 将 `DEFAULT_BINDINGS` 改为 tuple 或每次复制不可变副本。
  3. `__init__` 校验绑定值在 `pygame.key.get_pressed()` 长度范围内且为整数。
  4. 在 `get_movement_direction()` 注释中说明“后赋值覆盖”行为，或改为对向键归零。
- **建议代码**：

```python
from typing import ClassVar
import pygame

class InputHandler(ABC):
    @abstractmethod
    def tick(self) -> None: ...

    DEFAULT_BINDINGS: ClassVar[dict[str, int]] = {
        "up": pygame.K_UP,
        "down": pygame.K_DOWN,
        "left": pygame.K_LEFT,
        "right": pygame.K_RIGHT,
        "boost": pygame.K_LSHIFT,
        "precision": pygame.K_LCTRL,
        "pause": pygame.K_ESCAPE,
    }
```

```python
class PygameInputHandler(InputHandler):
    def __init__(self, bindings: dict[str, int] | None = None):
        self._bindings = dict(bindings if bindings is not None else self.DEFAULT_BINDINGS)
        max_key = len(pygame.key.get_pressed()) - 1
        for action, key in self._bindings.items():
            if not isinstance(key, int) or key < 0 or key > max_key:
                raise ValueError(f"Invalid key binding for {action!r}: {key!r}")
```

- **验证方法**：
  - 传入非法绑定值抛出 `ValueError`。
  - 修改 `DEFAULT_BINDINGS` 不影响已有实例。

---

### 4.6 批次 F：实体与战斗系统边界

#### F1 — 统一 Entity 基类接口

- **问题编号**：Major ARCH-2
- **文件**：`airwar/entities/base.py`
- **当前行为**：`take_damage` / `kill` 未在基类统一。
- **目标**：在 `Entity` 基类中声明 `take_damage` 与 `kill` 的默认实现或抽象接口。
- **修复步骤**：
  1. 在 `Entity` 中加入：

```python
@abstractmethod
def take_damage(self, damage: int) -> int:
    """Apply damage and return score awarded (0 if none)."""
    ...

def kill(self) -> None:
    """Mark entity as inactive. Subclasses may override for effects."""
    self.active = False
```

- **验证方法**：
  - 抽象方法测试：未实现的子类无法实例化。
  - 确认 `Player`、`Enemy`、`Boss` 签名统一。

#### F2 — Boss 狂暴除零保护顺序

- **问题编号**：Major ERR-6
- **文件**：`airwar/entities/enemy/boss/boss.py:486-489`
- **修复步骤**：
  1. 将 `max_health <= 0` 判断提前到除法之前。
- **建议代码**：

```python
def _trigger_enrage_if_needed(self, player_pos=None, player=None):
    if self._state.enraged or self.max_health <= 0:
        return
    health_ratio = self.health / self.max_health
    if health_ratio > self.ENRAGE_TRIGGER_RATIO:
        return
    ...
```

- **验证方法**：
  - 构造 `max_health=0` 的 Boss，调用 `_trigger_enrage_if_needed` 不抛异常。

#### F3 — BulletManager batch buffer 同步

- **问题编号**：Major ERR-7
- **文件**：`airwar/game/managers/bullet_manager.py:174-192`
- **当前行为**：`data is None` 检查在 `active_bullets.append` 之后。
- **修复步骤**：
  1. 将 `data is None` 检查提前到 append 之前。
- **建议代码**：

```python
for bullet in bullets:
    if not bullet.active:
        continue
    self._update_release_delay(bullet)
    if getattr(bullet, "held", False):
        continue
    data = getattr(bullet, "data", None)
    if data is None:
        continue
    active_bullets.append(bullet)
    bullet_map[id(bullet)] = bullet
```

- **验证方法**：
  - 构造 `data=None` 的子弹，确认不会被加入 active_bullets，buffer 索引正确。

#### F4 — GameLoopManager 依赖校验

- **问题编号**：Major ARCH-3
- **文件**：`airwar/game/managers/game_loop_manager.py:123-141`
- **修复步骤**：
  1. 在 `__init__` 末尾对所有非可选依赖做 `None` 检查。
- **建议代码**：

```python
required = {
    "lock_manager": self._lock_manager,
    "player": self._player,
    "bullet_manager": self._bullet_manager,
    "spawn_controller": self._spawn_controller,
    "boss_manager": self._boss_manager,
    "reward_system": self._reward_system,
    "collision_controller": self._collision_controller,
    "event_bus": self._event_bus,
}
missing = [name for name, value in required.items() if value is None]
if missing:
    raise ValueError(f"GameLoopManager missing required dependencies: {missing}")
```

- **验证方法**：
  - 传入 `None` 依赖时，构造即抛出 `ValueError`。

#### F5 — BossManager.clear_boss 走 SpawnController 清理路径

- **问题编号**：Major ARCH-4
- **文件**：`airwar/game/managers/boss_manager.py:143-145`
- **修复步骤**：
  1. 在 `SpawnController` 中提供 `clear_boss()` 方法处理计时器重置。
  2. `BossManager.clear_boss()` 调用 `self._spawn_controller.clear_boss()`。
- **建议代码**：

```python
# airwar/game/managers/spawn_controller.py
def clear_boss(self) -> None:
    self.boss = None
    self._boss_spawn_timer = 0
    # 其他必要状态重置

# airwar/game/managers/boss_manager.py
def clear_boss(self) -> None:
    self._spawn_controller.clear_boss()
```

- **验证方法**：
  - 调用 `BossManager.clear_boss()` 后，确认 `_boss_spawn_timer` 被重置。

#### F6 — 普通敌机 update 传入 player_pos

- **问题编号**：Major PAT-5
- **文件**：`airwar/game/managers/game_loop_manager.py:424`
- **修复步骤**：
  1. 从 player 获取位置，传入 `enemy.update(...)`。
- **建议代码**：

```python
player_pos = (self._player.rect.centerx, self._player.rect.centery) if self._player else None
for enemy in self._spawn_controller.enemies:
    enemy.update(self._spawn_controller.enemies, self._reward_system.slow_factor, player_pos)
```

- **验证方法**：
  - 运行 aggressive 敌机运动策略，确认能追踪玩家位置。

#### F7 — 清理 Boss 死代码

- **问题编号**：Minor PAT-11
- **文件**：`airwar/entities/enemy/boss/boss.py:584-606`
- **修复步骤**：
  1. 确认 `_update_enrage_transition`、`_update_enrage_release_hold`、`_update_enrage_return` 无调用点。
  2. 删除这三个方法。

#### F8 — PlayerState.force_substate 增加安全模式

- **问题编号**：Minor PAT-9
- **文件**：`airwar/entities/player_state.py:209-211`
- **修复步骤**：
  1. 增加 `validate: bool = True` 参数，存档恢复时调用 `force_substate(..., validate=False)` 并记录 warning。
  2. 默认启用验证。

#### F9 — Player.enter_boost 不静默吞异常

- **问题编号**：Minor PAT-10
- **文件**：`airwar/entities/player.py:269-274`
- **修复步骤**：
  1. 仅对已知可忽略条件（如已在 boost）静默处理，其他情况记录 warning。

---

### 4.7 批次 G：Rust ↔ Python 边界一致

#### G1 — 统一 bullet id 类型

- **问题编号**：Major INT-1
- **文件**：`airwar_core/src/bullets.rs`、`airwar/core_bindings.py:641`
- **当前行为**：Rust 注释 u64，实现 i64，Python u64。
- **目标**：统一为 i64（足够大且与 PyO3 默认兼容）。
- **修复步骤**：
  1. 修改 `bullets.rs` 中注释与读取均为 `i64`。
  2. Python fallback 使用 `<q`（小写 q = i64）。
  3. 更新 `.pyi` 存根注释。
- **建议代码**：

```rust
// airwar_core/src/bullets.rs
// bullet_id: i64
let bullet_id = i64::from_le_bytes(buf[offset..offset + 8].try_into().unwrap());
```

```python
# airwar/core_bindings.py
BULLET_BUF_FMT = "<qffffffi"  # id as i64
```

- **验证方法**：
  - Rust 与 Python fallback 对同一 buffer 返回相同 id。

#### G2 — sprite 非正输入统一返回空 bytes

- **问题编号**：Major INT-2
- **文件**：`airwar_core/src/sprites.rs`、`airwar/core_bindings.py`
- **修复步骤**：
  1. 在 Python fallback 的每个 sprite 函数开头，对 width/radius <= 0 返回 `b''`。
- **建议代码**：

```python
def create_single_bullet_glow(width: int, height: int, color: tuple[int, int, int], glow_radius: int) -> bytes:
    if width <= 0 or height <= 0 or glow_radius < 0:
        return b""
    ...
```

- **验证方法**：
  - 参数 `width=-5` 时 Rust 与 fallback 均返回 `b''`。

#### G3 — 颜色越界统一 clamp

- **问题编号**：Major INT-3
- **文件**：`airwar_core/src/particles.rs`、`airwar_core/src/sprites.rs`、`airwar/core_bindings.py`
- **修复步骤**：
  1. 推荐 Rust 侧也进行 clamp（0–255），保持与 Python 一致且更宽容。
  2. 在 PyO3 参数获取后使用 `clamp(0, 255)`。
- **建议代码（Rust）**：

```rust
let r = r.clamp(0, 255) as u8;
```

- **验证方法**：
  - 传入 `r=300`，Rust 与 fallback 均不抛异常且结果为 255。

#### G4 — compute_starfield_positions 负 phase 语义一致

- **问题编号**：Major INT-4
- **文件**：`airwar_core/src/starfield.rs:68`、`airwar/core_bindings.py:253`
- **修复步骤**：
  1. Rust 中使用欧几里得取模：`((phase % len as i32 + len as i32) % len as i32) as usize`。
- **建议代码**：

```rust
let idx = ((phase as i32).rem_euclid(sin_table.len() as i32)) as usize;
```

- **验证方法**：
  - 负 phase 时 Rust 与 Python 返回相同索引。

#### G5 — core_bindings 签名/ABI 校验

- **问题编号**：Major INT-5
- **文件**：`airwar/core_bindings.py:81-123`
- **修复步骤**：
  1. 维护一个 `RUST_SIGNATURES` 字典，记录函数名、参数数量/类型、返回值类型。
  2. 加载时使用 `inspect.signature` 粗略校验。
  3. 不匹配时打印 error 并切 fallback。
- **建议代码**：

```python
import inspect

_RUST_SIGNATURES = {
    "batch_update_bullets_buf": (inspect.Signature.empty, bytes),
    # ...
}

def _load_rust_module():
    ...
    for name in _RUST_NAMES:
        func = getattr(mod, name, None)
        if not callable(func):
            raise ImportError(f"Rust module missing function: {name}")
        sig = inspect.signature(func)
        expected = _RUST_SIGNATURES.get(name)
        if expected and len(sig.parameters) != len(expected[0].parameters):
            raise ImportError(f"Rust function {name} signature mismatch")
```

- **验证方法**：
  - 用 mock 对象模拟 ABI 不匹配，确认切到 fallback。

---

### 4.8 批次 H：杂项与测试补全

#### H1 — i18n set_locale 路径遍历防护

- **问题编号**：Major SEC-5
- **文件**：`airwar/i18n/__init__.py:108`
- **修复步骤**：
  1. 校验 locale 只包含字母、数字、下划线。
- **建议代码**：

```python
import re

_LOCALE_RE = re.compile(r"^[A-Za-z0-9_]+$")

def set_locale(locale: str) -> None:
    if not isinstance(locale, str) or not _LOCALE_RE.match(locale):
        raise ValueError(f"Invalid locale name: {locale!r}")
    ...
```

#### H2 — game_scene 缓存清理异常处理

- **问题编号**：Major OBS-1
- **文件**：`airwar/scenes/game_scene.py:703-747`
- **修复步骤**：
  1. 将 `except AttributeError/ImportError: pass` 改为至少记录 `logger.debug`。
  2. 区分预期清理失败与意外错误。

#### H3 — Scene 接口收紧

- **问题编号**：Minor PAT-1、PAT-2
- **文件**：`airwar/scenes/scene.py`
- **修复步骤**：
  1. `register()` 校验 scene 为 `Scene` 实例，并可选 `overwrite=True` 参数。
  2. `enter()` / `update()` 保持 `**kwargs` 但文档化必填键。

#### H4 — game_scene 注释与死代码

- **问题编号**：Nit
- **文件**：`airwar/scenes/game_scene.py:15,373-396`
- **修复步骤**：
  1. 删除关于 `__setattr__` hook 的过时注释。
  2. 检查 `set_homecoming_coordinator` 中重复赋值。

#### H5 — SceneDirector LeaderboardService 复用

- **问题编号**：Minor PAT-14
- **文件**：`airwar/game/scene_director.py:248-256`
- **修复步骤**：
  1. 在 `SceneDirector.__init__` 中创建 `LeaderboardService` 实例并复用。

---

## 5. 新增/更新测试清单

| 测试文件 | 新增/修改内容 |
|----------|--------------|
| `tests/test_lock_manager.py` | owner token、优先级仲裁、过期清理、TRANSIENT 合并 |
| `tests/test_frame_context.py` | 非法 dt、NaN/Inf、fixed_delta 边界 |
| `tests/test_scaled_viewport.py` | 非正构造、logical_size 不可变、resize 边界 |
| `tests/test_persistence.py` | 数据库损坏恢复、并发写入、唯一 tmp 文件 |
| 新增 `tests/test_database.py` | 密码验证、salt 缺失、分数类型、名称长度 |
| 新增 `tests/test_leaderboard_config.py` | URL/timeout 校验、CORS 配置 |
| 新增 `tests/test_leaderboard_server.py` | limit 范围、CORS 限制 |
| 新增 `tests/test_input_handler.py` | 绑定校验、默认绑定不可变、按键冲突 |
| 新增 `tests/test_entity_interface.py` | Entity 抽象方法、take_damage/kill 统一 |
| 新增 `tests/test_bullet_manager.py` | data=None 子弹跳过、buffer 同步 |
| 新增 `tests/test_boss.py` | max_health=0 不除零、clear_boss 计时器重置 |
| 新增 `tests/test_core_bindings.py` | Rust/fallback 边界行为一致、ABI 不匹配回退 |
| `tests/test_scene_manager.py` | switch 异常回滚、register 类型校验 |
| 新增 `tests/test_i18n.py` | locale 路径遍历防护 |

---

## 6. 执行顺序与依赖关系

```
批次 A（持久化）
  │
  ▼
批次 B（排行榜安全） ── 可并行 ──▶ 批次 E（帧时间/输入）
  │                              │
  ▼                              ▼
批次 C（主循环异常）           批次 F（实体/战斗）
  │                              │
  ▼                              ▼
批次 D（LockManager）          批次 G（Rust/Python）
  │                              │
  └──────────────┬───────────────┘
                 ▼
            批次 H（杂项/测试补全）
                 │
                 ▼
            全量回归测试
```

### 建议迭代节奏

1. **第 1 周**：A + B（Critical 全部解决）。
2. **第 2 周**：C + D（Major 稳定性与锁）。
3. **第 3 周**：E + F（Major 边界行为）。
4. **第 4 周**：G + H（Rust 一致性与测试补全）。

---

## 7. 验证清单

每次提交前必须执行：

```bash
python3 -m pytest tests/ -v
python3 -m ruff check .
python3 -m compileall -q airwar main.py
```

针对本计划的额外验证：

- [ ] 构造损坏 `users.json`，启动游戏能自动恢复。
- [ ] 多进程同时写入 `users.json`，数据不丢失。
- [ ] 启动排行榜服务端，`limit=101` 返回 422。
- [ ] 非允许来源的 CORS preflight 被拒绝。
- [ ] 主循环中注入单帧异常，游戏不崩溃。
- [ ] 子场景 `update()` 异常，`exit()` 仍被调用。
- [ ] `LockManager` 高优先级控制锁压制低优先级暂停。
- [ ] 过期锁自动清理。
- [ ] `FrameContext` 传入 NaN 抛出 `ValueError`。
- [ ] `ScaledViewport(0, 0)` 抛出 `ValueError`。
- [ ] 非法 pygame 键绑定抛出 `ValueError`。
- [ ] `Boss.max_health=0` 不触发除零。
- [ ] `BulletManager` 遇到 `data=None` 子弹不破坏 buffer。
- [ ] Rust 与 Python fallback 对非法 sprite 输入均返回空 bytes。
- [ ] `set_locale("../../etc/passwd")` 抛出 `ValueError`。

---

## 8. 风险与回滚策略

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 修改 `LockManager` 优先级语义可能影响现有玩法 | 中 | 先新增可选行为，通过特性开关切换；测试通过后再默认启用。 |
| 收紧 `FrameContext` 校验可能暴露现有调用点传非法 dt | 中 | 先改为记录 warning 不抛异常，观察日志后再升级。 |
| Rust 颜色 clamp 改变性能或视觉效果 | 低 | 在 sprite 渲染基准测试中对比帧率；视觉差异需人工确认。 |
| 数据库损坏自动重置可能丢失玩家数据 | 中 | 必须先备份到 `.corrupted.{ts}.bak`，并通知玩家。 |
| CORS 限制导致本地开发调试失败 | 低 | 提供 `AIRWAR_LEADERBOARD_CORS_ORIGINS=*` 开发模式。 |

### 回滚策略

- 每个批次独立提交到独立分支或至少独立 commit。
- 若某批次引入回归，直接 revert 该 commit。
- 关键修复（如 A、B）先合并到 `main`，其他批次可并行在 feature 分支开发。

---

## 9. 文档更新清单

- [ ] 更新 `AGENTS.md` 中 `LockManager` 优先级语义描述。
- [ ] 在 `README.md` / `README.en.md` 中增加排行榜环境变量说明（`AIRWAR_LEADERBOARD_CORS_ORIGINS` 等）。
- [ ] 在 `.env.example` 中增加新环境变量示例。
- [ ] 更新 `docs/audits/review-findings-main-interfaces-2026-07-11-0422.md` 中各 issue 的修复状态。

---

*本计划应与审查报告配套使用：每完成一项修复，在 `review-findings-main-interfaces-2026-07-11-0422.md` 对应条目后标记 `[x]` 并注明修复 commit。*
