import pygame
import math
from .scene import Scene
from airwar.utils.responsive import ResponsiveHelper
from airwar.ui.menu_background import MenuBackground
from airwar.ui.particles import ParticleSystem
from airwar.ui.effects import EffectsRenderer
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.config.design_tokens import get_design_tokens, MilitaryColors, ForestColors
from airwar.utils.mouse_interaction import MouseSelectableMixin


class MenuScene(Scene, MouseSelectableMixin):
    # 菜单阶段
    PHASE_DIFFICULTY = 'difficulty'
    PHASE_GPU = 'gpu'

    def __init__(self):
        Scene.__init__(self)
        MouseSelectableMixin.__init__(self)

    def enter(self, **kwargs) -> None:
        self.running = True
        self.phase = self.PHASE_DIFFICULTY  # 从难度选择开始
        self.difficulty = 'medium'
        self.difficulty_options = ['easy', 'medium', 'hard', 'tutorial']
        self.option_names = {
            'easy': 'EASY',
            'medium': 'MEDIUM',
            'hard': 'HARD',
            'tutorial': 'TUTORIAL'
        }
        # GPU 模式选项
        self.use_gpu = False  # 默认 pygame 模式
        self.gpu_options = ['pygame', 'GPU']
        self.gpu_option_labels = {
            'pygame': 'RENDERER: pygame (CPU)',
            'GPU': 'RENDERER: GPU (ModernGL)'
        }
        self.selected_index = 1
        self.gpu_selected_index = 0  # 默认选择 pygame
        self.animation_time = 0
        self.glow_offset = 0
        self.selection_confirmed = False
        self.back_requested = False
        self._gpu_error = False  # GPU 测试失败标志
        self._gpu_error_message = ''  # GPU 错误消息

        self._tokens = get_design_tokens()

        self.base_panel_width = self._tokens.spacing.PANEL_WIDTH
        self.base_panel_height = self._tokens.spacing.PANEL_HEIGHT
        self.base_option_height = self._tokens.spacing.OPTION_HEIGHT
        self.base_option_gap = self._tokens.spacing.OPTION_GAP
        self.base_title_y = self._tokens.components.TITLE_Y
        self.base_option_font_size = self._tokens.typography.OPTION_SIZE
        self.base_hint_font_size = self._tokens.typography.CAPTION_SIZE
        self.base_desc_font_size = self._tokens.typography.SMALL_SIZE

        pygame.font.init()
        self._init_fonts(1.0)

        self._background_renderer = MenuBackground()
        self._particle_system = ParticleSystem()
        self._effects_renderer = EffectsRenderer()
        self._particle_system.reset(self._tokens.components.PARTICLE_COUNT, 'particle')
        self._init_colors()

    def _init_fonts(self, scale: float) -> None:
        self.title_font = pygame.font.Font(None, ResponsiveHelper.font_size(110, scale))
        self.option_font = pygame.font.Font(None, ResponsiveHelper.font_size(self.base_option_font_size, scale))
        self.hint_font = pygame.font.Font(None, ResponsiveHelper.font_size(self.base_hint_font_size, scale))
        self.desc_font = pygame.font.Font(None, ResponsiveHelper.font_size(self.base_desc_font_size, scale))

    def _init_colors(self) -> None:
        colors = self._tokens.colors
        self.colors = {
            'bg': colors.BACKGROUND_PRIMARY,
            'bg_gradient': colors.BACKGROUND_SECONDARY,
            'title': colors.TEXT_PRIMARY,
            'title_glow': colors.HUD_AMBER_BRIGHT,
            'selected': colors.HUD_AMBER,
            'selected_glow': colors.HUD_AMBER_BRIGHT,
            'unselected': colors.TEXT_MUTED,
            'hint': colors.TEXT_HINT,
            'back': ForestColors.BACK_BUTTON,
            'particle': colors.PARTICLE_PRIMARY,
            'panel': colors.BACKGROUND_PANEL,
            'panel_border': colors.PANEL_BORDER,
            'option_selected_bg': colors.BUTTON_SELECTED_BG,
            'option_unselected_bg': colors.BUTTON_UNSELECTED_BG,
        }
        # Military style colors
        self.military_colors = {
            'bg': MilitaryColors.BG_PRIMARY,
            'bg_gradient': MilitaryColors.BG_PANEL,
            'title': MilitaryColors.AMBER_PRIMARY,
            'title_glow': MilitaryColors.AMBER_GLOW,
            'selected': MilitaryColors.AMBER_PRIMARY,
            'selected_glow': MilitaryColors.AMBER_GLOW,
            'unselected': MilitaryColors.TEXT_DIM,
            'panel': MilitaryColors.BG_PANEL,
            'panel_border': MilitaryColors.BORDER_GLOW,
            'option_selected_bg': MilitaryColors.BG_PANEL_LIGHT,
            'option_unselected_bg': MilitaryColors.BG_PANEL,
        }
        self.use_military_style = True

    def exit(self) -> None:
        """Clean up when exiting the menu scene."""
        self.running = False
        self.selection_confirmed = False
        self.back_requested = False

    def reset(self) -> None:
        """Reset the menu scene to initial state."""
        self.running = True
        self.phase = self.PHASE_DIFFICULTY
        self.difficulty = 'medium'
        self.use_gpu = False
        self.selected_index = 1
        self.gpu_selected_index = 0
        self.animation_time = 0
        self.glow_offset = 0
        self.selection_confirmed = False
        self.back_requested = False
        self._gpu_error = False
        self._gpu_error_message = ''
        self._background_renderer = MenuBackground()
        self._particle_system.reset(40, 'particle')

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.phase == self.PHASE_GPU:
                    # 从 GPU 阶段返回难度选择
                    self.phase = self.PHASE_DIFFICULTY
                    self.selected_index = 1
                else:
                    self.back_requested = True
                    self.running = False
            elif event.key in (pygame.K_UP, pygame.K_w):
                if self.phase == self.PHASE_DIFFICULTY:
                    self.selected_index = (self.selected_index - 1) % len(self.difficulty_options)
                else:
                    self.gpu_selected_index = (self.gpu_selected_index - 1) % len(self.gpu_options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                if self.phase == self.PHASE_DIFFICULTY:
                    self.selected_index = (self.selected_index + 1) % len(self.difficulty_options)
                else:
                    self.gpu_selected_index = (self.gpu_selected_index + 1) % len(self.gpu_options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._confirm_selection()
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.handle_mouse_click(event.pos):
                self._confirm_selection()

    def _confirm_selection(self) -> None:
        if self.phase == self.PHASE_DIFFICULTY:
            selected_option = self.difficulty_options[self.selected_index]
            if selected_option != 'tutorial':
                self.difficulty = selected_option
            # 进入 GPU 选择阶段
            self.phase = self.PHASE_GPU
            self.selected_index = 0
            self._gpu_error = False  # 清除错误状态
        else:
            # GPU 阶段确认
            self.use_gpu = (self.gpu_selected_index == 1)  # 1 = GPU
            if self.use_gpu:
                # 测试 GPU 是否可用
                if not self._test_gpu_mode():
                    # GPU 不可用，返回 GPU 选择阶段
                    self._gpu_error = True
                    self.phase = self.PHASE_GPU
                    self.gpu_selected_index = 0  # 重置为 pygame
                    return
            self.selection_confirmed = True
            self.running = False

    def _test_gpu_mode(self) -> bool:
        """测试 GPU 模式是否可用"""
        from airwar.game.rendering.hybrid_renderer import HybridRenderer
        from airwar.config import get_screen_width, get_screen_height

        screen_width = get_screen_width()
        screen_height = get_screen_height()
        test_renderer = HybridRenderer(screen_width, screen_height, use_gpu=False)
        result = test_renderer.test_gpu()
        test_renderer.release()
        return result

    def _on_hover_change(self, index: int) -> None:
        self.selected_index = index

    def update(self, *args, **kwargs) -> None:
        self.animation_time += 1
        self.glow_offset = math.sin(self.animation_time * self._tokens.animation.GLOW_SPEED) * 12

        self._background_renderer._animation_time = self.animation_time
        self._background_renderer.update()

        self._particle_system._animation_time = self.animation_time
        self._particle_system.update(direction=-1)

    def _draw_glow_text(self, surface: pygame.Surface, text: str, font: pygame.font.Font,
                        pos: tuple, color: tuple, glow_color: tuple, glow_radius: int = None) -> None:
        if glow_radius is None:
            glow_radius = self._tokens.animation.GLOW_RADIUS_TITLE

        for i in range(glow_radius, 0, -1):
            alpha = int(120 / i)
            glow_surf = font.render(text, True, glow_color)
            glow_surf.set_alpha(alpha)
            glow_rect = glow_surf.get_rect(center=(pos[0], pos[1] + i))
            surface.blit(glow_surf, glow_rect)

        main_text = font.render(text, True, color)
        surface.blit(main_text, main_text.get_rect(center=pos))

    def _draw_panel(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        panel_width = ResponsiveHelper.scale(self.base_panel_width, scale)
        panel_height = ResponsiveHelper.scale(self.base_panel_height, scale)
        panel_x = width // 2 - panel_width // 2
        panel_y = height // 2 - panel_height // 2 + ResponsiveHelper.scale(30, scale)

        if self.use_military_style:
            # Military style: chamfered panel
            draw_chamfered_panel(
                surface, panel_x, panel_y, panel_width, panel_height,
                self.military_colors['panel'],
                self.military_colors['panel_border'],
                self.military_colors['selected_glow'],
                chamfer_depth=12
            )
        else:
            # Original style: rounded panel with glow
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

    def _draw_option_item(self, surface: pygame.Surface, diff: str, index: int,
                          center_x: int, start_y: int, is_selected: bool) -> None:
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        option_height = ResponsiveHelper.scale(self.base_option_height, scale)
        option_gap = ResponsiveHelper.scale(self.base_option_gap, scale)
        y = start_y + index * (option_height + option_gap)

        # 根据文本长度计算所需宽度
        arrow = "> " if is_selected else "  "
        full_text = f"{arrow}{diff}"
        text_width = self.option_font.size(full_text)[0]
        # 加上左右 padding
        min_width = ResponsiveHelper.scale(360, scale)
        padding = ResponsiveHelper.scale(40, scale)
        box_width = max(min_width, text_width + padding)
        box_height = option_height
        box_rect = pygame.Rect(center_x - box_width // 2, y, box_width, box_height)
        self.append_option_rect(box_rect)

        if self.use_military_style:
            # Military style: chamfered options
            m_colors = self.military_colors
            if is_selected:
                # Selected: glow effect
                glow_rect = box_rect.inflate(6, 6)
                draw_chamfered_panel(
                    surface, glow_rect.x, glow_rect.y, glow_rect.width, glow_rect.height,
                    (0, 0, 0, 0),  # transparent bg
                    m_colors['selected_glow'],
                    m_colors['selected_glow'],
                    chamfer_depth=8
                )
                draw_chamfered_panel(
                    surface, box_rect.x, box_rect.y, box_rect.width, box_rect.height,
                    m_colors['option_selected_bg'],
                    m_colors['selected'],
                    None,
                    chamfer_depth=8
                )
            else:
                draw_chamfered_panel(
                    surface, box_rect.x, box_rect.y, box_rect.width, box_rect.height,
                    m_colors['option_unselected_bg'],
                    m_colors['unselected'],
                    None,
                    chamfer_depth=8
                )

            arrow = ">" if is_selected else " "
            # diff 已经是完整文本（GPU 选项或难度名称）
            text_color = m_colors['selected'] if is_selected else m_colors['unselected']
            text = self.option_font.render(f"  {arrow}  {diff}", True, text_color)
            text_rect = text.get_rect(midleft=(box_rect.x + 20, box_rect.centery))
            surface.blit(text, text_rect)
        else:
            # Original style: rounded options
            if is_selected:
                glow_color = self.colors['selected_glow']
                for i in range(4, 0, -1):
                    expand = i * 3
                    glow_rect = box_rect.inflate(expand * 2, expand * 2)
                    glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                    pygame.draw.rect(glow_surf, (*glow_color, 35 // i), glow_surf.get_rect(), border_radius=10)
                    surface.blit(glow_surf, glow_rect)

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

            arrow = ">" if is_selected else " "
            # diff 已经是完整文本（GPU 选项或难度名称）
            text_color = self.colors['selected'] if is_selected else self.colors['unselected']

            text = self.option_font.render(f"  {arrow}  {diff}", True, text_color)
            text_rect = text.get_rect(midleft=(box_rect.x + 20, box_rect.centery))
            surface.blit(text, text_rect)

    def _draw_title_section(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        title_y = ResponsiveHelper.scale(self.base_title_y, scale) + self.glow_offset * 0.5
        title_text = "AIR WAR"
        self._draw_glow_text(surface, title_text, self.title_font,
                           (width // 2, title_y), self.colors['title'], self.colors['title_glow'], 5)

    def _draw_bottom_hints(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        blink_interval = self._tokens.animation.BLINK_INTERVAL
        if (self.animation_time // blink_interval) % 2 == 0:
            hint_color = ForestColors.HINT_DIM
        else:
            hint_color = ForestColors.HINT_BRIGHT

        if self.phase == self.PHASE_DIFFICULTY:
            start_text = self.hint_font.render("CLICK or ENTER to select", True, hint_color)
        else:
            start_text = self.hint_font.render("SELECT RENDERER MODE", True, hint_color)
        surface.blit(start_text, start_text.get_rect(center=(width // 2, height - ResponsiveHelper.scale(self._tokens.components.HINT_Y_OFFSET, scale))))

        controls = self.desc_font.render("W/S to select", True, ForestColors.DESC_TEXT)
        surface.blit(controls, controls.get_rect(center=(width // 2, height - ResponsiveHelper.scale(self._tokens.components.CONTROLS_Y_OFFSET, scale))))

    def _draw_title_section(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        title_y = ResponsiveHelper.scale(self.base_title_y, scale) + self.glow_offset * 0.5
        if self.phase == self.PHASE_GPU:
            title_text = "SELECT RENDERER"
        else:
            title_text = "AIR WAR"
        self._draw_glow_text(surface, title_text, self.title_font,
                           (width // 2, title_y), self.colors['title'], self.colors['title_glow'], 5)

    def render(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)
        self._init_fonts(scale)

        # Use military style background if enabled
        if self.use_military_style:
            self._background_renderer.render_military_style(surface, self.military_colors)
        else:
            self._background_renderer.render(surface, self.colors)

        self._particle_system.render(surface, self.colors['particle'])

        self._draw_title_section(surface)
        self._draw_panel(surface)

        panel_width = ResponsiveHelper.scale(self.base_panel_width, scale)
        panel_height = ResponsiveHelper.scale(self.base_panel_height, scale)
        center_x = width // 2
        panel_y = height // 2 - panel_height // 2 + ResponsiveHelper.scale(30, scale)

        option_height = ResponsiveHelper.scale(self.base_option_height, scale)
        option_gap = ResponsiveHelper.scale(self.base_option_gap, scale)

        # 根据阶段选择渲染选项
        if self.phase == self.PHASE_DIFFICULTY:
            current_options = self.difficulty_options
            option_labels = self.option_names
        else:
            current_options = self.gpu_options
            option_labels = self.gpu_option_labels

        option_section_height = option_height * len(current_options) + option_gap * (len(current_options) - 1)
        start_y = panel_y + (panel_height - option_section_height) // 2

        self.clear_option_rects()
        effective_index = self.get_effective_selected_index(self.selected_index)
        for i, option in enumerate(current_options):
            self._draw_option_item(surface, option_labels.get(option, option.upper()), i, center_x, start_y, i == effective_index)

        self._draw_bottom_hints(surface)

        # GPU 错误提示
        if self._gpu_error:
            self._draw_gpu_error(surface)

    def _draw_gpu_error(self, surface: pygame.Surface) -> None:
        """绘制 GPU 错误提示"""
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        # 错误消息
        error_font_size = ResponsiveHelper.font_size(20, scale)
        error_font = pygame.font.Font(None, error_font_size)

        lines = [
            'GPU 初始化失败！',
            '您的系统不支持 ModernGL GPU 渲染',
            '建议使用 pygame (CPU) 模式运行游戏',
            '按 ENTER 选择 pygame 模式'
        ]

        # 计算文本区域高度
        line_height = error_font_size * 1.5
        total_height = len(lines) * line_height
        start_y = height // 2 + ResponsiveHelper.scale(200, scale)

        # 半透明背景
        bg_height = total_height + 40
        bg_width = ResponsiveHelper.scale(500, scale)
        bg_surface = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
        pygame.draw.rect(bg_surface, (40, 10, 10, 220), bg_surface.get_rect(), border_radius=10)
        bg_rect = bg_surface.get_rect(center=(width // 2, start_y + total_height // 2))
        surface.blit(bg_surface, bg_rect)

        # 绘制错误文本
        for i, line in enumerate(lines):
            if i == 0:
                # 第一行用红色
                text_color = (255, 100, 100)
            elif i == len(lines) - 1:
                # 最后一行用高亮
                text_color = (255, 220, 180)
            else:
                text_color = (200, 180, 160)

            text_surf = error_font.render(line, True, text_color)
            text_rect = text_surf.get_rect(center=(width // 2, start_y + i * line_height))
            surface.blit(text_surf, text_rect)

    def get_difficulty(self) -> str:
        return self.difficulty

    def get_use_gpu(self) -> bool:
        """返回是否使用 GPU 模式"""
        return self.use_gpu

    def get_selected_option(self) -> str:
        if self.phase == self.PHASE_DIFFICULTY:
            return self.difficulty_options[self.selected_index]
        else:
            return self.gpu_options[self.gpu_selected_index]

    def is_selection_confirmed(self) -> bool:
        return self.selection_confirmed

    def is_ready(self) -> bool:
        return not self.running

    def should_go_back(self) -> bool:
        return self.back_requested
