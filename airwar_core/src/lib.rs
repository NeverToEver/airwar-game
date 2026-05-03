use pyo3::prelude::*;

pub mod bullets;
pub mod collision;
pub mod movement;
pub mod particles;
pub mod sprites;
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
    m.add_function(wrap_pyfunction!(
        collision::batch_collide_bullets_vs_entities,
        m
    )?)?;

    // Persistent spatial hash
    m.add_class::<collision::PersistentSpatialHash>()?;

    // Movement functions
    m.add_function(wrap_pyfunction!(movement::update_movement, m)?)?;
    m.add_function(wrap_pyfunction!(movement::batch_update_movements, m)?)?;
    m.add_function(wrap_pyfunction!(movement::compute_boss_attack, m)?)?;

    // Particle functions
    m.add_function(wrap_pyfunction!(particles::batch_update_particles, m)?)?;
    m.add_function(wrap_pyfunction!(
        particles::generate_explosion_particles,
        m
    )?)?;

    // Sprite functions
    m.add_function(wrap_pyfunction!(sprites::create_single_bullet_glow, m)?)?;
    m.add_function(wrap_pyfunction!(sprites::create_spread_bullet_glow, m)?)?;
    m.add_function(wrap_pyfunction!(sprites::create_laser_bullet_glow, m)?)?;
    m.add_function(wrap_pyfunction!(sprites::create_explosive_missile_glow, m)?)?;
    m.add_function(wrap_pyfunction!(sprites::create_glow_circle, m)?)?;

    // Bullet functions
    m.add_function(wrap_pyfunction!(bullets::batch_update_bullets, m)?)?;

    Ok(())
}
