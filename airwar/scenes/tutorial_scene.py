import pygame
import math
import random
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
        
        self.base_panel_width = 700
        self.base_panel_height = 650
        self.base_title_y = 80
        self.base_section_start_y = 160
        self.base_section_gap = 140
        
        pygame.font.init()
        self._init_fonts(1.0)
        self._init_colors()
        
    def _init_fonts(self, scale: float) -> None:
        self.title_font = pygame.font.Font(None, ResponsiveHelper.font_size(90, scale))
        self.subtitle_font = pygame.font.Font(None, ResponsiveHelper.font_size(44, scale))
        self.section_title_font = pygame.font.Font(None, ResponsiveHelper.font_size(36, scale))
        self.content_font = pygame.font.Font(None, ResponsiveHelper.font_size(28, scale))
        self.key_font = pygame.font.Font(None, ResponsiveHelper.font_size(24, scale))
        self.button_font = pygame.font.Font(None, ResponsiveHelper.font_size(32, scale))
        self.hint_font = pygame.font.Font(None, ResponsiveHelper.font_size(26, scale))
        
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
            'section_bg': (20, 25, 50),
            'key_bg': (30, 35, 60),
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
        for _ in range(50):
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
        for _ in range(120):
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
            if event.key == pygame.K_ESCAPE:
                self.back_requested = True
                self.running = False
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.back_requested = True
                self.running = False
        elif event.type == pygame.MOUSEMOTION:
            self._handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.button_hover:
                self.back_requested = True
                self.running = False
                
    def _handle_mouse_motion(self, pos: tuple) -> None:
        width, height = pygame.display.get_surface().get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)
        
        panel_width = ResponsiveHelper.scale(self.base_panel_width, scale)
        panel_height = ResponsiveHelper.scale(self.base_panel_height, scale)
        panel_x = width // 2 - panel_width // 2
        panel_y = height // 2 - panel_height // 2
        
        btn_width = ResponsiveHelper.scale(240, scale)
        btn_height = ResponsiveHelper.scale(55, scale)
        btn_x = width // 2 - btn_width // 2
        btn_y = panel_y + panel_height - ResponsiveHelper.scale(100, scale)
        
        btn_rect = pygame.Rect(btn_x, btn_y, btn_width, btn_height)
        self.button_hover = btn_rect.collidepoint(pos)
        
    def update(self, *args, **kwargs) -> None:
        self.animation_time += 1
        self._update_particles()
        self._update_stars()
        
    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p['y'] -= p['speed'] * 0.003
            if p['y'] < -0.1:
                p['y'] = 1.1
                p['x'] = random.random()
                p['alpha'] = random.randint(80, 180)
                
    def _update_stars(self) -> None:
        for star in self.stars:
            star['y'] += star.get('speed', 0.008) * 0.008
            if star['y'] > 1:
                star['y'] = 0
                star['x'] = random.random()
                
    def render(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)
        self._init_fonts(scale)
        
        self._draw_background(surface)
        self._draw_stars(surface)
        self._draw_particles(surface)
        self._draw_panel(surface, width, height, scale)
        self._draw_title(surface, width, scale)
        self._draw_content_sections(surface, width, scale)
        self._draw_button(surface, width, scale)
        self._draw_hints(surface, width, scale)
        
    def _draw_background(self, surface: pygame.Surface) -> None:
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
            
    def _draw_panel(self, surface: pygame.Surface, width: int, height: int, scale: float) -> None:
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
        
    def _draw_title(self, surface: pygame.Surface, width: int, scale: float) -> None:
        title_y = ResponsiveHelper.scale(self.base_title_y, scale) + self.animation_time * 0.02
        
        title_glow_offset = math.sin(self.animation_time * 0.03) * 3
        
        for i in range(5, 0, -1):
            alpha = int(120 / i)
            glow_surf = self.title_font.render("AIR WAR", True, self.colors['title_glow'])
            glow_surf.set_alpha(alpha)
            glow_rect = glow_surf.get_rect(center=(width // 2, int(title_y + title_glow_offset + i)))
            surface.blit(glow_surf, glow_rect)
            
        main_title = self.title_font.render("AIR WAR", True, self.colors['title'])
        surface.blit(main_title, main_title.get_rect(center=(width // 2, int(title_y + title_glow_offset))))
        
        subtitle_y = title_y + ResponsiveHelper.scale(55, scale)
        subtitle = self.subtitle_font.render("TUTORIAL GUIDE", True, self.colors['title_glow'])
        surface.blit(subtitle, subtitle.get_rect(center=(width // 2, subtitle_y)))
        
    def _draw_content_sections(self, surface: pygame.Surface, width: int, scale: float) -> None:
        sections = [
            {
                'title': '🎮  BASIC CONTROLS',
                'items': [
                    ('↑ / W', 'Move Up'),
                    ('↓ / S', 'Move Down'),
                    ('← / A', 'Move Left'),
                    ('→ / D', 'Move Right'),
                    ('SPACE', 'Shoot (Auto-fire)'),
                ]
            },
            {
                'title': '🚀  MOTHER SHIP',
                'items': [
                    ('H (Hold)', 'Dock / Enter Mother Ship'),
                    ('-', 'Select power-ups inside'),
                    ('-', 'Hold H to take off'),
                ]
            },
            {
                'title': '⚠️  OTHER FUNCTIONS',
                'items': [
                    ('ESC', 'Pause Game'),
                    ('K (Hold 3s)', 'Give Up Game'),
                ]
            },
        ]
        
        start_y = ResponsiveHelper.scale(self.base_section_start_y, scale)
        section_gap = ResponsiveHelper.scale(self.base_section_gap, scale)
        
        for i, section in enumerate(sections):
            y_pos = start_y + i * section_gap
            self._draw_section(surface, width, scale, section['title'], section['items'], y_pos)
            
    def _draw_section(self, surface: pygame.Surface, width: int, scale: float, 
                     title: str, items: list, y_pos: int) -> None:
        section_width = ResponsiveHelper.scale(650, scale)
        section_x = width // 2 - section_width // 2
        
        title_y = y_pos
        title_surf = self.section_title_font.render(title, True, self.colors['title'])
        surface.blit(title_surf, (section_x + ResponsiveHelper.scale(10, scale), title_y))
        
        content_y = title_y + ResponsiveHelper.scale(45, scale)
        content_height = ResponsiveHelper.scale(100, scale)
        
        content_rect = pygame.Rect(section_x, content_y, section_width, content_height)
        pygame.draw.rect(surface, self.colors['section_bg'], content_rect, border_radius=8)
        border_surf = pygame.Surface((section_width, content_height), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*self.colors['panel_border'], 100),
                       border_surf.get_rect(), width=1, border_radius=8)
        surface.blit(border_surf, content_rect.topleft)
        
        item_y = content_y + ResponsiveHelper.scale(12, scale)
        item_gap = ResponsiveHelper.scale(22, scale)
        
        for j, (key, desc) in enumerate(items):
            if key != '-':
                self._draw_key_item(surface, section_x, item_y + j * item_gap, scale, key, desc)
            else:
                desc_surf = self.content_font.render(desc, True, self.colors['unselected'])
                surface.blit(desc_surf, (section_x + ResponsiveHelper.scale(30, scale), item_y + j * item_gap + 2))
                
    def _draw_key_item(self, surface: pygame.Surface, x: int, y: int, scale: float, 
                      key: str, desc: str) -> None:
        key_surf = self.key_font.render(key, True, self.colors['title'])
        key_width, key_height = key_surf.get_size()
        
        padding = ResponsiveHelper.scale(8, scale)
        box_width = key_width + padding * 2
        box_height = key_height + padding
        
        box_rect = pygame.Rect(x + ResponsiveHelper.scale(20, scale), y, box_width, box_height)
        pygame.draw.rect(surface, self.colors['key_bg'], box_rect, border_radius=4)
        border_surf = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*self.colors['panel_border'], 120),
                       border_surf.get_rect(), width=1, border_radius=4)
        surface.blit(border_surf, box_rect.topleft)
        
        surface.blit(key_surf, (box_rect.x + padding, box_rect.y + padding // 2))
        
        desc_surf = self.content_font.render(desc, True, self.colors['unselected'])
        surface.blit(desc_surf, (x + ResponsiveHelper.scale(130, scale), y + 2))
        
    def _draw_button(self, surface: pygame.Surface, width: int, scale: float) -> None:
        height = surface.get_height()
        panel_height = ResponsiveHelper.scale(self.base_panel_height, scale)
        panel_y = height // 2 - panel_height // 2
        
        btn_width = ResponsiveHelper.scale(240, scale)
        btn_height = ResponsiveHelper.scale(55, scale)
        btn_x = width // 2 - btn_width // 2
        btn_y = panel_y + panel_height - ResponsiveHelper.scale(100, scale)
        
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
        
        btn_text = self.button_font.render("BACK TO MENU", True, (245, 250, 255))
        surface.blit(btn_text, btn_text.get_rect(center=(btn_x + btn_width // 2, btn_y + btn_height // 2)))
        
    def _draw_hints(self, surface: pygame.Surface, width: int, scale: float) -> None:
        height = surface.get_height()
        hint_y = height - ResponsiveHelper.scale(50, scale)
        
        if (self.animation_time // 30) % 2 == 0:
            hint_color = (110, 110, 160)
        else:
            hint_color = (140, 140, 180)
            
        hints = self.hint_font.render("↑↓ Select    ENTER/ESC to Return", True, hint_color)
        surface.blit(hints, hints.get_rect(center=(width // 2, hint_y)))
        
    def is_back_requested(self) -> bool:
        return self.back_requested
        
    def is_ready(self) -> bool:
        return not self.running
        
    def is_running(self) -> bool:
        return self.running
