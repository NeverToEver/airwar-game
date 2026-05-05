use pyo3::prelude::*;
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
/// Input: (x, y, vx, vy, life, max_life, size, dt) for each particle
/// Output: (x, y, vx, vy, life, size, is_alive) for each particle (Python filters dead)
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
/// Returns list of (x, y, vx, vy, life, max_life, size)
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_batch_update_particles() {
        let particles = vec![
            (0.0, 0.0, 1.0, 1.0, 30, 30, 3.0),
            (10.0, 10.0, 1.0, 1.0, 1, 30, 3.0), // Will die
            (20.0, 20.0, 1.0, 1.0, 30, 30, 3.0),
        ];
        let results = batch_update_particles(particles, 1.0);
        // Now returns all 3 particles with is_alive flag, Python filters
        assert_eq!(results.len(), 3);
        // Count alive particles
        let alive_count = results.iter().filter(|r| r.6).count(); // is_alive is last element
        assert_eq!(alive_count, 2);
    }

    #[test]
    fn test_generate_explosion_particles() {
        let particles = generate_explosion_particles(100.0, 200.0, 30, 20, 40, 3.0, 8.0, 2.0, 5.0);
        assert_eq!(particles.len(), 30);
        // All particles should be centered on (100, 200)
        for (x, y, _, _, life, max_life, size) in &particles {
            assert!((*x - 100.0).abs() < 0.1);
            assert!((*y - 200.0).abs() < 0.1);
            assert!(*life >= 20 && *life <= 40);
            assert_eq!(*life, *max_life);
            assert!(*size >= 2.0 && *size <= 5.0);
        }
    }
}
