"""Homecoming phase renderers -- one module per cinematic phase.

Each renderer is self-contained and only knows about its own phase. The
``HomecomingUI`` coordinator in ``airwar/ui/homecoming_ui.py`` owns one
instance of each and dispatches ``render_sequence`` to the active phase.
"""

from airwar.ui.homecoming._constants import (
    PHASE_APPROACH,
    PHASE_BASE_LAUNCH,
    PHASE_BLACKOUT,
    PHASE_FTL_ESCAPE,
    PHASE_HANDOFF,
    PHASE_LANDING,
    PHASE_ORBITAL_STRIKE,
    PHASE_RETURN_BLACKOUT,
    PHASE_STATION_REVEAL,
)
from airwar.ui.homecoming.approach_camera import ApproachCameraRenderer
from airwar.ui.homecoming.blackout_transition import BlackoutTransitionRenderer
from airwar.ui.homecoming.ftl_animation import FtlAnimationRenderer
from airwar.ui.homecoming.landing_handoff import LandingHandoffRenderer
from airwar.ui.homecoming.station_reveal import StationRevealRenderer

__all__ = [
    "PHASE_APPROACH",
    "PHASE_BASE_LAUNCH",
    "PHASE_BLACKOUT",
    "PHASE_FTL_ESCAPE",
    "PHASE_HANDOFF",
    "PHASE_LANDING",
    "PHASE_ORBITAL_STRIKE",
    "PHASE_RETURN_BLACKOUT",
    "PHASE_STATION_REVEAL",
    "ApproachCameraRenderer",
    "BlackoutTransitionRenderer",
    "FtlAnimationRenderer",
    "LandingHandoffRenderer",
    "StationRevealRenderer",
]
