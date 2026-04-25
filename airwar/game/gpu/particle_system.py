"""GPU 粒子系统 - 用于大量粒子的 GPU 加速渲染"""
import moderngl
import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass
import math


@dataclass
class Particle:
    """粒子数据"""
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    r: float = 1.0
    g: float = 0.5
    b: float = 0.0


class GPUParticleSystem:
    """GPU 粒子系统

    适用于大量粒子（>100）的场景，如爆炸、火焰、烟雾等。
    粒子更新在 CPU 进行，渲染在 GPU 完成。

    使用实例化渲染，每个粒子作为一个精灵。
    """

    MAX_PARTICLES = 500

    def __init__(self, ctx: moderngl.Context):
        self._ctx = ctx
        self._particles: List[Particle] = []
        self._buffer: Optional[moderngl.Buffer] = None
        self._program: Optional[moderngl.Program] = None
        self._vao: Optional[moderngl.VertexArray] = None
        self._quad_buffer: Optional[moderngl.Buffer] = None

        self._init_shader()
        self._init_buffers()

    def _init_shader(self) -> None:
        """初始化粒子着色器"""
        vs = '''#version 330
in vec2 in_vert;
in vec2 in_uv;
in vec4 in_particle;  // x, y, life, size
in vec4 in_color;     // r, g, b, alpha

out vec2 v_uv;
out vec4 v_color;

uniform vec2 screen_size;

void main() {
    float life_ratio = in_particle.z;
    float size = in_particle.w * life_ratio;

    // 粒子位置
    vec2 pos = in_particle.xy;
    vec2 offset = (in_vert - 0.5) * size;
    vec2 ndc = (pos / screen_size) * 2.0 - 1.0;
    ndc.y = -ndc.y;

    gl_Position = vec4(ndc + offset / screen_size * 2.0, 0.0, 1.0);
    v_uv = in_uv;
    v_color = vec4(in_color.rgb, in_color.a * life_ratio);
}
'''
        fs = '''#version 330
in vec2 v_uv;
in vec4 v_color;
out vec4 frag_color;

void main() {
    // 圆形粒子
    vec2 center = v_uv - 0.5;
    float dist = length(center);
    if (dist > 0.5) discard;

    float glow = 1.0 - dist * 2.0;
    frag_color = vec4(v_color.rgb, v_color.a * glow);
}
'''
        self._program = self._ctx.program(
            vertex_shader=vs,
            fragment_shader=fs
        )

    def _init_buffers(self) -> None:
        """初始化缓冲区"""
        # 粒子 quad
        quad = np.array([
            0.0, 0.0, 0.0, 0.0,
            1.0, 0.0, 1.0, 0.0,
            1.0, 1.0, 1.0, 1.0,
            0.0, 0.0, 0.0, 0.0,
            1.0, 1.0, 1.0, 1.0,
            0.0, 1.0, 0.0, 1.0,
        ], dtype='f4')

        self._quad_buffer = self._ctx.buffer(quad.tobytes())
        self._buffer = self._ctx.buffer(reserve=self.MAX_PARTICLES * 8 * 4)

    def add_particle(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        life: float,
        size: float,
        r: float = 1.0,
        g: float = 0.5,
        b: float = 0.0
    ) -> None:
        """添加粒子"""
        if len(self._particles) >= self.MAX_PARTICLES:
            return
        self._particles.append(Particle(x, y, vx, vy, life, life, size, r, g, b))

    def add_explosion(self, x: float, y: float, count: int = 30) -> None:
        """添加爆炸效果"""
        for _ in range(count):
            angle = np.random.uniform(0, 2 * math.pi)
            speed = np.random.uniform(3.0, 8.0)
            life = np.random.uniform(20, 40)
            size = np.random.uniform(2, 5)
            self.add_particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                life, size,
                1.0, 0.5, 0.0
            )

    def update(self, dt: float = 1.0) -> None:
        """更新所有粒子"""
        dead_indices = []
        for i, p in enumerate(self._particles):
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vx *= 0.98
            p.vy *= 0.98
            p.life -= 1
            if p.life <= 0:
                dead_indices.append(i)

        # 移除死亡粒子
        for i in reversed(dead_indices):
            self._particles.pop(i)

    def render(self, screen_width: int, screen_height: int) -> None:
        """渲染所有粒子"""
        if not self._particles:
            return

        count = len(self._particles)

        # 构建粒子数据
        particle_data = np.zeros(count, dtype=[
            ('particle', '4f'),
            ('color', '4f'),
        ])

        for i, p in enumerate(self._particles):
            life_ratio = p.life / p.max_life
            particle_data[i]['particle'] = (p.x, p.y, life_ratio, p.size)
            particle_data[i]['color'] = (p.r, p.g, p.b, 1.0)

        # 上传数据
        self._buffer.write(particle_data.tobytes())

        # 创建 VAO
        vao = self._ctx.vertex_array(
            self._program,
            [
                (self._quad_buffer, '2f 2f/i', 'in_vert', 'in_uv'),
                (self._buffer, '4f 4f/i', 'in_particle', 'in_color'),
            ],
            mode=moderngl.TRIANGLES
        )

        # 渲染
        self._ctx.enable(moderngl.BLEND)
        self._ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self._program['screen_size'].value = (screen_width, screen_height)

        vao.render(moderngl.TRIANGLES, vertices=6, instances=count)

        vao.release()

    def clear(self) -> None:
        """清空所有粒子"""
        self._particles.clear()

    @property
    def count(self) -> int:
        """粒子数量"""
        return len(self._particles)

    def release(self) -> None:
        """释放资源"""
        if self._buffer:
            self._buffer.release()
        if self._quad_buffer:
            self._quad_buffer.release()
        if self._program:
            self._program.release()
        self._buffer = None
        self._quad_buffer = None
        self._program = None
