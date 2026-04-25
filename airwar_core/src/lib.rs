use pyo3::prelude::*;

pub mod vector2;
pub mod collision;
pub mod movement;

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
    Ok(())
}