import moderngl
import pygame
import numpy as np
from typing import Dict, List, Optional, Tuple
from PIL import Image


class GPUSpriteRenderer:
    """GPU 精灵渲染器 - 将 pygame.Surface 转换为 GPU 纹理并批量渲染"""

    MAX_SPRITES = 500

    def __init__(self, ctx: moderngl.Context):
        self._ctx = ctx
        self._textures: Dict[str, moderngl.Texture] = {}
        self._sprite_programs: Dict[str, moderngl.Program] = {}
        self._instance_buffer: Optional[moderngl.Buffer] = None
        self._quad_buffer: Optional[moderngl.Buffer] = None
        self._vao: Optional[moderngl.VertexArray] = None

        self._pending_sprites: List[dict] = []

        self._init_shaders()
        self._init_buffers()

    def _init_shaders(self) -> None:
        """初始化精灵渲染着色器"""
        vs = '''#version 330
in vec2 in_vert;
in vec2 in_uv;
in vec4 in_transform;  // x, y, scale_x, scale_y
in vec4 in_extras;     // rotation, alpha, tex_index, unused

out vec2 v_uv;

uniform vec2 screen_size;
uniform int texture_count;
uniform sampler2D textures[8];

void main() {
    float rot = in_extras.x;
    float c = cos(rot);
    float s = sin(rot);
    mat2 rotation = mat2(c, -s, s, c);

    vec2 scaled = in_vert * in_transform.zw;
    vec2 rotated = rotation * scaled;
    vec2 pos = rotated + in_transform.xy;

    // Convert to normalized coordinates
    vec2 ndc = (pos / screen_size) * 2.0 - 1.0;
    ndc.y = -ndc.y;

    gl_Position = vec4(ndc, 0.0, 1.0);
    v_uv = in_uv;
}
'''

        fs = '''#version 330
in vec2 v_uv;
out vec4 frag_color;

uniform sampler2D sprite;

void main() {
    vec4 color = texture(sprite, v_uv);
    if (color.a < 0.01) discard;
    frag_color = color;
}
'''
        self._sprite_programs['default'] = self._ctx.program(
            vertex_shader=vs,
            fragment_shader=fs
        )

    def _init_buffers(self) -> None:
        """初始化缓冲区和 VAO"""
        quad = np.array([
            0.0, 0.0, 0.0, 0.0,
            1.0, 0.0, 1.0, 0.0,
            1.0, 1.0, 1.0, 1.0,
            0.0, 0.0, 0.0, 0.0,
            1.0, 1.0, 1.0, 1.0,
            0.0, 1.0, 0.0, 1.0,
        ], dtype='f4')

        self._quad_buffer = self._ctx.buffer(quad.tobytes())
        self._instance_buffer = self._ctx.buffer(
            reserve=self.MAX_SPRITES * 8 * 4
        )

    def _surface_to_texture(self, name: str, surface: pygame.Surface) -> moderngl.Texture:
        """将 pygame.Surface 转换为 GPU 纹理"""
        if name in self._textures:
            return self._textures[name]

        width, height = surface.get_size()
        pygame_image = pygame.image.tostring(surface, 'RGBA')
        image = Image.frombytes('RGBA', (width, height), pygame_image)
        image = image.transpose(Image.FLIP_TOP_BOTTOM)

        data = image.tobytes()
        texture = self._ctx.texture((width, height), 4, data)
        texture.filter = moderngl.NEAREST, moderngl.NEAREST

        self._textures[name] = texture
        return texture

    def upload_surface(self, name: str, surface: pygame.Surface) -> None:
        """上传 Surface 为纹理"""
        self._surface_to_texture(name, surface)

    def get_texture(self, name: str) -> Optional[moderngl.Texture]:
        """获取已缓存的纹理"""
        return self._textures.get(name)

    def add_sprite(
        self,
        texture_name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        rotation: float = 0.0,
        alpha: float = 1.0,
        anchor: str = 'center'
    ) -> None:
        """添加精灵渲染任务

        Args:
            texture_name: 纹理名称
            x, y: 位置（中心或左上角，取决于 anchor）
            width, height: 尺寸
            rotation: 旋转角度（弧度）
            alpha: 透明度
            anchor: 锚点 ('center' 或 'topleft')
        """
        if anchor == 'center':
            half_w, half_h = width / 2, height / 2
        else:
            half_w, half_h = 0, 0

        self._pending_sprites.append({
            'texture': texture_name,
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'half_w': half_w,
            'half_h': half_h,
            'rotation': rotation,
            'alpha': alpha,
        })

    def render(self, screen_width: int, screen_height: int) -> None:
        """渲染所有待处理的精灵"""
        if not self._pending_sprites:
            return

        self._ctx.enable(moderngl.BLEND)
        self._ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        program = self._sprite_programs['default']
        program['screen_size'].value = (screen_width, screen_height)

        # 构建实例数据
        instance_data = np.zeros(len(self._pending_sprites), dtype=[
            ('transform', '4f'),
            ('extras', '4f'),
        ])

        for i, sprite in enumerate(self._pending_sprites):
            instance_data[i]['transform'] = (
                sprite['x'],
                sprite['y'],
                sprite['width'],
                sprite['height'],
            )
            instance_data[i]['extras'] = (
                sprite['rotation'],
                sprite['alpha'],
                0.0,  # tex_index
                0.0,
            )

        # 渲染每个纹理为一组
        by_texture: Dict[str, List[int]] = {}
        for i, sprite in enumerate(self._pending_sprites):
            tex_name = sprite['texture']
            if tex_name not in by_texture:
                by_texture[tex_name] = []
            by_texture[tex_name].append(i)

        for tex_name, indices in by_texture.items():
            texture = self._textures.get(tex_name)
            if not texture:
                continue

            # 筛选当前纹理的精灵
            mask = np.array([i in indices for i in range(len(self._pending_sprites))])
            filtered_data = instance_data[mask]

            if len(filtered_data) == 0:
                continue

            # 创建临时 VAO
            instance_data_bytes = filtered_data.tobytes()
            temp_instance_buffer = self._ctx.buffer(instance_data_bytes)

            vao = self._ctx.vertex_array(
                program,
                [
                    (self._quad_buffer, '2f 2f/i', 'in_vert', 'in_uv'),
                    (temp_instance_buffer, '4f 4f/i', 'in_transform', 'in_extras'),
                ],
                mode=moderngl.TRIANGLES
            )

            texture.use(0)
            vao.render(moderngl.TRIANGLES, vertices=6, instances=len(filtered_data))

            temp_instance_buffer.release()
            vao.release()

        self._pending_sprites.clear()

    def clear(self) -> None:
        """清空待处理精灵"""
        self._pending_sprites.clear()

    def release(self) -> None:
        """释放 GPU 资源"""
        for texture in self._textures.values():
            texture.release()
        self._textures.clear()

        for program in self._sprite_programs.values():
            program.release()
        self._sprite_programs.clear()

        if self._quad_buffer:
            self._quad_buffer.release()
        if self._instance_buffer:
            self._instance_buffer.release()

        self._quad_buffer = None
        self._instance_buffer = None


class SpriteCache:
    """精灵纹理缓存管理器"""

    def __init__(self, ctx: moderngl.Context):
        self._ctx = ctx
        self._surfaces: Dict[str, pygame.Surface] = {}
        self._renderer: Optional[GPUSpriteRenderer] = None

    def set_renderer(self, renderer: GPUSpriteRenderer) -> None:
        self._renderer = renderer

    def cache_surface(self, name: str, surface: pygame.Surface) -> None:
        """缓存 Surface 并上传到 GPU"""
        self._surfaces[name] = surface
        if self._renderer:
            self._renderer.upload_surface(name, surface)

    def get_surface(self, name: str) -> Optional[pygame.Surface]:
        return self._surfaces.get(name)

    def upload_all(self) -> None:
        """将所有缓存的 Surface 上传到 GPU"""
        if not self._renderer:
            return
        for name, surface in self._surfaces.items():
            self._renderer.upload_surface(name, surface)
