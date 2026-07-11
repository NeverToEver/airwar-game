use pyo3::prelude::*;

/// 计算向量长度
#[pyfunction]
pub fn vec2_length(x: f32, y: f32) -> f32 {
    (x * x + y * y).sqrt()
}

/// 归一化向量
#[pyfunction]
pub fn vec2_normalize(x: f32, y: f32) -> (f32, f32) {
    let len = (x * x + y * y).sqrt();
    if len > 0.0 {
        (x / len, y / len)
    } else {
        (0.0, 0.0)
    }
}

/// 向量加法
#[pyfunction]
pub fn vec2_add(x1: f32, y1: f32, x2: f32, y2: f32) -> (f32, f32) {
    (x1 + x2, y1 + y2)
}

/// 向量减法
#[pyfunction]
pub fn vec2_sub(x1: f32, y1: f32, x2: f32, y2: f32) -> (f32, f32) {
    (x1 - x2, y1 - y2)
}

/// 向量点积
#[pyfunction]
pub fn vec2_dot(x1: f32, y1: f32, x2: f32, y2: f32) -> f32 {
    x1 * x2 + y1 * y2
}

/// 标量乘法
#[pyfunction]
pub fn vec2_scale(x: f32, y: f32, scalar: f32) -> (f32, f32) {
    (x * scalar, y * scalar)
}

/// 向量距离
#[pyfunction]
pub fn vec2_distance(x1: f32, y1: f32, x2: f32, y2: f32) -> f32 {
    let dx = x2 - x1;
    let dy = y2 - y1;
    (dx * dx + dy * dy).sqrt()
}

/// 向量角度（弧度）
#[pyfunction]
pub fn vec2_angle(x: f32, y: f32) -> f32 {
    y.atan2(x)
}

/// 从角度创建向量
#[pyfunction]
pub fn vec2_from_angle(angle: f32, length: f32) -> (f32, f32) {
    (angle.cos() * length, angle.sin() * length)
}

/// 线性插值
#[pyfunction]
pub fn vec2_lerp(x1: f32, y1: f32, x2: f32, y2: f32, t: f32) -> (f32, f32) {
    (x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)
}

/// 向量限制（裁剪长度）
#[pyfunction]
pub fn vec2_clamp_length(x: f32, y: f32, max_length: f32) -> (f32, f32) {
    let max_length = max_length.abs();
    let len_sq = x * x + y * y;
    if len_sq > max_length * max_length {
        let len = len_sq.sqrt();
        (x / len * max_length, y / len * max_length)
    } else {
        (x, y)
    }
}
