import pygame
import sys
from airwar.scenes.game_scene import GameScene
from airwar.game.mother_ship.mother_ship_state import MotherShipState


class RippleEffectTestFixed:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Ripple Effect Clear Test - Fixed")
        self.clock = pygame.time.Clock()
        self.game_scene = GameScene()
        self.running = True

    def setup(self):
        self.game_scene.enter(difficulty='easy', username='TestPlayer')
        print("Test setup complete")
        print(f"Initial ripple effects: {len(self.game_scene.game_controller.state.ripple_effects)}")

    def _trigger_pressing(self):
        event_bus = self.game_scene._mother_ship_integrator._event_bus
        event_bus.publish('H_PRESSED')
        for _ in range(3):
            self.game_scene._mother_ship_integrator.update()

    def _trigger_progress_complete(self):
        event_bus = self.game_scene._mother_ship_integrator._event_bus
        event_bus.publish('PROGRESS_COMPLETE')
        for _ in range(3):
            self.game_scene._mother_ship_integrator.update()

    def _trigger_undocking(self):
        event_bus = self.game_scene._mother_ship_integrator._event_bus
        event_bus.publish('H_PRESSED')
        for _ in range(3):
            self.game_scene._mother_ship_integrator.update()

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

    def test_scenario_1_ripple_at_start_of_docking(self):
        print("\n" + "="*60)
        print("TEST SCENARIO 1: Ripple at START of docking")
        print("="*60)

        self._trigger_pressing()
        self.game_scene.game_controller.on_player_hit(20, self.game_scene.player)
        print(f"Created ripple effect: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        self._trigger_progress_complete()
        print(f"After progress complete (DOCKING state): {len(self.game_scene.game_controller.state.ripple_effects)} ripples")
        print(f"Current state: {self.game_scene._mother_ship_integrator._state_machine.current_state}")

        self._simulate_docking_animation()
        print(f"After docking animation (DOCKED state): {len(self.game_scene.game_controller.state.ripple_effects)} ripples")
        print(f"Current state: {self.game_scene._mother_ship_integrator._state_machine.current_state}")

        result = len(self.game_scene.game_controller.state.ripple_effects) == 0
        print(f"✓ Ripple effects cleared: {result}")
        return result

    def test_scenario_2_ripple_in_middle_of_docking(self):
        print("\n" + "="*60)
        print("TEST SCENARIO 2: Ripple in MIDDLE of docking")
        print("="*60)

        self._trigger_pressing()
        for _ in range(5):
            self._simulate_frame()

        self.game_scene.game_controller.on_player_hit(20, self.game_scene.player)
        print(f"Created ripple effect in middle: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        for _ in range(30):
            self._simulate_frame()

        self._trigger_progress_complete()
        print(f"After progress complete: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        self._simulate_docking_animation()
        print(f"After docking animation: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        result = len(self.game_scene.game_controller.state.ripple_effects) == 0
        print(f"✓ Ripple effects cleared: {result}")
        return result

    def test_scenario_3_ripple_near_end_of_docking(self):
        print("\n" + "="*60)
        print("TEST SCENARIO 3: Ripple NEAR END of docking")
        print("="*60)

        self._trigger_pressing()
        for _ in range(10):
            self._simulate_frame()

        self.game_scene.game_controller.on_player_hit(20, self.game_scene.player)
        print(f"Created ripple effect near end: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        for _ in range(70):
            self._simulate_frame()

        self._trigger_progress_complete()
        print(f"After progress complete: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        self._simulate_docking_animation()
        print(f"After docking animation: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        result = len(self.game_scene.game_controller.state.ripple_effects) == 0
        print(f"✓ Ripple effects cleared: {result}")
        return result

    def test_scenario_4_multiple_ripples(self):
        print("\n" + "="*60)
        print("TEST SCENARIO 4: Multiple ripples")
        print("="*60)

        self._trigger_pressing()
        for i in range(3):
            self.game_scene.game_controller.on_player_hit(20, self.game_scene.player)
            for _ in range(10):
                self._simulate_frame()
        print(f"Created multiple ripples: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        self._trigger_progress_complete()
        print(f"After progress complete: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        self._simulate_docking_animation()
        print(f"After docking animation: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        result = len(self.game_scene.game_controller.state.ripple_effects) == 0
        print(f"✓ All ripple effects cleared: {result}")
        return result

    def test_scenario_5_undocking_with_ripples(self):
        print("\n" + "="*60)
        print("TEST SCENARIO 5: Undocking with ripples")
        print("="*60)

        self._trigger_pressing()
        self._trigger_progress_complete()
        self._simulate_docking_animation()
        print(f"Docked: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        self._trigger_undocking()
        print(f"After undocking trigger: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")
        print(f"Current state: {self.game_scene._mother_ship_integrator._state_machine.current_state}")

        for _ in range(5):
            self._simulate_frame()

        self.game_scene.game_controller.on_player_hit(20, self.game_scene.player)
        print(f"Created ripple during undocking: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        self._simulate_undocking_animation()
        print(f"After undocking animation: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        result = len(self.game_scene.game_controller.state.ripple_effects) == 0
        print(f"✓ Ripple effects cleared after undocking: {result}")
        return result

    def test_scenario_6_idle_state_with_ripples(self):
        print("\n" + "="*60)
        print("TEST SCENARIO 6: Ripples when returning to IDLE")
        print("="*60)

        self._trigger_pressing()
        self.game_scene.game_controller.on_player_hit(20, self.game_scene.player)
        print(f"Created ripple before release: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")

        event_bus = self.game_scene._mother_ship_integrator._event_bus
        event_bus.publish('H_RELEASED')
        print(f"After H_RELEASED: {len(self.game_scene.game_controller.state.ripple_effects)} ripples")
        print(f"Current state: {self.game_scene._mother_ship_integrator._state_machine.current_state}")

        result = len(self.game_scene.game_controller.state.ripple_effects) == 0
        print(f"✓ Ripple effects cleared when returning to IDLE: {result}")
        return result

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
            self.reset_game()

            results.append(("Scenario 6 - Ripples in IDLE state", self.test_scenario_6_idle_state_with_ripples()))

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
    test = RippleEffectTestFixed()
    success = test.run()

    if not success:
        sys.exit(1)
