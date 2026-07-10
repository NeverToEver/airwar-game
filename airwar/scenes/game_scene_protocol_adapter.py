"""IGameScene protocol adapter - Phase42.2 god-class split.

Phase42.2 split:53 IGameScene forwarders moved from GameScene to
this adapter. Each method delegates to a component on the held
scene reference. GameScene keeps1-line forwarders to the adapter
so isinstance(scene, IGameScene) checks still pass.

Backward-compat: All public methods preserve signatures; methods
tolerate None target components (matching legacy behavior).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .game_scene_protocols import GameSceneProtocol


class IGameSceneAdapter:
    """Adapter implementing all53 IGameScene methods."""

    def __init__(self, scene: GameSceneProtocol) -> None:
        self._scene = scene

    # IScoreProvider (8 methods)

    def add_score(self, amount: int) -> None:
        s = self._scene
        if s.game_controller:
            s.game_controller.add_score(amount)

    def add_kill(self) -> None:
        s = self._scene
        if s.game_controller:
            s.game_controller.add_kill_count()

    def add_boss_kill(self) -> None:
        s = self._scene
        if s.game_controller:
            s.game_controller.add_boss_kill_count()

    def show_notification(self, message: str) -> None:
        s = self._scene
        if s.notification_manager:
            s.notification_manager.show(message)

    def get_score(self) -> int:
        return self._scene.score

    def get_cycle_count(self) -> int:
        return self._scene.cycle_count

    def get_kill_count(self) -> int:
        s = self._scene
        return s.game_controller.state.kill_count if s.game_controller else 0

    def get_boss_kill_count(self) -> int:
        s = self._scene
        return s.game_controller.state.boss_kill_count if s.game_controller else 0

    # IEntityProvider (5 methods)

    def get_enemies(self) -> list:
        s = self._scene
        if s.spawn_controller:
            return list(s.spawn_controller.enemies)
        return []

    def get_boss(self):
        s = self._scene
        return s.spawn_controller.boss if s.spawn_controller else None

    def clear_boss(self) -> None:
        s = self._scene
        if s.spawn_controller:
            s.spawn_controller.clear_boss()

    def trigger_explosion(self, x: float, y: float, radius: int) -> None:
        s = self._scene
        if s._game_loop_manager:
            s._game_loop_manager._on_explosion(x, y, radius)

    def trigger_boss_death_explosion(self, boss) -> None:
        s = self._scene
        if s._game_loop_manager and boss:
            s._game_loop_manager.trigger_boss_death_explosion(
                boss.rect.centerx,
                boss.rect.centery,
                boss.rect.width,
                boss.rect.height,
            )

    # IPlayerControl (5 methods)

    def set_player_position(self, x: float, y: float) -> None:
        s = self._scene
        if s.player:
            s.player.rect.x = x - s.player.rect.width // 2
            s.player.rect.y = y - s.player.rect.height // 2

    def set_player_position_topleft(self, x: float, y: float) -> None:
        s = self._scene
        if s.player:
            s.player.rect.x = x
            s.player.rect.y = y

    def set_player_invincible(self, invincible: bool, timer: int, silent: bool = False) -> None:
        """Set player invincibility state."""
        from airwar.game.systems.lock_manager import LockLayer, LockRequest

        s = self._scene
        if not s.game_controller:
            return
        if s._lock_manager:
            s._sync_lock_manager_targets()
            if invincible:
                s._lock_manager.acquire(
                    LockLayer.MOTHERSHIP,
                    LockRequest(
                        invincible=True,
                        is_silent_invincible=silent,
                        invincibility_duration=timer,
                    ),
                )
            else:
                s._lock_manager.release(LockLayer.MOTHERSHIP)
            return
        s.game_controller.set_invincible(invincible, timer, silent)

    def acquire_lock(self, layer, request) -> None:
        s = self._scene
        s._sync_lock_manager_targets()
        s._lock_manager.acquire(layer, request)

    def release_lock(self, layer) -> None:
        s = self._scene
        s._sync_lock_manager_targets()
        s._lock_manager.release(layer)

    # IGameScene composite (10 methods)

    def get_unlocked_buffs(self) -> list:
        return self._scene.unlocked_buffs

    def get_buff_levels(self) -> dict[str, int]:
        s = self._scene
        if not s.reward_system:
            return {}
        return dict(s.reward_system.buff_levels)

    def get_earned_buff_levels(self) -> dict[str, int]:
        s = self._scene
        if not s.reward_system:
            return {}
        return s.reward_system.get_earned_buff_levels()

    def get_talent_loadout(self) -> dict[str, str]:
        s = self._scene
        if not s.reward_system:
            return {}
        return dict(s.reward_system.talent_loadout)

    def get_player_health(self) -> int:
        s = self._scene
        return s.player.health if s.player else 0

    def get_player_max_health(self) -> int:
        s = self._scene
        return s.player.max_health if s.player else 0

    def get_difficulty(self) -> str:
        return self._scene.difficulty

    def get_username(self) -> str:
        s = self._scene
        return s.game_controller.state.username if s.game_controller else "Player"

    def set_paused(self, paused: bool) -> None:
        s = self._scene
        if s.game_controller:
            s.game_controller.set_paused(paused)

    def clear_ripple_effects(self) -> None:
        s = self._scene
        if s.game_controller:
            s.game_controller.clear_ripples()


__all__ = ["IGameSceneAdapter"]
