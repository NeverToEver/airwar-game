import moderngl
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SpriteInstance:
    """精灵实例数据"""
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    tint_r: float = 1.0
    tint_g: float = 1.0
    tint_b: float = 1.0
    alpha: float = 1.0


class SpriteBatch:
    """批量精灵渲染器，支持 GPU 实例化批量绘制"""

    MAX_INSTANCES = 1000

    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        texture: moderngl.Texture
    ):
        self._ctx = ctx
        self._program = program
        self._texture = texture

        self._instances: List[SpriteInstance] = []
        self._quad_vbo: Optional[moderngl.Buffer] = None
        self._instance_vbo: Optional[moderngl.Buffer] = None
        self._vao: Optional[moderngl.VertexArray] = None

        self._program['sprite'] = 0

        self._init_buffers()

    def _init_buffers(self) -> None:
        """初始化缓冲区和 VAO"""
        quad = np.array([
            -0.5, -0.5, 0.0, 0.0,
             0.5, -0.5, 1.0, 0.0,
             0.5,  0.5, 1.0, 1.0,
            -0.5, -0.5, 0.0, 0.0,
             0.5,  0.5, 1.0, 1.0,
            -0.5,  0.5, 0.0, 1.0,
        ], dtype='f4')

        self._quad_vbo = self._ctx.buffer(quad.tobytes())
        self._instance_vbo = self._ctx.buffer(reserve=self.MAX_INSTANCES * 16 * 4)

        self._vao = self._ctx.vertex_array(
            self._program,
            [
                (self._quad_vbo, '2f 2f/i', 'in_vert', 'in_uv'),
                (self._instance_vbo, '7f 4f/i', 'in_instance_data', 'in_instance_extra'),
            ],
            mode=moderngl.TRIANGLES
        )

    def add(self, instance: SpriteInstance) -> None:
        """添加精灵实例"""
        if len(self._instances) >= self.MAX_INSTANCES:
            self.flush()
        self._instances.append(instance)

    def add_batch(self, instances: List[SpriteInstance]) -> None:
        """批量添加精灵实例"""
        for inst in instances:
            self.add(inst)

    def clear(self) -> None:
        """清空所有实例"""
        self._instances.clear()

    def flush(self) -> None:
        """将实例数据上传到 GPU 并渲染"""
        if not self._instances:
            return

        data = np.zeros(len(self._instances), dtype=[
            ('transform', '4f'),
            ('extra', '4f'),
        ])

        for i, inst in enumerate(self._instances):
            scale_x = inst.width * inst.scale_x
            scale_y = inst.height * inst.scale_y

            data[i]['transform'] = (
                inst.x,
                inst.y,
                scale_x,
                inst.rotation,
            )
            data[i]['extra'] = (
                inst.scale_y,
                inst.tint_r,
                inst.tint_g,
                inst.tint_b,
                inst.alpha,
            )

        self._instance_vbo.write(data.tobytes())
        self._texture.use(0)

        self._ctx.enable(moderngl.BLEND)
        self._ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        self._vao.render(moderngl.TRIANGLES, vertices=6, instances=len(self._instances))

        self._instances.clear()

    def render(self) -> None:
        """渲染所有待处理精灵"""
        self.flush()

    def release(self) -> None:
        """释放 GPU 资源"""
        if self._quad_vbo:
            self._quad_vbo.release()
        if self._instance_vbo:
            self._instance_vbo.release()
        if self._vao:
            self._vao.release()


class SimpleSpriteBatch:
    """简化版精灵批次，不使用实例化（适合少量精灵）"""

    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        texture: moderngl.Texture
    ):
        self._ctx = ctx
        self._program = program
        self._texture = texture
        self._sprites: List[Tuple[np.ndarray, float, float, float, float, float]] = []

    def add(
        self,
        vertices: np.ndarray,
        x: float = 0.0,
        y: float = 0.0,
        scale: float = 1.0,
        rotation: float = 0.0,
        alpha: float = 1.0
    ) -> None:
        """添加精灵"""
        self._sprites.append((vertices, x, y, scale, rotation, alpha))

    def add_textured_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        u0: float = 0.0,
        v0: float = 0.0,
        u1: float = 1.0,
        v1: float = 1.0
    ) -> None:
        """添加纹理矩形"""
        w, h = width / 2, height / 2
        vertices = np.array([
            x - w, y - h, u0, v0,
            x + w, y - h, u1, v0,
            x + w, y + h, u1, v1,
            x - w, y - h, u0, v0,
            x + w, y + h, u1, v1,
            x - w, y + h, u0, v1,
        ], dtype='f4')
        self._sprites.append((vertices, 0, 0, 1.0, 0.0, 1.0))

    def clear(self) -> None:
        """清空"""
        self._sprites.clear()

    def render(self) -> None:
        """渲染所有精灵"""
        if not self._sprites:
            return

        self._texture.use(0)
        self._ctx.enable(moderngl.BLEND)
        self._ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        for vertices, x, y, scale, rotation, alpha in self._sprites:
            self._program['translate'].value = (x, y)
            self._program['scale'].value = (scale, scale)
            self._program['rotation'].value = rotation
            self._program['alpha'].value = alpha

            vbo = self._ctx.buffer(vertices.tobytes())
            vao = self._ctx.vertex_array(
                self._program,
                vbo,
                'in_vert',
                'in_uv'
            )
            vao.render(moderngl.TRIANGLES)
            vbo.release()
            vao.release()

        self._sprites.clear()
