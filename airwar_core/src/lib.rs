// Allow the 4 pedantic lints that surface in unit tests. These are
// legitimate: float_cmp asserts deterministic Rust-side computations
// (vec2_add returns exactly (4.0, 6.0) when fed (1.0, 2.0, 3.0, 4.0)),
// the format/closure warnings are style-only, and
// redundant_closure_for_method_calls flags `|x| x.sin()` in starfield.
// P3-5 ROADMAP §6 — keep `cargo clippy --all-targets -- -D warnings` clean.
#![allow(
    clippy::float_cmp,
    clippy::uninlined_format_args,
    clippy::redundant_closure,
    clippy::redundant_closure_for_method_calls
)]

use pyo3::prelude::*;

pub mod bullets;
pub mod collision;
pub mod movement;
pub mod particles;
pub mod sprites;
pub mod starfield;
pub mod vector2;

#[pymodule]
fn airwar_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Vector2 functions
    m.add_function(wrap_pyfunction!(vector2::vec2_length, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_normalize, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_add, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_sub, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_dot, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_scale, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_distance, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_angle, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_from_angle, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_lerp, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_clamp_length, m)?)?;

    // Collision functions
    m.add_function(wrap_pyfunction!(collision::batch_collide_bullets_vs_entities, m)?)?;

    // Movement functions
    m.add_function(wrap_pyfunction!(movement::update_movement, m)?)?;
    m.add_function(wrap_pyfunction!(movement::batch_update_movements, m)?)?;
    m.add_function(wrap_pyfunction!(movement::batch_update_movements_buf, m)?)?;
    m.add_function(wrap_pyfunction!(movement::compute_boss_attack, m)?)?;
    m.add_function(wrap_pyfunction!(movement::batch_hallucinated_enemy_centers, m)?)?;
    m.add_function(wrap_pyfunction!(movement::find_nearest_target, m)?)?;
    m.add_function(wrap_pyfunction!(movement::find_target_in_direction, m)?)?;

    // Particle functions
    m.add_function(wrap_pyfunction!(particles::batch_update_particles, m)?)?;
    m.add_function(wrap_pyfunction!(particles::generate_explosion_particles, m)?)?;
    m.add_function(wrap_pyfunction!(particles::batch_render_particles, m)?)?;

    // Sprite functions
    m.add_function(wrap_pyfunction!(sprites::create_single_bullet_glow, m)?)?;
    m.add_function(wrap_pyfunction!(sprites::create_spread_bullet_glow, m)?)?;
    m.add_function(wrap_pyfunction!(sprites::create_laser_bullet_glow, m)?)?;
    m.add_function(wrap_pyfunction!(sprites::create_explosive_missile_glow, m)?)?;
    m.add_function(wrap_pyfunction!(sprites::create_glow_circle, m)?)?;

    // Starfield functions
    m.add_function(wrap_pyfunction!(starfield::compute_starfield_positions, m)?)?;

    // Bullet functions
    m.add_function(wrap_pyfunction!(bullets::batch_update_bullets, m)?)?;
    m.add_function(wrap_pyfunction!(bullets::batch_update_bullets_buf, m)?)?;

    Ok(())
}
