use pyo3::prelude::*;

type MovementBaseParams = (u8, f32, f32, f32, f32, f32, f32, f32, f32, f32, f32, f32);
type MovementExtraParams = (f32, f32, f32, f32, f32, f32, f32, i32);
type MovementResult = (f32, f32, f32);

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
    update_movement_inner(
        move_type,
        timer,
        active_x,
        active_y,
        move_range_x,
        move_range_y,
        offset,
        _amplitude,
        frequency,
        speed,
        direction,
        zigzag_interval,
        _spiral_radius,
        current_x,
        current_y,
        noise_scale_x,
        noise_scale_y,
        noise_amplitude_x,
        noise_amplitude_y,
        noise_seed,
    )
}

/// Batch update multiple enemies' movement in a single FFI call.
///
/// base_params: (move_type, timer, active_x, active_y, move_range_x, move_range_y,
///   offset, amplitude, frequency, speed, direction, zigzag_interval) — 12 elements
/// extra_params: (spiral_radius, current_x, current_y, noise_scale_x, noise_scale_y,
///   noise_amplitude_x, noise_amplitude_y, noise_seed) — 8 elements
///
/// Returns Vec of (new_x, new_y, new_timer) in the same order.
#[pyfunction]
pub fn batch_update_movements(
    base_params: Vec<MovementBaseParams>,
    extra_params: Vec<MovementExtraParams>,
) -> Vec<MovementResult> {
    base_params
        .into_iter()
        .zip(extra_params)
        .map(
            |(
                (
                    move_type,
                    timer,
                    active_x,
                    active_y,
                    move_range_x,
                    move_range_y,
                    offset,
                    amplitude,
                    frequency,
                    speed,
                    direction,
                    zigzag_interval,
                ),
                (
                    spiral_radius,
                    current_x,
                    current_y,
                    noise_scale_x,
                    noise_scale_y,
                    noise_amplitude_x,
                    noise_amplitude_y,
                    noise_seed,
                ),
            )| {
                update_movement_inner(
                    move_type,
                    timer,
                    active_x,
                    active_y,
                    move_range_x,
                    move_range_y,
                    offset,
                    amplitude,
                    frequency,
                    speed,
                    direction,
                    zigzag_interval,
                    spiral_radius,
                    current_x,
                    current_y,
                    noise_scale_x,
                    noise_scale_y,
                    noise_amplitude_x,
                    noise_amplitude_y,
                    noise_seed,
                )
            },
        )
        .collect()
}

/// Inner implementation shared by single and batch variants.
#[allow(clippy::too_many_arguments)]
fn update_movement_inner(
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
    match mtype {
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
            let x = if dx.abs() > max_delta {
                current_x + max_delta * dx.signum()
            } else {
                target_x
            };
            let y = if dy.abs() > max_delta {
                current_y + max_delta * dy.signum()
            } else {
                target_y
            };
            (x, y, t)
        }
        MovementType::Aggressive => {
            let increment = speed.max(0.001);
            let t = timer + increment;
            let noise_x = smooth_noise(t * noise_scale_x, noise_seed) * noise_amplitude_x;
            let noise_y =
                smooth_noise(t * noise_scale_y, noise_seed + 500) * noise_amplitude_y + 0.15;
            let target_x = active_x + noise_x * 96.0;
            let target_y = active_y + noise_y * 60.0;
            let max_delta: f32 = 8.0;
            let dx = target_x - current_x;
            let dy = target_y - current_y;
            let x = if dx.abs() > max_delta {
                current_x + max_delta * dx.signum()
            } else {
                target_x
            };
            let y = if dy.abs() > max_delta {
                current_y + max_delta * dy.signum()
            } else {
                target_y
            };
            (x, y, t)
        }
    }
}

