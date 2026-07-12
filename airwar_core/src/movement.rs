use pyo3::prelude::*;

type MovementBaseParams = (u8, f32, f32, f32, f32, f32, f32, f32, f32, f32, f32, f32);
type MovementExtraParams = (f32, f32, f32, f32, f32, f32, f32, i32);
type MovementResult = (f32, f32, f32);

/// Movement pattern type (matches Python's `move_type` strings)
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
/// - `move_type`: 0=straight, 1=sine, 2=zigzag, 3=dive, 4=hover, 5=spiral, 6=noise, 7=aggressive
/// - timer: current timer value
/// - `active_x`, `active_y`: the "home" position the enemy moves around
/// - `move_range_x`, `move_range_y`: the range of movement around home position
/// - offset: sine offset (phase)
/// - amplitude: movement amplitude (reserved)
/// - frequency: movement frequency
/// - speed: zigzag speed / noise speed
/// - direction: zigzag direction (1 or -1)
/// - `zigzag_interval`: frames between direction changes (used as noise seed for noise/aggressive)
/// - `spiral_radius`: radius for spiral movement (reserved; used as `noise_scale_x` for noise/aggressive)
/// - `current_x`, `current_y`: current rect position (for `max_delta` clamping in noise/aggressive)
///
/// Returns: (`new_x`, `new_y`, `new_timer`)
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
    amplitude: f32,
    frequency: f32,
    speed: f32,
    direction: f32,
    zigzag_interval: f32,
    spiral_radius: f32,
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
}

/// Batch update multiple enemies' movement in a single FFI call.
///
/// `base_params`: (`move_type`, timer, `active_x`, `active_y`, `move_range_x`, `move_range_y`,
///   offset, amplitude, frequency, speed, direction, `zigzag_interval`) — 12 elements
/// `extra_params`: (`spiral_radius`, `current_x`, `current_y`, `noise_scale_x`, `noise_scale_y`,
///   `noise_amplitude_x`, `noise_amplitude_y`, `noise_seed`) — 8 elements
///
/// Returns Vec of (`new_x`, `new_y`, `new_timer`) in the same order.
#[pyfunction]
pub fn batch_update_movements(
    base_params: Vec<MovementBaseParams>,
    extra_params: Vec<MovementExtraParams>,
) -> PyResult<Vec<MovementResult>> {
    if base_params.len() != extra_params.len() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "base_params and extra_params must have same length",
        ));
    }
    Ok(base_params
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
        .collect())
}

/// Binary buffer variant of `batch_update_movements` for reduced FFI overhead.
///
/// base_buf layout per enemy (48 bytes, little-endian):
///   [0]      u8    move_type
///   [1..3)   [u8;2] padding
///   [4..8)   f32   timer
///   [8..12)  f32   active_x
///   [12..16) f32   active_y
///   [16..20) f32   move_range_x
///   [20..24) f32   move_range_y
///   [24..28) f32   offset
///   [28..32) f32   amplitude
///   [32..36) f32   frequency
///   [36..40) f32   speed
///   [40..44) f32   direction
///   [44..48) f32   zigzag_interval
///
/// extra_buf layout per enemy (32 bytes, little-endian):
///   [0..4)   f32   spiral_radius
///   [4..8)   f32   current_x
///   [8..12)  f32   current_y
///   [12..16) f32   noise_scale_x
///   [16..20) f32   noise_scale_y
///   [20..24) f32   noise_amplitude_x
///   [24..28) f32   noise_amplitude_y
///   [28..32) i32   noise_seed
const BASE_BUF_STRIDE: usize = 48;
const EXTRA_BUF_STRIDE: usize = 32;

