use pyo3::prelude::*;

/// Movement pattern type (matches Python's move_type strings)
/// 0 = straight, 1 = sine, 2 = zigzag, 3 = dive, 4 = hover, 5 = spiral
#[derive(Debug, Clone, Copy, PartialEq)]
#[repr(u8)]
pub enum MovementType {
    Straight = 0,
    Sine = 1,
    Zigzag = 2,
    Dive = 3,
    Hover = 4,
    Spiral = 5,
}

impl MovementType {
    pub fn from_u8(v: u8) -> Self {
        match v {
            1 => MovementType::Sine,
            2 => MovementType::Zigzag,
            3 => MovementType::Dive,
            4 => MovementType::Hover,
            5 => MovementType::Spiral,
            _ => MovementType::Straight,
        }
    }
}

/// Update a single enemy's movement and return new position
///
/// Parameters:
/// - move_type: 0=straight, 1=sine, 2=zigzag, 3=dive, 4=hover, 5=spiral
/// - timer: current timer value
/// - active_x, active_y: the "home" position the enemy moves around
/// - move_range_x, move_range_y: the range of movement around home position
/// - offset: sine offset (phase)
/// - _amplitude: movement amplitude (reserved)
/// - frequency: movement frequency
/// - speed: zigzag speed
/// - direction: zigzag direction (1 or -1)
/// - zigzag_interval: frames between direction changes
/// - _spiral_radius: radius for spiral movement (reserved)
///
/// Returns: (new_x, new_y, new_timer)
#[pyfunction]
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
) -> (f32, f32, f32) {
    let mtype = MovementType::from_u8(move_type);
    let new_timer = timer + 1.0;

    let (x, y) = match mtype {
        MovementType::Straight => {
            let x = active_x;
            let y = active_y + (new_timer * 0.05).sin() * (move_range_y * 0.3);
            (x, y)
        }
        MovementType::Sine => {
            let x = active_x + (new_timer * frequency + offset).sin() * move_range_x;
            let y = active_y + (new_timer * frequency * 0.5).sin() * move_range_y;
            (x, y)
        }
        MovementType::Zigzag => {
            let current_interval = new_timer as i32 % zigzag_interval as i32;
            let actual_direction = if current_interval == 0 && new_timer > 0.0 {
                -direction
            } else {
                direction
            };
            // NOTE: Rust zigzag differs from Python fallback:
            // Python accumulates from current x: new_x = self.rect.x + direction * speed
            // Rust computes from active_x: x = active_x + direction * speed
            // This makes Rust zigzag oscillate by only ~speed px instead of accumulating.
            // The Python fallback is used for zigzag in Enemy.update() instead.
            let x = active_x + actual_direction * speed;
            let y = active_y + (new_timer * 0.1).sin() * (move_range_y * 0.5);
            (x, y)
        }
        MovementType::Dive => {
            let wave = (new_timer * 0.05).sin() * (move_range_x * 0.3);
            let x = active_x + wave;
            let y = active_y + (new_timer * 0.03).sin() * (move_range_y * 0.3);
            (x, y)
        }
        MovementType::Hover => {
            let t = new_timer * 0.08;
            let x = active_x + t.sin() * move_range_x;
            let y = active_y + (t * 0.7).sin() * (move_range_y * 0.5);
            (x, y)
        }
        MovementType::Spiral => {
            let t = new_timer * frequency;
            let spiral_x = t.cos() * (move_range_x * 0.5);
            let spiral_y = (t * 2.0).sin() * (move_range_y * 0.3);
            let x = active_x + spiral_x;
            let y = active_y + spiral_y;
            (x, y)
        }
    };

    (x, y, new_timer)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_movement_straight() {
        let (x, y, timer) = update_movement(0, 0.0, 100.0, 100.0, 80.0, 40.0, 0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0);
        assert!((x - 100.0).abs() < 0.1);
        assert!(y > 90.0 && y < 120.0);
        assert_eq!(timer, 1.0);
    }

    #[test]
    fn test_movement_sine() {
        // With timer=0 and frequency=0.05, after increment new_timer=1.0
        // x = active_x + sin(1.0 * 0.05 + 0) * 80 = 100 + sin(0.05) * 80 ≈ 100 + 4
        let (x, y, timer) = update_movement(1, 0.0, 100.0, 100.0, 80.0, 40.0, 0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0);
        // x should be close to 100 + sin(0.05)*80 ≈ 104
        assert!(x > 100.0 && x < 110.0);
        assert_eq!(timer, 1.0);
    }

    #[test]
    fn test_movement_zigzag() {
        let (_, _, timer) = update_movement(2, 0.0, 100.0, 100.0, 80.0, 40.0, 0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0);
        assert_eq!(timer, 1.0);
    }

    #[test]
    fn test_movement_types() {
        // All movement types should work without panicking
        for move_type in 0..=5u8 {
            let result = update_movement(move_type, 10.0, 100.0, 100.0, 80.0, 40.0, 0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0);
            assert_eq!(result.2, 11.0); // timer should increment
        }
    }
}