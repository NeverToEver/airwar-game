"""Player entity module.

Slim coordinator that assembles 7 extracted components
(see :mod:`airwar.entities.player_components`) and forwards every
public method to the right one.

The original 755-line Player was split in Phase 4 W-delta (logic-clarity
refactor) into:

* :class:`~airwar.entities.player_components.PlayerMovement`
* :class:`~airwar.entities.player_components.PlayerWeapon`
* :class:`~airwar.entities.player_components.PlayerBoost`
* :class:`~airwar.entities.player_components.PlayerShield`
* :class:`~airwar.entities.player_components.PlayerPhaseDash`
* :class:`~airwar.entities.player_components.PlayerAim`
* :class:`~airwar.entities.player_components.PlayerHitbox`

The Player remains the runtime-facing entity API while each component owns
its own focused state.
"""

# === Third-party ===
import pygame

# === Local: different package in airwar ===
from airwar.config.constants_access import get_game_constants
from airwar.protocols import InputSourceProtocol

# === Local: same package ===
from .base import Entity
from .bullet import Bullet
from .player_components import (
    PlayerAim,
    PlayerBoost,
    PlayerHitbox,
    PlayerMovement,
    PlayerPhaseDash,
    PlayerShield,
    PlayerWeapon,
)
from .player_state import IllegalPlayerTransition, PlayerStateMachine

__all__ = ["Player"]


