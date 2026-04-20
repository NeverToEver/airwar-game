import pygame
import math
from typing import List, Callable, Optional


class RewardSelector:
    def __init__(self):
        self.visible: bool = False
        self.selected_index: int = 0
        self.options: List[dict] = []
        self.on_select: Optional[Callable] = None
        self.animation_time: int = 0
        self.glow_offset: float = 0
        self.stars: list = []
        self.particles: list = []
        self.buff_levels: dict = {}
        self.unlocked_buffs: list = []
        self._init_visual_elements()

    def _init_visual_elements(self) -> None:
        import random
        self.stars = []
        for _ in range(80):
            self.stars.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(0.5, 2.0),
                'brightness': random.randint(50, 150),
                'twinkle_speed': random.uniform(0.03, 0.08),
                'twinkle_offset': random.random() * math.pi * 2,
            })
        
        self.particles = []
        for _ in range(30):
            self.particles.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(1.5, 3.0),
                'speed': random.uniform(0.2, 0.6),
                'alpha': random.randint(80, 150),
                'pulse_speed': random.uniform(0.02, 0.05),
                'pulse_offset': random.random() * math.pi * 2,
            })

        pygame.font.init()
        self.title_font = pygame.font.Font(None, 56)
        self.option_font = pygame.font.Font(None, 36)
        self.hint_font = pygame.font.Font(None, 24)
        
        self.colors = {
            'bg': (8, 8, 25),
            'bg_gradient': (12, 12, 45),
            'title': (255, 255, 255),
            'title_glow': (100, 200, 255),
            'selected': (0, 255, 150),
            'selected_glow': (0, 200, 255),
            'unselected': (90, 90, 130),
            'desc_selected': (140, 200, 140),
            'desc_unselected': (80, 85, 120),
            'hint': (70, 75, 110),
            'particle': (100, 180, 255),
            'panel': (15, 20, 40),
            'panel_border': (50, 80, 140),
            'option_selected_bg': (25, 35, 65),
            'option_unselected_bg': (18, 20, 40),
            'upgraded': (200, 180, 255),
            'upgraded_glow': (180, 150, 220),
            'new_buff': (100, 255, 150),
            'upgraded_bg': (30, 25, 45),
        }

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

    def show(self, options: list, callback: Callable, buff_levels: dict = None, unlocked_buffs: list = None) -> None:
        self.visible = True
        self.options = options
        self.selected_index = 0
        self.on_select = callback
        self.animation_time = 0
        self.buff_levels = buff_levels or {}
        self.unlocked_buffs = unlocked_buffs or []

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
            self.glow_offset = math.sin(self.animation_time * 0.05) * 8
            self._update_stars()
            self._update_particles()

    def _update_stars(self) -> None:
        import random
        for star in self.stars:
            star['y'] += star.get('speed', 0.005) * 0.005
            if star['y'] > 1:
                star['y'] = 0
                star['x'] = random.random()

    def _update_particles(self) -> None:
        import random
        for p in self.particles[:]:
            p['y'] -= p['speed'] * 0.002
            if p['y'] < -0.1:
                p['y'] = 1.1
                p['x'] = random.random()
                p['alpha'] = random.randint(80, 150)

    def _draw_gradient_background(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        for y in range(height):
            ratio = y / height
            r = int(self.colors['bg'][0] * (1 - ratio) + self.colors['bg_gradient'][0] * ratio)
            g = int(self.colors['bg'][1] * (1 - ratio) + self.colors['bg_gradient'][1] * ratio)
            b = int(self.colors['bg'][2] * (1 - ratio) + self.colors['bg_gradient'][2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

    def _draw_stars(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        for star in self.stars:
            x = int(star['x'] * width)
            y = int(star['y'] * height)
            twinkle = math.sin(self.animation_time * star['twinkle_speed'] + star['twinkle_offset'])
            brightness = int(star['brightness'] * (0.5 + 0.5 * twinkle))
            pygame.draw.circle(surface, (brightness, brightness, brightness + 30), (x, y), int(star['size']))

    def _draw_particles(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        for p in self.particles:
            x = int(p['x'] * width)
            y = int(p['y'] * height)
            pulse = math.sin(self.animation_time * p['pulse_speed'] + p['pulse_offset'])
            alpha = int(p['alpha'] * (0.6 + 0.4 * pulse))
            size = int(p['size'] * (0.7 + 0.3 * pulse))

            particle_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            for i in range(size * 2, 0, -2):
                layer_alpha = int(alpha * (size * 2 - i) / (size * 2) * 0.4)
                pygame.draw.circle(particle_surf, (*self.colors['particle'], layer_alpha),
                                 (size * 2, size * 2), i)
            surface.blit(particle_surf, (x - size * 2, y - size * 2))

    def _draw_glow_text(self, surface: pygame.Surface, text: str, font: pygame.font.Font,
                        pos: tuple, color: tuple, glow_color: tuple, glow_radius: int = 2) -> None:
        for i in range(glow_radius, 0, -1):
            alpha = int(100 / i)
            glow_surf = font.render(text, True, glow_color)
            glow_surf.set_alpha(alpha)
            glow_rect = glow_surf.get_rect(center=(pos[0], pos[1] + i))
            surface.blit(glow_surf, glow_rect)

        main_text = font.render(text, True, color)
        surface.blit(main_text, main_text.get_rect(center=pos))

    def _draw_panel(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        
        panel_width = 480
        panel_height = 320
        panel_x = width // 2 - panel_width // 2
        panel_y = height // 2 - panel_height // 2 + self.glow_offset * 0.3
        
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        for i in range(3, 0, -1):
            expand = i * 4
            glow_surf = pygame.Surface((panel_width + expand * 2, panel_height + expand * 2), pygame.SRCALPHA)
            alpha = max(5, 20 // i)
            pygame.draw.rect(glow_surf, (*self.colors['title_glow'], alpha),
                          glow_surf.get_rect(), border_radius=18)
            surface.blit(glow_surf, (panel_x - expand, panel_y - expand))

        pygame.draw.rect(surface, self.colors['panel'], panel_rect, border_radius=15)

        border_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*self.colors['panel_border'], 120),
                       border_surf.get_rect(), width=2, border_radius=15)
        surface.blit(border_surf, panel_rect.topleft)

    def _draw_option_item(self, surface: pygame.Surface, option: dict, index: int,
                          center_x: int, start_y: int, is_selected: bool) -> None:
        option_height = 80
        option_gap = 15
        y = start_y + index * (option_height + option_gap)
        
        box_width = 440
        box_height = option_height
        box_rect = pygame.Rect(center_x - box_width // 2, y, box_width, box_height)

        buff_name = option['name']
        level = self.buff_levels.get(buff_name, 0)
        is_upgraded = buff_name in self.unlocked_buffs and level > 0

        if is_upgraded:
            glow_color = self.colors['upgraded_glow']
            bg_color = self.colors['upgraded_bg']
            border_color = self.colors['upgraded']
        elif is_selected:
            glow_color = self.colors['selected_glow']
            bg_color = self.colors['option_selected_bg']
            border_color = self.colors['selected']
        else:
            glow_color = self.colors['title_glow']
            bg_color = self.colors['option_unselected_bg']
            border_color = self.colors['unselected']

        if is_selected or is_upgraded:
            for i in range(4, 0, -1):
                expand = i * 3
                glow_rect = box_rect.inflate(expand * 2, expand * 2)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*glow_color, 30 // i), glow_surf.get_rect(), border_radius=10)
                surface.blit(glow_surf, glow_rect)

        pygame.draw.rect(surface, bg_color, box_rect, border_radius=10)
        border_surf = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        alpha = 200 if is_selected or is_upgraded else 70
        width = 2 if is_selected or is_upgraded else 1
        pygame.draw.rect(border_surf, (*border_color, alpha),
                       border_surf.get_rect(), width=width, border_radius=10)
        surface.blit(border_surf, box_rect.topleft)

        arrow = ">" if is_selected else " "
        
        if is_upgraded:
            name_text = f"{arrow} {buff_name} [Lv.{level}]"
            text_color = self.colors['upgraded'] if is_selected else self.colors['unselected']
        else:
            name_text = f"{arrow} {buff_name}"
            text_color = self.colors['selected'] if is_selected else self.colors['unselected']
        
        text = self.option_font.render(name_text, True, text_color)
        text_rect = text.get_rect(midleft=(box_rect.x + 25, box_rect.centery - 8))
        surface.blit(text, text_rect)

        desc_color = self.colors['desc_selected'] if is_selected else self.colors['desc_unselected']
        desc = self.hint_font.render(option['desc'], True, desc_color)
        desc_rect = desc.get_rect(midleft=(box_rect.x + 35, box_rect.centery + 16))
        surface.blit(desc, desc_rect)

    def _draw_title(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        
        title_y = 130 + self.glow_offset * 0.5
        self._draw_glow_text(surface, "CHOOSE YOUR REWARD", self.title_font,
                           (width // 2, title_y), self.colors['title'], self.colors['title_glow'], 3)

    def _draw_bottom_hint(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        
        if (self.animation_time // 25) % 2 == 0:
            hint_color = (90, 100, 140)
        else:
            hint_color = (120, 130, 170)
        hint = self.hint_font.render("W / S to select   ENTER to confirm", True, hint_color)
        surface.blit(hint, hint.get_rect(center=(width // 2, height - 50)))

    def render(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        self._draw_gradient_background(surface)
        self._draw_stars(surface)
        self._draw_particles(surface)
        
        width, height = surface.get_size()
        
        self._draw_title(surface)
        self._draw_panel(surface)

        panel_width = 480
        panel_height = 320
        center_x = width // 2
        panel_y = height // 2 - panel_height // 2 + self.glow_offset * 0.3
        
        option_section_height = 80 * 3 + 15 * 2
        start_y = panel_y + (panel_height - option_section_height) // 2 + 10
        
        for i, option in enumerate(self.options):
            self._draw_option_item(surface, option, i, center_x, start_y, i == self.selected_index)

        self._draw_bottom_hint(surface)
