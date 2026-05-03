use pyo3::prelude::*;

type BulletUpdateInput = (u64, f32, f32, f32, f32, i32, bool, f32);
type BulletUpdateOutput = (u64, f32, f32, bool);

/// Bullet update data: (id, x, y, vx, vy, bullet_type, is_laser, screen_height)
/// id is u64 to handle Python's arbitrary precision integers
/// Returns: (id, new_x, new_y, is_active)
#[pyfunction]
pub fn batch_update_bullets(bullets: Vec<BulletUpdateInput>) -> Vec<BulletUpdateOutput> {
    let mut results = Vec::with_capacity(bullets.len());

    for (id, x, y, vx, vy, _bullet_type, is_laser, screen_height) in bullets {
        let new_x = x + vx;
        let new_y = y + vy;

        // Check if bullet is off-screen (only for non-laser bullets)
        let is_active = if is_laser {
            // Lasers stay active (handled by trail system)
            true
        } else {
            new_y >= -10.0 && new_y <= screen_height + 10.0
        };

        results.push((id, new_x, new_y, is_active));
    }

    results
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_batch_update_bullets_basic() {
        // (id, x, y, vx, vy, bullet_type, is_laser, screen_height)
        let bullets: Vec<BulletUpdateInput> = vec![
            (0u64, 100.0, 100.0, 0.0, -10.0, 0, false, 800.0), // Active: moving up
            (1u64, 200.0, -20.0, 0.0, -10.0, 0, false, 800.0), // Inactive: off screen top
            (2u64, 300.0, 850.0, 0.0, 10.0, 0, false, 800.0),  // Inactive: off screen bottom
        ];
        let results = batch_update_bullets(bullets);
        assert_eq!(results.len(), 3);
        // Bullet 0: still active (moved to y=90)
        assert_eq!(results[0].0, 0);
        assert!((results[0].1 - 100.0).abs() < 0.001);
        assert!((results[0].2 - 90.0).abs() < 0.001);
        assert!(results[0].3);
        // Bullet 1: off screen top, inactive
        assert_eq!(results[1].0, 1);
        assert!(!results[1].3);
        // Bullet 2: off screen bottom (y=860 > 810), inactive
        assert_eq!(results[2].0, 2);
        assert!(!results[2].3);
    }

    #[test]
    fn test_batch_update_bullets_laser_stays_active() {
        let bullets: Vec<BulletUpdateInput> = vec![
            (0u64, 100.0, -50.0, 0.0, -5.0, 2, true, 800.0), // laser, off top but stays active
        ];
        let results = batch_update_bullets(bullets);
        assert_eq!(results.len(), 1);
        // Laser should stay active regardless of position
        assert!(results[0].3);
    }
}
