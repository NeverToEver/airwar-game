use pyo3::prelude::*;

type BulletUpdateInput = (i64, f32, f32, f32, f32, i32, bool, f32);
type BulletUpdateOutput = (i64, f32, f32, bool);

/// Bullet update data: (id, x, y, vx, vy, `bullet_type`, `is_laser`, `screen_height`)
/// id is u64 to handle Python's arbitrary precision integers
/// Returns: (id, `new_x`, `new_y`, `is_active`)
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

/// Binary buffer variant of `batch_update_bullets` for reduced FFI overhead.
///
/// Buffer layout per bullet (32 bytes, little-endian):
///   [0..8)   u64   id
///   [8..12)  f32   x
///   [12..16) f32   y
///   [16..20) f32   vx
///   [20..24) f32   vy
///   [24]     u8    is_laser (0 or 1)
///   [25..28) [u8;3] padding
///   [28..32) f32   screen_height
const BULLET_BUF_STRIDE: usize = 32;

#[pyfunction]
pub fn batch_update_bullets_buf(buf: &[u8]) -> PyResult<Vec<BulletUpdateOutput>> {
    if buf.len() % BULLET_BUF_STRIDE != 0 {
        return Err(pyo3::exceptions::PyValueError::new_err("bullet buffer length must be multiple of 32"));
    }
    let count = buf.len() / BULLET_BUF_STRIDE;
    let mut results = Vec::with_capacity(count);

    for i in 0..count {
        let offset = i * BULLET_BUF_STRIDE;
        let chunk = &buf[offset..offset + BULLET_BUF_STRIDE];

        let id = i64::from_le_bytes(chunk[0..8].try_into().unwrap());
        let x = f32::from_le_bytes(chunk[8..12].try_into().unwrap());
        let y = f32::from_le_bytes(chunk[12..16].try_into().unwrap());
        let vx = f32::from_le_bytes(chunk[16..20].try_into().unwrap());
        let vy = f32::from_le_bytes(chunk[20..24].try_into().unwrap());
        let is_laser = chunk[24] != 0;
        let screen_height = f32::from_le_bytes(chunk[28..32].try_into().unwrap());

        let new_x = x + vx;
        let new_y = y + vy;

        let is_active = if is_laser {
            true
        } else {
            new_y >= -10.0 && new_y <= screen_height + 10.0
        };

        results.push((id, new_x, new_y, is_active));
    }

    Ok(results)
}
