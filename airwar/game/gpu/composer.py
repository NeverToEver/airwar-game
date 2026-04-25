"""GPU 渲染编排器 - 封装 GPU 渲染管线，协调各组件"""
import moderngl
import pygame
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass

from .context import GPUContext
from .sprite_renderer import GPUSpriteRenderer, SpriteCache
from .background_renderer import GPUBackgroundRenderer
from .texture_manager import TextureManager
from .shader_manager import ShaderManager


@dataclass
class RenderLayer:
    """渲染层定义"""
    name: str
    z_order: int
    visible: bool = True


class GPUComposer:
    """GPU 渲染编排器，协调 GPU 渲染的各个层"""

    def __init__(self, screen_width: int = 1400, screen_height: int = 800):
        self._screen_size = (screen_width, screen_height)

        # 初始化 GPU 上下文
        self._gpu_ctx = GPUContext()
        self._init_context()

        # 初始化管理器
        self._shader_mgr = ShaderManager(self._gpu_ctx.context)
        self._texture_mgr = TextureManager(self._gpu_ctx.context)

        # 初始化渲染器
        self._sprite_renderer = GPUSpriteRenderer(self._gpu_ctx.context)
        self._sprite_cache = SpriteCache(self._gpu_ctx.context)
        self._sprite_cache.set_renderer(self._sprite_renderer)
        self._bg_renderer = GPUBackgroundRenderer(
            self._gpu_ctx.context,
            screen_width,
            screen_height
        )

        # FBO 用于捕获渲染结果
        self._fbo: Optional[moderngl.Framebuffer] = None
        self._init_fbo()

        # 渲染层控制
        self._layers: Dict[str, RenderLayer] = {}
        self._render_order: List[str] = []

        # 回调函数
        self._pre_render_callbacks: List[Callable] = []
        self._post_render_callbacks: List[Callable] = []

        self._setup_default_layers()

    def _init_fbo(self) -> None:
        """初始化 FBO 用于捕获渲染结果"""
        w, h = self._screen_size
        self._fbo = self._gpu_ctx.context.framebuffer(
            color_attachments=[self._gpu_ctx.context.texture((w, h), 4)],
            depth_attachment=self._gpu_ctx.context.depth_renderbuffer((w, h))
        )

    def _init_context(self) -> None:
        """初始化 GPU 上下文，尝试 EGL，失败则 fallback"""
        try:
            self._gpu_ctx.initialize(*self._screen_size)
        except Exception:
            self._gpu_ctx.initialize_fallback(*self._screen_size)

    def _setup_default_layers(self) -> None:
        """设置默认渲染层"""
        self._layers = {
            'background': RenderLayer('background', 0),
            'entities': RenderLayer('entities', 10),
            'effects': RenderLayer('effects', 20),
            'hud': RenderLayer('hud', 30),
            'ui': RenderLayer('ui', 40),
        }
        self._render_order = ['background', 'entities', 'effects', 'hud', 'ui']

    def set_layer_visible(self, layer_name: str, visible: bool) -> None:
        """设置层是否可见"""
        if layer_name in self._layers:
            self._layers[layer_name].visible = visible

    def upload_surface(self, name: str, surface: pygame.Surface) -> None:
        """上传 pygame.Surface 为 GPU 纹理"""
        self._sprite_cache.cache_surface(name, surface)

    def upload_all_surfaces(self) -> None:
        """上传所有缓存的 Surface 到 GPU"""
        self._sprite_cache.upload_all()

    def add_sprite(
        self,
        texture_name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        rotation: float = 0.0,
        alpha: float = 1.0,
        layer: str = 'entities'
    ) -> None:
        """添加精灵到指定层"""
        if layer not in self._layers or not self._layers[layer].visible:
            return
        self._sprite_renderer.add_sprite(
            texture_name, x, y, width, height,
            rotation=rotation, alpha=alpha
        )

    def add_pre_render_callback(self, callback: Callable) -> None:
        """添加渲染前回调"""
        self._pre_render_callbacks.append(callback)

    def add_post_render_callback(self, callback: Callable) -> None:
        """添加渲染后回调"""
        self._post_render_callbacks.append(callback)

    def render(self) -> None:
        """执行完整渲染流程（渲染到 FBO）"""
        # 执行 pre-render 回调
        for callback in self._pre_render_callbacks:
            callback()

        # 渲染到 FBO
        self._fbo.use()
        self._gpu_ctx.clear(0.039, 0.059, 0.122, 1.0)  # 深蓝色背景

        # 渲染各层
        for layer_name in self._render_order:
            layer = self._layers.get(layer_name)
            if not layer or not layer.visible:
                continue
            self._render_layer(layer_name)

        # 执行 post-render 回调
        for callback in self._post_render_callbacks:
            callback()

    def _render_layer(self, layer_name: str) -> None:
        """渲染单个层"""
        if layer_name == 'background':
            self._bg_renderer.render()
        elif layer_name in ('entities', 'effects', 'hud', 'ui'):
            self._sprite_renderer.render(*self._screen_size)

    def get_surface(self) -> pygame.Surface:
        """将 FBO 内容读取为 pygame Surface

        Returns:
            pygame.Surface: 包含当前渲染内容的 pygame Surface
        """
        if not self._fbo:
            surf = pygame.Surface(self._screen_size)
            surf.fill((10, 15, 31))
            return surf

        # 读取 FBO 像素数据 (RGBA)
        w, h = self._screen_size
        pixel_data = self._fbo.read(components=4)

        # 转换为 numpy 数组并处理
        arr = np.frombuffer(pixel_data, dtype='u1')
        arr = arr.reshape((h, w, 4))
        # 翻转 Y 轴（OpenGL 和 pygame 坐标系不同）
        arr = np.flip(arr, axis=0)

        # pygame.pixelcopy.array_to_surface 对带 alpha 的 surface 有问题
        # 我们先将 RGBA 转为 RGB，忽略 alpha 通道
        rgb_arr = arr[:, :, :3]

        # 转换为 pygame 期望的格式 (width, height, channels) 并确保 C contiguous
        rgb_arr = np.ascontiguousarray(np.transpose(rgb_arr, (1, 0, 2)))

        # 转换为 pygame Surface (RGB，不带 alpha)
        surf = pygame.Surface((w, h))
        pygame.pixelcopy.array_to_surface(surf, rgb_arr)

        return surf

    def update_background(self, delta_time: float) -> None:
        """更新背景动画"""
        self._bg_renderer.update(delta_time)

    def resize(self, screen_width: int, screen_height: int) -> None:
        """调整画布大小"""
        self._screen_size = (screen_width, screen_height)
        self._gpu_ctx.resize(screen_width, screen_height)
        self._bg_renderer.resize(screen_width, screen_height)

    def clear_sprites(self) -> None:
        """清空待渲染精灵"""
        self._sprite_renderer.clear()

    @property
    def context(self) -> moderngl.Context:
        return self._gpu_ctx.context

    @property
    def screen_size(self) -> Tuple[int, int]:
        return self._screen_size

    def release(self) -> None:
        """释放所有 GPU 资源"""
        self._sprite_renderer.release()
        self._bg_renderer.release()
        self._texture_mgr.release_all()
        self._shader_mgr.release_all()
        if self._fbo:
            self._fbo.release()
            self._fbo = None
        self._gpu_ctx.release()
