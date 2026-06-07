"""Talent console components — switcher, resupply, mission list.

Phase 4 Wave beta split of the original ``airwar.ui.base_talent_console``
god class into three single-responsibility widgets. The
``BaseTalentConsole`` orchestrator (``airwar/ui/base_talent_console.py``)
owns one instance of each and dispatches per-module render calls.
"""

from airwar.ui.talent.mission_list import MissionList
from airwar.ui.talent.resupply_panel import ResupplyPanel
from airwar.ui.talent.talent_switcher import BUFF_LABELS, TalentSwitcher

__all__ = [
    "BUFF_LABELS",
    "MissionList",
    "ResupplyPanel",
    "TalentSwitcher",
]
