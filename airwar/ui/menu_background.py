import pygame
import math
import random
from airwar.config.design_tokens import get_design_tokens, ForestColors


class MenuBackground:
    """雨林风格菜单背景渲染器

    性能优化：
    - 预渲染渐变背景到缓存
    - 使用简单的半透明形状代替复杂图形
    - 限制叶子/微粒数量
    - 动画使用简单的数学计算
    - 预渲染叶子/光斑表面到缓存
    """

    _gradient_cache = {}
    _leaf_surface_cache = {}
    _light_surface_cache = {}

    def __init__(self):
        self._animation_time = 0
        self._tokens = get_design_tokens()
        self._screen_size = None
        # 远景叶子层
        self._leaves_far = []
        self._init_leaves_far()
        # 近景微粒层
        self._particles = []
        self._init_particles()
        # 光斑位置
        self._light_spots = []
        self._init_light_spots()
        # 跑马灯效果 - 使用令牌配置
        self._marquee_time = 0.0
        self._marquee_speed = ForestColors.MARQUEE_SPEED
        self._marquee_strip_height = ForestColors.MARQUEE_STRIP_SIZE

    def _ensure_cached_surfaces(self, width: int, height: int):
        """确保缓存的表面尺寸与屏幕尺寸匹配"""
        if self._screen_size == (width, height):
            return
        self._screen_size = (width, height)
        MenuBackground._leaf_surface_cache.clear()
        MenuBackground._light_surface_cache.clear()

    def _get_leaf_surface(self, size: float) -> pygame.Surface:
        size_key = int(size * 100)
        if size_key not in MenuBackground._leaf_surface_cache:
            surf = pygame.Surface((int(size * 2), int(size * 3)), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, (15, 40, 15, 25), (0, 0, int(size * 2), int(size * 3)))
            MenuBackground._leaf_surface_cache[size_key] = surf
        return MenuBackground._leaf_surface_cache[size_key]

    def _get_light_surface(self, width: float, height: int) -> pygame.Surface:
        cache_key = (int(width * 100), height)
        if cache_key not in MenuBackground._light_surface_cache:
            surf = pygame.Surface((int(width * 2), height), pygame.SRCALPHA)
            points = [
                (width * 0.3, 0),
                (width * 1.7, 0),
                (width * 2, height),
                (0, height)
            ]
            pygame.draw.polygon(surf, (160, 190, 100, 255), points)
            MenuBackground._light_surface_cache[cache_key] = surf
        return MenuBackground._light_surface_cache[cache_key]

    def _init_leaves_far(self):
        """初始化远景叶子"""
        self._leaves_far = []
        for _ in range(6):
            self._leaves_far.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(0.1, 0.25),
                'speed': random.uniform(0.0001, 0.0003),
                'sway_phase': random.random() * math.tau,
                'sway_amount': random.uniform(0.01, 0.03),
                'alpha': random.randint(15, 30),
            })

    def _init_particles(self):
        """初始化浮动微粒"""
        self._particles = []

    def _init_light_spots(self):
        """初始化光斑"""
        self._light_spots = []

    def update(self):
        """更新动画状态"""
        self._animation_time += 1
        # 更新跑马灯时间（非线性移动）
        self._marquee_time += self._marquee_speed
        # 更新叶子位置
        for leaf in self._leaves_far:
            leaf['y'] += leaf['speed']
            if leaf['y'] > 1.2:
                leaf['y'] = -0.2
                leaf['x'] = random.random()
        # 更新微粒
        for p in self._particles:
            p['y'] -= p['speed']
            p['x'] += p['drift_x']
            if p['y'] < -0.1:
                p['y'] = 1.1
                p['x'] = random.random()
        # 更新光斑
        for spot in self._light_spots:
            spot['y'] += spot['speed']
            if spot['y'] > 1.2:
                spot['y'] = -0.2
                spot['x'] = random.uniform(0.1, 0.9)

    def _get_cached_gradient(self, surface: pygame.Surface, bg_color: tuple, gradient_color: tuple) -> pygame.Surface:
        """获取或创建渐变背景缓存"""
        width, height = surface.get_size()
        cache_key = (width, height, bg_color, gradient_color)

        if cache_key not in MenuBackground._gradient_cache:
            gradient = pygame.Surface((width, height))
            for y in range(0, height, 3):
                ratio = y / height
                r = int(bg_color[0] * (1 - ratio) + gradient_color[0] * ratio)
                g = int(bg_color[1] * (1 - ratio) + gradient_color[1] * ratio)
                b = int(bg_color[2] * (1 - ratio) + gradient_color[2] * ratio)
                pygame.draw.line(gradient, (r, g, b), (0, y), (width, y))
            MenuBackground._gradient_cache[cache_key] = gradient

        return MenuBackground._gradient_cache[cache_key]

    def render(self, surface: pygame.Surface, colors: dict):
        """渲染背景"""
        # 先清除屏幕
        surface.fill(colors['bg'])
        gradient = self._get_cached_gradient(
            surface,
            colors['bg'],
            colors.get('bg_gradient', colors['bg'])
        )
        surface.blit(gradient, (0, 0))

        # 渲染星星/微粒
        width, height = surface.get_size()
        star_color = self._tokens.colors.star_color
        for star in getattr(self, '_stars', []):
            x = int(star['x'] * width)
            y = int(star['y'] * height)
            twinkle = math.sin(self._animation_time * star['twinkle_speed'] + star['twinkle_offset'])
            brightness = int(star['brightness'] * (0.5 + 0.5 * twinkle))
            pygame.draw.circle(surface, star_color(brightness), (x, y), int(star['size']))

    def render_military_style(self, surface: pygame.Surface, colors: dict):
        """渲染雨林风格背景

        Args:
            surface: 目标 surface
            colors: 颜色配置
        """
        width, height = surface.get_size()
        bg_color = colors.get('bg', ForestColors.BG_PRIMARY)
        bg_gradient = colors.get('bg_gradient', ForestColors.BG_PANEL)

        # 渲染渐变背景
        gradient = self._get_cached_gradient(surface, bg_color, bg_gradient)
        surface.blit(gradient, (0, 0))

        # 渲染跑马灯效果
        self._render_marquee(surface, width, height)

        # 渲染光斑层
        self._render_light_spots(surface, width, height)

        # 渲染远景叶子层
        self._render_leaves(surface, width, height)

        # 渲染微粒层
        self._render_particles(surface, width, height)

    def _render_light_spots(self, surface: pygame.Surface, width: int, height: int) -> None:
        """渲染光斑层 - 模拟树隙透光"""
        self._ensure_cached_surfaces(width, height)
        for spot in self._light_spots:
            x = spot['x'] * width
            y = spot['y'] * height
            spot_width = spot['width'] * width

            pulse = math.sin(self._animation_time * spot['pulse_speed'] + spot['pulse_offset'])
            alpha = int(spot['alpha'] * (0.7 + 0.3 * pulse))

            light_surf = self._get_light_surface(spot_width, height)
            light_surf.set_alpha(alpha)
            surface.blit(light_surf, (int(x - spot_width), 0))

    def _render_leaves(self, surface: pygame.Surface, width: int, height: int) -> None:
        """渲染远景叶子层"""
        self._ensure_cached_surfaces(width, height)
        for leaf in self._leaves_far:
            x = leaf['x'] * width
            y = leaf['y'] * height
            size = leaf['size'] * min(width, height)

            sway = math.sin(self._animation_time * 0.01 + leaf['sway_phase']) * leaf['sway_amount'] * width

            leaf_surf = self._get_leaf_surface(leaf['size'])
            leaf_surf.set_alpha(leaf['alpha'])
            surface.blit(leaf_surf, (int(x - size + sway), int(y - size * 1.5)))

    def _render_particles(self, surface: pygame.Surface, width: int, height: int) -> None:
        """渲染浮动微粒层 - 模拟阳光中的尘埃"""
        for p in self._particles:
            x = p['x'] * width
            y = p['y'] * height

            # 闪烁效果
            pulse = math.sin(self._animation_time * p['pulse_speed'] + p['pulse_offset'])
            alpha = int(p['brightness'] * (0.4 + 0.6 * pulse))

            # 绘制微粒
            pygame.draw.circle(
                surface,
                (180, 200, 120),
                (int(x), int(y)),
                int(p['size'])
            )

    def _render_marquee(self, surface: pygame.Surface, width: int, height: int) -> None:
        """渲染跑马灯效果 - 使用ForestColors令牌，慢速线性移动"""
        strip_color = ForestColors.MARQUEE_COLOR
        strip_size = ForestColors.MARQUEE_STRIP_SIZE
        wobble = ForestColors.MARQUEE_WOBBLE_AMOUNT

        # 纵向条带 - 缓慢线性移动带轻微摆动
        base_y = (self._marquee_time % (height + strip_size * 2)) - strip_size
        offset_y = math.sin(self._marquee_time * 2) * height * wobble
        marquee_y = base_y + offset_y
        v_strip_surf = pygame.Surface((width, strip_size), pygame.SRCALPHA)
        v_strip_surf.fill(strip_color)
        surface.blit(v_strip_surf, (0, int(marquee_y)))

        # 横向条带 - 缓慢线性移动带轻微摆动
        base_x = (self._marquee_time % (width + strip_size * 2)) - strip_size
        offset_x = math.sin(self._marquee_time * 2 + math.pi) * width * wobble
        marquee_x = base_x + offset_x
        h_strip_surf = pygame.Surface((strip_size, height), pygame.SRCALPHA)
        h_strip_surf.fill(strip_color)
        surface.blit(h_strip_surf, (int(marquee_x), 0))
