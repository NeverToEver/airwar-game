import pygame


class EffectsRenderer:
    """特效渲染器 — 负责发光文字等视觉效果"""

    def __init__(self):
        self._glow_cache = {}

    def render_glow_text(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        pos: tuple,
        color: tuple,
        glow_color: tuple,
        glow_radius: int = 3
    ):
        """渲染发光文字"""
        for i in range(glow_radius, 0, -1):
            alpha = int(100 / i)
            glow_surf = font.render(text, True, glow_color)
            glow_surf.set_alpha(alpha)
            glow_rect = glow_surf.get_rect(center=(pos[0], pos[1] + i))
            surface.blit(glow_surf, glow_rect)

        main_text = font.render(text, True, color)
        surface.blit(main_text, main_text.get_rect(center=pos))

    def render_option_box(
        self,
        surface: pygame.Surface,
        text: str,
        y: int,
        is_selected: bool,
        colors: dict,
        option_width: int = 350,
        option_height: int = 60,
        scale: float = 1.0
    ):
        """渲染选项框"""
        from airwar.utils.responsive import ResponsiveHelper

        width = surface.get_width()
        center_x = width // 2

        box_width = ResponsiveHelper.scale(option_width, scale)
        box_height = ResponsiveHelper.scale(option_height, scale)
        box_rect = pygame.Rect(center_x - box_width // 2, y - box_height // 2, box_width, box_height)

        if is_selected:
            glow_color = colors.get('selected_glow', (0, 200, 255))
            for i in range(4, 0, -1):
                glow_rect = box_rect.inflate(i * 4, i * 4)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*glow_color, 50 // i), glow_surf.get_rect())
                surface.blit(glow_surf, glow_rect)

            pygame.draw.rect(surface, (25, 35, 65), box_rect, border_radius=12)
            pygame.draw.rect(surface, colors.get('selected', (0, 255, 150)), box_rect, 3, border_radius=12)
        else:
            pygame.draw.rect(surface, (18, 20, 40), box_rect, border_radius=12)
            pygame.draw.rect(surface, colors.get('unselected', (90, 90, 130)), box_rect, 2, border_radius=12)

        arrow = ">> " if is_selected else "   "
        option_text = pygame.font.Font(None, 48).render(f"{arrow}{text}", True,
            colors.get('selected', (0, 255, 150)) if is_selected else colors.get('unselected', (90, 90, 130)))
        text_rect = option_text.get_rect(center=(center_x, y))
        surface.blit(option_text, text_rect)
