"""Localized buff display names for compact UI surfaces."""

BUFF_DISPLAY_NAMES = {
    'Power Shot': '强力弹',
    'Rapid Fire': '快速射击',
    'Piercing': '穿透',
    'Spread Shot': '散射',
    'Explosive': '爆炸弹',
    'Laser': '激光',
    'Armor': '装甲',
    'Evasion': '闪避',
    'Barrier': '护盾',
    'Extra Life': '生命强化',
    'Regeneration': '生命恢复',
    'Lifesteal': '汲取',
    'Slow Field': '减速场',
    'Boost Recovery': '加速恢复',
    'Phase Dash': '相位突进',
    'Mothership Recall': '母舰返场',
}


def get_buff_display_name(name: str) -> str:
    return BUFF_DISPLAY_NAMES.get(name, name)
