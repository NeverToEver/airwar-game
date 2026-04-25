import moderngl
from typing import Dict, Optional
from pathlib import Path


class ShaderManager:
    """着色器管理器，负责加载和编译 GLSL 着色器"""

    def __init__(self, ctx: moderngl.Context):
        self._ctx = ctx
        self._programs: Dict[str, moderngl.Program] = {}

    def create_program(
        self,
        name: str,
        vertex_source: str,
        fragment_source: str,
        geometry_source: Optional[str] = None
    ) -> moderngl.Program:
        """创建着色器程序

        Args:
            name: 程序名称（用于缓存）
            vertex_source: 顶点着色器源码
            fragment_source: 片段着色器源码
            geometry_source: 可选的几何着色器源码

        Returns:
            编译好的 Program 对象
        """
        if name in self._programs:
            return self._programs[name]

        kwargs = {
            'vertex_shader': vertex_source,
            'fragment_shader': fragment_source,
        }
        if geometry_source:
            kwargs['geometry_shader'] = geometry_source

        program = self._ctx.program(**kwargs)
        self._programs[name] = program
        return program

    def load_from_file(
        self,
        name: str,
        vertex_path: str,
        fragment_path: str,
        geometry_path: Optional[str] = None
    ) -> moderngl.Program:
        """从文件加载着色器源码并创建程序

        Args:
            name: 程序名称
            vertex_path: 顶点着色器文件路径
            fragment_path: 片段着色器文件路径
            geometry_path: 可选的几何着色器文件路径
        """
        with open(vertex_path, 'r') as f:
            vertex_source = f.read()
        with open(fragment_path, 'r') as f:
            fragment_source = f.read()

        geometry_source = None
        if geometry_path:
            with open(geometry_path, 'r') as f:
                geometry_source = f.read()

        return self.create_program(name, vertex_source, fragment_source, geometry_source)

    def get(self, name: str) -> Optional[moderngl.Program]:
        """获取已缓存的着色器程序"""
        return self._programs.get(name)

    def release(self, name: str) -> None:
        """释放指定的着色器程序"""
        if name in self._programs:
            self._programs[name].release()
            del self._programs[name]

    def release_all(self) -> None:
        """释放所有着色器程序"""
        for program in self._programs.values():
            program.release()
        self._programs.clear()


# 内置着色器源码

SPRITE_VERTEX_SHADER = '''#version 330
in vec2 in_vert;
in vec2 in_uv;

out vec2 v_uv;

uniform vec2 translate;
uniform vec2 scale;
uniform float rotation;

void main() {
    mat2 rot = mat2(
        cos(rotation), -sin(rotation),
        sin(rotation), cos(rotation)
    );
    vec2 pos = rot * (in_vert * scale) + translate;
    v_uv = in_uv;
    gl_Position = vec4(pos, 0.0, 1.0);
}
'''

SPRITE_FRAGMENT_SHADER = '''#version 330
in vec2 v_uv;

out vec4 frag_color;

uniform sampler2D sprite;
uniform vec4 tint;
uniform float alpha;

void main() {
    vec4 color = texture(sprite, v_uv) * tint;
    if (color.a < 0.1) discard;
    frag_color = vec4(color.rgb, color.a * alpha);
}
'''

QUAD_VERTEX_SHADER = '''#version 330
in vec2 in_vert;
in vec2 in_uv;

out vec2 v_uv;

uniform mat4 model_view_proj;

void main() {
    v_uv = in_uv;
    gl_Position = model_view_proj * vec4(in_vert, 0.0, 1.0);
}
'''

TEXTURE_FRAGMENT_SHADER = '''#version 330
in vec2 v_uv;

out vec4 frag_color;

uniform sampler2D tex;
uniform float alpha;

void main() {
    vec4 color = texture(tex, v_uv);
    frag_color = vec4(color.rgb, color.a * alpha);
}
'''

SOLID_COLOR_FRAGMENT_SHADER = '''#version 330
out vec4 frag_color;

uniform vec4 color;

void main() {
    frag_color = color;
}
'''