class Player(Entity):
    """Player entity representing the user's spaceship.

    Thin coordinator that owns seven component instances and forwards
    public API calls to them. See the module docstring for the full
    backward-compat surface.

    Attributes:
        health: Current health points (0 to max_health).
        max_health: Maximum health points.
        speed: Movement speed in pixels per frame.
        bullet_damage: Damage dealt by each bullet.
        is_shielded: Whether the player currently has shield active.
    """

    # --- Class constants shared with gameplay systems ---
    PLAYER_SPRITE_W = 68
    PLAYER_SPRITE_H = 82
    DEFAULT_RECOVERY_RATE = PlayerBoost.DEFAULT_RECOVERY_RATE
    DEFAULT_SPEED_MULT = PlayerBoost.DEFAULT_SPEED_MULT
    DEFAULT_BOOST_MAX = PlayerBoost.DEFAULT_BOOST_MAX
    DEFAULT_BOOST_RECOVERY_DELAY = PlayerBoost.DEFAULT_RECOVERY_DELAY
    DEFAULT_BOOST_RECOVERY_RAMP = PlayerBoost.DEFAULT_RECOVERY_RAMP
    PLAYER_HITBOX_W = PlayerHitbox.DEFAULT_WIDTH
    PLAYER_HITBOX_H = PlayerHitbox.DEFAULT_HEIGHT
    BOOST_RAMP_MIN = PlayerBoost.BOOST_RAMP_MIN
    BOOST_RAMP_DELTA = PlayerBoost.BOOST_RAMP_DELTA
    PRECISION_SPEED_MULT = 0.35
    BULLET_SPAWN_Y_OFFSET = 36
    SPREAD_ANGLES = PlayerWeapon.SPREAD_ANGLES
    WING_MUZZLE_X_OFFSETS = PlayerWeapon.WING_MUZZLE_X_OFFSETS
    WING_MUZZLE_Y_OFFSET = PlayerWeapon.WING_MUZZLE_Y_OFFSET
    AIM_TURN_RATE_DEGREES = PlayerAim.AIM_TURN_RATE_DEGREES
    PHASE_DASH_COST_RATIO = PlayerPhaseDash.COST_RATIO
    PHASE_DASH_WINDUP_FRAMES = PlayerPhaseDash.WINDUP_FRAMES
    PHASE_DASH_ACTIVE_FRAMES = PlayerPhaseDash.ACTIVE_FRAMES
    PHASE_DASH_RECOVERY_FRAMES = PlayerPhaseDash.RECOVERY_FRAMES
    PHASE_DASH_COOLDOWN_FRAMES = PlayerPhaseDash.COOLDOWN_FRAMES
    PHASE_DASH_DISTANCE = PlayerPhaseDash.DISTANCE
    PHASE_DASH_MIN_DISTANCE = PlayerPhaseDash.MIN_DISTANCE
    PHASE_DASH_ALPHA_MIN = PlayerPhaseDash.ALPHA_MIN
    PHASE_DASH_ALPHA_MAX = PlayerPhaseDash.ALPHA_MAX
    ROTATED_SPRITE_ANGLE_STEP = PlayerAim.ROTATED_SPRITE_ANGLE_STEP
    ROTATED_SPRITE_CACHE_MAX = PlayerAim.ROTATED_SPRITE_CACHE_MAX

    # 1. Special methods

    def __init__(
        self,
        x: float,
        y: float,
        input_handler: InputSourceProtocol,
    ):
        constants = get_game_constants()
        super().__init__(x, y, self.PLAYER_SPRITE_W, self.PLAYER_SPRITE_H)
        self._constants = constants  # Cache for hot path access
        self._input_handler = input_handler

        # --- Component assembly (constants and input handler are already set above) ---
        self.movement: PlayerMovement = PlayerMovement(self, input_handler)
        self.boost: PlayerBoost = PlayerBoost(self)
        self.weapon: PlayerWeapon = PlayerWeapon(self)
        self.shield: PlayerShield = PlayerShield(self)
        self.phase_dash: PlayerPhaseDash = PlayerPhaseDash(self)
        self.aim: PlayerAim = PlayerAim(self)
        self.hitbox: PlayerHitbox = PlayerHitbox(self)

        # --- Health / speed (kept on Player for backward compat) ---
        self.health: int = constants.PLAYER.MAX_HEALTH
        self.max_health: int = constants.PLAYER.MAX_HEALTH
        self.base_speed: float = constants.PLAYER.SPEED
        self.speed: float = self.base_speed
        self.bullet_damage: int = constants.PLAYER.BULLET_DAMAGE

        # --- Orthogonal flags ---
        self.is_phase_dash_enabled: bool = False
        self.is_controls_locked: bool = False
        self.mothership_cooldown_mult: float = 1.0

        # --- Master pulse timer (read by aim / hitbox / phase-dash alpha) ---
        self._hitbox_timer: int = 0

        # --- Invincibility-blink state (mirrored from GameState by sync_invincibility_blink) ---
        self._blink_active: bool = False
        self._blink_timer: int = 0

        # --- HSM ---
        self._state = PlayerStateMachine(self)

    # 2. Properties (legacy attr accessors; many callers read these directly)
    #
    # Each forwarder property is a 1-line read/write to a component.
    # We declare them as class-level ``_Comp`` descriptors to keep
    # the boilerplate compact: 2-3 lines per attribute instead of 5.

    class _Comp:
        """Descriptor that forwards a public attribute to a component attr.

        Usage::

            fire_cooldown = _Comp("weapon", "_fire_cooldown")
            fire_interval = _Comp("weapon", "_fire_interval", set_transform=max(1, int(v)))
        """

        __slots__ = ("attr", "component", "set_transform")

        def __init__(self, component: str, attr: str, set_transform=None) -> None:
            self.component = component
            self.attr = attr
            self.set_transform = set_transform  # optional callable for setters

        def __get__(self, instance, owner=None):
            if instance is None:
                return self
            return getattr(getattr(instance, self.component), self.attr)

        def __set__(self, instance, value) -> None:
            target = getattr(instance, self.component)
            if self.set_transform is not None:
                value = self.set_transform(value)
            setattr(target, self.attr, value)

    fire_cooldown = _Comp("weapon", "_fire_cooldown")
    fire_interval = _Comp("weapon", "_fire_interval", set_transform=lambda v: max(1, int(v or 0)))
    precision_active = _Comp("movement", "precision_active")
    boost_max = _Comp("boost", "boost_max")
    boost_current = _Comp("boost", "boost_current")
    boost_recovery_rate = _Comp("boost", "boost_recovery_rate")
    boost_recovery_delay = _Comp("boost", "boost_recovery_delay")
    boost_recovery_ramp = _Comp("boost", "boost_recovery_ramp")
    is_boost_active = _Comp("boost", "is_boost_active")
    is_shielded = _Comp("shield", "is_shielded")
    hitbox_width = _Comp("hitbox", "hitbox_width")
    hitbox_height = _Comp("hitbox", "hitbox_height")

    @property
    def bullet_damage_value(self) -> int:
        return self.bullet_damage

    @bullet_damage_value.setter
    def bullet_damage_value(self, value: int) -> None:
        self.bullet_damage = value

    @property
    def boost_speed_mult(self) -> float:
        # Stored on the boost component to support per-difficulty tuning.
        return getattr(self.boost, "_boost_speed_mult", self.DEFAULT_SPEED_MULT)

    @boost_speed_mult.setter
    def boost_speed_mult(self, value: float) -> None:
        # Real speed multiplier is applied in movement.update via
        # ``base_speed * boost_speed_mult``; we cache it on the boost
        # component for any future per-difficulty tuning.
        self.boost._boost_speed_mult = value  # type: ignore[attr-defined]

    def apply_settings(self, settings: dict) -> None:
        self.movement.apply_settings(settings)

    # 3. Public lifecycle methods

    def update(self, *args, **kwargs) -> None:
        """Update player state each frame.

        Per-frame dispatch order (chosen to preserve the original
        game's per-frame invariants):

        1. tick input handler edge detection
        2. shield timer (decrements ``_shield_duration``)
        3. phase dash cooldown (decrements dash cooldown)
        4. if is_controls_locked: increment pulse timer, return
        5. if phase dashing: tick dash motion + recovery, weapon, aim, pulse
        6. read boost key state + edge detection
        7. phase dash attempt (preempts boost)
        8. boost mode (hold vs toggle) -> sets ``is_boost_active``
        9. precision mode (hold vs toggle) -> sets ``is_boost_active=False``
        10. movement: position update with current speed
        11. weapon cooldown / aim turn / pulse
        """
        if not self.active or not self._state.is_alive():
            return
        if hasattr(self._input_handler, "tick"):
            self._input_handler.tick()
        self.shield.update()

        if self.is_controls_locked:
            self._hitbox_timer += 1
            self.phase_dash.hitbox_timer = self._hitbox_timer
            return

        if self.phase_dash.is_dashing():
            self.phase_dash.update_motion()
            self.boost.update_recovery(active_blocked=True)
            self.weapon.update()
            self.aim.update()
            self._hitbox_timer += 1
            self.phase_dash.hitbox_timer = self._hitbox_timer
            return

        self.phase_dash.tick_cooldown()

        boost_pressed = self._input_handler.is_boost_pressed()
        boost_just_pressed = self._read_boost_just_pressed(boost_pressed)

        # Phase dash has priority over boost (even in toggle mode).
        if boost_just_pressed and self.phase_dash.can_dash():
            self.phase_dash.start(self._input_handler.get_movement_direction())
            self.phase_dash.update_motion()
            self.boost.update_recovery(active_blocked=True)
            self.weapon.update()
            self.aim.update()
            self._hitbox_timer += 1
            self.phase_dash.hitbox_timer = self._hitbox_timer
            return

        # Boost mode (hold vs toggle)
        if self.movement.shift_boost_mode == "toggle":
            if boost_just_pressed:
                self.boost._boost_toggle_active = not self.boost._boost_toggle_active
            self.boost.is_boost_active = self.boost._boost_toggle_active and self.boost.boost_current > 0
        else:
            self.boost.is_boost_active = boost_pressed and self.boost.boost_current > 0

        # Sync alive substate with boost active state.
        if self.boost.is_boost_active and not self._state.is_boosting():
            if hasattr(self._state, "enter_boost"):
                try:
                    self._state.enter_boost()
                except IllegalPlayerTransition:
                    pass
        elif not self.boost.is_boost_active and self._state.is_boosting():
            if hasattr(self._state, "exit_boost"):
                self._state.exit_boost()

        # Precision mode (hold vs toggle)
        precision = self.movement.update_precision_state()

        if precision:
            self.speed = self.base_speed * self.PRECISION_SPEED_MULT
            self.boost.is_boost_active = False
            self.boost.update_recovery()
        elif self.boost.is_boost_active:
            self.boost.reset_idle()
            self.boost.consume_one_frame()
            self.speed = self.base_speed * self.boost_speed_mult
        else:
            self.boost.update_recovery()
            self.speed = self.base_speed

        self.movement.update()
        self.weapon.update()
        self.aim.update()
        self._hitbox_timer += 1
        self.phase_dash.hitbox_timer = self._hitbox_timer

    def render(self, surface: pygame.Surface) -> None:
        """Render the player ship and hitbox indicator.

        Args:
            surface: Pygame surface to render onto.
        """
        sprite = self.aim.rotated_ship_sprite()
        if sprite is None:
            return
        # Juice: alpha-blink during post-hit invincibility. 6-frame on / 6-frame
        # off pattern at 60fps = ~5Hz strobe, fast enough to read as "i-frames
        # active" but slow enough to not look glitchy. Phase-dash still wins
        # priority (overrides the strobe).
        #
        # ``self._blink_*`` fields are mirrored from GameState.is_player_invincible
        # by ``sync_invincibility_blink`` (called once per frame from
        # GameController.set_invincible / _update_invincibility). The player
        # entity stays independent of the controller; entities never import
        # from the game layer.
        if self.phase_dash.is_dashing():
            sprite = sprite.copy()
            sprite.set_alpha(self.phase_dash.alpha())
        elif self._blink_active and self._blink_timer > 0:
            sprite = sprite.copy()
            # 12-frame period: bright for first 6, dim for next 6.
            sprite.set_alpha(120 if (self._blink_timer // 6) % 2 == 0 else 40)
        surface.blit(sprite, sprite.get_rect(center=(self.rect.centerx, self.rect.centery)))

        if self.precision_active:
            self.hitbox.render_precision_indicator(surface, self._hitbox_timer)

        self.hitbox.render_indicator(surface, self._hitbox_timer)

    # 4. Public behavior methods (1-line forwarders)

    def fire(self) -> Bullet | None:
        return self.weapon.fire()

    def sync_invincibility_blink(self, active: bool, timer: int) -> None:
        """Mirror GameState.is_player_invincible for the render-time alpha blink.

        Called once per frame from :class:`GameController._update_invincibility`.
        Keeping this on the entity side avoids a controller-to-entity
        back-reference.
        """
        self._blink_active = bool(active)
        self._blink_timer = int(timer)

    def auto_fire(self) -> None:
        if self.is_controls_locked:
            return
        self.weapon.auto_fire()

    def activate_shotgun(self) -> None:
        self.weapon.activate_shotgun()

    def activate_laser(self, duration: int) -> None:
        self.weapon.activate_laser(duration)

    def activate_explosive(self) -> None:
        self.weapon.activate_explosive()

    def set_weapon_modifiers(self, spread: bool, laser: bool, explosive: bool) -> None:
        self.weapon.set_weapon_modifiers(spread, laser, explosive)

    def get_weapon_status(self) -> dict:
        return self.weapon.get_weapon_status()

    def activate_phase_dash(self) -> None:
        self.is_phase_dash_enabled = True

    def take_damage(self, damage: int) -> None:
        if damage is None or damage < 0:
            return
        if self.shield.is_shielded:
            return
        self.health -= damage
        if self.health <= 0:
            self.health = 0

    def heal(self, amount: int) -> None:
        if amount is None or amount < 0:
            return
        self.health = min(self.max_health, self.health + amount)

    def activate_shield(self, duration: int) -> None:
        self.shield.activate(duration)

    def get_hitbox(self) -> pygame.Rect:
        return self.hitbox.get_hitbox()

    def get_boost_status(self) -> dict:
        return {
            "current": self.boost.boost_current,
            "max": self.boost.boost_max,
            "active": self.boost.is_boost_active,
            "dash_cooldown": self.phase_dash.cooldown,
            "dash_cooldown_max": self.PHASE_DASH_COOLDOWN_FRAMES,
            "dash_enabled": self.is_phase_dash_enabled,
            "dash_active": self.phase_dash.is_dashing(),
            "dash_ready": self.phase_dash.can_dash(),
        }

    def get_bullets(self) -> list[Bullet]:
        return self.weapon.get_bullets()

    def remove_bullet(self, bullet: Bullet) -> None:
        self.weapon.remove_bullet(bullet)

    def cleanup_inactive_bullets(self) -> None:
        self.weapon.cleanup_inactive_bullets()

    def is_colliding_with(self, other) -> bool:
        return self.hitbox.is_colliding_with(other)

    def is_phase_dashing(self) -> bool:
        return self.phase_dash.is_dashing()

    # --- HSM predicates (Phase 3) ---

    def is_alive(self) -> bool:
        return self._state.is_alive()

    def is_dying(self) -> bool:
        return self._state.is_dying()

    def is_dead(self) -> bool:
        return self._state.is_dead()

    def alive_substate(self):
        return self._state.alive_substate

    def is_alive_substate(self, sub) -> bool:
        return self._state.alive_substate == sub

    def is_phase_dash_invincible(self) -> bool:
        return self.phase_dash.is_invincible()

    def can_phase_dash(self) -> bool:
        return self.phase_dash.can_dash()

    def add_listener(self, listener) -> None:
        self.weapon.add_listener(listener)

    def remove_listener(self, listener) -> None:
        self.weapon.remove_listener(listener)

    def set_aim_target(self, x: float, y: float) -> None:
        self.aim.set_aim_target(x, y)

    def get_aim_target(self) -> tuple[float, float] | None:
        return self.aim.get_aim_target()

    def get_facing_direction(self):
        return self.aim.get_facing_direction()

    def get_facing_angle_degrees(self) -> float:
        return self.aim.get_facing_angle_degrees()

    def set_render_hitbox(self, value: bool) -> None:
        self.hitbox.set_render_hitbox(value)

    # 5. Private helpers

    def _read_boost_just_pressed(self, boost_pressed: bool) -> bool:
        if hasattr(self._input_handler, "is_boost_just_pressed"):
            return self._input_handler.is_boost_just_pressed()
        just_pressed = boost_pressed and not self.movement._boost_pressed_last_frame
        self.movement._boost_pressed_last_frame = boost_pressed
        return just_pressed
