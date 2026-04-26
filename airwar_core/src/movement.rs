use pyo3::prelude::*;

/// Movement pattern type (matches Python's move_type strings)
/// 0 = straight, 1 = sine, 2 = zigzag, 3 = dive, 4 = hover, 5 = spiral
/// 6 = noise, 7 = aggressive
#[derive(Debug, Clone, Copy, PartialEq)]
#[repr(u8)]
pub enum MovementType {
    Straight = 0,
    Sine = 1,
    Zigzag = 2,
    Dive = 3,
    Hover = 4,
    Spiral = 5,
    Noise = 6,
    Aggressive = 7,
}

impl MovementType {
    pub fn from_u8(v: u8) -> Self {
        match v {
            1 => MovementType::Sine,
            2 => MovementType::Zigzag,
            3 => MovementType::Dive,
            4 => MovementType::Hover,
            5 => MovementType::Spiral,
            6 => MovementType::Noise,
            7 => MovementType::Aggressive,
            _ => MovementType::Straight,
        }
    }
}

/// Smooth continuous noise function using cosine interpolation.
/// Returns value in range [-1, 1] with continuous derivatives.
fn smooth_noise(x: f32, seed: i32) -> f32 {
    let int_x = x as i32;
    let frac_x = x - int_x as f32;

    let v1 = ((int_x as f32) * 1.0 + (seed as f32) * 0.1).sin() * 0.5;
    let v2 = ((int_x as f32) * 2.3 + (seed as f32) * 0.2).sin() * 0.3;
    let v3 = ((int_x as f32) * 4.7 + (seed as f32) * 0.3).sin() * 0.2;
    let v4 = ((int_x as f32 + 1.0) * 1.0 + (seed as f32) * 0.1).sin() * 0.5;
    let v5 = ((int_x as f32 + 1.0) * 2.3 + (seed as f32) * 0.2).sin() * 0.3;
    let v6 = ((int_x as f32 + 1.0) * 4.7 + (seed as f32) * 0.3).sin() * 0.2;

    let t = 0.5 - 0.5 * (frac_x * std::f32::consts::PI).cos();
    let val0 = v1 + v2 + v3;
    let val1 = v4 + v5 + v6;

    let result = val0 + (val1 - val0) * t;
    (result * 1.2).clamp(-1.0, 1.0)
}

