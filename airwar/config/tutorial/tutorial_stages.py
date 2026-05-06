"""Structured tutorial stage definitions for the playable tutorial scene."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TutorialStage:
    id: str
    title: str
    instructions: list[str]
    objective: str
    objective_count: int
    duration: int
    spawn_setup: str


TUTORIAL_STAGES = [
    TutorialStage(
        id="movement_aiming",
        title="移动与瞄准",
        instructions=[
            "使用 WASD 或方向键移动战机，鼠标决定炮口朝向。",
            "武器会自动从左右翼开火，准星靠近敌人时会辅助锁定目标中心。",
            "快速移动鼠标可以切换或暂时脱离锁定，先熟悉位移、瞄准辅助和自动射击节奏。",
        ],
        objective="击杀3个训练靶",
        objective_count=3,
        duration=0,
        spawn_setup="movement_targets",
    ),
    TutorialStage(
        id="boost_phase_dash",
        title="加速与相位突进",
        instructions=[
            "按住 Shift 会提高移动速度并消耗能量，松开 Shift 后能量会逐步恢复。",
            "本阶段额外开放相位突进：有移动方向且能量充足时轻按 Shift，会向当前移动方向短距离闪避。",
            "观察左下角真实加速燃料仪表，看它在加速、突进和恢复之间变化。",
        ],
        objective="使用加速或相位突进累计4次",
        objective_count=4,
        duration=0,
        spawn_setup="none",
    ),
    TutorialStage(
        id="combat_basics",
        title="战斗基础",
        instructions=[
            "普通敌机会射击并提供分数。保持移动，让准星辅助锁定最近目标。",
            "本阶段会受到少量伤害，但教程会保留最低生命值，不会直接击毁战机。",
            "这里只练习基础输出和规避；正式战斗中的奖励与成长会在主流程中处理。",
        ],
        objective="击杀5架敌机",
        objective_count=5,
        duration=0,
        spawn_setup="easy_enemies",
    ),
    TutorialStage(
        id="mothership_docking",
        title="母舰停靠",
        instructions=[
            "按住 H 呼叫真实母舰并完成停靠，画面中央会显示正式模式的资本级母舰。",
            "停靠完成后左侧会出现真实母舰弹匣，弹药低于3格时顶部会弹出正式警告横幅。",
            "本阶段不模拟母舰开火，重点是记住按住 H 完成停靠并识别母舰支援界面。",
        ],
        objective="按住H完成停靠",
        objective_count=1,
        duration=0,
        spawn_setup="none",
    ),
    TutorialStage(
        id="homecoming_base",
        title="返航与基地",
        instructions=[
            "本阶段直接展示真实基地天赋控制台；按住 B 完成返航整备确认。",
            "控制台包含战机库、武器挂载、维修补给和任务规划4个正式标签页。",
            "面板中的天赋、补给、任务和 RP 是教程示例数据，但界面就是正式基地整备界面。",
        ],
        objective="按住B完成返航整备",
        objective_count=1,
        duration=0,
        spawn_setup="none",
    ),
    TutorialStage(
        id="boss_encounter",
        title="首领遭遇",
        instructions=[
            "首领拥有更高生命值，低于30%生命时会进入核心过载状态。",
            "核心过载会显示警告光效并显著加快弹幕节奏，保持移动并持续输出。",
            "击败教程首领后会出现简化撤离倒计时，等待倒计时结束即可完成阶段。",
        ],
        objective="击败简化首领并等待撤离",
        objective_count=1,
        duration=0,
        spawn_setup="boss",
    ),
    TutorialStage(
        id="tutorial_complete",
        title="教程完成",
        instructions=[
            "你已经完成全部核心机制训练。",
            "正式战斗会把这些系统组合起来，并加入完整母舰支援、基地菜单、奖励成长和更复杂首领行为。",
            "返回主菜单后可以选择难度并开始新的空战任务。",
        ],
        objective="查看总结",
        objective_count=1,
        duration=0,
        spawn_setup="none",
    ),
]


__all__ = ["TutorialStage", "TUTORIAL_STAGES"]
