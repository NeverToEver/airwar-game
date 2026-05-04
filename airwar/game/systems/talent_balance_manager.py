"""Talent loadout balancing for base-side respec decisions."""

from dataclasses import dataclass
from typing import Dict, Iterable


OFFENSE_ROUTE = "offense"
SUPPORT_ROUTE = "support"
LOADOUT_ROUTES = {
    OFFENSE_ROUTE: ("Spread Shot", "Laser"),
    SUPPORT_ROUTE: ("Phase Dash", "Mothership Recall"),
}
ROUTE_LABELS = {
    OFFENSE_ROUTE: "武器路线",
    SUPPORT_ROUTE: "机动支援",
}
BUFF_LABELS = {
    "Spread Shot": "散射弹幕",
    "Laser": "激光模式",
    "Phase Dash": "相位突进",
    "Mothership Recall": "母舰冷却",
}


@dataclass(frozen=True)
class TalentRouteView:
    route: str
    label: str
    options: tuple[str, ...]
    selected: str | None
    budget: int
    is_unlocked: bool
    locked_buffs: tuple[str, ...]


class TalentBalanceManager:
    """Calculates effective buff levels under route exclusivity constraints."""

    def __init__(self, earned_levels: Dict[str, int], loadout: Dict[str, str] | None = None):
        self._earned_levels = {name: max(0, int(level)) for name, level in earned_levels.items()}
        self._loadout = dict(loadout or {})
        self._normalize_loadout()

    @property
    def loadout(self) -> Dict[str, str]:
        return dict(self._loadout)

    def total_points(self) -> int:
        return sum(self._earned_levels.values())

    def route_views(self) -> list[TalentRouteView]:
        views = []
        for route, options in LOADOUT_ROUTES.items():
            budget = self._route_budget(options)
            selected = self._loadout.get(route)
            locked = tuple(name for name in options if selected and name != selected)
            views.append(
                TalentRouteView(
                    route=route,
                    label=ROUTE_LABELS[route],
                    options=options,
                    selected=selected,
                    budget=budget,
                    is_unlocked=budget > 0,
                    locked_buffs=locked,
                )
            )
        return views

    def select(self, route: str, buff_name: str) -> None:
        options = LOADOUT_ROUTES.get(route)
        if not options or buff_name not in options:
            raise ValueError(f"Invalid talent route selection: {route} -> {buff_name}")
        if self._route_budget(options) <= 0:
            raise ValueError(f"Route has no earned points: {route}")
        self._loadout[route] = buff_name

    def next_option(self, route: str) -> str | None:
        options = LOADOUT_ROUTES.get(route)
        if not options or self._route_budget(options) <= 0:
            return None
        current = self._loadout.get(route, options[0])
        next_index = (options.index(current) + 1) % len(options)
        self._loadout[route] = options[next_index]
        return self._loadout[route]

    def effective_levels(self) -> Dict[str, int]:
        levels = dict(self._earned_levels)
        for route, options in LOADOUT_ROUTES.items():
            budget = self._route_budget(options)
            if budget <= 0:
                continue

            selected = self._loadout.get(route, options[0])
            for name in options:
                levels[name] = 0
            levels[selected] = budget
        return levels

    def locked_buffs(self) -> set[str]:
        locked = set()
        for route, options in LOADOUT_ROUTES.items():
            selected = self._loadout.get(route)
            if not selected:
                continue
            locked.update(name for name in options if name != selected)
        return locked

    def apply_to_reward_system(self, reward_system, player) -> None:
        reward_system.apply_effective_levels(
            self.effective_levels(),
            locked_buffs=self.locked_buffs(),
            talent_loadout=self._loadout,
        )
        reward_system.reapply_all_effects(player)

    def _normalize_loadout(self) -> None:
        for route, options in LOADOUT_ROUTES.items():
            budget = self._route_budget(options)
            selected = self._loadout.get(route)
            if budget <= 0:
                self._loadout.pop(route, None)
            elif selected not in options:
                self._loadout[route] = self._default_selected(options)

    def _default_selected(self, options: Iterable[str]) -> str:
        for name in options:
            if self._earned_levels.get(name, 0) > 0:
                return name
        return tuple(options)[0]

    def _route_budget(self, options: Iterable[str]) -> int:
        return sum(self._earned_levels.get(name, 0) for name in options)
