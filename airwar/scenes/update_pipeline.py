"""F05 T1: 显式 UpdatePipeline。

The game-loop update order is the most order-sensitive part of the
codebase (any reordering changes observable behavior). Rather than
relying on positional calls inside ``GameScene.update``, this module
declares the per-frame subsystem order as an explicit, importable
constant.

Order semantics::

    PIPELINE_ORDER = [
        # --- Input ---
        "reward_selector",          # 1.  奖励选择器（若可见则独占输入）
        "aim_assist",               # 2.  准星吸附
        "homecoming",               # 3.  返航检测 + 序列
        # --- Animations ---
        "warning_banner",           # 4.  警告横幅（即使 dying 也要滚动）
        "entrance_animation",       # 5.  出生动画
        "dying_animation",          # 6.  死亡动画
        # --- Flow gates ---
        "pause_check",              # 7.  暂停检查（短路后续）
        "mothership_integrator",    # 8.  母舰整合（docking/cooldown）
        "give_up_detector",         # 9.  投降检测
        # --- Core simulation ---
        "core_logic",               # 10. GameController + 玩家 + 子弹 + 敌机
        "phase_dash_sync",          # 11. Phase Dash 无敌同步
        "collision",                # 12. 碰撞检测
        "post_collision_cleanup",   # 13. 碰撞后清理（保证 milestone 之前）
        # --- Side effects ---
        "milestone_check",          # 14. 里程碑奖励
        "auto_save",                # 15. 周期自动存档
    ]

Short-circuit semantics:
    The pipeline declares the **canonical** order, but several steps
    can short-circuit the rest of the frame when their conditions hold:

    * ``pause_check``        -> skip everything after if paused
    * ``reward_selector``    -> skip input/decision if visible
    * ``dying_animation``    -> skip sim after death anim starts
    * ``entrance_animation`` -> skip sim during initial entrance
    * ``homecoming``         -> skip sim during FTL sequence

Adding a new subsystem:
    1. Pick the right position in PIPELINE_ORDER
    2. Implement the step as a callable
    3. Register the step in :meth:`UpdatePipeline.add_step`
    4. Add a test that asserts the step runs at the declared position
"""

from __future__ import annotations

from collections.abc import Callable

# Canonical subsystem order. Keys are stable names; values are human
# descriptions used in diagnostics.
PIPELINE_ORDER: list[str] = [
    # Input layer (L1 → L2)
    "reward_selector",
    "aim_assist",
    "homecoming",
    # Animation layer (independent of game state)
    "warning_banner",
    "entrance_animation",
    "dying_animation",
    # Flow gates (may short-circuit)
    "pause_check",
    "mothership_integrator",
    "give_up_detector",
    # Core simulation
    "core_logic",
    "phase_dash_sync",
    "collision",
    "post_collision_cleanup",
    # Side effects
    "milestone_check",
    "auto_save",
]


# Steps that, when they "claim" the frame, prevent later steps from running.
# The check itself is the predicate; the implementation lives in GameScene.
SHORT_CIRCUIT_STEPS: frozenset[str] = frozenset(
    {
        "pause_check",
        "reward_selector",
        "dying_animation",
        "entrance_animation",
        "homecoming",
    }
)


class UpdatePipeline:
    """F05: explicit, ordered per-frame subsystem dispatcher.

    The pipeline is intentionally minimal: it owns the **order** and
    the **short-circuit decisions**, but delegates the actual work to
    callables that GameScene wires up. This keeps the order in one
    place while letting each subsystem remain self-contained.

    Usage:
        pipeline = UpdatePipeline()
        pipeline.add_step("aim_assist", lambda: aim.update())
        pipeline.add_step("collision", lambda: collisions.check())
        pipeline.execute()  # runs in PIPELINE_ORDER; short-circuits apply
    """

    def __init__(self) -> None:
        self._steps: dict[str, Callable[[], bool | None]] = {}
        # Track call order across the most recent execute() for testing.
        self.last_executed: list[str] = []

    def add_step(self, name: str, fn: Callable[[], bool | None]) -> None:
        """Register a step.

        Args:
            name: Stable step name; must be in PIPELINE_ORDER.
            fn: Callable that performs the step's work. Returning
                ``False`` short-circuits the rest of the frame.
        """
        if name not in PIPELINE_ORDER:
            raise ValueError(
                f"Unknown pipeline step {name!r}. Must be one of PIPELINE_ORDER. "
                f"Add it to PIPELINE_ORDER first to declare its position."
            )
        if name in self._steps:
            raise ValueError(f"Step {name!r} is already registered")
        self._steps[name] = fn

    def has_step(self, name: str) -> bool:
        return name in self._steps

    def execute(self) -> None:
        """Run all registered steps in PIPELINE_ORDER.

        Each step's callable may return ``False`` to short-circuit
        the remaining steps for this frame. Returning ``True`` or
        ``None`` continues the pipeline.
        """
        self.last_executed = []
        for name in PIPELINE_ORDER:
            if name not in self._steps:
                # Steps that aren't wired up (e.g. tests) are skipped silently.
                continue
            self.last_executed.append(name)
            result = self._steps[name]()
            if result is False and name in SHORT_CIRCUIT_STEPS:
                # The remaining steps are skipped for this frame.
                return

    def get_unwired_steps(self) -> list[str]:
        """Return the names of PIPELINE_ORDER steps that haven't been registered.

        Useful for diagnostics and tests.
        """
        return [name for name in PIPELINE_ORDER if name not in self._steps]


__all__ = [
    "PIPELINE_ORDER",
    "SHORT_CIRCUIT_STEPS",
    "UpdatePipeline",
]
