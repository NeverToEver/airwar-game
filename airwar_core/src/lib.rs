use pyo3::prelude::*;

pub mod vector2;
pub mod collision;
pub mod movement;
pub mod particles;
pub mod sprites;

#[pymodule]
fn airwar_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Vector2 functions
    m.add_function(wrap_pyfunction!(vector2::vec2_length, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_normalize, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_add, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_sub, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_dot, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_cross, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_scale, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_distance, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_length_squared, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_distance_squared, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_angle, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_from_angle, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_lerp, m)?)?;
    m.add_function(wrap_pyfunction!(vector2::vec2_clamp_length, m)?)?;

    // Collision functions
    m.add_function(wrap_pyfunction!(collision::spatial_hash_collide, m)?)?;
    m.add_function(wrap_pyfunction!(collision::spatial_hash_collide_single, m)?)?;

    // Movement functions
    m.add_function(wrap_pyfunction!(movement::update_movement, m)?)?;

    // Particle functions
    m.add_function(wrap_pyfunction!(particles::update_particle, m)?)?;
    m.add_function(wrap_pyfunction!(particles::batch_update_particles, m)?)?;
    m.add_function(wrap_pyfunction!(particles::generate_explosion_particles, m)?)?;

    // Sprite functions
    m.add_function(wrap_pyfunction!(sprites::create_single_bullet_glow, m)?)?;
    m.add_function(wrap_pyfunction!(sprites::create_spread_bullet_glow, m)?)?;
    m.add_function(wrap_pyfunction!(sprites::create_laser_bullet_glow, m)?)?;
    m.add_function(wrap_pyfunction!(sprites::create_explosive_missile_glow, m)?)?;
    m.add_function(wrap_pyfunction!(sprites::create_glow_circle, m)?)?;

    Ok(())
}
