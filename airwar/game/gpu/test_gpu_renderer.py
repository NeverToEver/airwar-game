#!/usr/bin/env python3
"""GPU 渲染管线测试"""
import pygame
import moderngl
import numpy as np
import sys
sys.path.insert(0, '/home/ubt/airwar')

from airwar.game.gpu import (
    GPUContext, ShaderManager, TextureManager,
    BufferManager, GPUSpriteRenderer
)
from airwar.utils.sprites import get_player_sprite, get_enemy_sprite


def test_gpu_pipeline():
    """测试完整 GPU 渲染流程"""
    print("=== GPU 渲染管线测试 ===\n")

    # 1. 初始化 ModernGL 上下文
    print("1. 初始化 ModernGL 上下文...")
    ctx = GPUContext()
    try:
        ctx.initialize(1400, 800)
        print(f"   OpenGL 版本: {ctx.version}")
        print(f"   屏幕尺寸: {ctx.screen_size}")
    except Exception as e:
        print(f"   失败: {e}")
        return False

    # 2. 创建着色器管理器
    print("\n2. 创建着色器管理器...")
    shader_mgr = ShaderManager(ctx.context)
    print("   着色器管理器创建成功")

    # 3. 创建纹理管理器
    print("\n3. 创建纹理管理器...")
    texture_mgr = TextureManager(ctx.context)
    print("   纹理管理器创建成功")

    # 4. 初始化 pygame（用于生成精灵）
    print("\n4. 初始化 pygame 并生成精灵...")
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)  # 隐藏窗口

    player_surf = get_player_sprite(50, 60)
    enemy_surf = get_enemy_sprite(50, 50, 1.0)
    print(f"   玩家精灵尺寸: {player_surf.get_size()}")
    print(f"   敌机精灵尺寸: {enemy_surf.get_size()}")

    # 5. 上传纹理到 GPU
    print("\n5. 上传纹理到 GPU...")
    texture_mgr.load_surface('player', player_surf)
    texture_mgr.load_surface('enemy', enemy_surf)
    print("   纹理上传成功")

    # 6. 创建精灵渲染器
    print("\n6. 创建 GPU 精灵渲染器...")
    sprite_renderer = GPUSpriteRenderer(ctx.context)
    print("   精灵渲染器创建成功")

    # 7. 添加测试精灵
    print("\n7. 添加测试精灵...")
    sprite_renderer.add_sprite('player', 400, 300, 50, 60, rotation=0.0)
    sprite_renderer.add_sprite('player', 500, 400, 50, 60, rotation=0.5)
    sprite_renderer.add_sprite('enemy', 600, 350, 50, 50)
    sprite_renderer.add_sprite('enemy', 700, 250, 50, 50)
    print("   添加了 4 个测试精灵")

    # 8. 渲染测试
    print("\n8. 执行渲染测试...")
    ctx.clear(0.1, 0.1, 0.2, 1.0)
    sprite_renderer.render(1400, 800)
    print("   渲染完成")

    # 9. 清理
    print("\n9. 清理资源...")
    sprite_renderer.release()
    texture_mgr.release_all()
    shader_mgr.release_all()
    ctx.release()
    pygame.quit()
    print("   清理完成")

    print("\n=== 测试通过 ===")
    return True


if __name__ == '__main__':
    success = test_gpu_pipeline()
    sys.exit(0 if success else 1)