/// Compute boss attack bullet spawn data in Rust.
///
/// Returns a list of (start_x, start_y, vx, vy, speed, bullet_type_code, damage) tuples
/// where bullet_type_code: 0=spread, 1=laser, 2=single.
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn compute_boss_attack(
    pattern: u8, // 0=spread, 1=aim, 2=wave
    phase: u8,
    attack_dir: u8, // 0=down, 1=left, 2=right, 3=up
    center_x: f32,
    _center_y: f32,
    rect_bottom: f32,
    rect_left: f32,
    rect_right: f32,
    rect_top: f32,
) -> Vec<(f32, f32, f32, f32, f32, u8, i32)> {
    let (base_angle, y_base) = match attack_dir {
        0 => (-90.0_f32, rect_bottom),
        1 => (180.0, (rect_top + rect_bottom) / 2.0),
        2 => (0.0, (rect_top + rect_bottom) / 2.0),
        _ => (90.0, rect_top),
    };
    let angle_rad = |deg: f32| deg * std::f32::consts::PI / 180.0;

    match pattern {
        0 => {
            // Spread attack
            let count = 5 + phase as i32;
            let spread_angle: f32 = if attack_dir == 1 || attack_dir == 2 {
                45.0
            } else {
                180.0
            };
            let offset = if attack_dir == 1 || attack_dir == 2 {
                22.5
            } else {
                0.0
            };
            let speed: f32 = 5.0;
            let damage: i32 = 12 + phase as i32 * 2;
            (0..count)
                .map(|i| {
                    let t = if count > 1 {
                        i as f32 / (count - 1) as f32
                    } else {
                        0.0
                    };
                    let angle = base_angle + (spread_angle * t) - offset;
                    let rad = angle_rad(angle);
                    (
                        center_x,
                        y_base,
                        rad.cos() * speed,
                        rad.sin() * speed,
                        speed,
                        0u8,
                        damage,
                    )
                })
                .collect()
        }
        1 => {
            // Aim attack — 3 bullets
            let (source_x, source_y) = match attack_dir {
                0 => (center_x, rect_bottom),
                1 => (rect_left, (rect_top + rect_bottom) / 2.0),
                2 => (rect_right, (rect_top + rect_bottom) / 2.0),
                _ => (center_x, rect_top),
            };
            let speed: f32 = 7.0;
            let damage: i32 = 18 + phase as i32 * 3;
            let dx = if attack_dir == 0 {
                0.0
            } else if attack_dir == 1 {
                -500.0
            } else if attack_dir == 2 {
                500.0
            } else {
                0.0
            };
            let dy = if attack_dir == 0 {
                500.0
            } else if attack_dir == 3 {
                -500.0
            } else {
                0.0
            };
            let len = f32::sqrt(dx * dx + dy * dy).max(0.001);
            let nx = dx / len;
            let ny = dy / len;
            let offsets: [f32; 3] = [-30.0, 0.0, 30.0];
            offsets
                .iter()
                .map(|&off| {
                    let sx = source_x + off;
                    (sx, source_y, nx * speed, ny * speed, speed, 1u8, damage)
                })
                .collect()
        }
        _ => {
            // Wave attack — 8 bullets
            let (source_x, source_y) = match attack_dir {
                0 => (center_x, rect_bottom),
                1 => (rect_left, (rect_top + rect_bottom) / 2.0),
                2 => (rect_right, (rect_top + rect_bottom) / 2.0),
                _ => (center_x, rect_top),
            };
            let speed: f32 = 4.0;
            let damage: i32 = 12;
            let interval: f32 = 22.5;
            (0..8)
                .map(|i| {
                    let angle = base_angle + interval * i as f32;
                    let rad = angle_rad(angle);
                    (
                        source_x,
                        source_y,
                        rad.cos() * speed,
                        rad.sin() * speed,
                        speed,
                        2u8,
                        damage,
                    )
                })
                .collect()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_smooth_noise_range() {
        for i in 0..100 {
            let val = smooth_noise(i as f32 * 0.1, 42);
            assert!(
                (-1.0..=1.0).contains(&val),
                "smooth_noise out of range: {}",
                val
            );
        }
    }

    #[test]
    fn test_movement_straight() {
        let (x, y, timer) = update_movement(
            0, 0.0, 100.0, 100.0, 80.0, 40.0, 0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0, 100.0, 100.0,
            0.04, 0.02, 0.7, 0.4, 0,
        );
        assert!((x - 100.0).abs() < 0.1);
        assert!(y > 90.0 && y < 120.0);
        assert_eq!(timer, 1.0);
    }

    #[test]
    fn test_movement_noise() {
        let (x, y, timer) = update_movement(
            6, 0.0, 100.0, 100.0, 80.0, 50.0, 0.0, 2.0, 0.05, 0.0, 0.0, 0.0, 0.0, 100.0, 100.0,
            0.04, 0.02, 0.7, 0.4, 9999,
        );
        assert_eq!(timer, 0.001);
        // Should stay within max_delta=6 of current (100, 100)
        assert!((x - 100.0).abs() <= 6.1);
        assert!((y - 100.0).abs() <= 6.1);
    }

    #[test]
    fn test_movement_aggressive() {
        let (x, y, timer) = update_movement(
            7, 0.0, 100.0, 100.0, 96.0, 60.0, 0.0, 2.0, 0.05, 0.0, 0.0, 0.0, 0.0, 100.0, 100.0,
            0.04, 0.02, 0.6, 0.5, 9999,
        );
        assert_eq!(timer, 0.001);
        // Should stay within max_delta=8 of current (100, 100)
        assert!((x - 100.0).abs() <= 8.1);
        assert!((y - 100.0).abs() <= 8.1);
    }

    #[test]
    fn test_movement_types() {
        // Types 0-5 return timer+1, types 6-7 return timer+speed
        for move_type in 0..=5u8 {
            let result = update_movement(
                move_type, 10.0, 100.0, 100.0, 80.0, 40.0, 0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0,
                100.0, 100.0, 0.04, 0.02, 0.7, 0.4, 0,
            );
            assert_eq!(result.2, 11.0);
        }
        // Noise returns timer+2.0 (speed), Aggressive returns timer+2.0 (speed)
        for move_type in 6..=7u8 {
            let result = update_movement(
                move_type, 10.0, 100.0, 100.0, 80.0, 40.0, 0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0,
                100.0, 100.0, 0.04, 0.02, 0.7, 0.4, 0,
            );
            assert_eq!(result.2, 12.0);
        }
    }

    #[test]
    fn test_batch_update_movements() {
        let base: Vec<MovementBaseParams> = vec![(
            0, 0.0, 200.0, 150.0, 80.0, 40.0, 0.0, 2.0, 0.05, 2.0, 1.0, 45.0,
        )];
        let extra: Vec<MovementExtraParams> = vec![(40.0, 200.0, 150.0, 0.04, 0.02, 0.7, 0.4, 0)];
        let results = batch_update_movements(base, extra);
        assert_eq!(results.len(), 1);
        assert!((results[0].0 - 200.0).abs() < 1.0);
    }
}
