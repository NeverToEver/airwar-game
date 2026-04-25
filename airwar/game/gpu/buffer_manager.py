import moderngl
import numpy as np
from typing import List, Optional, Tuple


class BufferManager:
    """顶点缓冲区和顶点数组对象管理器"""

    def __init__(self, ctx: moderngl.Context):
        self._ctx = ctx
        self._buffers: dict[str, moderngl.Buffer] = {}
        self._vaos: dict[str, moderngl.VertexArray] = {}

    def create_vbo(self, name: str, data: np.ndarray) -> moderngl.Buffer:
        """创建顶点缓冲区

        Args:
            name: 缓冲区名称
            data: numpy 顶点数据数组

        Returns:
            创建的 Buffer 对象
        """
        if name in self._buffers:
            return self._buffers[name]

        buffer = self._ctx.buffer(data.tobytes())
        self._buffers[name] = buffer
        return buffer

    def create_dynamic_vbo(self, name: str, size: int) -> moderngl.Buffer:
        """创建动态顶点缓冲区（用于频繁更新的数据）

        Args:
            name: 缓冲区名称
            size: 缓冲区大小（字节）

        Returns:
            创建的 Buffer 对象
        """
        if name in self._buffers:
            return self._buffers[name]

        buffer = self._ctx.buffer(reserve=size)
        self._buffers[name] = buffer
        return buffer

    def update_vbo(self, name: str, data: np.ndarray, offset: int = 0) -> None:
        """更新顶点缓冲区数据

        Args:
            name: 缓冲区名称
            data: 新的顶点数据
            offset: 写入偏移量（字节）
        """
        if name not in self._buffers:
            raise KeyError(f"Buffer '{name}' not found")

        self._buffers[name].write(data.tobytes(), offset=offset)

    def create_vao(
        self,
        name: str,
        program: moderngl.Program,
        vbo_name: str,
        *attributes: str
    ) -> moderngl.VertexArray:
        """创建顶点数组对象

        Args:
            name: VAO 名称
            program: 着色器程序
            vbo_name: 顶点缓冲区名称
            *attributes: 属性名列表

        Returns:
            创建的 VAO 对象
        """
        key = f"{name}_{vbo_name}"
        if key in self._vaos:
            return self._vaos[key]

        vbo = self._buffers.get(vbo_name)
        if not vbo:
            raise KeyError(f"VBO '{vbo_name}' not found")

        vao = self._ctx.vertex_array(program, vbo, *attributes)
        self._vaos[key] = vao
        return vao

    def create_instanced_vao(
        self,
        name: str,
        program: moderngl.Program,
        vbo_name: str,
        instance_vbo_name: str,
        *attributes: str,
        instance_attributes: str
    ) -> moderngl.VertexArray:
        """创建实例化 VAO（用于批量渲染相同类型的实体）

        Args:
            name: VAO 名称
            program: 着色器程序
            vbo_name: 顶点缓冲区名称
            instance_vbo_name: 实例数据缓冲区名称
            *attributes: 顶点属性名
            instance_attributes: 实例属性名
        """
        key = f"{name}_{vbo_name}_instanced"
        if key in self._vaos:
            return self._vaos[key]

        vbo = self._buffers.get(vbo_name)
        instance_vbo = self._buffers.get(instance_vbo_name)

        if not vbo:
            raise KeyError(f"VBO '{vbo_name}' not found")
        if not instance_vbo:
            raise KeyError(f"Instance VBO '{instance_vbo_name}' not found")

        vao = self._ctx.vertex_array(
            program,
            [(vbo, '2f 2f/i', *attributes), (instance_vbo, '4f/i', instance_attributes)],
            mode=moderngl.TRIANGLES
        )

        self._vaos[key] = vao
        return vao

    def get_buffer(self, name: str) -> Optional[moderngl.Buffer]:
        """获取缓冲区"""
        return self._buffers.get(name)

    def get_vao(self, name: str, vbo_name: str) -> Optional[moderngl.VertexArray]:
        """获取 VAO"""
        return self._vaos.get(f"{name}_{vbo_name}")

    def release(self, name: str, release_vaos: bool = True) -> None:
        """释放缓冲区及其 VAO"""
        if name in self._buffers:
            self._buffers[name].release()
            del self._buffers[name]

        if release_vaos:
            keys_to_delete = [k for k in self._vaos.keys() if k.startswith(f"{name}_")]
            for key in keys_to_delete:
                self._vaos[key].release()
                del self._vaos[key]

    def release_all(self) -> None:
        """释放所有缓冲区和 VAO"""
        for buffer in self._buffers.values():
            buffer.release()
        for vao in self._vaos.values():
            vao.release()
        self._buffers.clear()
        self._vaos.clear()


def create_quad_vertices(
    width: float = 1.0,
    height: float = 1.0
) -> np.ndarray:
    """创建矩形顶点数据（两个三角形）

    返回格式: x, y, u, v
    """
    w, h = width / 2, height / 2
    return np.array([
        -w, -h, 0.0, 0.0,
         w, -h, 1.0, 0.0,
         w,  h, 1.0, 1.0,
        -w, -h, 0.0, 0.0,
         w,  h, 1.0, 1.0,
        -w,  h, 0.0, 1.0,
    ], dtype='f4')


def create_sprite_vertices(
    x: float,
    y: float,
    width: float,
    height: float
) -> np.ndarray:
    """创建精灵顶点数据（带位置）

    Args:
        x, y: 中心位置
        width, height: 精灵尺寸
    """
    w, h = width / 2, height / 2
    return np.array([
        x - w, y - h, 0.0, 0.0,
        x + w, y - h, 1.0, 0.0,
        x + w, y + h, 1.0, 1.0,
        x - w, y - h, 0.0, 0.0,
        x + w, y + h, 1.0, 1.0,
        x - w, y + h, 0.0, 1.0,
    ], dtype='f4')
