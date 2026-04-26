import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRewardPool:
    def test_reward_pool_structure(self):
        from airwar.game.systems.reward_system import REWARD_POOL
        assert 'health' in REWARD_POOL
        assert 'offense' in REWARD_POOL
        assert 'defense' in REWARD_POOL
        assert 'utility' in REWARD_POOL

    def test_reward_pool_has_required_fields(self):
        from airwar.game.systems.reward_system import REWARD_POOL
        for category, rewards in REWARD_POOL.items():
            assert len(rewards) > 0
            for reward in rewards:
                assert 'name' in reward
                assert 'desc' in reward
                assert 'icon' in reward

    def test_reward_categories_count(self):
        from airwar.game.systems.reward_system import REWARD_POOL
        assert len(REWARD_POOL['health']) >= 3
        assert len(REWARD_POOL['offense']) >= 5
        assert len(REWARD_POOL['defense']) >= 3
        assert len(REWARD_POOL['utility']) >= 1

    def test_all_rewards_unique(self):
        from airwar.game.systems.reward_system import REWARD_POOL
        all_names = []
        for rewards in REWARD_POOL.values():
            all_names.extend([r['name'] for r in rewards])
        assert len(all_names) == len(set(all_names))

    def test_rewards_have_meaningful_descriptions(self):
        from airwar.game.systems.reward_system import REWARD_POOL
        for category, rewards in REWARD_POOL.items():
            for reward in rewards:
                assert len(reward['desc']) > 5


class TestRewardSelector:
    def test_reward_selector_initial_state(self):
        from airwar.scenes.game_scene import RewardSelector
        selector = RewardSelector()
        assert selector.visible is False
        assert selector.selected_index == 0
        assert selector.options == []

    def test_reward_selector_show(self):
        from airwar.scenes.game_scene import RewardSelector
        selector = RewardSelector()
        options = [
            {'name': 'Test1', 'desc': 'Desc1', 'icon': 'T1'},
            {'name': 'Test2', 'desc': 'Desc2', 'icon': 'T2'},
        ]
        selector.show(options, lambda x: None)
        assert selector.visible is True
        assert len(selector.options) == 2

    def test_reward_selector_hide(self):
        from airwar.scenes.game_scene import RewardSelector
        selector = RewardSelector()
        selector.show([{'name': 'Test', 'desc': 'D', 'icon': 'T'}], lambda x: None)
        selector.hide()
        assert selector.visible is False

    def test_reward_selector_selection_navigation(self):
        from airwar.scenes.game_scene import RewardSelector
        selector = RewardSelector()
        options = [
            {'name': 'Test1', 'desc': 'D1', 'icon': 'T1'},
            {'name': 'Test2', 'desc': 'D2', 'icon': 'T2'},
            {'name': 'Test3', 'desc': 'D3', 'icon': 'T3'},
        ]
        selector.show(options, lambda x: None)

        import pygame
        pygame.init()

        selector.handle_input(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_DOWN}))
        assert selector.selected_index == 1

        selector.handle_input(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_DOWN}))
        assert selector.selected_index == 2

        selector.handle_input(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_UP}))
        assert selector.selected_index == 1

    def test_reward_selector_wrap_around(self):
        from airwar.scenes.game_scene import RewardSelector
        selector = RewardSelector()
        options = [
            {'name': 'Test1', 'desc': 'D1', 'icon': 'T1'},
            {'name': 'Test2', 'desc': 'D2', 'icon': 'T2'},
        ]
        selector.show(options, lambda x: None)
        selector.selected_index = 0

        import pygame
        pygame.init()

        selector.handle_input(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_UP}))
        assert selector.selected_index == 1

        selector.handle_input(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_DOWN}))
        assert selector.selected_index == 0

    def test_reward_selector_generate_options_returns_3(self):
        from airwar.scenes.game_scene import RewardSelector
        selector = RewardSelector()
        options = selector.generate_options(0, [])
        assert len(options) == 3

    def test_reward_selector_confirm_calls_callback(self):
        from airwar.scenes.game_scene import RewardSelector
        selector = RewardSelector()
        options = [
            {'name': 'Test1', 'desc': 'D1', 'icon': 'T1'},
            {'name': 'Test2', 'desc': 'D2', 'icon': 'T2'},
        ]
        selected = []

        def callback(reward):
            selected.append(reward)

        selector.show(options, callback)
        selector.selected_index = 1

        import pygame
        pygame.init()

        selector.handle_input(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RETURN}))
        assert len(selected) == 1
        assert selected[0]['name'] == 'Test2'
