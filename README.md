# 空战

一款基于 Python + Pygame 的 2D 空战射击游戏，使用必需的 Rust 原生扩展加速。包含完整的 7 阶段新手教程、Boss 战、基地指挥中心（征用点数经济）、鼠标辅瞄、以及运行期生成素材的本地缓存。

## 快速开始

```bash
# 进入项目目录
cd airwar-game

# 安装依赖
pip install -r requirements.txt

# 启动游戏
python3 main.py
```

## 操作方式

| 按键 / 输入 | 功能 |
|-------------|------|
| 方向键 / WASD | 移动战机 |
| 鼠标 | 控制瞄准方向，带目标辅瞄与平滑输入延迟 |
| Shift 长按 | 加速推进，消耗加速燃料，速度提升至 1.7 倍 |
| Shift 按下松开 | 相位冲刺（需天赋解锁），消耗 25% 燃料，无敌冲刺 250px |
| 自动开火 | 战机会持续自动射击 |
| ESC | 暂停游戏 |
| B 长按 2.4 秒 | 返航基地，进入基地指挥中心整备 |
| H 长按 3 秒 | 呼叫母舰并对接保存进度 |
| K 长按 3 秒 | 放弃当前出击 |
| L | 展开 / 收起 HUD 面板 |

## 当前版本内容

- 默认 1920x1080 分辨率，支持窗口自适应缩放。
- 三种难度：简单 / 普通 / 困难，并带动态难度成长。
- 自动射击 + 鼠标辅瞄：默认锁定敌人，鼠标大幅移动时优先切换到移动方向目标；原始输入加入短延迟平滑，降低辅瞄抢鼠标带来的顿挫。
- 加速系统：长按 Shift 启动推进，带燃料消耗、延迟恢复和 270 度环形仪表 UI。按下松开可触发相位冲刺（需天赋解锁），消耗 25% 燃料进行短距离无敌突进。
- 武器模式：散射弹（扇形 3 发，-10°/0°/+10°）和激光（单发高伤害 35），两种模式可组合使用形成散射激光。
- 13 种增益，覆盖生命、攻击、防御、功能四类，含双路线天赋系统（进攻/支援）与路线内互斥选项。
- 里程碑奖励系统：达到分数阈值后选择强化，支持天赋路线切换与配置保存。
- 母舰系统：长按 H 对接保存，母舰可移动，带 10 发弹匣限制的爆炸导弹支援（250 伤害 / 80px 范围），弹药用尽时触发警告横幅。
- 基地指挥中心：长按 B 返航后经过 FTL 动画进入停机坪基地，使用征用点数（RP）进行维修（-2RP）、补给（-2RP）和天赋路线切换（进攻路线：散射/激光，支援路线：相位冲刺/母舰冷却减半）。RP 通过击杀 Boss（+5）和完成基地任务（+3）获得，点数随存档保留。再次按 B 或点击「继续出击」出发并触发轨道打击清屏。
- Boss 战：多阶段移动和攻击；Boss 血量降至 30% 时触发核心过载，攻击节奏加快、枪口焰跳动频率大幅提升。暴走总时长 6 秒，视觉表现为 Boss 扩散光圈 + 屏幕边缘暗角。每发弹幕都会触发枪口闪光，压迫感更强。
- 受击清弹：玩家受击进入短暂无敌时会清理普通敌弹；Boss 暴走布置弹幕不会被该清弹机制移除，但玩家无敌仍然生效。
- 运行期绘制素材缓存：首次启动时生成飞船 / 光效等素材并缓存在本地，后续启动复用图片素材以降低重复绘制成本。
- Rust 原生扩展：用于向量、碰撞、批量移动、粒子、子弹、光效等性能热点，是运行游戏的必需组件。
- 新手教程：主菜单可进入 7 阶段教学关卡，涵盖移动瞄准、加速突进、战斗基础、母舰停靠（含火力支援演示）、返航基地（含整备流程）、Boss 遭遇。教程复用真实游戏 UI 组件，体验与正式战斗一致。

## 技术栈

- Python 3.x
- Pygame
- Pillow
- Pytest / Ruff
- Rust + PyO3 + maturin（必需加速模块）

