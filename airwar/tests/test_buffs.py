
import pytest


class TestBuffRegistry:
    def test_buff_registry_exists(self):
        from airwar.game.buffs.buff_registry import BUFF_REGISTRY
        assert BUFF_REGISTRY is not None
        assert len(BUFF_REGISTRY) > 0

    def test_buff_registry_has_all_buffs(self):
        from airwar.game.buffs.buff_registry import BUFF_REGISTRY
        expected_buffs = [
            'Extra Life', 'Regeneration', 'Lifesteal',
            'Power Shot', 'Rapid Fire', 'Piercing', 'Spread Shot', 'Explosive', 'Shotgun', 'Laser',
            'Shield', 'Armor', 'Evasion', 'Barrier',
            'Speed Boost', 'Magnet', 'Slow Field'
        ]
        for buff_name in expected_buffs:
            assert buff_name in BUFF_REGISTRY, f"Missing buff: {buff_name}"

    def test_create_buff_power_shot(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Power Shot')
        assert buff is not None
        assert buff.get_name() == 'Power Shot'

    def test_create_buff_regeneration(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Regeneration')
        assert buff is not None
        assert buff.get_name() == 'Regeneration'

    def test_create_buff_invalid_raises_error(self):
        from airwar.game.buffs.buff_registry import create_buff
        with pytest.raises(ValueError):
            create_buff('InvalidBuffName')

    def test_all_buffs_have_apply_method(self):
        from airwar.game.buffs.buff_registry import BUFF_REGISTRY
        for name, buff_class in BUFF_REGISTRY.items():
            buff = buff_class()
            assert hasattr(buff, 'apply'), f"Buff {name} missing apply method"

    def test_all_buffs_have_get_name_method(self):
        from airwar.game.buffs.buff_registry import BUFF_REGISTRY
        for name, buff_class in BUFF_REGISTRY.items():
            buff = buff_class()
            assert hasattr(buff, 'get_name'), f"Buff {name} missing get_name method"
            assert buff.get_name() == name

    def test_all_buffs_have_get_color_method(self):
        from airwar.game.buffs.buff_registry import BUFF_REGISTRY
        for name, buff_class in BUFF_REGISTRY.items():
            buff = buff_class()
            assert hasattr(buff, 'get_color'), f"Buff {name} missing get_color method"
            color = buff.get_color()
            assert isinstance(color, tuple)
            assert len(color) == 3


class TestHealthBuffs:
    def test_extra_life_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        player.health = 50
        player.max_health = 100
        
        buff = create_buff('Extra Life')
        result = buff.apply(player)
        
        assert result.name == 'Extra Life'
        assert buff.calculate_value(100, 1) == 150
        assert buff.calculate_increment(100) == 50

    def test_regeneration_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Regeneration')
        assert buff is not None

    def test_lifesteal_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Lifesteal')
        assert buff is not None


class TestOffenseBuffs:
    def test_power_shot_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        base_damage = player.bullet_damage
        
        buff = create_buff('Power Shot')
        result = buff.apply(player)
        
        assert result.name == 'Power Shot'
        assert buff.calculate_value(base_damage, 1) == int(base_damage * 1.25)
        assert buff.calculate_increment(base_damage) == int(base_damage * 0.25)

    def test_rapid_fire_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        initial_cooldown = player.fire_cooldown
        
        buff = create_buff('Rapid Fire')
        result = buff.apply(player)
        
        assert result.name == 'Rapid Fire'

    def test_piercing_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Piercing')
        assert buff is not None

    def test_spread_shot_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        buff = create_buff('Spread Shot')
        result = buff.apply(player)
        
        assert result.name == 'Spread Shot'
        assert buff.calculate_value(0, 1) == 1
        assert buff.calculate_increment(0) == 1

    def test_explosive_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Explosive')
        assert buff is not None

    def test_shotgun_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        buff = create_buff('Shotgun')
        result = buff.apply(player)
        
        assert result.name == 'Shotgun'

    def test_laser_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        buff = create_buff('Laser')
        result = buff.apply(player)
        
        assert result.name == 'Laser'


class TestDefenseBuffs:
    def test_shield_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        buff = create_buff('Shield')
        result = buff.apply(player)
        
        assert result.name == 'Shield'
        player.activate_shield(180)
        assert player.is_shielded is True

    def test_armor_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Armor')
        assert buff is not None

    def test_evasion_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Evasion')
        assert buff is not None

    def test_barrier_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        buff = create_buff('Barrier')
        result = buff.apply(player)
        
        assert result.name == 'Barrier'
        assert buff.calculate_value(0, 1) == 1
        assert buff.calculate_increment(100) == 50


class TestUtilityBuffs:
    def test_speed_boost_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        initial_speed = player.speed
        
        buff = create_buff('Speed Boost')
        result = buff.apply(player)
        
        assert result.name == 'Speed Boost'
        player.speed *= 1.15
        assert player.speed > initial_speed

    def test_magnet_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Magnet')
        assert buff is not None

    def test_slow_field_buff(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Slow Field')
        assert buff is not None


class TestRewardSystemUpgrade:
    def test_reward_system_upgrade_power_shot(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        initial_damage = scene.player.bullet_damage
        reward = {'name': 'Power Shot', 'desc': '+25% bullet damage', 'icon': 'DMG'}
        scene._on_reward_selected(reward)
        first_damage = scene.player.bullet_damage
        
        reward2 = {'name': 'Power Shot', 'desc': '+25% bullet damage', 'icon': 'DMG'}
        scene._on_reward_selected(reward2)
        second_damage = scene.player.bullet_damage
        
        assert first_damage > initial_damage
        assert second_damage > first_damage

    def test_reward_system_upgrade_piercing(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        reward = {'name': 'Piercing', 'desc': 'Bullets pierce 1 enemy', 'icon': 'PIR'}
        scene._on_reward_selected(reward)
        first_level = scene.reward_system.piercing_level
        
        reward2 = {'name': 'Piercing', 'desc': 'Bullets pierce 1 enemy', 'icon': 'PIR'}
        scene._on_reward_selected(reward2)
        second_level = scene.reward_system.piercing_level
        
        assert first_level == 1
        assert second_level == 2

    def test_reward_system_upgrade_spread_shot(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        reward = {'name': 'Spread Shot', 'desc': 'Fire 3 bullets at once', 'icon': 'SPD'}
        scene._on_reward_selected(reward)
        first_level = scene.reward_system.spread_level
        
        reward2 = {'name': 'Spread Shot', 'desc': 'Fire 3 bullets at once', 'icon': 'SPD'}
        scene._on_reward_selected(reward2)
        second_level = scene.reward_system.spread_level
        
        assert first_level == 1
        assert second_level == 2

    def test_reward_system_upgrade_explosive(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        reward = {'name': 'Explosive', 'desc': 'Bullets deal 30 AoE damage', 'icon': 'EXP'}
        scene._on_reward_selected(reward)
        first_level = scene.reward_system.explosive_level
        
        reward2 = {'name': 'Explosive', 'desc': 'Bullets deal 30 AoE damage', 'icon': 'EXP'}
        scene._on_reward_selected(reward2)
        second_level = scene.reward_system.explosive_level
        
        assert first_level == 1
        assert second_level == 2


class TestRewardSystemLifesteal:
    def test_lifesteal_on_kill(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        scene.player.health = 50
        scene.player.max_health = 100
        
        reward = {'name': 'Lifesteal', 'desc': '+10% lifesteal on kill', 'icon': 'LST'}
        scene._on_reward_selected(reward)
        
        assert 'Lifesteal' in scene.reward_system.unlocked_buffs
        
        initial_health = scene.player.health
        scene.reward_system.apply_lifesteal(scene.player, 100)
        
        assert scene.player.health > initial_health
        assert scene.player.health <= scene.player.max_health

    def test_lifesteal_capped_at_max_health(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        scene.player.health = 100
        scene.player.max_health = 100
        
        reward = {'name': 'Lifesteal', 'desc': '+10% lifesteal on kill', 'icon': 'LST'}
        scene._on_reward_selected(reward)
        
        scene.reward_system.apply_lifesteal(scene.player, 1000)
        
        assert scene.player.health == 100


class TestRewardSystemExplosive:
    def test_explosive_damage_in_range(self):
        from airwar.scenes.game_scene import GameScene
        from airwar.entities import Enemy, EnemyData
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        reward = {'name': 'Explosive', 'desc': 'Bullets deal 30 AoE damage', 'icon': 'EXP'}
        scene._on_reward_selected(reward)
        
        enemy1 = Enemy(400, 400, EnemyData(health=100))
        enemy2 = Enemy(405, 405, EnemyData(health=100))
        
        initial_health1 = enemy1.health
        initial_health2 = enemy2.health
        
        scene.reward_system.do_explosive_damage(
            [enemy1, enemy2], 400, 400, 50
        )
        
        assert enemy1.health < initial_health1
        assert enemy2.health < initial_health2

    def test_explosive_damage_out_of_range(self):
        from airwar.scenes.game_scene import GameScene
        from airwar.entities import Enemy, EnemyData
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        reward = {'name': 'Explosive', 'desc': 'Bullets deal 30 AoE damage', 'icon': 'EXP'}
        scene._on_reward_selected(reward)
        
        enemy = Enemy(500, 500, EnemyData(health=100))
        initial_health = enemy.health
        
        scene.reward_system.do_explosive_damage(
            [enemy], 400, 400, 50
        )
        
        assert enemy.health == initial_health

    def test_no_explosive_damage_without_buff(self):
        from airwar.scenes.game_scene import GameScene
        from airwar.entities import Enemy, EnemyData
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        enemy = Enemy(405, 405, EnemyData(health=100))
        initial_health = enemy.health
        
        scene.reward_system.do_explosive_damage(
            [enemy], 400, 400, 50
        )
        
        assert enemy.health == initial_health


class TestRefactoredBuffSystem:
    def test_power_shot_calculate_value(self):
        from airwar.game.buffs.buff_registry import create_buff
        
        buff = create_buff('Power Shot')
        base = 50
        
        assert buff.calculate_value(base, 0) == 50
        assert buff.calculate_value(base, 1) == int(50 * 1.25)
        assert buff.calculate_value(base, 2) == int(50 * 1.25 * 1.25)
        assert buff.calculate_value(base, 3) == int(50 * 1.25 * 1.25 * 1.25)

    def test_rapid_fire_calculate_value(self):
        from airwar.game.buffs.buff_registry import create_buff
        
        buff = create_buff('Rapid Fire')
        base = 10
        
        assert buff.calculate_value(base, 0) == 10
        assert buff.calculate_value(base, 1) == max(1, int(10 * 0.8))
        assert buff.calculate_value(base, 2) == max(1, int(10 * 0.8 * 0.8))

    def test_reward_system_power_shot_upgrade(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        initial_damage = scene.reward_system._base_bullet_damage
        
        scene._on_reward_selected({'name': 'Power Shot', 'desc': '+25% bullet damage', 'icon': 'DMG'})
        assert scene.player.bullet_damage == int(initial_damage * 1.25)
        assert scene.reward_system.buff_levels['Power Shot'] == 1
        
        scene._on_reward_selected({'name': 'Power Shot', 'desc': '+25% bullet damage', 'icon': 'DMG'})
        assert scene.player.bullet_damage == int(initial_damage * 1.25 * 1.25)
        assert scene.reward_system.buff_levels['Power Shot'] == 2

    def test_reward_system_rapid_fire_upgrade(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        base_cooldown = scene.reward_system._base_fire_cooldown
        
        scene._on_reward_selected({'name': 'Rapid Fire', 'desc': '+20% fire rate', 'icon': 'RPD'})
        assert scene.player.fire_cooldown == max(1, int(base_cooldown * 0.8))
        assert scene.reward_system.buff_levels['Rapid Fire'] == 1
        
        scene._on_reward_selected({'name': 'Rapid Fire', 'desc': '+20% fire rate', 'icon': 'RPD'})
        assert scene.player.fire_cooldown == max(1, int(base_cooldown * 0.8 * 0.8))
        assert scene.reward_system.buff_levels['Rapid Fire'] == 2

    def test_buff_get_notification(self):
        from airwar.game.buffs.buff_registry import create_buff
        
        buff = create_buff('Power Shot')
        assert buff.get_notification(1) == 'REWARD: Power Shot'
        assert buff.get_notification(2) == 'UPGRADED: Power Shot (Lv.2)'
        assert buff.get_notification(3) == 'UPGRADED: Power Shot (Lv.3)'
