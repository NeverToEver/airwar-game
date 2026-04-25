import moderngl
from typing import Optional, Tuple


class GPUContext:
    """ModernGL 上下文管理器，负责 GPU 资源生命周期"""

    def __init__(self):
        self._ctx: Optional[moderngl.Context] = None
        self._screen_size: Tuple[int, int] = (0, 0)
        self._pygltri_mode: bool = False

    def initialize(self, screen_width: int = 1400, screen_height: int = 800) -> None:
        """初始化 GPU 上下文（优先使用 pygltri 模式，直接渲染到窗口）"""
        if self._ctx is not None:
            return

        try:
            import pyglet
            self._ctx = moderngl.create_context(require=430, backend='egl')
            self._pygltri_mode = True
        except Exception:
            self._ctx = moderngl.create_standalone_context(require=330, backend='egl')
            self._pygltri_mode = False

        self._ctx.enable(moderngl.DEPTH_TEST)
        self._ctx.enable(moderngl.BLEND)
        self._ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self._screen_size = (screen_width, screen_height)

    def initialize_fallback(self, screen_width: int = 1400, screen_height: int = 800) -> None:
        """初始化 GPU 上下文（standalone 模式）"""
        if self._ctx is not None:
            return

        self._ctx = moderngl.create_standalone_context(require=330)
        self._ctx.enable(moderngl.DEPTH_TEST)
        self._ctx.enable(moderngl.BLEND)
        self._ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self._screen_size = (screen_width, screen_height)
        self._pygltri_mode = False

    @property
    def is_pygltri_mode(self) -> bool:
        """是否是 pygltri 模式（直接渲染到窗口）"""
        return self._pygltri_mode

    @property
    def context(self) -> moderngl.Context:
        """获取 ModernGL 上下文"""
        if self._ctx is None:
            raise RuntimeError("GPUContext not initialized. Call initialize() first.")
        return self._ctx

    @property
    def screen_size(self) -> Tuple[int, int]:
        return self._screen_size

    @property
    def version(self) -> int:
        """获取 OpenGL 版本号"""
        return self._ctx.version_code if self._ctx else 0

    def resize(self, width: int, height: int) -> None:
        """更新屏幕尺寸"""
        self._screen_size = (width, height)

    def clear(self, r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 1.0) -> None:
        """清空屏幕"""
        self._ctx.clear(r, g, b, a)

    def release(self) -> None:
        """释放 GPU 资源"""
        if self._ctx is not None:
            self._ctx.release()
            self._ctx = None


_gpu_context: Optional[GPUContext] = None


def get_gpu_context() -> GPUContext:
    """获取全局 GPU 上下文单例"""
    global _gpu_context
    if _gpu_context is None:
        _gpu_context = GPUContext()
    return _gpu_context
