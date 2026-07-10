use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::cell::Cell;
use std::time::{SystemTime, UNIX_EPOCH};

/// Particle state for batch updates
#[derive(Debug, Clone)]
pub struct Particle {
    pub x: f32,
    pub y: f32,
    pub vx: f32,
    pub vy: f32,
    pub life: i32,
    pub max_life: i32,
    pub size: f32,
}

impl Particle {
    pub fn update(&mut self, dt: f32) {
        self.x += self.vx * dt;
        self.y += self.vy * dt;
        self.vx *= 0.98;
        self.vy *= 0.98;
        self.life -= 1;
    }

    pub fn is_alive(&self) -> bool {
        self.life > 0
    }

    pub fn get_alpha(&self) -> f32 {
        self.life as f32 / self.max_life as f32
    }
}

/// Batch update particles - takes arrays of particle data and returns updated data
/// Input: (x, y, vx, vy, life, `max_life`, size, dt) for each particle
/// Output: (x, y, vx, vy, life, size, `is_alive`) for each particle (Python filters dead)
#[pyfunction]
pub fn batch_update_particles(
    particles: Vec<(f32, f32, f32, f32, i32, i32, f32)>,
    dt: f32,
) -> Vec<(f32, f32, f32, f32, i32, f32, bool)> {
    let mut results = Vec::with_capacity(particles.len());

    for (x, y, vx, vy, life, _max_life, size) in particles {
        let nx = x + vx * dt;
        let ny = y + vy * dt;
        let nvx = vx * 0.98;
        let nvy = vy * 0.98;
        let nlife = life - 1;
        let is_alive = nlife > 0;

        results.push((nx, ny, nvx, nvy, nlife, size, is_alive));
    }

    results
}

/// Generate explosion particles
/// Returns list of (x, y, vx, vy, life, `max_life`, size)
#[pyfunction]
#[allow(clippy::too_many_arguments)]
pub fn generate_explosion_particles(
    center_x: f32,
    center_y: f32,
    particle_count: i32,
    life_min: i32,
    life_max: i32,
    speed_min: f32,
    speed_max: f32,
    size_min: f32,
    size_max: f32,
) -> Vec<(f32, f32, f32, f32, i32, i32, f32)> {
    let mut particles = Vec::with_capacity(particle_count as usize);
    let pi2 = std::f32::consts::PI * 2.0;

    for _ in 0..particle_count {
        let angle = fast_rand() * pi2;
        let speed = speed_min + fast_rand() * (speed_max - speed_min);
        let life = life_min + ((fast_rand() * (life_max - life_min) as f32) as i32);
        let size = size_min + fast_rand() * (size_max - size_min);

        let vx = angle.cos() * speed;
        let vy = angle.sin() * speed;

        particles.push((center_x, center_y, vx, vy, life, life, size));
    }

    particles
}

/// Particle render data: (x, y, size, glow_radius, alpha, r, g, b)
type ParticleRenderData = (f32, f32, f32, f32, f32, u8, u8, u8);

/// Batch render particles into a single RGBA buffer.
///
/// Each particle is rendered as a filled glow circle with additive blending.
/// Returns raw RGBA pixel buffer of `screen_width * screen_height * 4` bytes.
#[pyfunction]
pub fn batch_render_particles(py: Python<'_>, particles: Vec<ParticleRenderData>, screen_width: i32, screen_height: i32) -> Bound<'_, PyBytes> {
    let width = screen_width as usize;
    let height = screen_height as usize;
    let mut buf = vec![0u8; width * height * 4];

    for (px, py, size, glow_radius, alpha, red, green, blue) in particles {
        let center_x = px as i32;
        let center_y = py as i32;
        let total_radius = (size + glow_radius) as i32;
        let alpha_f = alpha.clamp(0.0, 1.0);

        for dy in -total_radius..=total_radius {
            for dx in -total_radius..=total_radius {
                let pixel_x = center_x + dx;
                let pixel_y = center_y + dy;
                if pixel_x < 0 || pixel_x >= screen_width || pixel_y < 0 || pixel_y >= screen_height {
                    continue;
                }

                let dist = ((dx * dx + dy * dy) as f32).sqrt();
                let a = if dist <= size {
                    // Core: full alpha
                    alpha_f
                } else if dist <= size + glow_radius {
                    // Glow: fade out
                    let t = 1.0 - (dist - size) / glow_radius;
                    alpha_f * t * t // quadratic falloff
                } else {
                    continue;
                };

                if a < 0.01 {
                    continue;
                }

                let idx = (pixel_y as usize * width + pixel_x as usize) * 4;
                // Additive blending
                let sa = (a * 255.0) as u16;
                let sr = u16::from(red) * sa / 255;
                let sg = u16::from(green) * sa / 255;
                let sb = u16::from(blue) * sa / 255;

                let dr = u16::from(buf[idx]) + sr;
                let dg = u16::from(buf[idx + 1]) + sg;
                let db = u16::from(buf[idx + 2]) + sb;
                let da = u16::from(buf[idx + 3]) + sa;

                buf[idx] = dr.min(255) as u8;
                buf[idx + 1] = dg.min(255) as u8;
                buf[idx + 2] = db.min(255) as u8;
                buf[idx + 3] = da.min(255) as u8;
            }
        }
    }

    PyBytes::new_bound(py, &buf)
}

thread_local! {
    static PARTICLE_RNG_STATE: Cell<u64> = Cell::new(initial_rng_seed());
}

fn initial_rng_seed() -> u64 {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system clock must be after UNIX_EPOCH for particle RNG seed")
        .as_nanos() as u64;
    nanos ^ 0x9E37_79B9_7F4A_7C15
}

/// Fast deterministic PRNG for particle generation.
fn fast_rand() -> f32 {
    PARTICLE_RNG_STATE.with(|state| {
        let mut value = state.get();
        value ^= value << 13;
        value ^= value >> 7;
        value ^= value << 17;
        state.set(value);
        (value as f64 / u64::MAX as f64) as f32
    })
}
