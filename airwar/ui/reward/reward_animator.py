"""Reward animator — animation timing and visual element updates.

Owns the time-based state that drives the selector's ambient motion
(``animation_time`` and the derived ``glow_offset``) plus the
background field updaters (``stars``, ``particles``, ``nebula_clouds``).
"""

import math
import random

from airwar.config.design_tokens import get_design_tokens


class RewardAnimator:
    """Time-based animation state and background field updaters.

    The animator does not render anything itself — it only advances
    per-frame state. The renderer reads the resulting fields to draw
    the panel.
    """

    def __init__(self):
        self._tokens = get_design_tokens()
        self.animation_time: int = 0
        self.glow_offset: float = 0.0
        self.stars: list[dict] = []
        self.particles: list[dict] = []
        self.nebula_clouds: list[dict] = []
        self._init_visual_elements()

    def _init_visual_elements(self) -> None:
        tokens = self._tokens
        anim = tokens.animation
        self.stars = []
        for _ in range(tokens.components.STAR_COUNT):
            self.stars.append(
                {
                    "x": random.random(),
                    "y": random.random(),
                    "size": random.uniform(0.5, 2.5),
                    "brightness": random.randint(80, 200),
                    "twinkle_speed": random.uniform(anim.TWINKLE_SPEED_MIN, anim.TWINKLE_SPEED_MAX),
                    "twinkle_offset": random.random() * math.pi * 2,
                }
            )

        self.particles = []
        for _ in range(tokens.components.PARTICLE_COUNT):
            self.particles.append(
                {
                    "x": random.random(),
                    "y": random.random(),
                    "size": random.uniform(1.5, 4.0),
                    "speed": random.uniform(anim.PARTICLE_SPEED_MIN * 0.3, anim.PARTICLE_SPEED_MAX * 0.5),
                    "alpha": random.randint(100, 200),
                    "pulse_speed": random.uniform(0.01, 0.04),
                    "pulse_offset": random.random() * math.pi * 2,
                }
            )

        self.nebula_clouds = []
        for _ in range(anim.NEBULA_COUNT):
            self.nebula_clouds.append(
                {
                    "x": random.random(),
                    "y": random.random(),
                    "radius": random.uniform(anim.NEBULA_RADIUS_MIN, anim.NEBULA_RADIUS_MAX),
                    "alpha": random.randint(anim.NEBULA_ALPHA_MIN, anim.NEBULA_ALPHA_MAX),
                    "color": tokens.forest.GOLD_GLOW,
                    "drift_x": random.uniform(-anim.NEBULA_DRIFT_X_RANGE, anim.NEBULA_DRIFT_X_RANGE),
                    "drift_y": random.uniform(-anim.NEBULA_DRIFT_Y_RANGE, anim.NEBULA_DRIFT_Y_RANGE),
                }
            )

    def tick(self) -> None:
        """Advance one frame of animation state.

        Increments ``animation_time`` and recomputes the smooth glow offset
        used by title/panel positioning.
        """
        self.animation_time += 1
        self.glow_offset = math.sin(self.animation_time * self._tokens.animation.GLOW_SPEED) * 8

    def update_stars(self) -> None:
        """Drift stars downward; respawn at top when they leave the screen."""
        for star in self.stars:
            star["y"] += star.get("speed", 0.005) * 0.005
            if star["y"] > 1:
                star["y"] = 0
                star["x"] = random.random()

    def update_particles(self) -> None:
        """Drift particles upward and wrap horizontally / vertically."""
        for p in self.particles[:]:
            p["y"] -= p["speed"] * 0.002
            p["x"] += p.get("drift_x", 0) if "drift_x" in p else 0
            if p["y"] < -0.1:
                p["y"] = 1.1
                p["x"] = random.random()
                p["alpha"] = random.randint(100, 200)
            if p["x"] < -0.1:
                p["x"] = 1.1
            elif p["x"] > 1.1:
                p["x"] = -0.1

    def update_nebula_clouds(self) -> None:
        """Drift nebula clouds and wrap around the screen edges."""
        for cloud in self.nebula_clouds:
            cloud["x"] += cloud["drift_x"]
            cloud["y"] += cloud["drift_y"]
            if cloud["x"] < -0.2:
                cloud["x"] = 1.2
            elif cloud["x"] > 1.2:
                cloud["x"] = -0.2
            if cloud["y"] < -0.2:
                cloud["y"] = 1.2
            elif cloud["y"] > 1.2:
                cloud["y"] = -0.2
