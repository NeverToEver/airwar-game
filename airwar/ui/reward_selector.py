import pygame
from typing import List, Callable, Optional


class RewardSelector:
    def __init__(self):
        self.visible: bool = False
        self.selected_index: int = 0
        self.options: List[dict] = []
        self.on_select: Optional[Callable] = None
        self.animation_time: int = 0

    def generate_options(self, cycle_count: int, unlocked_buffs: list) -> list:
        from airwar.game.systems.reward_system import REWARD_POOL
        import random
        options = []
        categories = list(REWARD_POOL.keys())

        for _ in range(3):
            cat = random.choice(categories)
            rewards = REWARD_POOL[cat]

            if cat == 'offense' and cycle_count > 2:
                rewards = [r for r in rewards if r['name'] not in ['Spread Shot', 'Explosive']]

            reward = random.choice(rewards)
            attempts = 0
            while reward in options and attempts < 10:
                reward = random.choice(rewards)
                attempts += 1

            options.append(reward)

        return options

    def show(self, options: list, callback: Callable) -> None:
        self.visible = True
        self.options = options
        self.selected_index = 0
        self.on_select = callback
        self.animation_time = 0

    def hide(self) -> None:
        self.visible = False
        self.options = []

    def handle_input(self, event: pygame.event.Event) -> None:
        if not self.visible:
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_index = (self.selected_index - 1) % len(self.options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_index = (self.selected_index + 1) % len(self.options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._confirm_selection()

    def _confirm_selection(self) -> None:
        if self.on_select and self.options:
            selected = self.options[self.selected_index]
            self.on_select(selected)
        self.hide()

    def update(self) -> None:
        if self.visible:
            self.animation_time += 1

    def render(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        width, height = surface.get_size()

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((8, 8, 25, 240))
        surface.blit(overlay, (0, 0))

        title = pygame.font.Font(None, 60).render("CHOOSE YOUR REWARD", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(width // 2, 100)))

        box_width = 580
        box_height = 110
        start_y = 180
        start_x = width // 2 - box_width // 2

        for i, option in enumerate(self.options):
            y = start_y + i * (box_height + 35)
            x = start_x

            is_selected = i == self.selected_index
            box_color = (35, 55, 85) if is_selected else (22, 28, 48)
            border_color = (0, 255, 150) if is_selected else (70, 90, 130)

            box_rect = pygame.Rect(x, y, box_width, box_height)

            if is_selected:
                glow_rect = box_rect.inflate(8, 8)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (0, 255, 150, 40), glow_surf.get_rect(), border_radius=15)
                surface.blit(glow_surf, glow_rect)

            pygame.draw.rect(surface, box_color, box_rect, border_radius=12)
            pygame.draw.rect(surface, border_color, box_rect, 3 if is_selected else 2, border_radius=12)

            icon_box_width = 85
            icon_box_rect = pygame.Rect(x + 12, y + 12, icon_box_width, box_height - 24)
            pygame.draw.rect(surface, (28, 38, 60), icon_box_rect, border_radius=8)
            pygame.draw.rect(surface, border_color, icon_box_rect, 1, border_radius=8)

            arrow = ">>> " if is_selected else "    "
            icon_text = pygame.font.Font(None, 32).render(f"{arrow}{option['icon']}", True,
                                                        (0, 255, 150) if is_selected else (140, 140, 160))
            icon_text_rect = icon_text.get_rect(center=(x + 12 + icon_box_width // 2, y + box_height // 2))
            surface.blit(icon_text, icon_text_rect)

            text_x = x + icon_box_width + 35

            name_text = pygame.font.Font(None, 38).render(option['name'], True,
                                                        (255, 255, 255) if is_selected else (200, 200, 220))
            surface.blit(name_text, (text_x, y + 22))

            desc_text = pygame.font.Font(None, 28).render(option['desc'], True,
                                                        (160, 210, 160) if is_selected else (100, 110, 140))
            surface.blit(desc_text, (text_x, y + 62))

        hint = pygame.font.Font(None, 26).render("W/S or UP/DOWN to select, ENTER to confirm", True, (90, 110, 140))
        surface.blit(hint, hint.get_rect(center=(width // 2, height - 60)))
