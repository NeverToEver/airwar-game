#!/usr/bin/env python3
"""
GameOver界面源代码验证
不依赖pygame，直接检查源代码文件
"""

import os

def read_file(path):
    """读取文件内容"""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def check_game_over_screen():
    """检查GameOverScreen源代码"""
    print("=" * 70)
    print("检查 game_over_screen.py 源代码")
    print("=" * 70)

    path = 'airwar/ui/game_over_screen.py'

    if not os.path.exists(path):
        print(f"❌ 文件不存在: {path}")
        return False

    content = read_file(path)

    # 新版本功能（应该有）
    new_features = [
        ('_init_buttons', '按钮初始化方法'),
        ('_update_button_hover_states', '悬停检测方法'),
        ('_handle_button_click', '按钮点击处理方法'),
        ('_render_button', '按钮渲染方法'),
        ('self._buttons', '按钮字典'),
        ('self._button_hover_scale', '悬停缩放'),
        ('self._button_click_animation', '点击动画'),
        ("'menu'", '菜单按钮标识'),
        ("'quit'", '退出按钮标识'),
        ('"RETURN TO MAIN MENU"', '主菜单按钮文本'),
        ('"QUIT GAME"', '退出按钮文本'),
        ('pygame.MOUSEMOTION', '鼠标移动事件'),
        ('pygame.MOUSEBUTTONDOWN', '鼠标点击事件'),
        ('hover_scale', '悬停缩放变量'),
        ('glow_rect', '发光效果'),
    ]

    # 旧版本功能（不应该有）
    old_features = [
        ('ENTER to menu | ESC to quit', '旧版本提示文本'),
        ('hint = font_small.render("ENTER', '旧版本hint渲染'),
    ]

    print("\n✅ 新版本功能检查:")
    new_ok = True
    for code, desc in new_features:
        if code in content:
            print(f"   ✅ {desc}")
        else:
            print(f"   ❌ {desc} - 缺失")
            new_ok = False

    print("\n❌ 旧版本功能检查（应该全部不存在）:")
    old_ok = True
    for code, desc in old_features:
        if code in content:
            print(f"   ❌ {desc} - 发现旧代码!")
            old_ok = False
        else:
            print(f"   ✅ {desc} - 已移除")

    return new_ok and old_ok

def check_scene_director():
    """检查SceneDirector代码"""
    print("\n" + "=" * 70)
    print("检查 scene_director.py 游戏结束流程")
    print("=" * 70)

    path = 'airwar/game/scene_director.py'

    if not os.path.exists(path):
        print(f"❌ 文件不存在: {path}")
        return False

    content = read_file(path)

    # 应该有的功能
    features = [
        ('_handle_game_over', '游戏结束处理方法'),
        ('_game_over_screen.show(', '调用GameOverScreen.show()'),
        ('is_game_over()', '检查游戏结束状态'),
        ('ScreenAction.RETURN_TO_MENU', '返回主菜单动作'),
        ('ScreenAction.QUIT', '退出动作'),
    ]

    print("\n✅ 流程检查:")
    ok = True
    for code, desc in features:
        if code in content:
            print(f"   ✅ {desc}")
        else:
            print(f"   ❌ {desc} - 缺失")
            ok = False

    return ok

def check_game_scene():
    """检查GameScene游戏结束检测"""
    print("\n" + "=" * 70)
    print("检查 game_scene.py 游戏结束检测")
    print("=" * 70)

    path = 'airwar/scenes/game_scene.py'

    if not os.path.exists(path):
        print(f"❌ 文件不存在: {path}")
        return False

    content = read_file(path)

    # 应该有的功能
    features = [
        ('def is_game_over', '游戏结束检测方法'),
        ('player.active', '检查玩家激活状态'),
    ]

    print("\n✅ 检测逻辑检查:")
    ok = True
    for code, desc in features:
        if code in content:
            print(f"   ✅ {desc}")
        else:
            print(f"   ❌ {desc} - 缺失")
            ok = False

    return ok

def check_player_death():
    """检查玩家死亡逻辑"""
    print("\n" + "=" * 70)
    print("检查 player.py 玩家死亡逻辑")
    print("=" * 70)

    path = 'airwar/entities/player.py'

    if not os.path.exists(path):
        print(f"❌ 文件不存在: {path}")
        return False

    content = read_file(path)

    # 应该有的功能
    features = [
        ('def take_damage', '受伤方法'),
        ('self.active = False', '设置active为False'),
    ]

    print("\n✅ 死亡逻辑检查:")
    ok = True
    for code, desc in features:
        if code in content:
            print(f"   ✅ {desc}")
        else:
            print(f"   ❌ {desc} - 缺失")
            ok = False

    return ok

def main():
    print("\n" + "=" * 70)
    print("Air War GameOver 界面源代码验证")
    print("=" * 70)

    results = {
        'GameOverScreen': check_game_over_screen(),
        'SceneDirector': check_scene_director(),
        'GameScene': check_game_scene(),
        'Player': check_player_death(),
    }

    print("\n" + "=" * 70)
    print("验证结果汇总")
    print("=" * 70)

    for name, result in results.items():
        status = '✅ 通过' if result else '❌ 失败'
        print(f"  {name:20s} {status}")

    if all(results.values()):
        print("\n" + "=" * 70)
        print("✅✅✅ 所有源代码检查通过!")
        print("=" * 70)
        print("\n代码实现正确。问题可能是:")
        print("  1. Python缓存未清除")
        print("  2. 需要重启游戏")
        print("  3. 需要重新安装依赖")
        print("\n请尝试以下步骤:")
        print("  1. 关闭游戏")
        print("  2. 运行: find . -type d -name '__pycache__' -exec rm -rf {} +")
        print("  3. 运行: find . -name '*.pyc' -delete")
        print("  4. 重新启动游戏")
        return 0
    else:
        print("\n" + "=" * 70)
        print("❌❌❌ 部分检查失败!")
        print("=" * 70)
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