## 项目结构

```text
airwar-game/
|-- main.py                    # 游戏启动入口
|-- airwar/                    # Python 游戏源码
|   |-- config/                # 配置、设计令牌、难度参数
|   |-- entities/              # 玩家、敌人、Boss、子弹等实体
|   |-- game/                  # 游戏主流程、管理器、系统、渲染、母舰、动画
|   |-- scenes/                # 欢迎、教程、战斗、暂停、死亡、退出确认等场景
|   |-- ui/                    # HUD、奖励选择、基地指挥中心、准星、提示等 UI
|   |-- input/                 # 输入处理
|   |-- utils/                 # 数据库、字体、素材绘制与缓存等工具
|   |-- window/                # 窗口创建与缩放
|   |-- tests/                 # Python 测试
|   `-- core_bindings.py       # Rust 扩展绑定入口
|-- airwar_core/               # Rust 原生扩展
|   `-- src/
|       |-- lib.rs             # 模块导出入口
|       |-- vector2.rs         # 向量计算
|       |-- collision.rs       # 空间哈希碰撞
|       |-- movement.rs        # 敌人 / Boss 运动计算
|       |-- particles.rs       # 粒子更新与生成
|       |-- bullets.rs         # 子弹批量更新
|       `-- sprites.rs         # 光效素材生成
|-- scripts/                   # 开发辅助脚本
|-- tests/                     # 根目录级测试
|-- docs/                      # 文档与审计记录
|-- build_linux.sh             # Linux 打包脚本
|-- build_macos.sh             # macOS 打包脚本
|-- build_windows.bat          # Windows 打包脚本
|-- requirements.txt
|-- requirements-dev.txt
|-- pytest.ini
`-- pyproject.toml
```

## 架构概览

- 场景模式：`SceneManager` 管理欢迎、游戏、暂停、死亡、退出确认等场景生命周期。
- 管理器拆分：生成、碰撞、子弹、Boss、里程碑、输入协调等逻辑由独立 manager 处理。
- 系统拆分：生命、奖励、难度、通知、天赋平衡等玩法规则集中在 `airwar/game/systems/`。
- UI 与渲染分层：HUD、准星、基地指挥中心、奖励选择等组件独立于核心玩法逻辑。
- Rust 原生扩展为必需组件：`airwar/core_bindings.py` 直接导入 `airwar_core`，缺失时会在导入阶段失败。

## Rust 原生扩展

`airwar_core/` 使用 PyO3 + maturin 提供必需性能加速。Rust extension is REQUIRED for performance；没有安装时，游戏会在导入阶段失败。

### 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd airwar_core
maturin develop --release
```

### 验证

```bash
python3 -c "from airwar.core_bindings import batch_update_bullets; print('Rust 原生扩展: 已安装')"
```

## 素材缓存与性能分析

游戏会把首次运行时生成的素材保存到本地缓存目录，避免每次启动都重复绘制同一批 Surface。可以使用脚本观察生成素材的缓存效果：

```bash
python3 scripts/profile_generated_assets.py
```

## CI（GitHub Actions）

每次 push 和 pull_request 触发，单 job 运行在 `ubuntu-latest`：

1. Python 3.12 + Rust stable + libsdl2-dev
2. pip install + maturin build + ruff check + compileall + shellcheck + pytest

本地模拟 CI：

```bash
python3 -m ruff check . && python3 -m compileall -q airwar main.py && python3 -m pytest
```

## 测试与代码检查

请在项目根目录执行测试，不要在 `airwar/` 子目录内运行。

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 全量测试
python3 -m pytest

# 代码检查
python3 -m ruff check .

# 指定测试文件
python3 -m pytest airwar/tests/test_core.py

# 指定测试用例
python3 -m pytest airwar/tests/test_core.py::TestPlayer -v
```

## 打包

```bash
# Linux
bash build_linux.sh

# macOS
bash build_macos.sh

# Windows
build_windows.bat
```

打包产物位于 `dist/AirWar`。构建阶段需要 Python 3.12+、Rust 工具链和对应平台编译器；运行打包产物时不需要用户手动安装 Python 或 Rust。
