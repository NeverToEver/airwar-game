"""
调试脚本：测试H键触发母舰功能
"""
import pygame
import sys
from unittest.mock import patch, MagicMock

# 初始化pygame
pygame.init()
pygame.display.set_mode((800, 600))

# 导入游戏模块
from airwar.scenes.game_scene import GameScene
from airwar.game.mother_ship.mother_ship_state import MotherShipState

def test_h_key_docking_flow():
    """测试完整的H键触发进入母舰流程"""
    print("=" * 60)
    print("测试H键触发进入母舰流程")
    print("=" * 60)

    # 创建游戏场景
    scene = GameScene()
    print(f"\n1. GameScene创建完成")
    print(f"   - _mother_ship_integrator: {scene._mother_ship_integrator is not None}")
    print(f"   - entrance_animation: {scene.game_controller.state.entrance_animation}")

    # 模拟进入动画期间
    scene.game_controller.state.entrance_animation = True
    scene.game_controller.state.entrance_timer = 0
    scene.game_controller.state.entrance_duration = 60  # 60帧的进入动画

    print(f"\n2. 进入动画开始（entrance_animation = True）")
    print(f"   - entrance_duration: {scene.game_controller.state.entrance_duration}")

    # 模拟按住H键
    with patch('pygame.key.get_pressed', return_value={pygame.K_h: True}):
        print(f"\n3. 模拟按住H键...")

        # 运行几帧，看看事件是否被正确发布
        for frame in range(10):
            scene.update()

            if frame == 0:
                print(f"\n4. 第{frame}帧后的状态：")
                state_machine = scene._mother_ship_integrator._state_machine
                print(f"   - 当前状态: {state_machine.current_state}")
                print(f"   - docking_animation_active: {scene._mother_ship_integrator._docking_animation_active}")

        # 继续运行足够多的帧来触发进度完成（3秒 = 180帧 @ 60fps）
        print(f"\n5. 继续运行180帧（3秒）...")

        for frame in range(180):
            scene.update()

            if frame == 0:
                state_machine = scene._mother_ship_integrator._state_machine
                print(f"   - 当前状态: {state_machine.current_state}")
                print(f"   - docking_animation_active: {scene._mother_ship_integrator._docking_animation_active}")

        # 检查最终状态
        print(f"\n6. 180帧后的状态：")
        state_machine = scene._mother_ship_integrator._state_machine
        print(f"   - 当前状态: {state_machine.current_state}")
        print(f"   - 预期状态: {MotherShipState.DOCKING} 或 {MotherShipState.DOCKED}")
        print(f"   - docking_animation_active: {scene._mother_ship_integrator._docking_animation_active}")
        print(f"   - progress: {scene._mother_ship_integrator._input_detector._progress.current_progress}")

        # 验证结果
        if state_machine.current_state in [MotherShipState.DOCKING, MotherShipState.DOCKED]:
            print(f"\n✅ 测试通过：状态转换正确")
        else:
            print(f"\n❌ 测试失败：状态转换不正确")
            print(f"   预期: {MotherShipState.DOCKING} 或 {MotherShipState.DOCKED}")
            print(f"   实际: {state_machine.current_state}")

    pygame.quit()

if __name__ == '__main__':
    test_h_key_docking_flow()
