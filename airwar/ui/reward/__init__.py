"""Reward selector components — layout, click, animation, rendering.

Phase 4 W-alpha split of the original ``airwar.ui.reward_selector``
god class into four single-responsibility components. The
``RewardSelector`` orchestrator (``airwar/ui/reward_selector.py``) owns
one instance of each and dispatches public calls to the right
component.
"""

from airwar.ui.reward.reward_animator import RewardAnimator
from airwar.ui.reward.reward_card_renderer import RewardCardRenderer
from airwar.ui.reward.reward_click_handler import RewardClickHandler
from airwar.ui.reward.reward_layout import RewardLayout

__all__ = [
    "RewardAnimator",
    "RewardCardRenderer",
    "RewardClickHandler",
    "RewardLayout",
]
