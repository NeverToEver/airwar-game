import moderngl
import numpy as np
from typing import List, Tuple


class GPUBackgroundRenderer:
    """GPU 加速的背景渲染器 - 视差星空/雨林效果"""

    MAX_LAYER_ITEMS = 100

    def __init__(self, ctx: moderngl.Context, screen_width: int, screen_height: int):
        self._ctx = ctx
        self._screen_size = (screen_width, screen_height)
        self._time = 0.0

        self._programs = {}
        self._buffers = {}
        self._vaos = {}

        self._init_shaders()
        self._init_buffers()

    def _init_shaders(self) -> None:
        """初始化着色器"""
        gradient_vs = '''#version 330
in vec2 in_vert;
out vec2 v_uv;
uniform vec2 screen_size;
void main() {
    // Convert from screen pixel coords (0,0 to screen_size) to NDC (-1,1)
    vec2 ndc = (in_vert / screen_size) * 2.0 - 1.0;
    ndc.y = -ndc.y;
    gl_Position = vec4(ndc, 0.0, 1.0);
    v_uv = in_vert / screen_size;
}
'''
        gradient_fs = '''#version 330
in vec2 v_uv;
out vec4 frag_color;
uniform float time;

void main() {
    vec3 top = vec3(0.031, 0.059, 0.031);
    vec3 bottom = vec3(0.059, 0.137, 0.059);
    // 使用 time 做轻微的颜色变化
    float t = sin(time * 0.1) * 0.02;
    vec3 color = mix(top, bottom, v_uv.y + t);
    frag_color = vec4(color, 1.0);
}
'''
        self._programs['gradient'] = self._ctx.program(
            vertex_shader=gradient_vs,
            fragment_shader=gradient_fs
        )

        leaf_vs = '''#version 330
in vec2 in_vert;
in vec2 in_uv;
in vec4 in_instance;
out vec2 v_uv;
out float v_alpha;
uniform vec2 screen_size;
uniform float time;

void main() {
    vec2 pos = in_instance.xy;
    vec2 size = in_instance.zw;
    float sway = sin(time * 0.5 + in_instance.x * 0.1) * 5.0;
    pos.x += sway;
    // 使用 screen_size 计算宽高比，防止 uniform 被优化掉
    float aspect = screen_size.x / screen_size.y;
    vec2 offset = (in_vert - 0.5) * size * vec2(aspect, 1.0);
    gl_Position = vec4(pos + offset, 0.0, 1.0);
    v_uv = in_uv;
    v_alpha = 0.6;
}
'''
        leaf_fs = '''#version 330
in vec2 v_uv;
in float v_alpha;
out vec4 frag_color;
uniform vec4 leaf_color;

void main() {
    vec2 center = v_uv - vec2(0.5);
    float ellipse = length(center * vec2(1.0, 0.5));
    if (ellipse > 0.5) discard;
    frag_color = vec4(leaf_color.rgb, leaf_color.a * v_alpha);
}
'''
        self._programs['leaf'] = self._ctx.program(
            vertex_shader=leaf_vs,
            fragment_shader=leaf_fs
        )
        self._programs['leaf']['leaf_color'].value = (0.08, 0.2, 0.08, 0.4)

        ray_vs = '''#version 330
in vec2 in_vert;
in vec4 in_instance;
out float v_intensity;
uniform vec2 screen_size;
uniform float time;

void main() {
    vec2 pos = vec2(in_instance.x, 0.0);
    float width = in_instance.y;
    vec2 local = (in_vert - 0.5) * vec2(width, screen_size.y);
    gl_Position = vec4(pos + local, 0.0, 1.0);
    v_intensity = in_instance.z;
}
'''
        ray_fs = '''#version 330
in float v_intensity;
out vec4 frag_color;
uniform float time;

void main() {
    // 使用 time 做轻微的强度变化
    float intensity = v_intensity * (0.9 + 0.1 * sin(time * 0.3));
    frag_color = vec4(0.706, 0.784, 0.392, intensity);
}
'''
        self._programs['ray'] = self._ctx.program(
            vertex_shader=ray_vs,
            fragment_shader=ray_fs
        )

    def _init_buffers(self) -> None:
        quad = np.array([
            0.0, 0.0, 0.0, 0.0,
            1.0, 0.0, 1.0, 0.0,
            1.0, 1.0, 1.0, 1.0,
            0.0, 0.0, 0.0, 0.0,
            1.0, 1.0, 1.0, 1.0,
            0.0, 1.0, 0.0, 1.0,
        ], dtype='f4')

        self._buffers['quad'] = self._ctx.buffer(quad.tobytes())

        self._buffers['leaf_instance'] = self._ctx.buffer(
            reserve=self.MAX_LAYER_ITEMS * 4 * 4
        )
        self._buffers['ray_instance'] = self._ctx.buffer(
            reserve=self.MAX_LAYER_ITEMS * 4 * 4
        )

        self._vaos['gradient'] = self._ctx.vertex_array(
            self._programs['gradient'],
            self._buffers['quad'],
            'in_vert'
        )

        self._vaos['leaf'] = self._ctx.vertex_array(
            self._programs['leaf'],
            [
                (self._buffers['quad'], '2f 2f/i', 'in_vert', 'in_uv'),
                (self._buffers['leaf_instance'], '4f/i', 'in_instance'),
            ],
            mode=moderngl.TRIANGLES
        )

        self._vaos['ray'] = self._ctx.vertex_array(
            self._programs['ray'],
            [
                (self._buffers['quad'], '2f/i', 'in_vert'),
                (self._buffers['ray_instance'], '4f/i', 'in_instance'),
            ],
            mode=moderngl.TRIANGLES
        )

    def update(self, delta_time: float) -> None:
        """更新背景动画"""
        self._time += delta_time

    def render(self) -> None:
        """渲染背景"""
        w, h = self._screen_size

        # ctx.screen 在 standalone context 下可能不可用，跳过 use()
        if hasattr(self._ctx, 'screen') and self._ctx.screen is not None:
            self._ctx.screen.use()
        self._ctx.clear(0.031, 0.059, 0.031, 1.0)

        # Set gradient uniforms
        self._programs['gradient']['screen_size'].value = (float(w), float(h))
        self._programs['gradient']['time'].value = self._time
        self._vaos['gradient'].render(moderngl.TRIANGLES)

        self._render_leaf_layer(w, h)
        self._render_ray_layer(w, h)

    def _render_leaf_layer(self, w: float, h: float) -> None:
        """渲染叶子层"""
        w, h = self._screen_size

        count = 15
        data = np.zeros(count, dtype='4f')

        for i in range(count):
            x = (i / count) * w * 1.5 - w * 0.25
            y = (np.sin(self._time * 0.2 + i * 0.5) * 0.5 + 0.5) * h
            size = 80 + (i % 5) * 20
            data[i] = (x / w - 1.0, 1.0 - y / h, size / w, size / h)

        self._buffers['leaf_instance'].write(data.tobytes())
        self._programs['leaf']['screen_size'].value = (w, h)
        self._programs['leaf']['time'].value = self._time

        self._ctx.enable(moderngl.BLEND)
        self._ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        # quad 有 6 个顶点
        self._vaos['leaf'].render(moderngl.TRIANGLES, vertices=6, instances=count)

    def _render_ray_layer(self, w: float, h: float) -> None:
        """渲染光线层"""
        w, h = self._screen_size

        count = 3
        data = np.zeros(count, dtype='4f')

        for i in range(count):
            x = (i / count) * w + self._time * 10
            x = x % (w + 100) - 50
            width = 40 + i * 15
            intensity = 0.1 + 0.05 * np.sin(self._time * 0.3 + i)
            data[i] = (x / w - 1.0, width / w, intensity, 0.0)

        self._buffers['ray_instance'].write(data.tobytes())
        self._programs['ray']['screen_size'].value = (w, h)
        self._programs['ray']['time'].value = self._time

        self._ctx.enable(moderngl.BLEND)
        self._ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        # quad 有 6 个顶点
        self._vaos['ray'].render(moderngl.TRIANGLES, vertices=6, instances=count)

    def resize(self, screen_width: int, screen_height: int) -> None:
        """调整尺寸"""
        self._screen_size = (screen_width, screen_height)

    def release(self) -> None:
        for vao in self._vaos.values():
            vao.release()
        for buf in self._buffers.values():
            buf.release()
        for prog in self._programs.values():
            prog.release()
        self._vaos.clear()
        self._buffers.clear()
        self._programs.clear()
