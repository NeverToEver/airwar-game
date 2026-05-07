# Install / Uninstall 完善工作记录

**日期:** 2026-05-07
**范围:** 构建脚本、运行脚本、卸载脚本、Rust fallback、包元数据、运行时数据路径

---

## 发现的问题

### 严重
1. `core_bindings.py` 无 try/except，`RUST_AVAILABLE` 不存在 — Rust 扩展实际是强制依赖，但文档声称有 fallback
2. `run.sh` 用 `curl | sh` 和 `sudo apt-get install -y` 静默改系统，未征得用户同意
3. `uninstall.bat` 删除整个项目目录（含源码和存档），与 `uninstall.sh` 行为矛盾
4. 运行时数据 (`users.json`, `user_docking_save.json`, `generated_assets/`) 放在 `airwar/data/` 源码目录内，被 PyInstaller 打包进发布版
5. `uninstall.sh` 先删 `.venv` 再跑 `pip uninstall`，顺序错误；遗漏清理 `.venv-build`, `dist/`, `build/` 等

### 中等
6. `pyproject.toml` 只有 ruff 配置，无法 `pip install .`
7. Python 版本要求不一致 (`run.sh`: >=3.11, 构建脚本: 3.12+, `airwar_core`: >=3.10)
8. 构建脚本不清理 `.venv-build`；macOS DMG 提示有误 (`--onefile` 不产生 `.app`)

---

## 修改内容

### 新增文件
- **`airwar/utils/platform_paths.py`** — 平台化运行时目录
  - 存档 → `~/.local/share/airwar/` (Linux), `~/Library/Application Support/airwar/` (macOS), `%APPDATA%\airwar\` (Windows)
  - 缓存 → `~/.cache/airwar/` (Linux), `~/Library/Caches/airwar/` (macOS), `%LOCALAPPDATA%\airwar\Cache\` (Windows)
  - 均支持 `AIRWAR_DATA_DIR` / `AIRWAR_CACHE_DIR` / `AIRWAR_GENERATED_ASSET_DIR` 环境变量覆盖
- **`airwar/__main__.py`** — `python -m airwar` 入口
- **`clean.sh`** — 轻量清理脚本（仅删构建产物和缓存，保留 venv）

### 重写
- **`airwar/core_bindings.py`** — 增加 try/except + 完整纯 Python fallback（17 个函数、PersistentSpatialHash 类），导出 `RUST_AVAILABLE`
- **`run.sh`** — `--install-deps` / `AIRWAR_INSTALL_DEPS=1` 才装系统依赖；Rust 构建失败仅警告
- **`uninstall.sh`** — 先 pip uninstall 再删 .venv；增加清理 .venv-build、dist、build、各类缓存
- **`uninstall.bat`** — 匹配 Linux 行为，不再删源码/存档

### 数据路径迁移
- `database.py`, `persistence_manager.py`, `generated_asset_cache.py` — 改为引用 `platform_paths.*_dir()`
- `main.py` — 启动时确保平台目录存在

### 构建脚本
- `build_linux.sh`, `build_macos.sh`, `build_windows.bat` — 移除 `--add-data="airwar/data:..."`, 添加 `trap cleanup EXIT` 自动清理 `.venv-build`, 统一要求 Python >= 3.11

### 包元数据
- `pyproject.toml` — 添加 `[build-system]`, `[project]`, dependencies, `[project.scripts]` 入口点 `airwar`

### 次要
- `CLAUDE.md`, `README.md` — 更新以匹配实际行为
- `airwar_core/pyproject.toml` — Python 版本 >=3.11
- `run.bat` — 匹配 `run.sh` 的 `--install-deps` 模式

---

## Rust vs Python Fallback 对比结论

四路并行审计（移动/Boss/粒子、sprites/glow、调用方兼容性、Rust 签名）：

- **游戏逻辑 (移动/碰撞/粒子/Boss/子弹):** 零差异
- **Sprites:** 2 个 Python fallback 的循环起止 bug 已修复。其余差异为 Rust 原版既有问题 (`fill_glow_circle` 边界漏 radius、x/y 循环变量交换等)
- **调用方:** 所有签名匹配。"Rust" 路径名称有误导性（fallback 也走这个路径），但行为正确
- **已知次生问题:** 无 Rust 时碰撞检测走 O(N*M) 暴力 fallback 而非已有的 O(N) 空间哈希纯 Python 路径
