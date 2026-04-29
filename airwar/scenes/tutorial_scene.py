"""Tutorial scene -- multi-page military-cockpit themed control reference."""
import math
import pygame
from .scene import Scene
from airwar.config.design_tokens import get_design_tokens
from airwar.config.tutorial import TUTORIAL_PAGES
from airwar.ui.menu_background import MenuBackground
from airwar.ui.particles import ParticleSystem
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.utils.mouse_interaction import MouseInteractiveMixin


class TutorialScene(Scene, MouseInteractiveMixin):
    """Multi-page tutorial with chamfered military-cockpit visual style.

    Navigation:
      - Keyboard: <- -> / ^ v to flip pages, ESC to exit
      - Mouse: click PREV / NEXT / BACK TO MENU buttons
      - Last page shows BACK TO MENU instead of NEXT
    """

    PANEL_W = 820
    PANEL_H = 620
    CHAMFER = 12
    BTN_W = 180
    BTN_H = 48

    def __init__(self):
        Scene.__init__(self)
        MouseInteractiveMixin.__init__(self)
        self._tokens = get_design_tokens()
        self._SceneColors = self._tokens.scene
        self._Typography = self._tokens.typography
        self._background = MenuBackground()
        self._particles = ParticleSystem()
        self._current_page = 0
        self._total_pages = len(TUTORIAL_PAGES)
        self._exit_requested = False
        self._anim_time = 0
        self._hover_scale = {  # per-button lerp state
            'prev': 1.0, 'next': 1.0, 'back': 1.0, 'close': 1.0,
        }
        self._click_decay = {}  # per-button click animation
        self._mouse_pos = (0, 0)
        self._fonts: dict = {}

    # -- Scene lifecycle ------------------------------------------------------

    def enter(self, **kwargs) -> None:
        self.clear_hover()
        self.clear_buttons()
        self._current_page = 0
        self._exit_requested = False
        self._anim_time = 0
        self._hover_scale = {k: 1.0 for k in self._hover_scale}
        self._click_decay.clear()
        self._mouse_pos = (0, 0)
        self._particles.reset(self._tokens.components.PARTICLE_COUNT, 'particle')

    def exit(self) -> None:
        pass

    def reset(self) -> None:
        self.enter()

    # -- Event handling -------------------------------------------------------

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event)
        elif event.type == pygame.MOUSEMOTION:
            self._mouse_pos = event.pos
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._mouse_pos = event.pos
                if self.handle_mouse_click(event.pos):
                    self._handle_button_click(self.get_hovered_button())

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self._request_exit()
        elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
            self._page_next()
        elif event.key in (pygame.K_LEFT, pygame.K_UP):
            self._page_prev()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self._current_page == self._total_pages - 1:
                self._request_exit()

    def _handle_button_click(self, button_name: str) -> None:
        if button_name == 'prev':
            self._page_prev()
        elif button_name == 'next':
            self._page_next()
        elif button_name == 'back':
            self._request_exit()
        elif button_name == 'close':
            self._request_exit()

    def _page_next(self) -> None:
        if self._current_page < self._total_pages - 1:
            self._current_page += 1

    def _page_prev(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1

    def _request_exit(self) -> None:
        self._exit_requested = True

    # -- Update ---------------------------------------------------------------

    def update(self, *args, **kwargs) -> None:
        self._anim_time += 1
        self._background._animation_time = self._anim_time
        self._background.update()
        self._particles._animation_time = self._anim_time
        self._particles.update(direction=-1)

        # Button hover scale lerp
        for btn, target in self._compute_button_hover_targets():
            cur = self._hover_scale[btn]
            self._hover_scale[btn] = cur + (target - cur) * 0.15

        # Click decay
        for btn in list(self._click_decay):
            self._click_decay[btn] *= 0.82
            if self._click_decay[btn] < 0.01:
                del self._click_decay[btn]

    def _compute_button_hover_targets(self):
        """Yield (button_name, target_scale) for each visible button."""
        surf = pygame.display.get_surface()
        if surf is None:
            return
        screen_w = surf.get_width()
        screen_h = surf.get_height()
        cx = screen_w // 2
        panel_bottom = (screen_h + self.PANEL_H) // 2

        btn_y = panel_bottom + 24
        # PREV button
        prev_rect = pygame.Rect(
            cx - self.BTN_W - 30, btn_y, self.BTN_W, self.BTN_H)
        yield ('prev', 1.08 if prev_rect.collidepoint(self._mouse_pos) else 1.0)

        if self._current_page < self._total_pages - 1:
            next_rect = pygame.Rect(
                cx + 30, btn_y, self.BTN_W, self.BTN_H)
            yield ('next', 1.08 if next_rect.collidepoint(self._mouse_pos) else 1.0)
        else:
            back_rect = pygame.Rect(
                cx + 30, btn_y, self.BTN_W, self.BTN_H)
            yield ('back', 1.08 if back_rect.collidepoint(self._mouse_pos) else 1.0)

    # -- Render ---------------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        SC = self._SceneColors
        screen_w, screen_h = surface.get_width(), surface.get_height()

        # 1. Background
        self._background.render_themed_style(surface, {
            'bg': (6, 8, 14),
            'bg_gradient': (12, 15, 22),
        })

        # 2. Particles
        self._particles.render(surface, 'particle')

        # 3. Central chamfered panel
        px = (screen_w - self.PANEL_W) // 2
        py = (screen_h - self.PANEL_H) // 2 - 10
        draw_chamfered_panel(
            surface, px, py, self.PANEL_W, self.PANEL_H,
            (12, 15, 22),
            (80, 130, 170, 70),
            (140, 170, 210, 25),
            self.CHAMFER,
        )

        # 4. Title + subtitle
        page = TUTORIAL_PAGES[self._current_page]
        self._render_page_title(surface, page, px, py, screen_w)

        # 5. Section cards (2-column grid)
        self._render_page_sections(surface, page, px, py, screen_w)

        # 6. Page indicator dots
        self._render_page_dots(surface, px, py, screen_w)

        # 7. Navigation buttons
        self._render_nav_buttons(surface, px, py, screen_w, screen_h)

    def _render_page_title(self, surface, page, px, py, screen_w):
        SC = self._SceneColors
        T = self._Typography

        title_font = self._get_font(T.SUBHEADING_SIZE)
        sub_font = self._get_font(T.SMALL_SIZE)
        title_text = page['title']

        tx = screen_w // 2
        ty = py + 48

        # Multi-layer glow offset
        glow_color = (140, 170, 210)
        for blur in (4, 2):
            alpha = 60 if blur == 4 else 120
            glow_surf = title_font.render(title_text, True, glow_color)
            glow_surf.set_alpha(alpha)
            for ox in range(-blur, blur + 1, 2):
                for oy in range(-blur, blur + 1, 2):
                    if ox * ox + oy * oy <= blur * blur:
                        r = glow_surf.get_rect(center=(tx + ox, ty + oy))
                        surface.blit(glow_surf, r)

        # Main title
        main_surf = title_font.render(title_text, True, SC.TEXT_PRIMARY)
        surface.blit(main_surf, main_surf.get_rect(center=(tx, ty)))

        # Subtitle
        if page.get('subtitle'):
            sub_surf = sub_font.render(page['subtitle'], True, SC.TEXT_DIM)
            surface.blit(sub_surf, sub_surf.get_rect(center=(tx, ty + 30)))

    def _render_page_sections(self, surface, page, px, py, screen_w):
        SC = self._SceneColors
        sections = page['sections']
        n = len(sections)

        if n == 0:
            return

        # 2-column layout
        cols = 2
        rows = (n + cols - 1) // cols
        card_w = (self.PANEL_W - 60) // cols
        card_h = 280 if rows > 1 else 340
        start_y = py + 120

        for i, sec in enumerate(sections):
            col = i % cols
            row = i // cols
            cx = px + 20 + col * (card_w + 20)
            cy = start_y + row * (card_h + 16)

            # Section card background
            draw_chamfered_panel(
                surface, cx, cy, card_w, card_h,
                SC.BG_PANEL_LIGHT,
                SC.BORDER_TEAL,
                None,
                8,
            )

            # Section title
            title_font = self._get_font(self._Typography.CAPTION_SIZE)
            title_surf = title_font.render(sec['title'], True, SC.TEXT_PRIMARY)
            surface.blit(title_surf, title_surf.get_rect(
                center=(cx + card_w // 2, cy + 22)))

            # Separator line
            line_y = cy + 44
            pygame.draw.line(surface, (*SC.BORDER_TEAL[:3], 60),
                             (cx + 20, line_y), (cx + card_w - 20, line_y), 1)

            # Items
            item_font = self._get_font(self._Typography.TINY_SIZE)
            item_start_y = cy + 56
            item_h = (card_h - 70) // max(len(sec['items']), 1)

            for j, (key, desc) in enumerate(sec['items']):
                iy = item_start_y + j * item_h

                # Key text (left-aligned, accent color)
                key_surf = item_font.render(key, True, SC.ACCENT_PRIMARY)
                surface.blit(key_surf, (cx + 16, iy))

                # Desc text (right-aligned, muted)
                desc_surf = item_font.render(desc, True, SC.TEXT_DIM)
                surface.blit(desc_surf, (cx + card_w - desc_surf.get_width() - 16, iy))

    def _render_page_dots(self, surface, px, py, screen_w):
        SC = self._SceneColors
        dot_r = 5
        dot_gap = 16
        total_w = self._total_pages * dot_r * 2 + (self._total_pages - 1) * dot_gap
        start_x = screen_w // 2 - total_w // 2
        dot_y = py + self.PANEL_H - 36

        for i in range(self._total_pages):
            dx = start_x + i * (dot_r * 2 + dot_gap)
            if i == self._current_page:
                color = SC.GOLD_PRIMARY
                r = dot_r + 1
            else:
                color = SC.HINT_DIM
                r = dot_r
            pygame.draw.circle(surface, color, (dx + r, dot_y), r)

    def _render_nav_buttons(self, surface, px, py, screen_w, screen_h):
        SC = self._SceneColors
        cx = screen_w // 2
        panel_bottom = py + self.PANEL_H
        btn_y = panel_bottom + 24

        # Register buttons for mouse interaction
        self.clear_buttons()

        # PREV button (if not first page)
        prev_rect = None
        if self._current_page > 0:
            prev_rect = pygame.Rect(
                cx - self.BTN_W - 30, btn_y, self.BTN_W, self.BTN_H)
            self._render_chamfered_button(
                surface, prev_rect, '<-- PREV', 'prev')
            self.register_button('prev', prev_rect)

        # NEXT or BACK TO MENU button
        if self._current_page < self._total_pages - 1:
            next_rect = pygame.Rect(
                cx + 30, btn_y, self.BTN_W, self.BTN_H)
            self._render_chamfered_button(
                surface, next_rect, 'NEXT -->', 'next')
            self.register_button('next', next_rect)
        else:
            back_rect = pygame.Rect(
                cx + 30, btn_y, self.BTN_W + 40, self.BTN_H)
            self._render_chamfered_button(
                surface, back_rect, 'BACK TO MENU', 'back',
                accent=True)
            self.register_button('back', back_rect)

        # Close hint
        hint_font = self._get_font(18)
        blink = (self._anim_time // 25) % 2 == 0
        hint_color = SC.HINT_DIM if blink else SC.TEXT_DIM
        hint_surf = hint_font.render(
            'Press Left/Right to navigate  |  ESC to close', True, hint_color)
        surface.blit(hint_surf, hint_surf.get_rect(
            center=(cx, panel_bottom + 72)))

    def _render_chamfered_button(self, surface, rect, label, btn_key,
                                  accent=False):
        SC = self._SceneColors
        scale = self._hover_scale.get(btn_key, 1.0)
        click_s = self._click_decay.get(btn_key, 0.0)
        final_scale = scale + click_s * 0.05

        w, h = int(rect.width * final_scale), int(rect.height * final_scale)
        dx = (w - rect.width) // 2
        dy = (h - rect.height) // 2

        is_hovered = scale > 1.01
        bg = SC.FOREST_GREEN if is_hovered and accent else \
            (SC.GOLD_PRIMARY if is_hovered else SC.BG_PANEL_LIGHT)
        border = SC.BORDER_TEAL if is_hovered else SC.BORDER_GLOW

        draw_chamfered_panel(
            surface, rect.x - dx, rect.y - dy, w, h,
            bg, border,
            (SC.GOLD_GLOW if is_hovered else None),
            8,
        )

        font = self._get_font(self._Typography.SMALL_SIZE)
        text_surf = font.render(label, True,
                                SC.TEXT_PRIMARY if is_hovered else SC.TEXT_DIM)
        surface.blit(text_surf, text_surf.get_rect(
            center=(rect.centerx, rect.centery)))

    # -- Helpers --------------------------------------------------------------

    def _get_font(self, size: int) -> pygame.font.Font:
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def is_running(self) -> bool:
        return not self._exit_requested

    def is_ready(self) -> bool:
        return self._exit_requested

    def should_quit(self) -> bool:
        return self._exit_requested
