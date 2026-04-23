"""
Test module for TutorialNavigator component.

This module contains unit tests for the TutorialNavigator class.
Following the F.I.R.S.T. principles: Fast, Independent, Repeatable, Self-Validating, Timely.
"""

import pytest
from airwar.scenes.tutorial import TutorialNavigator
from airwar.config.tutorial import TUTORIAL_STEPS


class TestTutorialNavigator:
    def test_initial_state(self):
        nav = TutorialNavigator()
        assert nav.get_current_index() == 0
        assert nav.get_current_step()['id'] == 'welcome'
        assert nav.is_first_step()
        assert not nav.is_last_step()

    def test_next_step(self):
        nav = TutorialNavigator()
        assert nav.next_step()
        assert nav.get_current_index() == 1
        assert nav.get_current_step()['id'] == 'movement'

    def test_next_step_boundary(self):
        nav = TutorialNavigator()
        for _ in range(len(TUTORIAL_STEPS)):
            nav.next_step()
        assert not nav.next_step()
        assert nav.is_last_step()

    def test_previous_step(self):
        nav = TutorialNavigator()
        nav.next_step()
        assert nav.previous_step()
        assert nav.get_current_index() == 0
        assert nav.is_first_step()

    def test_previous_step_boundary(self):
        nav = TutorialNavigator()
        assert not nav.previous_step()
        assert nav.is_first_step()

    def test_can_go_previous(self):
        nav = TutorialNavigator()
        assert not nav.can_go_previous()
        nav.next_step()
        assert nav.can_go_previous()

    def test_can_go_next(self):
        nav = TutorialNavigator()
        assert nav.can_go_next()
        while nav.can_go_next():
            nav.next_step()
        assert not nav.can_go_next()

    def test_progress_indicators(self):
        nav = TutorialNavigator()
        progress = nav.get_progress()
        assert len(progress) == len(TUTORIAL_STEPS)
        assert progress[0] is True
        for i in range(1, len(progress)):
            assert progress[i] is False

    def test_progress_indicators_after_navigation(self):
        nav = TutorialNavigator()
        nav.next_step()
        progress = nav.get_progress()
        assert progress[0] is True
        assert progress[1] is True
        for i in range(2, len(progress)):
            assert progress[i] is False

    def test_is_complete_step(self):
        nav = TutorialNavigator()
        assert not nav.is_complete_step()
        while not nav.is_last_step():
            nav.next_step()
        assert nav.is_complete_step()

    def test_reset(self):
        nav = TutorialNavigator()
        nav.next_step()
        nav.next_step()
        nav.reset()
        assert nav.get_current_index() == 0
        assert nav.is_first_step()

    def test_get_total_steps(self):
        nav = TutorialNavigator()
        assert nav.get_total_steps() == len(TUTORIAL_STEPS)

    def test_complete_navigation_sequence(self):
        nav = TutorialNavigator()
        step_ids = ['welcome', 'movement', 'buff', 'mechanics', 'ready']
        
        for i, expected_id in enumerate(step_ids):
            assert nav.get_current_step()['id'] == expected_id
            if i < len(step_ids) - 1:
                assert nav.next_step()

    def test_welcome_step_type(self):
        nav = TutorialNavigator()
        step = nav.get_current_step()
        assert step['id'] == 'welcome'
        assert step['type'] == 'welcome'

    def test_mechanics_step_is_fourth(self):
        nav = TutorialNavigator()
        nav.next_step()
        nav.next_step()
        nav.next_step()
        assert nav.get_current_step()['id'] == 'mechanics'

    def test_selected_index_initial(self):
        nav = TutorialNavigator()
        assert nav.get_selected_index() == 0

    def test_move_selection_up(self):
        nav = TutorialNavigator()
        nav.move_selection_down(4)
        assert nav.get_selected_index() == 1
        nav.move_selection_up(4)
        assert nav.get_selected_index() == 0

    def test_move_selection_down(self):
        nav = TutorialNavigator()
        nav.move_selection_down(4)
        assert nav.get_selected_index() == 1
        nav.move_selection_down(4)
        assert nav.get_selected_index() == 2

    def test_move_selection_boundary(self):
        nav = TutorialNavigator()
        assert not nav.move_selection_up(4)
        assert nav.get_selected_index() == 0
        for _ in range(10):
            nav.move_selection_down(4)
        assert nav.get_selected_index() == 4
        assert not nav.move_selection_down(4)

    def test_reset_clears_selection(self):
        nav = TutorialNavigator()
        nav.move_selection_down(4)
        nav.move_selection_down(4)
        assert nav.get_selected_index() == 2
        nav.reset()
        assert nav.get_selected_index() == 0
