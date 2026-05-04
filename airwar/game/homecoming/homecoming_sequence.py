"""Homecoming sequence -- animated return-to-base state machine."""

from collections.abc import Callable
from enum import Enum


class HomecomingPhase(Enum):
    """Visual phases in the return-to-base sequence."""

    INACTIVE = "inactive"
    FTL_ESCAPE = "ftl_escape"
    BLACKOUT = "blackout"
    STATION_REVEAL = "station_reveal"
    APPROACH = "approach"
    LANDING = "landing"
    HANDOFF = "handoff"
    BASE_LAUNCH = "base_launch"
    RETURN_BLACKOUT = "return_blackout"
    ORBITAL_STRIKE = "orbital_strike"
    COMPLETE = "complete"


class HomecomingSequence:
    """Runs the staged return-home animation and exposes safe scene hooks."""

    FTL_FRAMES = 54
    BLACKOUT_FRAMES = 34
    STATION_REVEAL_FRAMES = 70
    APPROACH_FRAMES = 96
    LANDING_FRAMES = 72
    HANDOFF_FRAMES = 64
    BASE_LAUNCH_FRAMES = 76
    RETURN_BLACKOUT_FRAMES = 34
    ORBITAL_STRIKE_FRAMES = 86
    ORBITAL_STRIKE_IMPACT_PROGRESS = 0.56

    def __init__(self, on_complete_callback: Callable[[], None] | None = None):
        self._on_complete_callback = on_complete_callback
        self._on_departure_complete_callback: Callable[[], None] | None = None
        self._on_orbital_strike_callback: Callable[[], None] | None = None
        self._phase = HomecomingPhase.INACTIVE
        self._frame = 0
        self._screen_size = (0, 0)
        self._start_center = (0.0, 0.0)
        self._current_center = (0.0, 0.0)
        self._landing_center = (0.0, 0.0)
        self._base_entry_center = (0.0, 0.0)
        self._completed_callback_sent = False
        self._orbital_strike_callback_sent = False

    @property
    def phase(self) -> HomecomingPhase:
        return self._phase

    def is_active(self) -> bool:
        return self._phase not in (HomecomingPhase.INACTIVE, HomecomingPhase.COMPLETE)

    def is_complete(self) -> bool:
        return self._phase == HomecomingPhase.COMPLETE

    def start(self, player, screen_width: int, screen_height: int) -> bool:
        if self.is_active():
            return False

        self._screen_size = (screen_width, screen_height)
        self._start_center = (float(player.rect.centerx), float(player.rect.centery))
        self._current_center = self._start_center
        self._landing_center = (screen_width / 2, screen_height * 0.72)
        self._base_entry_center = (screen_width / 2, screen_height * 0.47)
        self._completed_callback_sent = False
        self._orbital_strike_callback_sent = False
        self._on_departure_complete_callback = None
        self._on_orbital_strike_callback = None
        self._set_phase(HomecomingPhase.FTL_ESCAPE)
        return True

    def start_departure(
        self,
        player,
        screen_width: int,
        screen_height: int,
        on_complete_callback: Callable[[], None] | None = None,
        on_orbital_strike_callback: Callable[[], None] | None = None,
    ) -> bool:
        if self.is_active():
            return False

        self._screen_size = (screen_width, screen_height)
        self._landing_center = (screen_width / 2, screen_height * 0.72)
        self._base_entry_center = (screen_width / 2, screen_height * 0.47)
        self._start_center = self._base_entry_center
        self._current_center = self._start_center
        self._completed_callback_sent = False
        self._orbital_strike_callback_sent = False
        self._on_departure_complete_callback = on_complete_callback
        self._on_orbital_strike_callback = on_orbital_strike_callback
        self._apply_player_position(player)
        self._set_phase(HomecomingPhase.BASE_LAUNCH)
        return True

    def update(self, player) -> None:
        if not self.is_active():
            return

        self._frame += 1
        if self._phase == HomecomingPhase.FTL_ESCAPE:
            self._update_ftl_escape(player)
        elif self._phase == HomecomingPhase.BLACKOUT:
            self._update_blackout()
        elif self._phase == HomecomingPhase.STATION_REVEAL:
            self._update_station_reveal()
        elif self._phase == HomecomingPhase.APPROACH:
            self._update_approach(player)
        elif self._phase == HomecomingPhase.LANDING:
            self._update_landing(player)
        elif self._phase == HomecomingPhase.HANDOFF:
            self._update_handoff(player)
        elif self._phase == HomecomingPhase.BASE_LAUNCH:
            self._update_base_launch(player)
        elif self._phase == HomecomingPhase.RETURN_BLACKOUT:
            self._update_return_blackout()
        elif self._phase == HomecomingPhase.ORBITAL_STRIKE:
            self._update_orbital_strike()

    def get_player_center(self) -> tuple[float, float]:
        return self._current_center

    def get_landing_center(self) -> tuple[float, float]:
        return self._landing_center

    def get_base_entry_center(self) -> tuple[float, float]:
        return self._base_entry_center

    def get_phase_progress(self) -> float:
        duration = self._phase_duration()
        if duration <= 0:
            return 0.0
        return max(0.0, min(1.0, self._frame / duration))

    def reset(self) -> None:
        self._set_phase(HomecomingPhase.INACTIVE)
        self._completed_callback_sent = False
        self._orbital_strike_callback_sent = False
        self._on_departure_complete_callback = None
        self._on_orbital_strike_callback = None

    def _update_ftl_escape(self, player) -> None:
        progress = self.get_phase_progress()
        eased = progress * progress
        x = self._start_center[0]
        y = self._start_center[1] - (self._start_center[1] + player.rect.height * 2.5) * eased
        self._current_center = (x, y)
        self._apply_player_position(player)
        if progress >= 1.0:
            self._set_phase(HomecomingPhase.BLACKOUT)

    def _update_blackout(self) -> None:
        if self.get_phase_progress() >= 1.0:
            self._set_phase(HomecomingPhase.STATION_REVEAL)

    def _update_station_reveal(self) -> None:
        if self.get_phase_progress() >= 1.0:
            sw, sh = self._screen_size
            self._current_center = (sw / 2, sh + 110)
            self._set_phase(HomecomingPhase.APPROACH)

    def _update_approach(self, player) -> None:
        progress = self.get_phase_progress()
        eased = 1 - (1 - progress) ** 3
        sw, sh = self._screen_size
        start = (sw / 2, sh + 110)
        pre_landing = (self._landing_center[0], self._landing_center[1] + 130)
        x = start[0] + (pre_landing[0] - start[0]) * eased
        y = start[1] + (pre_landing[1] - start[1]) * eased
        self._current_center = (x, y)
        self._apply_player_position(player)
        if progress >= 1.0:
            self._set_phase(HomecomingPhase.LANDING)

    def _update_landing(self, player) -> None:
        progress = self.get_phase_progress()
        eased = 1 - (1 - progress) * (1 - progress)
        start = (self._landing_center[0], self._landing_center[1] + 125)
        x = start[0] + (self._landing_center[0] - start[0]) * eased
        y = start[1] + (self._landing_center[1] - start[1]) * eased
        self._current_center = (x, y)
        self._apply_player_position(player)
        if progress >= 1.0:
            self._set_phase(HomecomingPhase.HANDOFF)

    def _update_handoff(self, player) -> None:
        progress = self.get_phase_progress()
        eased = progress * progress * (3 - 2 * progress)
        x = self._landing_center[0] + (self._base_entry_center[0] - self._landing_center[0]) * eased
        y = self._landing_center[1] + (self._base_entry_center[1] - self._landing_center[1]) * eased
        self._current_center = (x, y)
        self._apply_player_position(player)

        if self.get_phase_progress() >= 1.0:
            self._set_phase(HomecomingPhase.COMPLETE)
            if self._on_complete_callback and not self._completed_callback_sent:
                self._completed_callback_sent = True
                self._on_complete_callback()

    def _update_base_launch(self, player) -> None:
        progress = self.get_phase_progress()
        eased = progress * progress * progress
        sw, sh = self._screen_size
        launch_exit = (sw / 2, sh + player.rect.height * 2.2)
        x = self._base_entry_center[0] + (launch_exit[0] - self._base_entry_center[0]) * eased
        y = self._base_entry_center[1] + (launch_exit[1] - self._base_entry_center[1]) * eased
        self._current_center = (x, y)
        self._apply_player_position(player)
        if progress >= 1.0:
            self._set_phase(HomecomingPhase.RETURN_BLACKOUT)

    def _update_return_blackout(self) -> None:
        if self.get_phase_progress() >= 1.0:
            self._set_phase(HomecomingPhase.ORBITAL_STRIKE)

    def _update_orbital_strike(self) -> None:
        progress = self.get_phase_progress()
        if (
            not self._orbital_strike_callback_sent
            and progress >= self.ORBITAL_STRIKE_IMPACT_PROGRESS
        ):
            self._orbital_strike_callback_sent = True
            if self._on_orbital_strike_callback:
                self._on_orbital_strike_callback()

        if progress >= 1.0:
            self._set_phase(HomecomingPhase.COMPLETE)
            if self._on_departure_complete_callback and not self._completed_callback_sent:
                self._completed_callback_sent = True
                self._on_departure_complete_callback()

    def _set_phase(self, phase: HomecomingPhase) -> None:
        self._phase = phase
        self._frame = 0

    def _phase_duration(self) -> int:
        durations = {
            HomecomingPhase.FTL_ESCAPE: self.FTL_FRAMES,
            HomecomingPhase.BLACKOUT: self.BLACKOUT_FRAMES,
            HomecomingPhase.STATION_REVEAL: self.STATION_REVEAL_FRAMES,
            HomecomingPhase.APPROACH: self.APPROACH_FRAMES,
            HomecomingPhase.LANDING: self.LANDING_FRAMES,
            HomecomingPhase.HANDOFF: self.HANDOFF_FRAMES,
            HomecomingPhase.BASE_LAUNCH: self.BASE_LAUNCH_FRAMES,
            HomecomingPhase.RETURN_BLACKOUT: self.RETURN_BLACKOUT_FRAMES,
            HomecomingPhase.ORBITAL_STRIKE: self.ORBITAL_STRIKE_FRAMES,
        }
        return durations.get(self._phase, 0)

    def _apply_player_position(self, player) -> None:
        player.rect.x = int(self._current_center[0] - player.rect.width / 2)
        player.rect.y = int(self._current_center[1] - player.rect.height / 2)
