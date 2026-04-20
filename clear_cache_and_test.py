#!/usr/bin/env python3
"""
清理Python缓存并验证GameOver界面实现
使用说明:
1. 运行此脚本清除所有Python缓存文件
2. 验证GameOverScreen类包含新功能的必要方法
"""

import os
import sys
import shutil
from pathlib import Path


def clear_pycache(root_dir: Path):
    """递归清除所有__pycache__目录"""
    count = 0
    for pycache in root_dir.rglob("__pycache__"):
        shutil.rmtree(pycache)
        count += 1
        print(f"  删除: {pycache}")
    return count


def clear_pyc_files(root_dir: Path):
    """清除所有.pyc文件"""
    count = 0
    for pyc in root_dir.rglob("*.pyc"):
        pyc.unlink()
        count += 1
        print(f"  删除: {pyc}")
    return pyc_files(root_dir) if False else 0


def pyc_files(root_dir: Path):
    count = 0
    for pyc in root_dir.rglob("*.pyc"):
        count += 1
    return count


def verify_game_over_screen():
    """验证GameOverScreen类包含新功能"""
    print("\n" + "="*60)
    print("验证 GameOverScreen 实现")
    print("="*60)

    game_over_path = Path("airwar/ui/game_over_screen.py")

    if not game_over_path.exists():
        print(f"❌ 文件不存在: {game_over_path}")
        return False

    content = game_over_path.read_text()

    required_features = {
        "可点击按钮初始化": "_init_buttons" in content,
        "鼠标悬停检测": "_update_button_hover_states" in content,
        "按钮点击处理": "_handle_button_click" in content,
        "按钮渲染": "_render_button" in content,
        "新界面文字": "RETURN TO MAIN MENU" in content,
        "退出按钮文字": "QUIT GAME" in content,
        "发光效果": "glow" in content.lower(),
    }

    all_passed = True
    for feature, present in required_features.items():
        status = "✅" if present else "❌"
        print(f"  {status} {feature}")
        if not present:
            all_passed = False

    old_features = {
        "旧界面提示文本": "ENTER to menu | ESC to quit" in content,
    }

    for feature, present in old_features.items():
        status = "❌ (已移除)" if present else "✅ (已移除)"
        print(f"  {status} {feature}")
        if present:
            all_passed = False

    return all_passed


def verify_game_over_flow():
    """验证游戏结束触发流程"""
    print("\n" + "="*60)
    print("验证游戏结束触发流程")
    print("="*60)

    scene_director_path = Path("airwar/game/scene_director.py")
    game_scene_path = Path("airwar/scenes/game_scene.py")

    checks = []

    if scene_director_path.exists():
        content = scene_director_path.read_text()
        checks.append(("scene_director.py 存在", True))
        checks.append(("导入 GameOverScreen", "from airwar.ui.game_over_screen import" in content))
        checks.append(("包含 _handle_game_over 方法", "def _handle_game_over" in content))
        checks.append(("调用 _game_over_screen.show", "_game_over_screen.show(" in content))
    else:
        checks.append(("scene_director.py 存在", False))

    if game_scene_path.exists():
        content = game_scene_path.read_text()
        checks.append(("game_scene.py 存在", True))
        checks.append(("包含 is_game_over 方法", "def is_game_over" in content))
        checks.append(("检查 player.active", "player.active" in content))
    else:
        checks.append(("game_scene.py 存在", False))

    all_passed = True
    for check, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    return all_passed


def main():
    print("="*60)
    print("GameOver界面缓存清理和验证工具")
    print("="*60)

    root = Path(__file__).parent

    print("\n步骤1: 清除Python缓存文件")
    print("-"*60)
    pycache_count = clear_pycache(root)
    print(f"\n已删除 {pycache_count} 个 __pycache__ 目录")

    print("\n步骤2: 清除.pyc文件")
    print("-"*60)
    pyc_removed = clear_pyc_files(root)
    remaining_pyc = pyc_files(root)
    print(f"已删除 {pyc_removed} 个 .pyc 文件")
    print(f"剩余 .pyc 文件: {remaining_pyc}")

    game_over_ok = verify_game_over_screen()
    flow_ok = verify_game_over_flow()

    print("\n" + "="*60)
    print("验证结果")
    print("="*60)
    print(f"  {'✅' if game_over_ok else '❌'} GameOver界面实现")
    print(f"  {'✅' if flow_ok else '❌'} 游戏结束流程")

    if game_over_ok and flow_ok:
        print("\n✅ 所有验证通过！")
        print("\n下一步:")
        print("  1. 重新启动游戏")
        print("  2. 玩到生命耗尽")
        print("  3. 应该看到新的GameOver界面，包含可点击的按钮")
        return 0
    else:
        print("\n❌ 验证失败，请检查代码")
        return 1


if __name__ == "__main__":
    sys.exit(main())
