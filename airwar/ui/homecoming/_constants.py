"""Phase name constants shared by the coordinator and all phase renderers.

Lives in its own module so renderer modules can import these constants
without triggering a circular import on ``airwar.ui.homecoming`` (whose
``__init__`` imports the renderer classes).
"""

PHASE_FTL_ESCAPE = "ftl_escape"
PHASE_BLACKOUT = "blackout"
PHASE_STATION_REVEAL = "station_reveal"
PHASE_APPROACH = "approach"
PHASE_LANDING = "landing"
PHASE_HANDOFF = "handoff"
PHASE_BASE_LAUNCH = "base_launch"
PHASE_RETURN_BLACKOUT = "return_blackout"
PHASE_ORBITAL_STRIKE = "orbital_strike"
