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

/// 向量叉积（返回标量）
#[pyfunction]
pub fn vec2_cross(x1: f32, y1: f32, x2: f32, y2: f32) -> f32 {
    x1 * y2 - y1 * x2
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

/// 向量长度平方（避免开方，更快）
#[pyfunction]
pub fn vec2_length_squared(x: f32, y: f32) -> f32 {
    x * x + y * y
}

/// 向量距离平方（避免开方，更快）
#[pyfunction]
pub fn vec2_distance_squared(x1: f32, y1: f32, x2: f32, y2: f32) -> f32 {
    let dx = x2 - x1;
    let dy = y2 - y1;
    dx * dx + dy * dy
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
    let len_sq = x * x + y * y;
    if len_sq > max_length * max_length {
        let len = len_sq.sqrt();
        (x / len * max_length, y / len * max_length)
    } else {
        (x, y)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vec2_length() {
        assert!((vec2_length(3.0, 4.0) - 5.0).abs() < 0.001);
        assert!((vec2_length(0.0, 0.0) - 0.0).abs() < 0.001);
    }

    #[test]
    fn test_vec2_normalize() {
        let (x, y) = vec2_normalize(3.0, 4.0);
        assert!((x - 0.6).abs() < 0.001);
        assert!((y - 0.8).abs() < 0.001);
        let (x, y) = vec2_normalize(0.0, 0.0);
        assert_eq!((x, y), (0.0, 0.0));
    }

    #[test]
    fn test_vec2_distance() {
        let d = vec2_distance(0.0, 0.0, 3.0, 4.0);
        assert!((d - 5.0).abs() < 0.001);
    }

    #[test]
    fn test_vec2_dot() {
        assert!((vec2_dot(1.0, 0.0, 0.0, 1.0) - 0.0).abs() < 0.001);
        assert!((vec2_dot(1.0, 0.0, 1.0, 0.0) - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_vec2_cross() {
        assert!((vec2_cross(1.0, 0.0, 0.0, 1.0) - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_vec2_add() {
        let (x, y) = vec2_add(1.0, 2.0, 3.0, 4.0);
        assert_eq!(x, 4.0);
        assert_eq!(y, 6.0);
    }

    #[test]
    fn test_vec2_sub() {
        let (x, y) = vec2_sub(5.0, 7.0, 2.0, 3.0);
        assert_eq!(x, 3.0);
        assert_eq!(y, 4.0);
    }

    #[test]
    fn test_vec2_scale() {
        let (x, y) = vec2_scale(2.0, 3.0, 2.0);
        assert_eq!(x, 4.0);
        assert_eq!(y, 6.0);
    }

    #[test]
    fn test_vec2_length_squared() {
        assert!((vec2_length_squared(3.0, 4.0) - 25.0).abs() < 0.001);
    }

    #[test]
    fn test_vec2_distance_squared() {
        assert!((vec2_distance_squared(0.0, 0.0, 3.0, 4.0) - 25.0).abs() < 0.001);
    }

    #[test]
    fn test_vec2_lerp() {
        let (x, y) = vec2_lerp(0.0, 0.0, 10.0, 10.0, 0.5);
        assert!((x - 5.0).abs() < 0.001);
        assert!((y - 5.0).abs() < 0.001);
    }

    #[test]
    fn test_vec2_clamp_length() {
        let (x, y) = vec2_clamp_length(10.0, 0.0, 5.0);
        assert!((x - 5.0).abs() < 0.001);
        assert_eq!(y, 0.0);
        let (x, y) = vec2_clamp_length(3.0, 4.0, 10.0);
        assert!((x - 3.0).abs() < 0.001);
        assert!((y - 4.0).abs() < 0.001);
    }
}