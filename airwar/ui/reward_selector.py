import pygame
import math
from typing import List, Callable, Optional
from airwar.utils.mouse_interaction import MouseSelectableMixin
from airwar.config.design_tokens import ForestColors, MilitaryUI
from airwar.ui.chamfered_panel import draw_chamfered_panel


class RewardSelector(MouseSelectableMixin):
    def __init__(self):
        MouseSelectableMixin.__init__(self)
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
        self._gradient_cache: Optional[pygame.Surface] = None
        self._gradient_cache_size: tuple = (0, 0)
        self._init_visual_elements()

    def _init_visual_elements(self) -> None:
        from airwar.config.design_tokens import get_design_tokens
        import random

        self._tokens = get_design_tokens()
        tokens = self._tokens
        colors = tokens.colors
        self.use_military_style = True

        self.stars = []
        for _ in range(80):
            self.stars.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(0.5, 2.0),
                'brightness': random.randint(50, 150),
                'twinkle_speed': random.uniform(tokens.animation.TWINKLE_SPEED_MIN, tokens.animation.TWINKLE_SPEED_MAX),
                'twinkle_offset': random.random() * math.pi * 2,
            })

        self.particles = []
        for _ in range(30):
            self.particles.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(1.5, 3.0),
                'speed': random.uniform(tokens.animation.PARTICLE_SPEED_MIN * 0.5, tokens.animation.PARTICLE_SPEED_MAX * 0.6),
                'alpha': random.randint(80, 150),
                'pulse_speed': random.uniform(0.02, 0.05),
                'pulse_offset': random.random() * math.pi * 2,
            })

        pygame.font.init()
        self.title_font = pygame.font.Font(None, tokens.typography.SUBHEADING_SIZE)
        self.option_font = pygame.font.Font(None, tokens.typography.BODY_SIZE)
        self.hint_font = pygame.font.Font(None, tokens.typography.SMALL_SIZE)

        self.colors = {
            'bg': colors.BACKGROUND_PRIMARY,
            'bg_gradient': colors.BACKGROUND_SECONDARY,
            'title': colors.TEXT_PRIMARY,
            'title_glow': colors.HUD_AMBER_BRIGHT,
            'selected': colors.HUD_AMBER,
            'selected_glow': colors.HUD_AMBER_BRIGHT,
            'unselected': colors.TEXT_MUTED,
            'desc_selected': (140, 200, 140),
            'desc_unselected': (80, 85, 120),
            'hint': colors.TEXT_HINT,
            'particle': colors.PARTICLE_PRIMARY,
            'panel': colors.BACKGROUND_PANEL,
            'panel_border': colors.PANEL_BORDER,
            'option_selected_bg': colors.BUTTON_SELECTED_BG,
            'option_unselected_bg': colors.BUTTON_UNSELECTED_BG,
            'upgraded': colors.BUTTON_SELECTED_GLOW,
            'upgraded_glow': colors.HUD_AMBER_BRIGHT,
            'new_buff': colors.SUCCESS,
            'upgraded_bg': colors.BUTTON_SELECTED_BG,
        }

        self._init_military_colors()

    def _init_military_colors(self) -> None:
        self.military_colors = {
            'bg': ForestColors.BG_PRIMARY,
            'bg_gradient': ForestColors.BG_PANEL,
            'title': ForestColors.TEXT_PRIMARY,
            'title_glow': ForestColors.GOLD_GLOW,
            'selected': ForestColors.GOLD_PRIMARY,
            'selected_glow': ForestColors.GOLD_BRIGHT,
            'unselected': ForestColors.TEXT_DIM,
            'desc_selected': ForestColors.FOREST_GREEN,
            'desc_unselected': ForestColors.TEXT_DIM,
            'hint': ForestColors.TEXT_DIM,
            'particle': ForestColors.GOLD_PRIMARY,
            'panel': ForestColors.BG_PANEL,
            'panel_border': ForestColors.BORDER_GLOW,
            'option_selected_bg': ForestColors.BG_PANEL,
            'option_unselected_bg': ForestColors.BG_PANEL_LIGHT,
            'upgraded': ForestColors.GOLD_BRIGHT,
            'upgraded_glow': ForestColors.GOLD_GLOW,
            'new_buff': ForestColors.FOREST_GREEN,
            'upgraded_bg': ForestColors.BG_PANEL,
        }

    def generate_options(self, boss_kill_count: int, unlocked_buffs: list) -> list:
        from airwar.game.systems.reward_system import REWARD_POOL
        import random
        options = []
        categories = list(REWARD_POOL.keys())

        for _ in range(3):
            cat = random.choice(categories)
            rewards = REWARD_POOL[cat]

            if cat == 'offense' and boss_kill_count < 2:
                rewards = [r for r in rewards if r['name'] not in ['Explosive']]

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
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.handle_mouse_click(event.pos):
                self._confirm_selection()

    def _confirm_selection(self) -> None:
        if self.on_select and self.options:
            selected = self.options[self.selected_index]
            self.on_select(selected)
        self.hide()

    def update(self) -> None:
        if self.visible:
            self.animation_time += 1
            self.glow_offset = math.sin(self.animation_time * self._tokens.animation.GLOW_SPEED) * 8
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
        size = (width, height)
        if self._gradient_cache is None or self._gradient_cache_size != size:
            self._gradient_cache = pygame.Surface((width, height))
            for y in range(height):
                ratio = y / height
                r = int(self.colors['bg'][0] * (1 - ratio) + self.colors['bg_gradient'][0] * ratio)
                g = int(self.colors['bg'][1] * (1 - ratio) + self.colors['bg_gradient'][1] * ratio)
                b = int(self.colors['bg'][2] * (1 - ratio) + self.colors['bg_gradient'][2] * ratio)
                pygame.draw.line(self._gradient_cache, (r, g, b), (0, y), (width, y))
            self._gradient_cache_size = size
        surface.blit(self._gradient_cache, (0, 0))

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
        self.append_option_rect(box_rect)

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

        if self.use_military_style:
            if (self.animation_time // 25) % 2 == 0:
                hint_color = ForestColors.TEXT_DIM
            else:
                hint_color = ForestColors.TEXT_PRIMARY
            hint = self.hint_font.render("Click or W/S to select, ENTER to confirm", True, hint_color)
        else:
            if (self.animation_time // 25) % 2 == 0:
                hint_color = (90, 100, 140)
            else:
                hint_color = (120, 130, 170)
            hint = self.hint_font.render("Click or W/S to select, ENTER to confirm", True, hint_color)
        surface.blit(hint, hint.get_rect(center=(width // 2, height - 50)))

    def render(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        if self.use_military_style:
            self._draw_military_background(surface)
        else:
            self._draw_gradient_background(surface)
        self._draw_stars(surface)
        self._draw_particles(surface)

        width, height = surface.get_size()

        if self.use_military_style:
            self._draw_military_title(surface)
        else:
            self._draw_title(surface)

        if self.use_military_style:
            self._draw_military_panel(surface)
        else:
            self._draw_panel(surface)

        panel_width = 480
        panel_height = 320
        center_x = width // 2
        panel_y = height // 2 - panel_height // 2 + self.glow_offset * 0.3

        option_section_height = 80 * 3 + 15 * 2
        start_y = panel_y + (panel_height - option_section_height) // 2 + 10

        self.clear_option_rects()
        effective_index = self.get_effective_selected_index(self.selected_index)
        for i, option in enumerate(self.options):
            if self.use_military_style:
                self._draw_military_option_item(surface, option, i, center_x, start_y, i == effective_index)
            else:
                self._draw_option_item(surface, option, i, center_x, start_y, i == effective_index)

        self._draw_bottom_hint(surface)

    def _draw_military_background(self, surface: pygame.Surface) -> None:
        """Draw military style background with grid effect."""
        width, height = surface.get_size()
        # Fill with primary background
        surface.fill(ForestColors.BG_PRIMARY)

        # Draw grid overlay
        spacing = MilitaryUI.GRID_SPACING
        alpha = MilitaryUI.GRID_ALPHA
        grid_color = (*ForestColors.GOLD_PRIMARY[:3], alpha)

        for x in range(0, width, spacing):
            pygame.draw.line(surface, grid_color, (x, 0), (x, height))
        for y in range(0, height, spacing):
            pygame.draw.line(surface, grid_color, (0, y), (width, y))

    def _draw_military_title(self, surface: pygame.Surface) -> None:
        """Draw title in military style."""
        width, height = surface.get_size()
        title_y = 130 + self.glow_offset * 0.5
        title_text = "CHOOSE YOUR REWARD"

        for blur, alpha, color in [(3, 15, ForestColors.GOLD_DIM), (2, 25, ForestColors.GOLD_PRIMARY)]:
            glow_surf = self.title_font.render(title_text, True, color)
            glow_surf.set_alpha(alpha)
            for offset_x in range(-blur, blur + 1, 2):
                for offset_y in range(-blur, blur + 1, 2):
                    if offset_x * offset_x + offset_y * offset_y <= blur * blur:
                        glow_rect = glow_surf.get_rect(center=(width // 2 + offset_x, title_y + offset_y))
                        surface.blit(glow_surf, glow_rect)

        title = self.title_font.render(title_text, True, ForestColors.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=(width // 2, title_y)))

    def _draw_military_panel(self, surface: pygame.Surface) -> None:
        """Draw panel in military style with chamfered corners."""
        width, height = surface.get_size()

        panel_width = 500
        panel_height = 340
        panel_x = width // 2 - panel_width // 2
        panel_y = height // 2 - panel_height // 2 + self.glow_offset * 0.3

        # Draw chamfered panel with glow
        draw_chamfered_panel(
            surface,
            panel_x, panel_y,
            panel_width, panel_height,
            ForestColors.BG_PANEL,
            ForestColors.BORDER_GLOW,
            ForestColors.GOLD_GLOW,
            MilitaryUI.CHAMFER_DEPTH
        )

    def _draw_military_option_item(self, surface: pygame.Surface, option: dict, index: int,
                          center_x: int, start_y: int, is_selected: bool) -> None:
        """Draw option item in military style with chamfered corners."""
        option_height = 80
        option_gap = 15
        y = start_y + index * (option_height + option_gap)

        box_width = 460
        box_height = option_height
        box_rect = pygame.Rect(center_x - box_width // 2, y, box_width, box_height)
        self.append_option_rect(box_rect)

        buff_name = option['name']
        level = self.buff_levels.get(buff_name, 0)
        is_upgraded = buff_name in self.unlocked_buffs and level > 0

        if is_upgraded:
            glow_color = ForestColors.GOLD_GLOW
        elif is_selected:
            glow_color = ForestColors.GOLD_GLOW
        else:
            glow_color = None

        # Draw glow for selected/upgraded
        if glow_color:
            draw_chamfered_panel(
                surface,
                box_rect.x - 3, box_rect.y - 3,
                box_width + 6, box_height + 6,
                ForestColors.BG_PANEL,
                glow_color,
                glow_color,
                10
            )

        # Draw chamfered box
        if is_upgraded:
            bg_color = ForestColors.BG_PANEL
            border_color = ForestColors.GOLD_BRIGHT
        elif is_selected:
            bg_color = ForestColors.BG_PANEL
            border_color = ForestColors.GOLD_PRIMARY
        else:
            bg_color = ForestColors.BG_PANEL_LIGHT
            border_color = ForestColors.BORDER_DIM

        draw_chamfered_panel(
            surface,
            box_rect.x, box_rect.y,
            box_width, box_height,
            bg_color,
            border_color,
            None,
            8
        )

        arrow = ">" if is_selected else " "

        if is_upgraded:
            name_text = f"{arrow} {buff_name} [Lv.{level}]"
            text_color = ForestColors.GOLD_BRIGHT if is_selected else ForestColors.TEXT_DIM
        else:
            name_text = f"{arrow} {buff_name}"
            text_color = ForestColors.GOLD_PRIMARY if is_selected else ForestColors.TEXT_DIM

        text = self.option_font.render(name_text, True, text_color)
        text_rect = text.get_rect(midleft=(box_rect.x + 25, box_rect.centery - 8))
        surface.blit(text, text_rect)

        desc_color = ForestColors.FOREST_GREEN if is_selected else ForestColors.TEXT_DIM
        desc = self.hint_font.render(option['desc'], True, desc_color)
        desc_rect = desc.get_rect(midleft=(box_rect.x + 35, box_rect.centery + 16))
        surface.blit(desc, desc_rect)
