"""Multiplayer vertical-slice tests.

These tests cover only the *minimum* slice required to validate that two
Player instances can coexist and be driven by independent input sources.
They do NOT cover full split-screen rendering, dual HUD, or co-op
game-controller semantics -- those are deferred. See
``docs/multiplayer_feasibility.md`` for the full scope discussion.
"""

import pygame
import pytest


@pytest.fixture(scope="module", autouse=True)
def _init_pygame():
    pygame.init()
    pygame.display.set_mode((800, 600))
    return


class TestPlayerId:
    """Player.player_id defaults to 0 and is settable via the constructor."""

    def test_default_player_id_is_zero(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler

        p = Player(400, 900, MockInputHandler())
        assert p.player_id == 0

    def test_explicit_player_id_is_stored(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler

        p = Player(400, 900, MockInputHandler(), player_id=1)
        assert p.player_id == 1

    def test_backward_compat_construction(self):
        """Existing 3-arg call sites must still work unchanged."""
        from airwar.entities import Player
        from airwar.input import PygameInputHandler

        # This call shape is used in ~30+ call sites across the codebase.
        p = Player(400, 900, PygameInputHandler())
        assert p.player_id == 0
        assert p.health > 0


class TestTwoPlayersIndependent:
    """Two Player instances must be drivable by independent input sources."""

    def test_two_players_move_in_different_directions(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler

        p1 = Player(100, 900, MockInputHandler(), player_id=0)
        p2 = Player(100, 900, MockInputHandler(), player_id=1)

        ih1 = p1._input_handler
        ih2 = p2._input_handler

        ih1.set_direction(1, 0)  # P1 moves right
        ih2.set_direction(-1, 0)  # P2 moves left

        p1.update()
        p2.update()

        assert p1.rect.x > 100, "P1 should have moved right"
        assert p2.rect.x < 100, "P2 should have moved left"

    def test_two_players_have_independent_bullet_pools(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler

        p1 = Player(100, 900, MockInputHandler(), player_id=0)
        p2 = Player(100, 900, MockInputHandler(), player_id=1)

        for _ in range(3):
            p1.auto_fire()
            p2.auto_fire()

        # Each Player owns its own bullet list -- they must not share.
        p1_bullets = p1.get_bullets()
        p2_bullets = p2.get_bullets()
        assert p1_bullets is not p2_bullets
        assert len(p1_bullets) > 0
        assert len(p2_bullets) > 0

    def test_two_players_take_independent_damage(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler

        p1 = Player(100, 900, MockInputHandler(), player_id=0)
        p2 = Player(100, 900, MockInputHandler(), player_id=1)
        start = p1.health

        p1.take_damage(20)
        assert p1.health == start - 20
        # P2 must be unaffected by P1's damage.
        assert p2.health == p2.max_health


class TestPygameInputHandlerBindings:
    """PygameInputHandler must accept a custom key_bindings preset."""

    def test_default_bindings_present(self):
        from airwar.input import PygameInputHandler

        ih = PygameInputHandler()
        # Smoke check: every key in DEFAULT_BINDINGS is in the live handler.
        for key, code in PygameInputHandler.DEFAULT_BINDINGS.items():
            assert ih._bindings[key] == code

    def test_player2_preset_keys_dont_overlap_with_default(self):
        """The Player 2 preset must use keys that don't collide with P1.

        P1 movement uses WASD / arrows. P2 uses IJKL / tfgh. These
        sets must be disjoint so the two players don't fight for input.
        (Pause / boost / precision are intentionally global; movement
        keys must not be shared.)
        """
        from airwar.input import PygameInputHandler

        # Boost/precision and pause are allowed to be global; only
        # the *movement* key sets must be disjoint.
        shared = {"boost", "precision", "pause"}
        p1_movement = {
            v for k, v in PygameInputHandler.DEFAULT_BINDINGS.items() if k not in shared
        }
        p2_movement = {
            v for k, v in PygameInputHandler.PLAYER2_BINDINGS.items() if k not in shared
        }
        assert p1_movement.isdisjoint(p2_movement), (
            "P1 and P2 movement keys must not overlap"
        )

    def test_handler_uses_custom_bindings(self):
        """PygameInputHandler with custom bindings must read the right keys."""
        from airwar.input import PygameInputHandler

        custom = {
            "left": pygame.K_j,
            "left_alt": pygame.K_f,
            "right": pygame.K_l,
            "right_alt": pygame.K_h,
            "up": pygame.K_i,
            "up_alt": pygame.K_t,
            "down": pygame.K_k,
            "down_alt": pygame.K_g,
            "pause": pygame.K_ESCAPE,
            "boost": pygame.K_u,
            "precision": pygame.K_o,
        }
        ih = PygameInputHandler(key_bindings=custom)
        assert ih._bindings["left"] == pygame.K_j
        assert ih._bindings["boost"] == pygame.K_u
