import moderngl
import pygame
from typing import Dict, Optional, Tuple
from PIL import Image
import io


class TextureManager:
    """纹理管理器，负责加载图片并上传到 GPU 显存"""

    def __init__(self, ctx: moderngl.Context):
        self._ctx = ctx
        self._textures: Dict[str, moderngl.Texture] = {}

    def load(self, name: str, filepath: str) -> moderngl.Texture:
        """从文件加载纹理

        Args:
            name: 纹理名称（用于缓存）
            filepath: 图片文件路径

        Returns:
            GPU 上的 Texture 对象
        """
        if name in self._textures:
            return self._textures[name]

        image = Image.open(filepath).convert('RGBA')
        texture = self._create_texture_from_image(name, image)
        return texture

    def load_surface(self, name: str, surface: pygame.Surface) -> moderngl.Texture:
        """从 pygame.Surface 加载纹理

        Args:
            name: 纹理名称
            surface: pygame 表面

        Returns:
            GPU 上的 Texture 对象
        """
        if name in self._textures:
            return self._textures[name]

        image = self._surface_to_image(surface)
        texture = self._create_texture_from_image(name, image)
        return texture

    def _surface_to_image(self, surface: pygame.Surface) -> Image.Image:
        """将 pygame.Surface 转换为 PIL Image"""
        pygame_image = pygame.image.tostring(surface, 'RGBA')
        width, height = surface.get_size()
        return Image.frombytes('RGBA', (width, height), pygame_image)

    def _create_texture_from_image(self, name: str, image: Image.Image) -> moderngl.Texture:
        """从 PIL Image 创建 GPU 纹理"""
        image = image.transpose(Image.FLIP_TOP_BOTTOM)

        width, height = image.size
        data = image.tobytes()

        texture = self._ctx.texture((width, height), 4, data)
        texture.filter = moderngl.NEAREST, moderngl.NEAREST
        texture.build_mipmaps()

        self._textures[name] = texture
        return texture

    def get(self, name: str) -> Optional[moderngl.Texture]:
        """获取已缓存的纹理"""
        return self._textures.get(name)

    def create_render_target(
        self,
        name: str,
        width: int,
        height: int
    ) -> Tuple[moderngl.Texture, moderngl.Framebuffer]:
        """创建渲染目标（用于离屏渲染）

        Args:
            name: 目标名称
            width: 宽度
            height: 高度

        Returns:
            (纹理, 帧缓冲) 元组
        """
        texture = self._ctx.texture((width, height), 4)
        texture.filter = moderngl.LINEAR, moderngl.LINEAR

        fbo = self._ctx.framebuffer(color_attachments=[texture])

        self._textures[name] = texture
        return texture, fbo

    def release(self, name: str) -> None:
        """释放指定的纹理"""
        if name in self._textures:
            self._textures[name].release()
            del self._textures[name]

    def release_all(self) -> None:
        """释放所有纹理"""
        for texture in self._textures.values():
            texture.release()
        self._textures.clear()

    def bind(self, name: str, unit: int = 0) -> None:
        """绑定纹理到指定单元"""
        texture = self._textures.get(name)
        if texture:
            texture.use(unit)
