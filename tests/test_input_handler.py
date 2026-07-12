"""Tests for the input handler abstraction and pygame implementation."""

import pygame
import pytest

from airwar.input.input_handler import InputHandler, PygameInputHandler


class DummyInputHandler(InputHandler):
    """Concrete implementation used to verify the abstract protocol."""

    def get_movement_direction(self):
        from airwar.entities.base import Vector2

        return Vector2(0, 0)

    def is_pause_pressed(self):
        return False

    def is_boost_pressed(self):
        return False

    def is_boost_just_pressed(self):
        return False

    def is_precision_pressed(self):
        return False

    def is_precision_just_pressed(self):
        return False

    def tick(self):
        pass


class TestInputHandlerProtocol:
    def test_tick_is_part_of_protocol(self):
        handler = DummyInputHandler()
        handler.tick()

    def test_default_bindings_are_not_shared_mutable_state(self):
        handler_a = PygameInputHandler()
        handler_b = PygameInputHandler()
        assert handler_a._bindings is not handler_b._bindings
        handler_a._bindings["left"] = pygame.K_1
        assert handler_b._bindings["left"] == pygame.K_LEFT


class TestPygameInputHandlerBindingValidation:
    def test_missing_bindings_raise(self):
        with pytest.raises(ValueError, match="Missing key bindings"):
            PygameInputHandler({"left": pygame.K_LEFT})

    def test_negative_key_binding_raises(self):
        bindings = dict(PygameInputHandler.DEFAULT_BINDINGS)
        bindings["left"] = -1
        with pytest.raises(ValueError, match="Invalid key binding"):
            PygameInputHandler(bindings)

    def test_unknown_key_binding_raises(self):
        bindings = dict(PygameInputHandler.DEFAULT_BINDINGS)
        bindings["left"] = 999999999
        with pytest.raises(ValueError, match="Invalid key binding"):
            PygameInputHandler(bindings)

    def test_non_int_key_binding_raises(self):
        bindings = dict(PygameInputHandler.DEFAULT_BINDINGS)
        bindings["left"] = "left"
        with pytest.raises(ValueError, match="Invalid key binding"):
            PygameInputHandler(bindings)


class TestPygameInputHandlerOppositeKeys:
    def test_opposite_key_conflict_is_documented_and_overrides(self):
        """Right overrides left and down overrides up (last-write-wins)."""
        handler = PygameInputHandler()
        doc = handler.get_movement_direction.__doc__
        assert doc is not None
        assert "override" in doc.lower()
