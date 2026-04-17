import pygame
from airwar.scenes.game_scene import GameScene
from airwar.game.mother_ship.mother_ship_state import MotherShipState


class DebugRippleTest:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        self.game_scene = GameScene()
        self.game_scene.enter(difficulty='easy', username='DebugTest')

    def test_with_debug(self):
        print("Initial state:")
        print(f"  Mother ship state: {self.game_scene._mother_ship_integrator._state_machine.current_state}")
        print(f"  Ripple effects: {len(self.game_scene.game_controller.state.ripple_effects)}")

        print("\nCreating ripple effect...")
        self.game_scene.game_controller.on_player_hit(20, self.game_scene.player)
        print(f"  Ripple effects: {len(self.game_scene.game_controller.state.ripple_effects)}")

        print("\nTriggering docking progress...")
        event_bus = self.game_scene._mother_ship_integrator._event_bus
        event_bus.publish('PROGRESS_COMPLETE')

        print(f"  Mother ship state: {self.game_scene._mother_ship_integrator._state_machine.current_state}")
        print(f"  Ripple effects after PROGRESS_COMPLETE: {len(self.game_scene.game_controller.state.ripple_effects)}")

        print("\nSimulating docking animation frames...")
        for i in range(5):
            self.game_scene._mother_ship_integrator.update()
            print(f"  Frame {i+1}: state={self.game_scene._mother_ship_integrator._state_machine.current_state}, ripples={len(self.game_scene.game_controller.state.ripple_effects)}")

        print("\nAfter docking animation (checking if DOCKING_ANIMATION_COMPLETE event fires)...")

        if self.game_scene._mother_ship_integrator.is_docking_animation_active():
            print("  Docking animation still active, continuing...")
            for i in range(100):
                self.game_scene._mother_ship_integrator.update()
                if not self.game_scene._mother_ship_integrator.is_docking_animation_active():
                    print(f"  Animation completed at frame {i+1}")
                    break

        print(f"\nFinal state:")
        print(f"  Mother ship state: {self.game_scene._mother_ship_integrator._state_machine.current_state}")
        print(f"  Ripple effects: {len(self.game_scene.game_controller.state.ripple_effects)}")
        print(f"  Is docked: {self.game_scene._mother_ship_integrator.is_docked()}")


if __name__ == "__main__":
    test = DebugRippleTest()
    test.test_with_debug()
