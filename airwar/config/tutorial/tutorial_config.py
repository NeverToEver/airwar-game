"""
Tutorial system — multi-page content configuration.

4 pages covering all game mechanics, content verified against actual game code:
- Movement & Combat (WASD, auto-fire, SHIFT boost)
- Mothership Docking (H-dock, ammo, cover fire)
- Special Actions (K-surrender, ESC-pause, L-HUD)
- Progression (milestones, buffs, boss kills)
"""

TUTORIAL_PAGES = [
    {
        'title': 'MOVEMENT & COMBAT',
        'subtitle': 'Basic Controls',
        'sections': [
            {
                'title': 'Movement',
                'items': [
                    ('W / ↑', 'Move Up'),
                    ('S / ↓', 'Move Down'),
                    ('A / ←', 'Move Left'),
                    ('D / →', 'Move Right'),
                    ('SHIFT (hold)', 'Boost — +70% speed, consumes energy'),
                ],
            },
            {
                'title': 'Combat',
                'items': [
                    ('Auto-Fire', 'Your ship fires automatically'),
                    ('Boost Dodge', 'Use SHIFT boost to evade bullets'),
                ],
            },
        ],
    },
    {
        'title': 'MOTHERSHIP DOCKING',
        'subtitle': 'Save Progress & Call Support',
        'sections': [
            {
                'title': 'Docking',
                'items': [
                    ('H (hold 3s)', 'Call mothership to dock'),
                    ('WASD', 'Move mothership while docked'),
                    ('Auto-Save', 'Progress saved when docking completes'),
                ],
            },
            {
                'title': 'Mothership Firepower',
                'items': [
                    ('Cover Fire', 'Explosive missiles target enemies'),
                    ('Ammo System', '10-cell magazine, depletes over 20s'),
                    ('Ammo Warning', 'Auto-undock when ammo depleted'),
                ],
            },
        ],
    },
    {
        'title': 'SPECIAL ACTIONS',
        'subtitle': 'Surrender & Interface',
        'sections': [
            {
                'title': 'Actions',
                'items': [
                    ('K (hold 3s)', 'Surrender — end current run'),
                    ('ESC', 'Pause game'),
                    ('L', 'Toggle HUD panel expanded / collapsed'),
                ],
            },
        ],
    },
    {
        'title': 'PROGRESSION',
        'subtitle': 'Milestones & Rewards',
        'sections': [
            {
                'title': 'Milestones',
                'items': [
                    ('Score Targets', 'Reach thresholds to unlock buffs'),
                    ('W / S', 'Navigate reward options'),
                    ('ENTER / SPACE', 'Select power-up'),
                    ('Mouse Click', 'Alternative selection'),
                ],
            },
            {
                'title': 'Difficulty',
                'items': [
                    ('Boss Kills', 'Each kill increases difficulty'),
                    ('12 Buff Types', 'Health, offense, defense, utility'),
                ],
            },
        ],
    },
]
