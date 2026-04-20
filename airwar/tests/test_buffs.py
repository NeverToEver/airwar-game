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

    def test_create_buff_invalid_raises_error(self):
        from airwar.game.buffs.buff_registry import create_buff
        with pytest.raises(ValueError):
            create_buff('InvalidBuffName')

    @pytest.mark.parametrize('buff_name', [
        'Extra Life', 'Regeneration', 'Lifesteal',
        'Power Shot', 'Rapid Fire', 'Piercing', 'Spread Shot', 'Explosive', 'Shotgun', 'Laser',
        'Shield', 'Armor', 'Evasion', 'Barrier',
        'Speed Boost', 'Magnet', 'Slow Field'
    ])
    def test_all_buffs_can_be_created(self, buff_name):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff(buff_name)
        assert buff is not None
        assert buff.get_name() == buff_name

    @pytest.mark.parametrize('buff_name', [
        'Extra Life', 'Regeneration', 'Lifesteal',
        'Power Shot', 'Rapid Fire', 'Piercing', 'Spread Shot', 'Explosive', 'Shotgun', 'Laser',
        'Shield', 'Armor', 'Evasion', 'Barrier',
        'Speed Boost', 'Magnet', 'Slow Field'
    ])
    def test_all_buffs_have_required_methods(self, buff_name):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff(buff_name)
        assert hasattr(buff, 'apply')
        assert hasattr(buff, 'get_name')
        assert hasattr(buff, 'get_color')
        assert hasattr(buff, 'get_notification')
        color = buff.get_color()
        assert isinstance(color, tuple)
        assert len(color) == 3


class TestBuffCalculations:
    def test_power_shot_calculate_value(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Power Shot')
        base = 50
        assert buff.calculate_value(base, 0) == 50
        assert buff.calculate_value(base, 1) == int(50 * 1.25)
        assert buff.calculate_value(base, 2) == int(50 * 1.25 * 1.25)

    def test_rapid_fire_calculate_value(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Rapid Fire')
        base = 10
        assert buff.calculate_value(base, 0) == 10
        assert buff.calculate_value(base, 1) == max(1, int(10 * 0.8))
        assert buff.calculate_value(base, 2) == max(1, int(10 * 0.8 * 0.8))

    def test_extra_life_calculate_value(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Extra Life')
        assert buff.calculate_value(100, 1) == 150
        assert buff.calculate_increment(100) == 50

    def test_spread_shot_calculate_value(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Spread Shot')
        assert buff.calculate_value(0, 1) == 1
        assert buff.calculate_increment(0) == 1

    def test_barrier_calculate_value(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Barrier')
        assert buff.calculate_value(0, 1) == 1
        assert buff.calculate_increment(100) == 50

    def test_buff_get_notification(self):
        from airwar.game.buffs.buff_registry import create_buff
        buff = create_buff('Power Shot')
        assert buff.get_notification(1) == 'REWARD: Power Shot'
        assert buff.get_notification(2) == 'UPGRADED: Power Shot (Lv.2)'
        assert buff.get_notification(3) == 'UPGRADED: Power Shot (Lv.3)'


class TestBuffApplication:
    def test_extra_life_buff_apply(self):
        from airwar.game.buffs.buff_registry import create_buff
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        player = Player(100, 200, MockInputHandler())
        player.health = 50
        player.max_health = 100
        buff = create_buff('Extra Life')
        result = buff.apply(player)
        assert result.name == 'Extra Life'

    def test_power_shot_buff_apply(self):
        from airwar.game.buffs.buff_registry import create_buff
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        player = Player(100, 200, MockInputHandler())
        buff = create_buff('Power Shot')
        result = buff.apply(player)
        assert result.name == 'Power Shot'

    def test_shield_buff_apply(self):
        from airwar.game.buffs.buff_registry import create_buff
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        player = Player(100, 200, MockInputHandler())
        buff = create_buff('Shield')
        result = buff.apply(player)
        assert result.name == 'Shield'
        player.activate_shield(180)
        assert player.is_shielded is True


class TestRewardSystemUpgrades:
    @pytest.mark.parametrize('reward_name,level_attr', [
        ('Piercing', 'piercing_level'),
        ('Spread Shot', 'spread_level'),
        ('Explosive', 'explosive_level'),
        ('Armor', 'armor_level'),
        ('Evasion', 'evasion_level'),
    ])
    def test_reward_system_upgrades(self, reward_name, level_attr):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        initial_level = getattr(scene.reward_system, level_attr, 0)
        
        reward = {'name': reward_name, 'desc': 'Test reward', 'icon': 'TST'}
        scene._on_reward_selected(reward)
        first_level = getattr(scene.reward_system, level_attr, 0)
        
        reward2 = {'name': reward_name, 'desc': 'Test reward', 'icon': 'TST'}
        scene._on_reward_selected(reward2)
        second_level = getattr(scene.reward_system, level_attr, 0)
        
        assert first_level > initial_level
        assert second_level > first_level

    def test_power_shot_upgrade_increases_damage(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        initial_damage = scene.reward_system._base_bullet_damage
        scene._on_reward_selected({'name': 'Power Shot', 'desc': '+25% bullet damage', 'icon': 'DMG'})
        assert scene.player.bullet_damage == int(initial_damage * 1.25)
        
        scene._on_reward_selected({'name': 'Power Shot', 'desc': '+25% bullet damage', 'icon': 'DMG'})
        assert scene.player.bullet_damage == int(initial_damage * 1.25 * 1.25)


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
        
        scene.reward_system.do_explosive_damage([enemy1, enemy2], 400, 400, 50)
        
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
        
        scene.reward_system.do_explosive_damage([enemy], 400, 400, 50)
        
        assert enemy.health == initial_health

    def test_no_explosive_damage_without_buff(self):
        from airwar.scenes.game_scene import GameScene
        from airwar.entities import Enemy, EnemyData
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        enemy = Enemy(405, 405, EnemyData(health=100))
        initial_health = enemy.health
        
        scene.reward_system.do_explosive_damage([enemy], 400, 400, 50)
        
        assert enemy.health == initial_health
