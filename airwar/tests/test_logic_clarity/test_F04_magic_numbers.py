"""F04: 11 魔法数字（magic numbers / hardcoded values）。

Maps: docs/logic-clarity/11-phase5b-handoff.md §6.2 § F04.
(The previous docs/logic-clarity/04-test-suite.md was retired in the
2026-06-08 docs cleanup; the F04 magic-number contract is preserved
in the new handoff doc, with BULLET_CLEAR_RADIUS and 6 homecoming
phase frames confirmed as already-on-GAME_CONSTANTS.)

These tests verify the post-refactor contract: all magic numbers
should be moved to GAME_CONSTANTS or a similar central registry.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


class TestF04SentinelRemovedFromGameScene:
    """M1, M7: PERMANENT_INVINCIBILITY_FRAMES = 999999 不应散落。"""

    def test_no_999999_in_game_scene(self):
        path = REPO_ROOT / "airwar" / "scenes" / "game_scene.py"
        text = path.read_text()
        # The sentinel 999999 should not appear as a literal in business code
        # (only allowed in a comment or docstring that references the constant)
        # We check raw occurrences of the bare integer.
        bare_999999 = re.findall(r"\b999999\b", text)
        # We allow it in comments but not as a value
        for match in bare_999999:
            # Find the line
            line_no = text[: text.find(match)].count("\n") + 1
            line = text.splitlines()[line_no - 1]
            if not line.lstrip().startswith("#") and "999999" not in line.split("#")[-1]:
                pytest.fail(f"M1: bare 999999 found in game_scene.py line {line_no}: {line.strip()}")

    def test_no_999999_in_homecoming_coordinator(self):
        path = REPO_ROOT / "airwar" / "game" / "systems" / "homecoming_coordinator.py"
        text = path.read_text()
        bare_999999 = re.findall(r"\b999999\b", text)
        for match in bare_999999:
            line_no = text[: text.find(match)].count("\n") + 1
            line = text.splitlines()[line_no - 1]
            if not line.lstrip().startswith("#") and "999999" not in line.split("#")[-1]:
                pytest.fail(f"M7: bare 999999 in homecoming_coordinator.py line {line_no}: {line.strip()}")


class TestF04FrameConstantsInConfig:
    """M2, M3: DOCKING_INVINCIBILITY_FRAMES / AUTO_SAVE_INTERVAL 应在常量。"""

    def test_constants_module_has_permanent_invincibility(self):
        from airwar.game.constants import GAME_CONSTANTS

        assert GAME_CONSTANTS.PERSISTENCE.PERMANENT_INVINCIBILITY_FRAMES == 999_999
        assert GAME_CONSTANTS.PERSISTENCE.DOCKING_INVINCIBILITY_FRAMES == 1200
        assert GAME_CONSTANTS.PERSISTENCE.AUTO_SAVE_INTERVAL == 1800


class TestF04EnrageConstantsInGameConstants:
    """M9: 27 个 ENRAGE_* 常量应在 GAME_CONSTANTS.BOSS.ENRAGE。"""

    def test_enrage_constants_centralized(self):
        from airwar.game.constants import GAME_CONSTANTS
        from airwar.entities.enemy.boss import boss_state

        expected = {
            "ENRAGE_TRIGGER_RATIO": "TRIGGER_RATIO",
            "ENRAGE_DURATION": "DURATION",
            "ENRAGE_TRANSITION_DURATION": "TRANSITION_DURATION",
            "ENRAGE_SLOW_FACTOR": "SLOW_FACTOR",
            "ENRAGE_BULLET_SPEED": "BULLET_SPEED",
            "ENRAGE_LASER_SPEED": "LASER_SPEED",
            "ENRAGE_RELEASE_BULLET_SPEED": "RELEASE_BULLET_SPEED",
            "ENRAGE_RELEASE_LASER_SPEED": "RELEASE_LASER_SPEED",
            "ENRAGE_ATTACK_INTERVAL": "ATTACK_INTERVAL",
            "ENRAGE_ATTACK_WINDUP": "ATTACK_WINDUP",
            "ENRAGE_RELEASE_INTERVAL": "RELEASE_INTERVAL",
            "ENRAGE_SNAPSHOT_LASER_COUNT": "SNAPSHOT_LASER_COUNT",
            "ENRAGE_SNAPSHOT_RING_COUNT": "SNAPSHOT_RING_COUNT",
            "ENRAGE_PATH_RADIUS_SCALE": "PATH_RADIUS_SCALE",
            "ENRAGE_SQUARE_PATH_RATIO": "SQUARE_PATH_RATIO",
            "ENRAGE_TRAIL_LENGTH": "TRAIL_LENGTH",
            "ENRAGE_TRAIL_RENDER_MAX": "TRAIL_RENDER_MAX",
            "ENRAGE_TRAIL_FINAL_SCALE": "TRAIL_FINAL_SCALE",
            "ENRAGE_TRAIL_SCALE": "TRAIL_SCALE",
            "ENRAGE_TRAIL_BLUR_PASSES": "TRAIL_BLUR_PASSES",
            "ENRAGE_EXIT_BACK_OFFSET": "EXIT_BACK_OFFSET",
            "ENRAGE_MUZZLE_FLASH_DURATION": "MUZZLE_FLASH_DURATION",
            "ENRAGE_MUZZLE_FLASH_PULSES": "MUZZLE_FLASH_PULSES",
            "ENRAGE_MUZZLE_FORWARD_SCALE": "MUZZLE_FORWARD_SCALE",
            "ENRAGE_MUZZLE_SIDE_SCALE": "MUZZLE_SIDE_SCALE",
            "ENRAGE_RELEASE_HOLD_DURATION": "RELEASE_HOLD_DURATION",
            "ENRAGE_RETURN_DURATION": "RETURN_DURATION",
            "ENRAGE_CORE_COLOR": "CORE_COLOR",
            "ENRAGE_DANGER_COLOR": "DANGER_COLOR",
            "ENRAGE_TRAIL_TINT": "TRAIL_TINT",
        }
        assert len(expected) == 30
        for legacy_name, constants_name in expected.items():
            assert getattr(boss_state, legacy_name) == getattr(GAME_CONSTANTS.BOSS_ENRAGE, constants_name)


class TestF04HomecomingPhaseFramesInConstants:
    """M10: 6 阶段帧数应在 GAME_CONSTANTS.HOMECOMING.PHASES。"""

    def test_homecoming_phase_frames_in_current_location(self):
        from airwar.game.homecoming import homecoming_sequence
        from airwar.game.constants import GAME_CONSTANTS

        expected = {
            "FTL_FRAMES": "FTL_ESCAPE",
            "BLACKOUT_FRAMES": "BLACKOUT",
            "STATION_REVEAL_FRAMES": "STATION_REVEAL",
            "APPROACH_FRAMES": "APPROACH",
            "LANDING_FRAMES": "LANDING",
            "HANDOFF_FRAMES": "HANDOFF",
            "BASE_LAUNCH_FRAMES": "BASE_LAUNCH",
            "RETURN_BLACKOUT_FRAMES": "RETURN_BLACKOUT",
            "ORBITAL_STRIKE_FRAMES": "ORBITAL_STRIKE",
            "ORBITAL_STRIKE_IMPACT_PROGRESS": "ORBITAL_STRIKE_IMPACT_PROGRESS",
        }
        for legacy_name, constants_name in expected.items():
            assert getattr(homecoming_sequence.HomecomingSequence, legacy_name) == getattr(
                GAME_CONSTANTS.HOMECOMING_PHASES,
                constants_name,
            )


class TestF04MaxSubscribersInConstants:
    """M11: MAX_SUBSCRIBERS 应在 GAME_CONSTANTS。"""

    def test_max_subscribers_currently_in_event_bus(self):
        from airwar.game.constants import GAME_CONSTANTS
        from airwar.game.mother_ship.event_bus import EventBus

        bus = EventBus()
        assert EventBus.MAX_SUBSCRIBERS == GAME_CONSTANTS.EVENTS.MAX_SUBSCRIBERS
        assert bus._max_callback_failures == GAME_CONSTANTS.EVENTS.MAX_CALLBACK_FAILURES
