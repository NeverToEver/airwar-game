import pygame
import sys
from airwar.scenes.game_scene import GameScene
from airwar.game.mother_ship.mother_ship_state import MotherShipState
from airwar.game.mother_ship import EventBus


class RippleEffectTest:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Ripple Effect Clear Test")
        self.clock = pygame.time.Clock()
        self.game_scene = GameScene()
        self.running = True

    def setup(self):
        self.game_scene.enter(difficulty='easy', username='TestPlayer')
        print("Test setup complete")
        print(f"Initial ripple effects: {len(self.game_scene.game_controller.state.ripple_effects)}")

    def test_scenario_1_ripple_at_start_of_docking(self):
        print("\n" + "="*60)
        print("TEST SCENARIO 1: Ripple at START of docking")
        print("="*60)

        self.game_scene.game_controller.on_player_hit(20, self.game_scene.player)
        print(f"Created ripple effect: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        self._trigger_docking()
        print(f"After docking triggered: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        self._simulate_docking_animation()

        result = len(self.game_scene.game_controller.state.ripple_effects) == 0
        print(f"✓ Ripple effects cleared: {result}")
        return result

    def test_scenario_2_ripple_in_middle_of_docking(self):
        print("\n" + "="*60)
        print("TEST SCENARIO 2: Ripple in MIDDLE of docking")
        print("="*60)

        for _ in range(5):
            self._simulate_frame()

        self.game_scene.game_controller.on_player_hit(20, self.game_scene.player)
        print(f"Created ripple effect in middle: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        for _ in range(30):
            self._simulate_frame()

        self._trigger_docking()
        print(f"After docking triggered: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        self._simulate_docking_animation()

        result = len(self.game_scene.game_controller.state.ripple_effects) == 0
        print(f"✓ Ripple effects cleared: {result}")
        return result

    def test_scenario_3_ripple_near_end_of_docking(self):
        print("\n" + "="*60)
        print("TEST SCENARIO 3: Ripple NEAR END of docking")
        print("="*60)

        for _ in range(10):
            self._simulate_frame()

        self.game_scene.game_controller.on_player_hit(20, self.game_scene.player)
        print(f"Created ripple effect near end: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        for _ in range(70):
            self._simulate_frame()

        self._trigger_docking()
        print(f"After docking triggered: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        self._simulate_docking_animation()

        result = len(self.game_scene.game_controller.state.ripple_effects) == 0
        print(f"✓ Ripple effects cleared: {result}")
        return result

    def test_scenario_4_multiple_ripples(self):
        print("\n" + "="*60)
        print("TEST SCENARIO 4: Multiple ripples")
        print("="*60)

        for i in range(3):
            self.game_scene.game_controller.on_player_hit(20, self.game_scene.player)
            for _ in range(10):
                self._simulate_frame()
        print(f"Created multiple ripples: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        self._trigger_docking()
        print(f"After docking triggered: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        self._simulate_docking_animation()

        result = len(self.game_scene.game_controller.state.ripple_effects) == 0
        print(f"✓ All ripple effects cleared: {result}")
        return result

    def test_scenario_5_undocking_with_ripples(self):
        print("\n" + "="*60)
        print("TEST SCENARIO 5: Undocking with ripples")
        print("="*60)

        self._trigger_docking()
        self._simulate_docking_animation()
        print(f"Docked: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        self._trigger_undocking()
        self._simulate_frame()
        self.game_scene.game_controller.on_player_hit(20, self.game_scene.player)
        print(f"Created ripple during undocking: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        self._simulate_undocking_animation()

        result = len(self.game_scene.game_controller.state.ripple_effects) == 0
        print(f"✓ Ripple effects cleared after undocking: {result}")
        return result

    def _trigger_docking(self):
        event_bus = self.game_scene._mother_ship_integrator._event_bus
        event_bus.publish('PROGRESS_COMPLETE')

    def _trigger_undocking(self):
        event_bus = self.game_scene._mother_ship_integrator._event_bus
        event_bus.publish('H_PRESSED')

    def _simulate_docking_animation(self):
        for _ in range(100):
            self.game_scene._mother_ship_integrator.update()
            if not self.game_scene._mother_ship_integrator.is_docking_animation_active():
                break

    def _simulate_undocking_animation(self):
        for _ in range(80):
            self.game_scene._mother_ship_integrator.update()
            if not self.game_scene._mother_ship_integrator.is_undocking_animation_active():
                break

    def _simulate_frame(self):
        self.game_scene.update()
        self.game_scene.game_controller.update(self.game_scene.player, False)

    def run_all_tests(self):
        print("\n" + "="*60)
        print("RUNNING ALL TEST SCENARIOS")
        print("="*60)

        results = []
        try:
            results.append(("Scenario 1 - Ripple at START", self.test_scenario_1_ripple_at_start_of_docking()))
            self.reset_game()

            results.append(("Scenario 2 - Ripple in MIDDLE", self.test_scenario_2_ripple_in_middle_of_docking()))
            self.reset_game()

            results.append(("Scenario 3 - Ripple NEAR END", self.test_scenario_3_ripple_near_end_of_docking()))
            self.reset_game()

            results.append(("Scenario 4 - Multiple ripples", self.test_scenario_4_multiple_ripples()))
            self.reset_game()

            results.append(("Scenario 5 - Undocking with ripples", self.test_scenario_5_undocking_with_ripples()))

        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False

        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        all_passed = True
        for name, result in results:
            status = "✓ PASSED" if result else "✗ FAILED"
            print(f"{status}: {name}")
            if not result:
                all_passed = False

        print("="*60)
        if all_passed:
            print("✓ ALL TESTS PASSED")
        else:
            print("✗ SOME TESTS FAILED")
        print("="*60)

        return all_passed

    def reset_game(self):
        self.game_scene = GameScene()
        self.setup()

    def run(self):
        self.setup()

        all_passed = self.run_all_tests()

        if all_passed:
            print("\n✓ SUCCESS: All ripple effect clear tests passed!")
            return True
        else:
            print("\n✗ FAILURE: Some ripple effect clear tests failed!")
            return False


if __name__ == "__main__":
    test = RippleEffectTest()
    success = test.run()

    if not success:
        sys.exit(1)
