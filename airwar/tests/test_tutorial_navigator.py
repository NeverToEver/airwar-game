"""
Test module for TutorialNavigator component.

This module contains unit tests for the TutorialNavigator class.
Following the F.I.R.S.T. principles: Fast, Independent, Repeatable, Self-Validating, Timely.
"""

import pytest
from airwar.components.tutorial import TutorialNavigator
from airwar.config.tutorial import TUTORIAL_STEPS


class TestTutorialNavigator:
    """Test suite for TutorialNavigator class."""

    def test_initial_state(self):
        """Test that navigator initializes to first step."""
        nav = TutorialNavigator()
        assert nav.get_current_index() == 0
        assert nav.get_current_step()['id'] == 'movement'
        assert nav.is_first_step()
        assert not nav.is_last_step()

    def test_next_step(self):
        """Test navigation to next step."""
        nav = TutorialNavigator()
        assert nav.next_step()
        assert nav.get_current_index() == 1
        assert nav.get_current_step()['id'] == 'mother_ship'

    def test_next_step_boundary(self):
        """Test that next_step returns False at last step."""
        nav = TutorialNavigator()
        for _ in range(len(TUTORIAL_STEPS)):
            nav.next_step()
        assert not nav.next_step()
        assert nav.is_last_step()

    def test_previous_step(self):
        """Test navigation to previous step."""
        nav = TutorialNavigator()
        nav.next_step()
        assert nav.previous_step()
        assert nav.get_current_index() == 0
        assert nav.is_first_step()

    def test_previous_step_boundary(self):
        """Test that previous_step returns False at first step."""
        nav = TutorialNavigator()
        assert not nav.previous_step()
        assert nav.is_first_step()

    def test_can_go_previous(self):
        """Test can_go_previous method."""
        nav = TutorialNavigator()
        assert not nav.can_go_previous()
        nav.next_step()
        assert nav.can_go_previous()

    def test_can_go_next(self):
        """Test can_go_next method."""
        nav = TutorialNavigator()
        assert nav.can_go_next()
        while nav.can_go_next():
            nav.next_step()
        assert not nav.can_go_next()

    def test_progress_indicators(self):
        """Test progress indicator generation."""
        nav = TutorialNavigator()
        progress = nav.get_progress()
        assert len(progress) == len(TUTORIAL_STEPS)
        assert progress[0] is True
        for i in range(1, len(progress)):
            assert progress[i] is False

    def test_progress_indicators_after_navigation(self):
        """Test progress indicators update after navigation."""
        nav = TutorialNavigator()
        nav.next_step()
        progress = nav.get_progress()
        assert progress[0] is True
        assert progress[1] is True
        for i in range(2, len(progress)):
            assert progress[i] is False

    def test_is_complete_step(self):
        """Test is_complete_step method."""
        nav = TutorialNavigator()
        assert not nav.is_complete_step()
        while not nav.is_last_step():
            nav.next_step()
        assert nav.is_complete_step()

    def test_reset(self):
        """Test that reset returns to initial state."""
        nav = TutorialNavigator()
        nav.next_step()
        nav.next_step()
        nav.reset()
        assert nav.get_current_index() == 0
        assert nav.is_first_step()

    def test_get_total_steps(self):
        """Test get_total_steps method."""
        nav = TutorialNavigator()
        assert nav.get_total_steps() == len(TUTORIAL_STEPS)

    def test_complete_navigation_sequence(self):
        """Test complete navigation from first to last step."""
        nav = TutorialNavigator()
        step_ids = ['movement', 'mother_ship', 'pause', 'complete']
        
        for i, expected_id in enumerate(step_ids):
            assert nav.get_current_step()['id'] == expected_id
            if i < len(step_ids) - 1:
                assert nav.next_step()
