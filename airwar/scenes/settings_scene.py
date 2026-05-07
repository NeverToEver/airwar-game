"""Settings scene — configure control behavior per user account."""
import math
import pygame
from .scene import Scene
from airwar.utils.fonts import get_cjk_font
from airwar.utils.database import DatabaseError
from airwar.utils.responsive import ResponsiveHelper
from airwar.ui.menu_background import MenuBackground
from airwar.ui.particles import ParticleSystem
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.ui.scene_rendering_utils import fit_text_to_width
from airwar.config.design_tokens import get_design_tokens, SceneColors
from airwar.utils.mouse_interaction import MouseInteractiveMixin


class SettingsScene(Scene, MouseInteractiveMixin):
    """Settings screen for per-user control configuration.

    Allows the player to switch between hold and toggle mode for:
      - Ctrl (precision / slow-down mode)
      - Shift (boost acceleration mode)

    Phase dash behavior is unaffected by the shift boost setting.
    Settings are persisted to UserDB when a registered user is available.
    """

    PANEL_W = 500
    PANEL_H = 420
    CHAMFER = 12
    SETTING_ROW_H = 64
    TOGGLE_BTN_W = 120
    TOGGLE_BTN_H = 44
    SETTING_GAP = 16
    BACK_BTN_W = 160
    BACK_BTN_H = 46
    TITLE_HEIGHT = 80
    CONTENT_START_Y = 120
    BOTTOM_HINT_Y_OFFSET = 60

    LABEL_OPTIONS = {
        'ctrl_mode': ('Ctrl 减速', '按住', '点按'),
        'shift_boost_mode': ('Shift 加速', '按住', '点按'),
    }

    def __init__(self):
        Scene.__init__(self)
        MouseInteractiveMixin.__init__(self)
        self.running = False
        self._db = None
        self._username = None
        self._settings_ref = None
        self._focus_index = 0
        self._focus_count = 3  # ctrl, shift, back
        self._animation_time = 0
        self._message = ""
        self._message_timer = 0

    def enter(self, **kwargs) -> None:
        self.running = True
        self.clear_hover()
        self.clear_buttons()
        self._db = kwargs.get('db')
        self._username = kwargs.get('username')
        self._settings_ref = kwargs.get('settings_ref', {})
        self._focus_index = 0
        self._animation_time = 0
        self._message = ""
        self._message_timer = 0

        self._tokens = get_design_tokens()
        pygame.font.init()
        self.title_font = get_cjk_font(self._tokens.typography.TITLE_SIZE)
        self.section_font = get_cjk_font(self._tokens.typography.SUBHEADING_SIZE)
        self.body_font = get_cjk_font(self._tokens.typography.BODY_SIZE)
        self.hint_font = get_cjk_font(self._tokens.typography.SMALL_SIZE)
        self.tip_font = get_cjk_font(self._tokens.typography.TINY_SIZE)

        self._background = MenuBackground()
        self._particles = ParticleSystem()
        self._particles.reset(self._tokens.components.PARTICLE_COUNT, 'particle')

    def exit(self) -> None:
        pass

    def is_running(self) -> bool:
        return self.running

    # -- Event handling ---------------------------------------------------

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event)
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and self.handle_mouse_click(event.pos):
            btn = self.get_hovered_button()
            if btn:
                self._handle_button_click(btn)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            pass

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self.running = False
            return

        if event.key in (pygame.K_TAB, pygame.K_DOWN, pygame.K_s):
            self._focus_index = (self._focus_index + 1) % self._focus_count
        elif event.key in (pygame.K_UP, pygame.K_w):
            self._focus_index = (self._focus_index - 1) % self._focus_count
        elif event.key == pygame.K_RETURN:
            if self._focus_index == 2:
                self.running = False
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            if self._focus_index == 0:
                self._toggle_setting('ctrl_mode')
            elif self._focus_index == 1:
                self._toggle_setting('shift_boost_mode')

    def _handle_button_click(self, button_name: str) -> None:
        if button_name == 'back':
            self.running = False
        elif button_name == 'ctrl_hold':
            self._set_setting('ctrl_mode', 'hold')
        elif button_name == 'ctrl_toggle':
            self._set_setting('ctrl_mode', 'toggle')
        elif button_name == 'shift_hold':
            self._set_setting('shift_boost_mode', 'hold')
        elif button_name == 'shift_toggle':
            self._set_setting('shift_boost_mode', 'toggle')

    def _toggle_setting(self, key: str) -> None:
        current = self._settings_ref.get(key, 'hold')
        new_value = 'toggle' if current == 'hold' else 'hold'
        self._set_setting(key, new_value)

    def _set_setting(self, key: str, value: str) -> None:
        self._settings_ref[key] = value
        self._save_to_db()
        self._message = f"{self.LABEL_OPTIONS[key][0]}: {'点按' if value == 'toggle' else '按住'}"
        self._message_timer = 90

    def _save_to_db(self) -> None:
        if not self._db or not self._username:
            return
        try:
            if self._db.user_exists(self._username):
                self._db.update_user_settings(self._username, dict(self._settings_ref))
        except DatabaseError:
            pass

    # -- Update -------------------------------------------------------------

    def update(self, *args, **kwargs) -> None:
        self._animation_time += 1
        if self._message_timer > 0:
            self._message_timer -= 1
            if self._message_timer <= 0:
                self._message = ""
        self._background._animation_time = self._animation_time
        self._background.update()
        self._particles._animation_time = self._animation_time
        self._particles.update(direction=-1)

    # -- Render -------------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        SC = SceneColors
        sw, sh = surface.get_width(), surface.get_height()

        self._background.render_themed_style(surface, {
            'bg': SC.BG_PRIMARY,
            'bg_gradient': SC.BG_PANEL,
        })
        self._particles.render(surface, 'particle')

        self._render_title(surface, sw, sh)
        self._render_settings(surface, sw, sh)
        self._render_back_button(surface, sw, sh)
        self._render_hint(surface, sw, sh)

        if self._message:
            self._render_message(surface, sw, sh)

    def _render_title(self, surface: pygame.Surface, sw: int, sh: int) -> None:
        SC = SceneColors
        title_size = min(self._tokens.typography.TITLE_SIZE, max(56, sh // 10))
        font = get_cjk_font(title_size)
        ty = max(50, int(title_size * 0.7)) + math.sin(self._animation_time * 0.04) * 2

        for blur, alpha, color in [(4, 18, SC.GOLD_DIM), (2, 30, SC.GOLD_PRIMARY)]:
            glow = font.render("设置", True, color)
            glow.set_alpha(alpha)
            for ox in range(-blur, blur + 1, 2):
                for oy in range(-blur, blur + 1, 2):
                    if ox * ox + oy * oy <= blur * blur:
                        r = glow.get_rect(center=(sw // 2 + ox, int(ty) + oy))
                        surface.blit(glow, r)
        title = font.render("设置", True, SC.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=(sw // 2, int(ty))))

    def _render_settings(self, surface: pygame.Surface, sw: int, sh: int) -> None:
        SC = SceneColors
        panel_w = min(self.PANEL_W, sw - 40)
        panel_x = (sw - panel_w) // 2
        panel_y = 110

        draw_chamfered_panel(surface, panel_x, panel_y, panel_w, self.PANEL_H,
                             SC.BG_PANEL_LIGHT, SC.BORDER_DIM, SC.GOLD_GLOW, self.CHAMFER)

        keys = ['ctrl_mode', 'shift_boost_mode']
        row_start_y = panel_y + 40

        for i, key in enumerate(keys):
            y = row_start_y + i * (self.SETTING_ROW_H + self.SETTING_GAP)
            is_focused = (i == self._focus_index)
            self._draw_setting_row(surface, panel_x, panel_w, y, key, is_focused)

    def _draw_setting_row(self, surface: pygame.Surface, panel_x: int, panel_w: int,
                          y: int, key: str, is_focused: bool) -> None:
        SC = SceneColors
        current = self._settings_ref.get(key, 'hold')
        label, hold_text, toggle_text = self.LABEL_OPTIONS[key]

        # Draw row background if focused
        row_x = panel_x + 16
        row_w = panel_w - 32
        row_h = self.SETTING_ROW_H
        if is_focused:
            draw_chamfered_panel(surface, row_x - 4, y - 4, row_w + 8, row_h + 8,
                                 SC.BG_PANEL, SC.GOLD_GLOW, SC.GOLD_GLOW, 8)
        draw_chamfered_panel(surface, row_x, y, row_w, row_h,
                             SC.BG_PANEL if is_focused else SC.BG_PANEL_LIGHT,
                             SC.GOLD_PRIMARY if is_focused else SC.BORDER_DIM,
                             None, 6)

        # Label
        label_color = SC.GOLD_PRIMARY if is_focused else SC.TEXT_PRIMARY
        label_surf = self.body_font.render(label, True, label_color)
        label_x = row_x + 20
        label_y = y + (row_h - label_surf.get_height()) // 2
        surface.blit(label_surf, (label_x, label_y))

        # Toggle buttons
        btn_x = row_x + row_w - self.TOGGLE_BTN_W * 2 - 20
        btn_y = y + (row_h - self.TOGGLE_BTN_H) // 2
        btn_center_y = btn_y + self.TOGGLE_BTN_H // 2

        values = [('hold', hold_text), ('toggle', toggle_text)]
        for j, (val, text) in enumerate(values):
            bx = btn_x + j * (self.TOGGLE_BTN_W + 4)
            btn_name = f'{key.split("_")[0]}_{val}'
            btn_rect = pygame.Rect(bx, btn_y, self.TOGGLE_BTN_W, self.TOGGLE_BTN_H)
            self.register_button(btn_name, btn_rect)

            is_active = (current == val)
            hover = self.is_button_hovered(btn_name)

            fill = (40, 60, 70) if is_active else SC.BG_PANEL
            if hover and not is_active:
                fill = (50, 55, 65)
            border = SC.GOLD_PRIMARY if (is_active or hover) else SC.BORDER_DIM

            draw_chamfered_panel(surface, bx, btn_y, self.TOGGLE_BTN_W, self.TOGGLE_BTN_H,
                                 fill, border, None, 6)

            text_color = SC.TEXT_BRIGHT if is_active else SC.TEXT_DIM
            text_surf = fit_text_to_width(self.hint_font, text, text_color, self.TOGGLE_BTN_W - 16)
            surface.blit(text_surf, text_surf.get_rect(center=(bx + self.TOGGLE_BTN_W // 2, btn_center_y)))

    def _render_back_button(self, surface: pygame.Surface, sw: int, sh: int) -> None:
        SC = SceneColors
        scale = ResponsiveHelper.get_scale_factor(sw, sh)
        btn_w = ResponsiveHelper.scale(self.BACK_BTN_W, scale)
        btn_h = ResponsiveHelper.scale(self.BACK_BTN_H, scale)
        btn_x = (sw - btn_w) // 2
        btn_y = sh - 130

        is_focused = (self._focus_index == 2)
        self.register_button('back', pygame.Rect(btn_x, btn_y, btn_w, btn_h))
        hover = self.is_button_hovered('back')

        if is_focused or hover:
            draw_chamfered_panel(surface, btn_x - 4, btn_y - 4, btn_w + 8, btn_h + 8,
                                 SC.BG_PANEL, SC.GOLD_GLOW, SC.GOLD_GLOW, 8)

        draw_chamfered_panel(surface, btn_x, btn_y, btn_w, btn_h,
                             SC.BG_PANEL if (is_focused or hover) else SC.BG_PANEL_LIGHT,
                             SC.GOLD_PRIMARY if (is_focused or hover) else SC.BORDER_DIM,
                             None, 6)
        txt_color = SC.TEXT_PRIMARY if (is_focused or hover) else SC.TEXT_DIM
        txt_surf = fit_text_to_width(self.body_font, "返回", txt_color, btn_w - 24)
        surface.blit(txt_surf, txt_surf.get_rect(center=(btn_x + btn_w // 2, btn_y + btn_h // 2)))

    def _render_hint(self, surface: pygame.Surface, sw: int, sh: int) -> None:
        SC = SceneColors
        blink = (self._animation_time // 30) % 2 == 0
        color = SC.TEXT_DIM if blink else SC.TEXT_PRIMARY
        hints = "TAB: 切换  |  ← →: 更改  |  ENTER: 确认  |  ESC: 返回"
        hint_surf = self.hint_font.render(hints, True, color)
        surface.blit(hint_surf, hint_surf.get_rect(center=(sw // 2, sh - 50)))

    def _render_message(self, surface: pygame.Surface, sw: int, sh: int) -> None:
        SC = SceneColors
        msg_surf = self.tip_font.render(self._message, True, SC.FOREST_GREEN)
        surface.blit(msg_surf, msg_surf.get_rect(center=(sw // 2, 88)))
