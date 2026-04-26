"""Menu background — animated background rendering for menu scenes."""
import pygame
import math
import random
from airwar.config.design_tokens import get_design_tokens, SceneColors


class _ScanBeam:
    """单个雷达扫描束 — 带随机目标点和平滑插值移动。"""

    def __init__(self, orientation: str, screen_size: float):
        self.orientation = orientation
        self._screen_size = screen_size
        self.position = random.uniform(0, screen_size)
        self.target = random.uniform(0, screen_size)
        self.speed = random.uniform(0.6, 2.0)
        self.glow_radius = random.randint(6, 14)
        self.alpha = random.randint(25, 55)
        self._phase = random.random() * math.tau

    def update(self) -> None:
        diff = self.target - self.position
        if abs(diff) < 2.0:
            self.target = random.uniform(0, self._screen_size)
            self.speed = random.uniform(0.6, 2.0)
        self.position += diff * self.speed * 0.03

    def pulse(self, time: float) -> float:
        return 0.7 + 0.3 * math.sin(time * 0.04 + self._phase)


class MenuBackground:
    """菜单背景渲染器 — 渐变背景、雷达扫描束、微粒、光斑。

    性能优化：
    - 预渲染渐变背景到缓存
    - 扫描束发光表面缓存
    - 限制微粒数量
    - 全部动画使用数学计算，无表面重建
    """

    _gradient_cache = {}
    _leaf_surface_cache = {}
    _light_surface_cache = {}
    _scan_glow_cache = {}

    def __init__(self):
        self._animation_time = 0
        self._tokens = get_design_tokens()
        self._screen_size = None
        self._scan_beams = []
        self._scan_beams_initialized = False
        # 远景叶子层
        self._leaves_far = []
        self._init_leaves_far()
        # 近景微粒层
        self._particles = []
        self._init_particles()
        # 光斑位置
        self._light_spots = []
        self._init_light_spots()

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

    def _ensure_scan_beams(self, width: int, height: int) -> None:
        """确保扫描束已按屏幕尺寸初始化"""
        if self._scan_beams_initialized:
            return
        self._scan_beams = []
        # 3 条水平扫描线 + 2 条垂直扫描线
        for _ in range(3):
            self._scan_beams.append(_ScanBeam('h', height))
        for _ in range(2):
            self._scan_beams.append(_ScanBeam('v', width))
        self._scan_beams_initialized = True

    def update(self):
        """更新动画状态"""
        self._animation_time += 1
        for beam in self._scan_beams:
            beam.update()
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

    def render_themed_style(self, surface: pygame.Surface, colors: dict):
        """渲染菜单背景

        Args:
            surface: 目标 surface
            colors: 颜色配置
        """
        width, height = surface.get_size()
        bg_color = colors.get('bg', SceneColors.BG_PRIMARY)
        bg_gradient = colors.get('bg_gradient', SceneColors.BG_PANEL)

        self._ensure_scan_beams(width, height)

        # 渲染渐变背景
        gradient = self._get_cached_gradient(surface, bg_color, bg_gradient)
        surface.blit(gradient, (0, 0))

        # 渲染雷达扫描束
        self._render_scan_beams(surface, width, height)

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
                SceneColors.PARTICLE_COLOR,
                (int(x), int(y)),
                int(p['size'])
            )

    def _get_scan_glow_surface(self, orientation: str, length: int, radius: int,
                                base_alpha: int) -> pygame.Surface:
        """获取或创建扫描束发光渐变表面缓存"""
        cache_key = (orientation, length, radius, base_alpha)
        if cache_key not in MenuBackground._scan_glow_cache:
            thickness = radius * 2 + 4
            if orientation == 'h':
                surf = pygame.Surface((length, thickness), pygame.SRCALPHA)
            else:
                surf = pygame.Surface((thickness, length), pygame.SRCALPHA)

            accel_color = SceneColors.ACCENT_PRIMARY
            # 垂直于扫描方向的发光渐变
            for i in range(thickness):
                dist = abs(i - thickness / 2) / (thickness / 2)
                falloff = max(0.0, 1.0 - dist) ** 2.2
                alpha = int(base_alpha * falloff * 0.7)
                if alpha > 0:
                    if orientation == 'h':
                        pygame.draw.line(surf, (*accel_color, alpha),
                                         (0, i), (length, i))
                    else:
                        pygame.draw.line(surf, (*accel_color, alpha),
                                         (i, 0), (i, length))
            MenuBackground._scan_glow_cache[cache_key] = surf
        return MenuBackground._scan_glow_cache[cache_key]

    def _render_scan_beams(self, surface: pygame.Surface, width: int,
                            height: int) -> None:
        """渲染雷达扫描束 — 随机目标点、平滑插值、发光渐变。"""
        for beam in self._scan_beams:
            pulse = beam.pulse(self._animation_time)
            glow_radius = int(beam.glow_radius * pulse)
            alpha = int(beam.alpha * pulse)

            if beam.orientation == 'h':
                glow_surf = self._get_scan_glow_surface(
                    'h', width, glow_radius, alpha)
                y_pos = int(beam.position) - glow_radius - 2
                surface.blit(glow_surf, (0, y_pos))
            else:
                glow_surf = self._get_scan_glow_surface(
                    'v', height, glow_radius, alpha)
                x_pos = int(beam.position) - glow_radius - 2
                surface.blit(glow_surf, (x_pos, 0))