/// Update a single enemy's movement and return new position
///
/// Parameters:
/// - move_type: 0=straight, 1=sine, 2=zigzag, 3=dive, 4=hover, 5=spiral, 6=noise, 7=aggressive
/// - timer: current timer value
/// - active_x, active_y: the "home" position the enemy moves around
/// - move_range_x, move_range_y: the range of movement around home position
/// - offset: sine offset (phase)
/// - _amplitude: movement amplitude (reserved)
/// - frequency: movement frequency
/// - speed: zigzag speed / noise speed
/// - direction: zigzag direction (1 or -1)
/// - zigzag_interval: frames between direction changes (used as noise seed for noise/aggressive)
/// - _spiral_radius: radius for spiral movement (reserved; used as noise_scale_x for noise/aggressive)
/// - current_x, current_y: current rect position (for max_delta clamping in noise/aggressive)
///
/// Returns: (new_x, new_y, new_timer)
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn update_movement(
    move_type: u8,
    timer: f32,
    active_x: f32,
    active_y: f32,
    move_range_x: f32,
    move_range_y: f32,
    offset: f32,
    _amplitude: f32,
    frequency: f32,
    speed: f32,
    direction: f32,
    zigzag_interval: f32,
    _spiral_radius: f32,
    current_x: f32,
    current_y: f32,
    noise_scale_x: f32,
    noise_scale_y: f32,
    noise_amplitude_x: f32,
    noise_amplitude_y: f32,
    noise_seed: i32,
) -> (f32, f32, f32) {
    let mtype = MovementType::from_u8(move_type);

    let (x, y, out_timer) = match mtype {
        MovementType::Straight => {
            let t = timer + 1.0;
            let x = active_x;
            let y = active_y + (t * 0.05).sin() * (move_range_y * 0.3);
            (x, y, t)
        }
        MovementType::Sine => {
            let t = timer + 1.0;
            let x = active_x + (t * frequency + offset).sin() * move_range_x;
            let y = active_y + (t * frequency * 0.5).sin() * move_range_y;
            (x, y, t)
        }
        MovementType::Zigzag => {
            let t = timer + 1.0;
            let current_interval = t as i32 % zigzag_interval as i32;
            let actual_direction = if current_interval == 0 && t > 0.0 {
                -direction
            } else {
                direction
            };
            let x = active_x + actual_direction * speed;
            let y = active_y + (t * 0.1).sin() * (move_range_y * 0.5);
            (x, y, t)
        }
        MovementType::Dive => {
            let t = timer + 1.0;
            let wave = (t * 0.05).sin() * (move_range_x * 0.3);
            let x = active_x + wave;
            let y = active_y + (t * 0.03).sin() * (move_range_y * 0.3);
            (x, y, t)
        }
        MovementType::Hover => {
            let t = timer + 1.0;
            let v = t * 0.08;
            let x = active_x + v.sin() * move_range_x;
            let y = active_y + (v * 0.7).sin() * (move_range_y * 0.5);
            (x, y, t)
        }
        MovementType::Spiral => {
            let t = timer + 1.0;
            let spiral_x = (t * frequency).cos() * (move_range_x * 0.5);
            let spiral_y = (t * 2.0 * frequency).sin() * (move_range_y * 0.3);
            let x = active_x + spiral_x;
            let y = active_y + spiral_y;
            (x, y, t)
        }
        MovementType::Noise => {
            let increment = speed.max(0.001);
            let t = timer + increment;
            let noise_x = smooth_noise(t * noise_scale_x, noise_seed) * noise_amplitude_x;
            let noise_y = smooth_noise(t * noise_scale_y, noise_seed + 500) * noise_amplitude_y;
            let target_x = active_x + noise_x * 80.0;
            let target_y = active_y + noise_y * 50.0;
            let max_delta: f32 = 6.0;
            let dx = target_x - current_x;
            let dy = target_y - current_y;
            let x = if dx.abs() > max_delta { current_x + max_delta * dx.signum() } else { target_x };
            let y = if dy.abs() > max_delta { current_y + max_delta * dy.signum() } else { target_y };
            (x, y, t)
        }
        MovementType::Aggressive => {
            let increment = speed.max(0.001);
            let t = timer + increment;
            let noise_x = smooth_noise(t * noise_scale_x, noise_seed) * noise_amplitude_x;
            let noise_y = smooth_noise(t * noise_scale_y, noise_seed + 500) * noise_amplitude_y + 0.15;
            let target_x = active_x + noise_x * 96.0;
            let target_y = active_y + noise_y * 60.0;
            let max_delta: f32 = 8.0;
            let dx = target_x - current_x;
            let dy = target_y - current_y;
            let x = if dx.abs() > max_delta { current_x + max_delta * dx.signum() } else { target_x };
            let y = if dy.abs() > max_delta { current_y + max_delta * dy.signum() } else { target_y };
            (x, y, t)
        }
    };

    (x, y, out_timer)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_smooth_noise_range() {
        for i in 0..100 {
            let val = smooth_noise(i as f32 * 0.1, 42);
            assert!(val >= -1.0 && val <= 1.0, "smooth_noise out of range: {}", val);
        }
    }

    #[test]
    fn test_movement_straight() {
        let (x, y, timer) = update_movement(0, 0.0, 100.0, 100.0, 80.0, 40.0, 0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0, 100.0, 100.0, 0.04, 0.02, 0.7, 0.4, 0);
        assert!((x - 100.0).abs() < 0.1);
        assert!(y > 90.0 && y < 120.0);
        assert_eq!(timer, 1.0);
    }

    #[test]
    fn test_movement_noise() {
        let (x, y, timer) = update_movement(6, 0.0, 100.0, 100.0, 80.0, 50.0, 0.0, 2.0, 0.05, 0.0, 0.0, 0.0, 0.0, 100.0, 100.0, 0.04, 0.02, 0.7, 0.4, 9999);
        assert_eq!(timer, 1.0);
        // Should stay within max_delta=6 of current (100, 100)
        assert!((x - 100.0).abs() <= 6.1);
        assert!((y - 100.0).abs() <= 6.1);
    }

    #[test]
    fn test_movement_aggressive() {
        let (x, y, timer) = update_movement(7, 0.0, 100.0, 100.0, 96.0, 60.0, 0.0, 2.0, 0.05, 0.0, 0.0, 0.0, 0.0, 100.0, 100.0, 0.04, 0.02, 0.6, 0.5, 9999);
        assert_eq!(timer, 1.0);
        // Should stay within max_delta=8 of current (100, 100)
        assert!((x - 100.0).abs() <= 8.1);
        assert!((y - 100.0).abs() <= 8.1);
    }

    #[test]
    fn test_movement_types() {
        // All movement types should work without panicking
        for move_type in 0..=7u8 {
            let result = update_movement(move_type, 10.0, 100.0, 100.0, 80.0, 40.0, 0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0, 100.0, 100.0, 0.04, 0.02, 0.7, 0.4, 0);
            assert_eq!(result.2, 11.0);
        }
    }
}