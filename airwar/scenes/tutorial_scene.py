import pygame
import math
import random
import sys
from .scene import Scene
from airwar.utils.responsive import ResponsiveHelper


class TutorialScene(Scene):
    """Tutorial scene showing game controls guide"""

    def __init__(self):
        self.running = True
        self.back_requested = False
        self.animation_time = 0
        self.particles = []
        self.stars = []
        self.button_hover = False
        self._exit_callback = None
        
        self.base_panel_width = 500
        self.base_panel_height = 580
        self.base_option_height = 60
        self.base_option_gap = 8
        self.base_title_y = 80
        
        pygame.font.init()
        self._init_fonts(1.0)
        self._init_colors()
        
    def _init_fonts(self, scale: float) -> None:
        self.title_font = pygame.font.Font(None, ResponsiveHelper.font_size(80, scale))
        self.option_font = pygame.font.Font(None, ResponsiveHelper.font_size(self.base_option_height, scale))
        self.hint_font = pygame.font.Font(None, ResponsiveHelper.font_size(24, scale))
        self.desc_font = pygame.font.Font(None, ResponsiveHelper.font_size(22, scale))
        
    def _init_colors(self) -> None:
        self.colors = {
            'bg': (8, 8, 25),
            'bg_gradient': (15, 15, 50),
            'title': (255, 255, 255),
            'title_glow': (100, 200, 255),
            'selected': (0, 255, 150),
            'selected_glow': (0, 200, 255),
            'unselected': (90, 90, 130),
            'hint': (70, 70, 110),
            'particle': (100, 180, 255),
            'panel': (15, 20, 40),
            'panel_border': (50, 80, 140),
            'option_selected_bg': (25, 35, 65),
            'option_unselected_bg': (18, 20, 40),
        }
        
    def enter(self, **kwargs) -> None:
        self.running = True
        self.back_requested = False
        self.button_hover = False
        self.animation_time = 0
        self._init_particles()
        self._init_stars()
        
    def exit(self) -> None:
        pass
        
    def _init_particles(self) -> None:
        self.particles = []
        for _ in range(40):
            self.particles.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(1.5, 3.5),
                'speed': random.uniform(0.3, 0.9),
                'alpha': random.randint(80, 180),
                'pulse_speed': random.uniform(0.02, 0.05),
                'pulse_offset': random.random() * math.pi * 2,
            })
            
    def _init_stars(self) -> None:
        self.stars = []
        for _ in range(100):
            self.stars.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(0.5, 2.0),
                'brightness': random.randint(50, 150),
                'twinkle_speed': random.uniform(0.03, 0.08),
                'twinkle_offset': random.random() * math.pi * 2,
            })
            
    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            print(f"[TUTORIAL SCENE] KEYDOWN received: key={event.key}")
            if event.key == pygame.K_ESCAPE:
                print("[TUTORIAL SCENE] ESC pressed, setting running=False")
                self.back_requested = True
                self.running = False
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                print("[TUTORIAL SCENE] ENTER/SPACE pressed, setting running=False")
                self.back_requested = True
                self.running = False
        elif event.type == pygame.MOUSEMOTION:
            self._handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.button_hover:
                print("[TUTORIAL SCENE] Button clicked, setting running=False")
                self.back_requested = True
                self.running = False
                
    def _handle_mouse_motion(self, pos: tuple) -> None:
        width, height = pygame.display.get_surface().get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)
        
        panel_width = ResponsiveHelper.scale(self.base_panel_width, scale)
        panel_height = ResponsiveHelper.scale(self.base_panel_height, scale)
        panel_x = width // 2 - panel_width // 2
        panel_y = height // 2 - panel_height // 2
        
        btn_width = ResponsiveHelper.scale(280, scale)
        btn_height = ResponsiveHelper.scale(50, scale)
        btn_x = width // 2 - btn_width // 2
        btn_y = panel_y + panel_height - ResponsiveHelper.scale(60, scale)
        
        btn_rect = pygame.Rect(btn_x, btn_y, btn_width, btn_height)
        self.button_hover = btn_rect.collidepoint(pos)
        
    def update(self, *args, **kwargs) -> None:
        import random
        self.animation_time += 1
        
        for star in self.stars:
            star['y'] += star.get('speed', 0.008) * 0.008
            if star['y'] > 1:
                star['y'] = 0
                star['x'] = random.random()

        for p in self.particles[:]:
            p['y'] -= p['speed'] * 0.003
            if p['y'] < -0.1:
                p['y'] = 1.1
                p['x'] = random.random()
                p['alpha'] = random.randint(80, 180)
                
    def render(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)
        self._init_fonts(scale)
        
        self._draw_gradient_background(surface)
        self._draw_stars(surface)
        self._draw_particles(surface)
        self._draw_panel(surface)
        self._draw_title_section(surface)
        self._draw_content(surface)
        self._draw_button(surface)
        self._draw_bottom_hints(surface)
        
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
            
    def _draw_panel(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        panel_width = ResponsiveHelper.scale(self.base_panel_width, scale)
        panel_height = ResponsiveHelper.scale(self.base_panel_height, scale)
        panel_x = width // 2 - panel_width // 2
        panel_y = height // 2 - panel_height // 2

        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        for i in range(4, 0, -1):
            expand = i * 4
            glow_surf = pygame.Surface((panel_width + expand * 2, panel_height + expand * 2), pygame.SRCALPHA)
            alpha = max(5, 25 // i)
            pygame.draw.rect(glow_surf, (*self.colors['title_glow'], alpha),
                          glow_surf.get_rect(), border_radius=18)
            surface.blit(glow_surf, (panel_x - expand, panel_y - expand))

        pygame.draw.rect(surface, self.colors['panel'], panel_rect, border_radius=15)

        border_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*self.colors['panel_border'], 140),
                       border_surf.get_rect(), width=2, border_radius=15)
        surface.blit(border_surf, panel_rect.topleft)
            
    def _draw_glow_text(self, surface: pygame.Surface, text: str, font: pygame.font.Font,
                        pos: tuple, color: tuple, glow_color: tuple, glow_radius: int = 2) -> None:
        for i in range(glow_radius, 0, -1):
            alpha = int(120 / i)
            glow_surf = font.render(text, True, glow_color)
            glow_surf.set_alpha(alpha)
            glow_rect = glow_surf.get_rect(center=(pos[0], pos[1] + i))
            surface.blit(glow_surf, glow_rect)

        main_text = font.render(text, True, color)
        surface.blit(main_text, main_text.get_rect(center=pos))

    def _draw_title_section(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        title_y = ResponsiveHelper.scale(self.base_title_y, scale)
        title_text = "AIR WAR"
        self._draw_glow_text(surface, title_text, self.title_font,
                           (width // 2, title_y), self.colors['title'], self.colors['title_glow'], 5)

    def _draw_content(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        panel_width = ResponsiveHelper.scale(self.base_panel_width, scale)
        panel_height = ResponsiveHelper.scale(self.base_panel_height, scale)
        center_x = width // 2
        panel_y = height // 2 - panel_height // 2
        
        option_height = ResponsiveHelper.scale(self.base_option_height, scale)
        option_gap = ResponsiveHelper.scale(self.base_option_gap, scale)
        
        content_items = [
            ("CONTROLS", [
                ("W / UP", "Move Up"),
                ("S / DOWN", "Move Down"),
                ("A / LEFT", "Move Left"),
                ("D / RIGHT", "Move Right"),
                ("SPACE", "Shoot"),
            ]),
            ("MOTHER SHIP", [
                ("H (Hold)", "Dock / Enter"),
                ("H (Hold)", "Take Off"),
            ]),
            ("OTHER", [
                ("ESC", "Pause Game"),
                ("K (Hold 3s)", "Give Up"),
            ]),
        ]
        
        total_height = sum(len(items) * (option_height + option_gap) for _, items in content_items)
        total_height += len(content_items) * option_gap * 2
        
        start_y = panel_y + ResponsiveHelper.scale(110, scale)
        
        for section_idx, (section_title, items) in enumerate(content_items):
            section_y = start_y + section_idx * ResponsiveHelper.scale(50, scale)
            for item_idx, (key, desc) in enumerate(items):
                y_pos = section_y + item_idx * (option_height + option_gap)
                self._draw_option_item(surface, key, desc, center_x, y_pos, False, section_idx == 0 and item_idx == 0)
                
    def _draw_option_item(self, surface: pygame.Surface, key: str, desc: str,
                          center_x: int, y_pos: int, is_selected: bool, is_first: bool) -> None:
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        option_height = ResponsiveHelper.scale(self.base_option_height, scale)
        
        box_width = ResponsiveHelper.scale(440, scale)
        box_height = option_height
        box_rect = pygame.Rect(center_x - box_width // 2, y_pos, box_width, box_height)

        if is_first:
            pygame.draw.rect(surface, self.colors['option_selected_bg'], box_rect, border_radius=10)
            border_surf = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
            pygame.draw.rect(border_surf, (*self.colors['selected'], 200),
                           border_surf.get_rect(), width=2, border_radius=10)
            surface.blit(border_surf, box_rect.topleft)
        else:
            pygame.draw.rect(surface, self.colors['option_unselected_bg'], box_rect, border_radius=10)
            border_surf = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
            pygame.draw.rect(border_surf, (*self.colors['unselected'], 80),
                           border_surf.get_rect(), width=1, border_radius=10)
            surface.blit(border_surf, box_rect.topleft)

        text_color = self.colors['selected'] if is_first else self.colors['unselected']
        key_text = self.option_font.render(f"{key}", True, self.colors['title'])
        desc_text = self.desc_font.render(f"{desc}", True, text_color)
        surface.blit(key_text, key_text.get_rect(midleft=(box_rect.x + 20, box_rect.centery)))
        surface.blit(desc_text, desc_text.get_rect(midright=(box_rect.right - 20, box_rect.centery)))
        
    def _draw_button(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        panel_height = ResponsiveHelper.scale(self.base_panel_height, scale)
        panel_y = height // 2 - panel_height // 2

        btn_width = ResponsiveHelper.scale(280, scale)
        btn_height = ResponsiveHelper.scale(50, scale)
        btn_x = width // 2 - btn_width // 2
        btn_y = panel_y + panel_height - ResponsiveHelper.scale(60, scale)

        btn_color = tuple(min(c + 25, 255) for c in (20, 50, 100)) if self.button_hover else (20, 50, 100)

        if self.button_hover:
            for i in range(4, 0, -1):
                expand = i * 3
                glow_surf = pygame.Surface((btn_width + expand * 2, btn_height + expand * 2), pygame.SRCALPHA)
                alpha = max(3, 20 // i)
                pygame.draw.rect(glow_surf, (*self.colors['title_glow'], alpha),
                               glow_surf.get_rect(), border_radius=12)
                surface.blit(glow_surf, (btn_x - expand, btn_y - expand))

        btn_rect = pygame.Rect(btn_x, btn_y, btn_width, btn_height)
        pygame.draw.rect(surface, btn_color, btn_rect, border_radius=10)

        border_surf = pygame.Surface((btn_width, btn_height), pygame.SRCALPHA)
        border_color = self.colors['title'] if self.button_hover else self.colors['title_glow']
        pygame.draw.rect(border_surf, (*border_color, 160),
                       border_surf.get_rect(), width=2, border_radius=10)
        surface.blit(border_surf, btn_rect.topleft)

        btn_text = self.hint_font.render("BACK TO MENU", True, (245, 250, 255))
        surface.blit(btn_text, btn_text.get_rect(center=(btn_x + btn_width // 2, btn_y + btn_height // 2)))
        
    def _draw_bottom_hints(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        if (self.animation_time // 30) % 2 == 0:
            hint_color = (110, 110, 160)
        else:
            hint_color = (140, 140, 180)
        start_text = self.hint_font.render("ESC / ENTER / SPACE to return", True, hint_color)
        surface.blit(start_text, start_text.get_rect(center=(width // 2, height - ResponsiveHelper.scale(30, scale))))
        
    def is_back_requested(self) -> bool:
        return self.back_requested
        
    def is_ready(self) -> bool:
        return not self.running
        
    def is_running(self) -> bool:
        print(f"[TUTORIAL SCENE] is_running() called, returning={self.running}")
        return self.running