#[pyfunction]
pub fn batch_update_movements_buf(
    base_buf: &[u8],
    extra_buf: &[u8],
) -> PyResult<Vec<MovementResult>> {
    let count = base_buf.len() / BASE_BUF_STRIDE;
    if !base_buf.len().is_multiple_of(BASE_BUF_STRIDE) || extra_buf.len() < count * EXTRA_BUF_STRIDE {
        return Err(pyo3::exceptions::PyValueError::new_err("movement buffers length mismatch"));
    }
    let mut results = Vec::with_capacity(count);

    for i in 0..count {
        let bo = i * BASE_BUF_STRIDE;
        let bc = &base_buf[bo..bo + BASE_BUF_STRIDE];

        let move_type = bc[0];
        let timer = f32::from_le_bytes(bc[4..8].try_into().unwrap());
        let active_x = f32::from_le_bytes(bc[8..12].try_into().unwrap());
        let active_y = f32::from_le_bytes(bc[12..16].try_into().unwrap());
        let move_range_x = f32::from_le_bytes(bc[16..20].try_into().unwrap());
        let move_range_y = f32::from_le_bytes(bc[20..24].try_into().unwrap());
        let offset = f32::from_le_bytes(bc[24..28].try_into().unwrap());
        let amplitude = f32::from_le_bytes(bc[28..32].try_into().unwrap());
        let frequency = f32::from_le_bytes(bc[32..36].try_into().unwrap());
        let speed = f32::from_le_bytes(bc[36..40].try_into().unwrap());
        let direction = f32::from_le_bytes(bc[40..44].try_into().unwrap());
        let zigzag_interval = f32::from_le_bytes(bc[44..48].try_into().unwrap());

        let eo = i * EXTRA_BUF_STRIDE;
        let ec = &extra_buf[eo..eo + EXTRA_BUF_STRIDE];

        let spiral_radius = f32::from_le_bytes(ec[0..4].try_into().unwrap());
        let current_x = f32::from_le_bytes(ec[4..8].try_into().unwrap());
        let current_y = f32::from_le_bytes(ec[8..12].try_into().unwrap());
        let noise_scale_x = f32::from_le_bytes(ec[12..16].try_into().unwrap());
        let noise_scale_y = f32::from_le_bytes(ec[16..20].try_into().unwrap());
        let noise_amplitude_x = f32::from_le_bytes(ec[20..24].try_into().unwrap());
        let noise_amplitude_y = f32::from_le_bytes(ec[24..28].try_into().unwrap());
        let noise_seed = i32::from_le_bytes(ec[28..32].try_into().unwrap());

        let result = update_movement_inner(
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
        );
        results.push(result);
    }

    Ok(results)
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
    if !active_x.is_finite() || !active_y.is_finite() || !current_x.is_finite() || !current_y.is_finite() {
        return (current_x, current_y, timer);
    }
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
            let interval = (zigzag_interval as i32).max(1);
            let current_interval = t as i32 % interval;
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
            let noise_y = smooth_noise(t * noise_scale_y, noise_seed + 500) * noise_amplitude_y + 0.15;
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

/// Batch-compute hallucinated enemy positions for the haunting visual system.
///
/// For each enemy `(cx, cy, entity_id)`, compute a jittered, optionally lunging
/// position based on frame counter, haunting strength, and player proximity.
#[pyfunction]
#[pyo3(signature = (enemies, player_center, frame, strength, lunge_scale))]
pub fn batch_hallucinated_enemy_centers(
    enemies: Vec<(f32, f32, i64)>,
    player_center: Option<(f32, f32)>,
    frame: i64,
    strength: f32,
    lunge_scale: f32,
) -> Vec<(f32, f32)> {
    let f = frame as f32;
    enemies
        .into_iter()
        .map(|(cx, cy, entity_id)| {
            let eid = entity_id as f32;
            let pulse = (f * 0.13 + eid % 31.0).sin().max(0.0);
            let jitter_x = (f * 0.21 + eid % 17.0).sin() * 8.0 * strength;
            let jitter_y = (f * 0.18 + eid % 23.0).cos() * 6.0 * strength;

            let (lx, ly) = match player_center {
                Some((px, py)) => {
                    let dx = px - cx;
                    let dy = py - cy;
                    let length = dx.hypot(dy);
                    if length <= 0.001 {
                        (0.0, 0.0)
                    } else {
                        let lunge = pulse * (12.0 + 36.0 * strength) * lunge_scale;
                        (dx / length * lunge, dy / length * lunge)
                    }
                }
                None => (0.0, 0.0),
            };

            (cx + jitter_x + lx, cy + jitter_y + ly)
        })
        .collect()
}

/// Find the candidate nearest to (`query_x`, `query_y`) by squared Euclidean distance.
#[pyfunction]
#[pyo3(signature = (candidates, query_x, query_y))]
pub fn find_nearest_target(candidates: Vec<(i64, f32, f32)>, query_x: f32, query_y: f32) -> Option<i64> {
    candidates
        .into_iter()
        .min_by(|(_, x1, y1), (_, x2, y2)| {
            let d1 = (x1 - query_x).powi(2) + (y1 - query_y).powi(2);
            let d2 = (x2 - query_x).powi(2) + (y2 - query_y).powi(2);
            d1.partial_cmp(&d2).unwrap_or(std::cmp::Ordering::Equal)
        })
        .map(|(id, _, _)| id)
}

/// Find the candidate most in the direction of mouse movement using dot-product
/// scoring. Only targets with dot >= `direction_cone_dot` are considered.
#[pyfunction]
#[pyo3(signature = (candidates, origin_x, origin_y, move_x, move_y, direction_cone_dot, exclude_id))]
pub fn find_target_in_direction(
    candidates: Vec<(i64, f32, f32)>,
    origin_x: f32,
    origin_y: f32,
    move_x: f32,
    move_y: f32,
    direction_cone_dot: f32,
    exclude_id: Option<i64>,
) -> Option<i64> {
    let movement_len = move_x.hypot(move_y);
    if movement_len <= 0.0 {
        return None;
    }
    let mx = move_x / movement_len;
    let my = move_y / movement_len;

    let mut best_id = None;
    let mut best_score = 0.0f32;
    for (id, cx, cy) in candidates {
        if exclude_id == Some(id) {
            continue;
        }
        let tx = cx - origin_x;
        let ty = cy - origin_y;
        let dist = tx.hypot(ty);
        if dist <= 0.0 {
            continue;
        }
        let dot = (tx / dist) * mx + (ty / dist) * my;
        if dot > best_score && dot >= direction_cone_dot {
            best_score = dot;
            best_id = Some(id);
        }
    }
    best_id
}
